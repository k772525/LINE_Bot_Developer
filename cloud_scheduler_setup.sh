#!/bin/bash
# Google Cloud Scheduler 設定腳本
# 用於設定每分鐘調用提醒檢查的排程任務

# 設定變數
PROJECT_ID="gcp1-462701"
REGION="us-central1"
SERVICE_URL="https://your-cloud-run-service-url.run.app"
SECRET_TOKEN="your-secure-random-token-here"

echo "🚀 開始設定 Google Cloud Scheduler..."

# 1. 啟用必要的 API
echo "📡 啟用 Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com

# 2. 創建 App Engine 應用（Cloud Scheduler 需要）
echo "🏗️  檢查 App Engine 應用..."
gcloud app describe --project=$PROJECT_ID 2>/dev/null || {
    echo "創建 App Engine 應用..."
    gcloud app create --region=$REGION --project=$PROJECT_ID
}

# 3. 創建提醒檢查的排程任務
echo "⏰ 創建提醒檢查排程任務..."
gcloud scheduler jobs create http reminder-check-job \
    --project=$PROJECT_ID \
    --location=$REGION \
    --schedule="* * * * *" \
    --uri="$SERVICE_URL/api/check-reminders" \
    --http-method=POST \
    --headers="Content-Type=application/json,Authorization=Bearer $SECRET_TOKEN" \
    --description="每分鐘檢查並發送用藥提醒" \
    --time-zone="Asia/Taipei"

echo "✅ Cloud Scheduler 設定完成！"
echo ""
echo "📋 接下來的步驟："
echo "1. 更新您的 Cloud Run 服務環境變數，添加 REMINDER_SECRET_TOKEN"
echo "2. 確保您的 Cloud Run 服務 URL 正確"
echo "3. 測試排程任務："
echo "   gcloud scheduler jobs run reminder-check-job --location=$REGION"
echo ""
echo "🔍 監控排程任務："
echo "   gcloud scheduler jobs describe reminder-check-job --location=$REGION"
echo "   gcloud logging read 'resource.type=\"cloud_scheduler_job\"' --limit=10"