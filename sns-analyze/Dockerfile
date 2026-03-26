FROM python:3.12-slim

# Node.jsをインストール
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# フロントエンドをビルド
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

# Pythonの依存パッケージをインストール
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# バックエンドをコピー
COPY backend/ ./backend/

WORKDIR /app/backend

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
