# app/utils/flex/settings.py

from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    MessageAction, PostbackAction, URIAction
)

def create_text(text, **kwargs):
    """建立一個文字元件的輔助函式"""
    base = {"type": "text", "text": text, "wrap": True}
    base.update(kwargs)
    return base

def create_main_settings_menu():
    """生成「主設定」選單卡片 - 美化版本"""
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "⚙️ 設定選單",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF",
                    "align": "center"
                }
            ],
            "backgroundColor": "#4A90E2",
            "paddingAll": "20px",
            "cornerRadius": "8px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "lg",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": "請選擇您要進行的設定項目：",
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True,
                    "margin": "none"
                },
                # 登入設定按鈕
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "md",
                    "paddingAll": "16px",
                    "backgroundColor": "#F8F9FA",
                    "cornerRadius": "8px",
                    "action": {"type": "postback", "data": "action=login_settings", "displayText": "登入設定"},
                    "contents": [
                        {
                            "type": "text",
                            "text": "🔐",
                            "size": "xl",
                            "flex": 0,
                            "gravity": "center"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "登入設定",
                                    "weight": "bold",
                                    "size": "md",
                                    "color": "#333333"
                                },
                                {
                                    "type": "text",
                                    "text": "會員登入與身份驗證",
                                    "size": "sm",
                                    "color": "#666666",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "text",
                            "text": "›",
                            "size": "lg",
                            "color": "#CCCCCC",
                            "flex": 0,
                            "gravity": "center"
                        }
                    ]
                },
                # 家人設定按鈕
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "md",
                    "paddingAll": "16px",
                    "backgroundColor": "#F8F9FA",
                    "cornerRadius": "8px",
                    "action": {"type": "message", "text": "家人綁定與管理"},
                    "contents": [
                        {
                            "type": "text",
                            "text": "👨‍👩‍👧‍👦",
                            "size": "xl",
                            "flex": 0,
                            "gravity": "center"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "家人設定",
                                    "weight": "bold",
                                    "size": "md",
                                    "color": "#333333"
                                },
                                {
                                    "type": "text",
                                    "text": "新增管理家庭成員",
                                    "size": "sm",
                                    "color": "#666666",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "text",
                            "text": "›",
                            "size": "lg",
                            "color": "#CCCCCC",
                            "flex": 0,
                            "gravity": "center"
                        }
                    ]
                },
                # 分隔線
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#E5E5E5"
                },
                # 使用說明按鈕
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "md",
                    "paddingAll": "16px",
                    "backgroundColor": "#F8F9FA",
                    "cornerRadius": "8px",
                    "action": {"type": "postback", "data": "action=show_instructions", "displayText": "使用說明"},
                    "contents": [
                        {
                            "type": "text",
                            "text": "📖",
                            "size": "xl",
                            "flex": 0,
                            "gravity": "center"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "使用說明",
                                    "weight": "bold",
                                    "size": "md",
                                    "color": "#333333"
                                },
                                {
                                    "type": "text",
                                    "text": "了解如何使用各項功能",
                                    "size": "sm",
                                    "color": "#666666",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "text",
                            "text": "›",
                            "size": "lg",
                            "color": "#CCCCCC",
                            "flex": 0,
                            "gravity": "center"
                        }
                    ]
                }
            ]
        },
        "styles": {
            "body": {
                "backgroundColor": "#FFFFFF"
            }
        }
    }

def create_login_card(login_url):
    """生成一個引導使用者點擊登入的卡片"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🔒 身份驗證",
                    "weight": "bold",
                    "color": "#FFFFFF"
                }
            ],
            "backgroundColor": "#2B3A4F",
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "為了提供更完整的個人化服務，請點擊下方按鈕，透過 LINE Login 授權我們讀取您的基本個人資料。",
                    "wrap": True,
                    "size": "sm"
                },
                {
                    "type": "text",
                    "text": "您的資料將被妥善保管。",
                    "size": "sm",
                    "color": "#AAAAAA",
                    "wrap": True
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "前往 LINE Login 登入",
                        "uri": login_url
                    },
                    "style": "primary",
                    "color": "#06C755"
                }
            ]
        }
    }

def create_instructions_card():
    """生成使用說明卡片"""
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📖 使用說明",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF"
                }
            ],
            "backgroundColor": "#636E72",
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "lg",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "paddingAll": "12px",
                    "backgroundColor": "#FFF3E0",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🤖 掃描新藥單",
                            "weight": "bold",
                            "color": "#E65100"
                        },
                        {
                            "type": "text",
                            "text": "• 拍攝處方箋照片\n• AI 自動辨識藥品\n• 建立用藥提醒",
                            "size": "sm",
                            "wrap": True
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "paddingAll": "12px",
                    "backgroundColor": "#E8F5E8",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "💊 藥丸辨識",
                            "weight": "bold",
                            "color": "#2E7D32"
                        },
                        {
                            "type": "text",
                            "text": "• 拍攝藥丸照片\n• 多模型同時辨識\n• 查看藥品詳細資訊",
                            "size": "sm",
                            "wrap": True
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "paddingAll": "12px",
                    "backgroundColor": "#E3F2FD",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "👨‍👩‍👧‍👦 家人管理",
                            "weight": "bold",
                            "color": "#1976D2"
                        },
                        {
                            "type": "text",
                            "text": "• 新增家庭成員\n• 管理家人用藥\n• 設定提醒通知",
                            "size": "sm",
                            "wrap": True
                        }
                    ]
                },
                {
                    "type": "separator"
                },
                {
                    "type": "text",
                    "text": "如有任何問題，請隨時聯繫我們的客服團隊。",
                    "size": "xs",
                    "color": "#666666",
                    "wrap": True
                }
            ]
        }
    }