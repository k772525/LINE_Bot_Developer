# app/routes/scheduler_api.py
# Cloud Scheduler 調用的 API 端點

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import os

scheduler_api = Blueprint('scheduler_api', __name__)

@scheduler_api.route('/api/check-reminders', methods=['POST'])
def check_reminders_endpoint():
    """
    提醒檢查端點，由 Google Cloud Scheduler 每分鐘調用
    """
    try:
        # 驗證請求來源（增加安全性）
        auth_header = request.headers.get('Authorization')
        expected_token = f"Bearer {os.environ.get('REMINDER_SECRET_TOKEN', 'default-secret')}"
        
        if auth_header != expected_token:
            current_app.logger.warning(f"未授權的提醒檢查請求: {request.remote_addr}")
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 執行提醒檢查邏輯
        from app.services.reminder_service import check_and_send_reminders
        
        current_app.logger.info("開始執行排程提醒檢查...")
        check_and_send_reminders(current_app)
        
        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'message': 'Reminders checked successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"提醒檢查失敗: {str(e)}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@scheduler_api.route('/api/health-detailed', methods=['GET'])
def health_check_detailed():
    """
    詳細的健康檢查端點，包含資料庫連線狀態
    """
    try:
        from app.utils.db import get_db_connection
        
        # 檢查資料庫連線
        db_status = 'unknown'
        try:
            db = get_db_connection()
            if db:
                with db.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                db_status = 'connected'
        except Exception as db_e:
            db_status = f'failed: {str(db_e)}'
        
        # 檢查環境變數
        required_env_vars = [
            'LINE_CHANNEL_ACCESS_TOKEN',
            'LINE_CHANNEL_SECRET', 
            'DB_HOST',
            'DB_USER',
            'DB_PASS',
            'DB_NAME'
        ]
        
        env_status = {}
        for var in required_env_vars:
            env_status[var] = 'set' if os.environ.get(var) else 'missing'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'environment': env_status,
            'is_cloud_run': os.environ.get('K_SERVICE') is not None,
            'version': '1.0.0'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@scheduler_api.route('/api/test-reminder', methods=['POST'])
def test_reminder():
    """
    測試提醒功能的端點
    """
    try:
        # 僅允許在開發環境或有特殊權限時使用
        if os.environ.get('FLASK_ENV') != 'development':
            auth_header = request.headers.get('Authorization')
            expected_token = f"Bearer {os.environ.get('REMINDER_SECRET_TOKEN', 'default-secret')}"
            if auth_header != expected_token:
                return jsonify({'error': 'Unauthorized'}), 401
        
        from app.utils.db import DB
        from app.services.reminder_service import send_reminder_logic
        from app import line_bot_api
        
        # 獲取當前時間的提醒（使用台北時區）
        import pytz
        taipei_tz = pytz.timezone('Asia/Taipei')
        current_time_taipei = datetime.now(taipei_tz)
        current_time_str = current_time_taipei.strftime("%H:%M")
        
        print(f"當前台北時間: {current_time_str}")
        print(f"當前UTC時間: {datetime.utcnow().strftime('%H:%M')}")
        
        reminders = DB.get_reminders_for_scheduler(current_time_str)
        
        result = {
            'current_time': current_time_str,
            'reminders_found': len(reminders),
            'reminders': []
        }
        
        for reminder in reminders:
            try:
                send_reminder_logic(reminder, current_time_str, line_bot_api)
                result['reminders'].append({
                    'id': reminder.get('id'),
                    'member': reminder.get('member'),
                    'drug_name': reminder.get('drug_name'),
                    'status': 'sent'
                })
            except Exception as e:
                result['reminders'].append({
                    'id': reminder.get('id'),
                    'member': reminder.get('member'),
                    'drug_name': reminder.get('drug_name'),
                    'status': f'failed: {str(e)}'
                })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500