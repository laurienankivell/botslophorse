from flask import Flask, jsonify
import os, re, json
import praw
import torch
import sqlite3
import pandas as pd
import logging

from datetime import datetime, timedelta
from transformers import pipeline
from flask_cors import CORS

logging.basicConfig( level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",)

app = Flask(__name__)
CORS(app)

# --- Database Setup ---
DB_FILE = "comments.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT UNIQUE,
            label TEXT,
            score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Reddit Auth ---
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="ReformUK_astroturf_study_v1"
)

search_terms = ["Reform UK", "Nigel Farage", "migration crisis", "illegal immigrants", "stop the boats", "migrant invasion"]
subreddits = "ukpolitics+unitedkingdom+uknews+britishproblems+AskUK+London+bbcnews+BritishPolitics+Scotland+tories+reformUK"

migration_pattern = r"\b(?:migrant|migration|asylum|refugee|illegals|invasion|boats|border|farage|reform)\b"

stance_classifier = None

def get_classifier():
    global stance_classifier
    if stance_classifier is None:
        logging.info("Initializing stance classifier...")
        try:
            device = 0 if torch.cuda.is_available() else -1
            stance_classifier = pipeline(
                "text-classification",
                model="eevvgg/StanceBERTa",
                device=device,
                truncation=True
            )
            logging.info("Classifier loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load classifier: {e}")
            return None
    return stance_classifier


def clean_text(text):
    text = re.sub(r"http\S+|www\S+|https\S+", "", str(text))
    text = re.sub(r"[^A-Za-z0-9\s]", "", text)
    return text.lower()

device = 0 if torch.cuda.is_available() else -1

# --- API Endpoints ---
@app.route("/scrape", methods=["GET"])
def scrape():
    logging.info("=== Starting scrape request ===")
    a_week_ago = datetime.now() - timedelta(days=7)
    logging.info(f"Looking for posts newer than {a_week_ago}")

    posts = []
    for term in search_terms:
        logging.info(f"Searching for term: {term}")
        for submission in reddit.subreddit(subreddits).search(term, limit=15):
            created = datetime.fromtimestamp(submission.created_utc)
            logging.debug(f"Found submission {submission.id} created at {created}")
            if created >= a_week_ago:
                posts.append(submission.id)
    logging.info(f"Collected {len(posts)} posts matching search terms")

    comments = []
    for submission_id in posts:
        logging.info(f"Fetching comments for post {submission_id}")
        submission_obj = reddit.submission(id=submission_id)
        submission_obj.comments.replace_more(limit=0)
        for comment in submission_obj.comments.list():
            created = datetime.fromtimestamp(comment.created_utc)
            if created >= a_week_ago:
                comments.append(comment.body)
    logging.info(f"Collected {len(comments)} raw comments")

    df_comments = pd.DataFrame(comments, columns=["comment_body"])
    logging.info("Cleaning comment text")
    df_comments["clean_text_comment"] = df_comments["comment_body"].apply(clean_text)

    df_mig2 = df_comments[
        df_comments["clean_text_comment"].str.contains(migration_pattern, regex=True, na=False)
    ]
    logging.info(f"{len(df_mig2)} comments matched migration keywords")

    if df_mig2.empty:
        logging.info("No relevant comments found after filtering")
        return jsonify({"message": "No relevant comments found."})

    logging.info("Loading stance classifier")
    classifier = get_classifier()
    if classifier is None:
        return jsonify({"error": "Classifier not available"}), 500

    results = classifier(df_mig2["clean_text_comment"].tolist(), batch_size=16)

    logging.info(f"Classifying {len(df_mig2)} comments")
    results = classifier(df_mig2["clean_text_comment"].tolist(), batch_size=16)

    df_mig2["label"] = [r["label"] for r in results]
    df_mig2["score"] = [r["score"] for r in results]
    logging.info("Classification complete")

    df_final = df_mig2[(df_mig2["label"] == "negative") & (df_mig2["score"] >= 0.70)]
    logging.info(f"{len(df_final)} comments classified as negative with score >= 0.70")

    logging.info("Inserting data into DB")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for _, row in df_final.iterrows():
        try:
            c.execute(
                "INSERT INTO comments (text, label, score) VALUES (?, ?, ?)",
                (row["comment_body"], row["label"], row["score"]),
            )
            logging.debug(f"Inserted comment: {row['comment_body'][:80]}...")
        except sqlite3.IntegrityError:
            logging.debug("Duplicate comment skipped")
    conn.commit()
    conn.close()
    logging.info("DB insert complete")

    logging.info("=== Scrape request finished ===")
    return jsonify({"message": f"Processed {len(df_mig2)} comments. Added {len(df_final)} anti-migrant ones."})


@app.route("/health", methods=["GET"])
def health_check():
    try:
        # Try a quick DB connection
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "ok", "database": "reachable"}), 200
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

@app.route("/data", methods=["GET"])
def get_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT text, label, score, created_at FROM comments ORDER BY created_at DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()

    data = [{"text": r[0], "label": r[1], "score": r[2], "created_at": r[3]} for r in rows]
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)