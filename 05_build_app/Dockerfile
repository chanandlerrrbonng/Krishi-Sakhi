# Ask-It Streamlit chat UI
# Build from ask-it/ (not this folder):
#   docker build -f 05_build_app/Dockerfile -t ask-it-chat:latest .
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 05_build_app/rag_client.py 05_build_app/chat_app.py ./

EXPOSE 8501

CMD ["streamlit", "run", "chat_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
