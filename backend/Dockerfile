FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from transformers import pipeline; pipeline('text-classification', model='eevvgg/StanceBERTa')"
# Expose Flask port
EXPOSE 5000

# Run Flask in dev mode with auto-reload
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"]
