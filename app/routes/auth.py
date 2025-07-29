# app/routes/auth.py

import uuid
import requests
from flask import Blueprint, request, redirect, session, current_app, jsonify
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from config import Config

auth_bp = Blueprint('auth', __name__)
@auth_bp.route("/login")
def login():
    try:
        state = uuid.uuid4().hex
        session['state'] = state
        
        # 處理不同環境的 URL 構建
        base_url = request.url_root
        
        # 處理 ngrok 的 http -> https 轉換
        if 'ngrok' in base_url and base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        
        # 處理 Cloud Run 的 URL（確保使用 https）
        if 'run.app' in base_url and base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        
        # 移除末尾的斜線並構建 redirect_uri
        base_url = base_url.rstrip('/')
        redirect_uri = f"{base_url}/auth/callback"
        auth_url = (f"https://access.line.me/oauth2/v2.1/authorize?"
                    f"response_type=code&client_id={Config.LINE_LOGIN_CHANNEL_ID}&"
                    f"redirect_uri={redirect_uri}&state={state}&scope=profile%20openid")
        
        current_app.logger.info(f"=== LOGIN START ===")
        current_app.logger.info(f"State: {state}")
        current_app.logger.info(f"Redirect URI: {redirect_uri}")
        current_app.logger.info(f"Auth URL: {auth_url}")
        current_app.logger.info(f"==================")
        
        return redirect(auth_url)
    except Exception as e:
        current_app.logger.error(f"Login error: {e}", exc_info=True)
        return "登入服務暫時無法使用", 500

@auth_bp.route("/callback")
def auth_callback():
    try:
        code = request.args.get('code')
        state_from_line = request.args.get('state')
        state_from_session = session.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        
        current_app.logger.info(f"=== CALLBACK START ===")
        current_app.logger.info(f"Code: {code}")
        current_app.logger.info(f"State from LINE: {state_from_line}")
        current_app.logger.info(f"State from session: {state_from_session}")
        current_app.logger.info(f"Error: {error}")
        current_app.logger.info(f"Error description: {error_description}")
        current_app.logger.info(f"All request args: {dict(request.args)}")
        current_app.logger.info(f"=====================")
        
        # 檢查是否有錯誤
        if error:
            current_app.logger.error(f"LINE Login error: {error} - {error_description}")
            return f"授權失敗：{error_description or error}", 400
            
        # 檢查必要參數
        if not code:
            current_app.logger.error("Missing authorization code")
            return "授權失敗：缺少授權碼", 400
            
        # 檢查 state
        if not state_from_line or not state_from_session or state_from_line != state_from_session:
            current_app.logger.error(f"State mismatch: LINE={state_from_line}, Session={state_from_session}")
            return "授權失敗：state 不符，請重試。", 400
        
        # 清理 session 中的 state
        session.pop('state', None)
        
        token_url = "https://api.line.me/oauth2/v2.1/token"
        
        # 處理不同環境的 URL 構建
        base_url = request.url_root
        
        # 處理 ngrok 的 http -> https 轉換
        if 'ngrok' in base_url and base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        
        # 處理 Cloud Run 的 URL（確保使用 https）
        if 'run.app' in base_url and base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://')
        
        # 移除末尾的斜線並構建 redirect_uri
        base_url = base_url.rstrip('/')
        redirect_uri = f"{base_url}/auth/callback"
        token_payload = {
            'grant_type': 'authorization_code', 'code': code,
            'redirect_uri': redirect_uri, 'client_id': Config.LINE_LOGIN_CHANNEL_ID,
            'client_secret': Config.LINE_LOGIN_CHANNEL_SECRET
        }
        
        current_app.logger.info(f"=== TOKEN REQUEST ===")
        current_app.logger.info(f"Token URL: {token_url}")
        current_app.logger.info(f"Redirect URI: {redirect_uri}")
        current_app.logger.info(f"Client ID: {Config.LINE_LOGIN_CHANNEL_ID}")
        current_app.logger.info(f"Payload: {dict(token_payload)}")
        current_app.logger.info(f"====================")
        
        response = requests.post(token_url, data=token_payload)
        
        current_app.logger.info(f"Token response status: {response.status_code}")
        if response.status_code != 200:
            current_app.logger.error(f"Token request failed: {response.text}")
            return f"授權失敗：無法取得存取權杖 (狀態碼: {response.status_code})", 400
            
        access_token = response.json()['access_token']
        current_app.logger.info(f"Successfully got access token")
        
        profile_url = "https://api.line.me/v2/profile"
        headers = {'Authorization': f'Bearer {access_token}'}
        profile_response = requests.get(profile_url, headers=headers)
        profile_response.raise_for_status()
        profile = profile_response.json()
        
        # 將使用者資訊存入 session
        session['user_profile'] = profile
        user_id = profile['userId']
        display_name = profile['displayName']
        
        # 發送成功訊息
        configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).push_message(PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=f"嗨，{display_name}！您已成功登入。")]
            ))
        # 建立美觀的登入成功頁面
        success_html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登入成功 - 家庭健康小幫手</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            max-width: 420px;
            width: 100%;
            animation: slideUp 0.6s ease-out;
        }}
        
        @keyframes slideUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .success-icon {{
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #06C755, #05B04A);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            animation: bounce 0.8s ease-out 0.3s both;
        }}
        
        .success-icon::before {{
            content: '✓';
            color: white;
            font-size: 36px;
            font-weight: bold;
        }}
        
        @keyframes bounce {{
            0%, 20%, 53%, 80%, 100% {{
                transform: translate3d(0,0,0);
            }}
            40%, 43% {{
                transform: translate3d(0, -8px, 0);
            }}
            70% {{
                transform: translate3d(0, -4px, 0);
            }}
            90% {{
                transform: translate3d(0, -2px, 0);
            }}
        }}
        
        h1 {{
            color: #1a202c;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 12px;
            line-height: 1.2;
        }}
        
        .welcome-text {{
            color: #4a5568;
            font-size: 18px;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .user-name {{
            color: #06C755;
            font-weight: 700;
            font-size: 20px;
        }}
        
        .description {{
            color: #718096;
            font-size: 16px;
            line-height: 1.6;
            margin: 24px 0 32px;
        }}
        
        .features {{
            background: #f7fafc;
            border-radius: 16px;
            padding: 20px;
            margin: 24px 0;
            text-align: left;
        }}
        
        .features h3 {{
            color: #2d3748;
            font-size: 16px;
            margin-bottom: 12px;
            text-align: center;
        }}
        
        .feature-list {{
            list-style: none;
            padding: 0;
        }}
        
        .feature-list li {{
            color: #4a5568;
            font-size: 14px;
            margin-bottom: 8px;
            padding-left: 20px;
            position: relative;
        }}
        
        .feature-list li::before {{
            content: '✨';
            position: absolute;
            left: 0;
            top: 0;
        }}
        
        
        .footer-text {{
            color: #a0aec0;
            font-size: 12px;
            margin-top: 20px;
            line-height: 1.4;
        }}
        
        @media (max-width: 480px) {{
            .container {{
                padding: 30px 20px;
                margin: 10px;
            }}
            
            h1 {{
                font-size: 24px;
            }}
            
            .welcome-text {{
                font-size: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon"></div>
        
        <h1>🎉 登入成功！</h1>
        
        <div class="welcome-text">
            嗨，<span class="user-name">{display_name}</span>！
        </div>
        
        <p class="description">
            歡迎回到家庭健康小幫手！您已成功完成身份驗證，現在可以享受完整的個人化服務。
        </p>
        
        <div class="features">
            <h3>🔓 已解鎖功能</h3>
            <ul class="feature-list">
                <li>雲端同步您的健康資料</li>
                <li>跨裝置存取藥歷記錄</li>
                <li>個人化用藥提醒設定</li>
                <li>安全的隱私資料保護</li>
                <li>家人健康資料管理</li>
            </ul>
        </div>
        
        <p class="footer-text">
            🎉 登入完成！請手動關閉此分頁<br>
            然後返回 LINE 應用程式繼續使用服務
        </p>
    </div>

    <script>
        // 頁面載入完成後的處理
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('Login success page loaded');
            
            // 添加互動效果
            const container = document.querySelector('.container');
            container.addEventListener('click', function(e) {{
                if (e.target === container) {{
                    container.style.transform = 'scale(1.02)';
                    setTimeout(() => {{
                        container.style.transform = 'scale(1)';
                    }}, 150);
                }}
            }});
        }});
    </script>
</body>
</html>
        """
        
        return success_html, 200
    except Exception as e:
        current_app.logger.error(f"登入回調處理錯誤: {e}", exc_info=True)
        return "登入過程中發生錯誤。", 500

@auth_bp.route("/status")
def auth_status():
    """檢查登入狀態 API"""
    if 'user_profile' in session:
        return jsonify({
            "logged_in": True,
            "user_profile": session['user_profile']
        })
    else:
        return jsonify({
            "logged_in": False,
            "login_available": bool(Config.LINE_LOGIN_CHANNEL_ID and Config.LINE_LOGIN_CHANNEL_SECRET)
        })