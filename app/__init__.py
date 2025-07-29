# app/__init__.py

import os
import json
from decimal import Decimal
from datetime import datetime, date
from flask import Flask
from linebot import LineBotApi, WebhookHandler

# 匯入我們自己建立的模組
from config import Config
from .utils.db import init_app as init_db

# 為了讓 Flask 能夠找到我們的藍圖，需要在這裡宣告
line_bot_api = None
handler = None

class CustomJSONEncoder(json.JSONEncoder):
    """自訂的 JSON 編碼器，用來處理 datetime 和 Decimal 型別。"""
    def default(self, obj):
        if isinstance(obj, datetime):
            # 保持完整的日期時間格式，包含時間資訊
            return obj.isoformat()
        elif isinstance(obj, date):
            # 只有日期的情況才只返回日期部分
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def create_app(config_class_string):
    """
    應用程式工廠函式。
    
    Args:
        config_class_string (str): 設定類別的路徑字串，例如 'config.Config'。
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # 1. 載入設定
    app.config.from_object(config_class_string)
    
    # 2. 驗證設定
    # 直接呼叫 Config 類上的靜態方法
    Config.validate_config()

    # 3. 設置自訂的 JSON Encoder
    app.json_encoder = CustomJSONEncoder
    
    # 4. 初始化 LINE Bot SDK
    # 這裡我們需要全域宣告，以便藍圖可以匯入並使用它們
    global line_bot_api, handler
    line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
    handler = WebhookHandler(app.config['LINE_CHANNEL_SECRET'])
    
    # 5. 初始化資料庫
    init_db(app)

    # 6. 註冊藍圖 (Blueprints)
    # 我們在這裡匯入並註冊藍圖，避免循環匯入問題
    from .routes.line_webhook import webhook_bp
    from .routes.liff_views import liff_bp
    from .routes.auth import auth_bp
    from .routes.scheduler_api import scheduler_api
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(liff_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(scheduler_api)

    # 建立必要的資料夾 (如果不存在)
    # 這裡假設您的 `app.py` 中的 uploads 資料夾是需要的
    uploads_path = os.path.join(app.static_folder, 'uploads')
    os.makedirs(uploads_path, exist_ok=True)
    
    print("Flask App 建立成功，並已註冊所有藍圖。")
    
    return app