import os
import praw
import pandas as pd
import re
import json
import torch
from datetime import datetime, timedelta
from transformers import pipeline
# Using standard tqdm for the cloud logs instead of notebook version
from tqdm import tqdm 

# --- STEP 1: AUTHENTICATION (Using Secrets) ---
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="ReformUK_astroturf_study_v1"
)

# --- STEP 2: YOUR ORIGINAL SEARCH TERMS ---
search_terms = [
    "Reform UK", "Nigel Farage", "migration crisis", 
    "illegal immigrants", "British sovereignty", 
    "take back control", "stop the boats", "migrant invasion", 
    "great replacement", "Brexit betrayal"
]

subreddits = "ukpolitics+unitedkingdom+uknews+britishproblems+AskUK+London+bbcnews+BritishPolitics+Scotland+MHoCConservatives+tories+reformUK"

# --- STEP 3: COLLECTION & CLEANING (Your Logic) ---
# Changed this line to 1 week
a_week_ago = datetime.now() - timedelta(days=7)
posts = [] # <--- FIXED: Added this so the list exists before the loop starts

for term in search_terms:
    for submission in reddit.subreddit(subreddits).search(term, limit=10):
        if datetime.fromtimestamp(submission.created_utc) >= a_week_ago:
            posts.append({
                "id": submission.id,
                "title": submission.title,
                "selftext": submission.selftext,
                "subreddit": str(submission.subreddit)
            })

df_posts = pd.DataFrame(posts).drop_duplicates(subset='id')

comments = []
for submission_id in df_posts["id"]:
    submission_obj = reddit.submission(id=submission_id)
    submission_obj.comments.replace_more(limit=0)
    for comment in submission_obj.comments.list():
        # Only keep if comment made in last week
        if datetime.fromtimestamp(comment.created_utc) >= a_week_ago:
            comments.append({
                "comment_body": comment.body,
                "created_utc": comment.created_utc
            })


df_comments = pd.DataFrame(comments)

# --- STEP 4: YOUR ORIGINAL FILTERS (UK & MIGRATION) ---
uk_keywords = [r"\bUK\b", r"\bBritain\b", r"\bBritish\b", r"\bNigel Farage\b", r"\bReform UK\b", r"\bStop the Boats\b"]
migration_pattern = r"\b(?:migrant|migration|asylum|refugee|illegals|invasion)\b"

def clean_text(text):
    text = re.sub(r"http\S+|www\S+|https\S+", "", str(text))
    text = re.sub(r"[^A-Za-z0-9\s]", "", text)
    return text.lower()

def is_uk_relevant(text):
    return any(re.search(pattern, str(text), flags=re.IGNORECASE) for pattern in uk_keywords)

df_comments["clean_text_comment"] = df_comments["comment_body"].apply(clean_text)
df_mig2 = df_comments[
    (df_comments["comment_body"].apply(is_uk_relevant)) & 
    (df_comments["clean_text_comment"].str.contains(migration_pattern, regex=True, na=False))
].copy()

# --- STEP 5: YOUR STANCEBERTA LOGIC ---
device = 0 if torch.cuda.is_available() else -1
stance_classifier = pipeline("text-classification", model="eevvgg/StanceBERTa", device=device, truncation=True)

if not df_mig2.empty:
    # Running your batch logic
    raw_results = []
    # Note: using standard tqdm for cloud logs
    for result in tqdm(stance_classifier(df_mig2['clean_text_comment'].tolist(), batch_size=32), total=len(df_mig2)):
        raw_results.append(result)

    df_mig2['label'] = [r['label'] for r in raw_results]
    df_mig2['score'] = [r['score'] for r in raw_results]

    # Your 0.75 Threshold
    df_final = df_mig2[(df_mig2['label'] == 'negative') & (df_mig2['score'] >= 0.75)]
    
    # --- STEP 6: OUTPUT FOR THE WEBSITE ---
    new_entries = df_final[['comment_body']].rename(columns={'comment_body': 'text'}).to_dict(orient='records')
    
    file_path = 'live_horse_data.json'
    try:
        with open(file_path, 'r') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = []

    # Merge new data and keep only latest 100 unique comments
    seen = {item['text'] for item in existing_data}
    for item in new_entries:
        if item['text'] not in seen:
            existing_data.insert(0, item)
            seen.add(item['text'])

    with open(file_path, 'w') as f:
        json.dump(existing_data[:100], f, indent=4)

print(f"✅ Processed {len(df_mig2)} comments. Added {len(new_entries)} anti-migrant ones to the horse.")
