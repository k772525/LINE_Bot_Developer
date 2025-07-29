# config.py (最終修正版)

import os

class Config:
    """應用程式組態設定。"""
    
    # --- LINE Bot API 設定 ---
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
    YOUR_BOT_ID = os.environ.get('YOUR_BOT_ID')
    
    # --- LIFF 應用程式設定 ---
    LIFF_CHANNEL_ID = os.environ.get('LIFF_CHANNEL_ID')
    
    # 藥單分析流程的 LIFF
    LIFF_ID_CAMERA = os.environ.get('LIFF_ID_CAMERA')
    LIFF_ID_EDIT = os.environ.get('LIFF_ID_EDIT')
    
    # 提醒管理流程的 LIFF (使用您定義的清晰名稱)
    LIFF_ID_PRESCRIPTION_REMINDER = os.environ.get('LIFF_ID_PRESCRIPTION_REMINDER')
    LIFF_ID_MANUAL_REMINDER = os.environ.get('LIFF_ID_MANUAL_REMINDER')
    
    # 健康記錄的 LIFF
    LIFF_ID_HEALTH_FORM = os.environ.get('LIFF_ID_HEALTH_FORM')
    
    # --- LINE Login 設定 ---
    LINE_LOGIN_CHANNEL_ID = os.environ.get('LINE_LOGIN_CHANNEL_ID')
    LINE_LOGIN_CHANNEL_SECRET = os.environ.get('LINE_LOGIN_CHANNEL_SECRET')
    
    # --- Flask Session 設定 ---
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
    
    # --- Google Gemini API 設定 ---
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    # --- Google Speech-to-Text API 設定 ---
    # Google Speech-to-Text 使用相同的服務帳戶憑證
    GOOGLE_APPLICATION_CREDENTIALS ='cji25.json'
    SPEECH_TO_TEXT_ENABLED = os.environ.get('SPEECH_TO_TEXT_ENABLED', 'true').lower() == 'true'
    SPEECH_LANGUAGE_CODE = os.environ.get('SPEECH_LANGUAGE_CODE', 'zh-TW')
    
    
    # --- 药丸辨识 API 設定 ---
    PILL_API_URLS = [
        "https://line-bot-712800774423.us-central1.run.app",
        "https://line-bot2-712800774423.us-central1.run.app", 
        "https://detect-api-self.wenalyzer.xyz/detect"
    ]
    
    # --- MySQL 資料庫設定 ---
    DB_HOST = os.environ.get('DB_HOST')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASS')
    DB_NAME = os.environ.get('DB_NAME')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))

    @staticmethod
    def validate_config():
        """檢查所有必要的環境變數是否都已設定。"""
        # 包含了所有14個必要變數的完整列表
        required_vars = [
            'LINE_CHANNEL_ACCESS_TOKEN', 'LINE_CHANNEL_SECRET', 'LIFF_CHANNEL_ID', 'YOUR_BOT_ID',
            'LIFF_ID_CAMERA', 'LIFF_ID_EDIT', 'LIFF_ID_PRESCRIPTION_REMINDER', 'LIFF_ID_MANUAL_REMINDER', 'LIFF_ID_HEALTH_FORM',
            'LINE_LOGIN_CHANNEL_ID', 'LINE_LOGIN_CHANNEL_SECRET',
            'GEMINI_API_KEY',
            'DB_HOST', 'DB_USER', 'DB_PASS', 'DB_NAME', 'DB_PORT'
        ]
        
        # SECRET_KEY 是可選的，如果沒有設定會使用預設值
        optional_vars = ['SECRET_KEY']
        
        # 創建環境變數到 Config 屬性的映射
        env_to_config_map = {
            'DB_PASS': 'DB_PASSWORD'  # DB_PASS 環境變數對應 DB_PASSWORD 屬性
        }
        
        missing_vars = []
        for var in required_vars:
            # 獲取對應的 Config 屬性名稱
            config_attr = env_to_config_map.get(var, var)
            if not getattr(Config, config_attr, None):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f".env 檔案缺少必要的設定: {', '.join(missing_vars)}")