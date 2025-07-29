# 使用輕量級的 Python 映像檔
FROM python:3.11-slim

# 設定環境變數，避免產生 .pyc 檔案
ENV PYTHONDONTWRITEBYTECODE 1
# 確保 Python 輸出是即時的，方便在 Cloud Run 中查看日誌
ENV PYTHONUNBUFFERED 1

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    # 如果你使用 psycopg2-binary，則 libpq-dev 不是必需的
    libpq-dev \
    # 添加 FFmpeg 支援語音處理
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有專案檔案到工作目錄
# ！！！重要安全提醒！！！
# 請確保你的服務帳戶金鑰 .json 檔案【不】在此目錄中，不要將金鑰複製到映像檔裡。
COPY . .

# 設定環境變數
# Cloud Run 會自動處理驗證，不需要 GOOGLE_APPLICATION_CREDENTIALS
ENV PORT=8080
ENV PYTHONPATH="/app"

# 向外部暴露容器的 8080 port
EXPOSE 8080

# --- 核心修正 ---
# 啟動 Gunicorn，並告訴它從 run.py 檔案中尋找名為 app 的變數
# 同時設定一個合理的超時時間 (例如 300 秒)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 300 run:app
