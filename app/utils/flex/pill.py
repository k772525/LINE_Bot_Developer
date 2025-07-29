# app/utils/flex/pill.py

from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, URIAction, SeparatorComponent,
    PostbackAction, MessageAction, CarouselContainer
)

def create_text(text, **kwargs):
    """建立一個文字元件的輔助函式"""
    base = {"type": "text", "text": text, "wrap": True}
    base.update(kwargs)
    return base

# --- 藥丸辨識流程所需的卡片 ---
def generate_pill_identification_menu():
    """生成藥丸辨識的主選單輪播，包含模型選擇和模型說明"""
    
    # ==================== 第一張卡片：選擇辨識模型 ====================
    model_selection_bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#B9DCEC",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "🤖 選擇辨識模型",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#1F2D3D",
                    "align": "center"
                },
                {
                    "type": "image",
                    "url": "https://storage.googleapis.com/cji10125-0623/pill_test/f08d78e8-b8df-4287-9359-641bfde8eb75.png",
                    "size": "md",
                    "aspectMode": "cover",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": "請先選擇要使用的 AI 模型：",
                    "wrap": True,
                    "size": "sm",
                    "color": "#555555",
                    "margin": "md",
                    "align": "center"
                },
                
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#FF6B6B",
                    "action": {
                        "type": "postback",
                        "label": "🎯 單一模型辨識",
                        "data": "action=select_model_mode&mode=single"
                    }
                },
                {
                    "type": "button",
                    "style": "primary", 
                    "color": "#4ECDC4",
                    "action": {
                        "type": "postback",
                        "label": "🚀 多模型同時辨識",
                        "data": "action=select_model_mode&mode=multi"
                    }
                }
            ]
        },
        "styles": {
            "body": {
                "background_color": "#B9DCEC"
            },
            "footer": {
                "separator": True,
                "separator_color": "#DDDDDD",
                "background_color": "#B9DCEC"
            }
        }
    }
    
    # 第二張卡片：模型說明
    model_info_bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                create_text("📖 模型說明", weight="bold", size="lg", color="#FFFFFF")
            ],
            "background_color": "#636E72",
            "padding_all": "16px"
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
                    "padding_all": "12px",
                    "background_color": "#FFF3E0",
                    "corner_radius": "8px",
                    "contents": [
                        create_text("🎯 單一模型辨識", weight="bold", color="#E65100"),
                        create_text("• 選擇特定模型進行辨識\n• 速度較快\n• 適合快速檢測", size="sm", wrap=True)
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "padding_all": "12px",
                    "background_color": "#E8F5E8",
                    "corner_radius": "8px",
                    "contents": [
                        create_text("🚀 多模型同時辨識", weight="bold", color="#2E7D32"),
                        create_text("• 同時使用多個模型\n• 準確度更高\n• 提供多重驗證結果", size="sm", wrap=True)
                    ]
                },
                create_text("💡 建議：如果追求最高準確度，請選擇多模型辨識。", size="xs", color="#666666", wrap=True)
            ]
        }
    }
    
    # 創建輪播容器
    bubbles = [
        BubbleContainer.new_from_json_dict(model_selection_bubble),
        BubbleContainer.new_from_json_dict(model_info_bubble)
    ]
    
    carousel = CarouselContainer(contents=bubbles)
    return FlexSendMessage(alt_text="藥丸辨識選單", contents=carousel)

# --- 單一模型選擇選單 ---
def generate_single_model_selection_menu():
    """生成單一模型選擇選單，包含模型說明卡片"""
    
    # 第一張卡片：模型選擇
    model_selection_bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                create_text("🎯 選擇單一模型", weight="bold", size="lg", color="#FFFFFF")
            ],
            "backgroundColor": "#FF6B6B",
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "image",
                    "url": "https://storage.googleapis.com/cji10125-0623/pill_test/f08d78e8-b8df-4287-9359-641bfde8eb75.png",
                    "size": "5xl",
                    "aspectMode": "cover",
                    "align": "center"
                }
                
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#6C5CE7",
                    "action": {
                        "type": "postback",
                        "label": "🧠 高精度模型",
                        "data": "action=use_single_model&model=1"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#A29BFE",
                    "action": {
                        "type": "postback",
                        "label": "⚡高效率模型",
                        "data": "action=use_single_model&model=2"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#74B9FF",
                    "action": {
                        "type": "postback",
                        "label": "🎯Transformer模型",
                        "data": "action=use_single_model&model=3"
                    }
                }
            ]
        }
    }
    
    # 第二張卡片：模型詳細說明
    model_info_bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                create_text("📖 模型詳細說明", weight="bold", size="lg", color="#FFFFFF")
            ],
            "backgroundColor": "#636E72",
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "lg",
            "contents": [
                # YOLO12 模型說明
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "paddingAll": "12px",
                    "backgroundColor": "#E8F4FD",
                    "cornerRadius": "8px",
                    "contents": [
                        create_text("🧠 高精度 - YOLO12", weight="bold", color="#1565C0"),
                        create_text("• 最新版本的 YOLO 架構\n• 高精度物件偵測\n• 適合複雜場景辨識\n• 處理時間較長但準確度最高", size="sm", wrap=True, color="#424242")
                    ]
                },
                # YOLO11 模型說明
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "paddingAll": "12px",
                    "backgroundColor": "#F3E5F5",
                    "cornerRadius": "8px",
                    "contents": [
                        create_text("⚡ 高效率 - YOLO11", weight="bold", color="#7B1FA2"),
                        create_text("• 成熟穩定的 YOLO 版本\n• 速度與精度平衡\n• 適合一般藥丸辨識\n• 處理速度快，準確度良好", size="sm", wrap=True, color="#424242")
                    ]
                },
                # RF-DETR 模型說明
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "paddingAll": "12px",
                    "backgroundColor": "#E8F5E8",
                    "cornerRadius": "8px",
                    "contents": [
                        create_text("🎯Transformer-RF-DETR ONNX", weight="bold", color="#2E7D32"),
                        create_text("• 基於 Transformer 的檢測架構\n• 優化的 ONNX 推理引擎\n• 特別適合小物件檢測\n• 在藥丸形狀辨識上表現優異", size="sm", wrap=True, color="#424242")
                    ]
                },
                {
                    "type": "separator",
                    "margin": "md"
                }
            ]
        }
    }
    
    # 創建輪播容器
    bubbles = [
        BubbleContainer.new_from_json_dict(model_selection_bubble),
        BubbleContainer.new_from_json_dict(model_info_bubble)
    ]
    
    carousel = CarouselContainer(contents=bubbles)
    return FlexSendMessage(alt_text="選擇單一模型", contents=carousel)

# --- 拍照指引選單 ---
def generate_camera_guide_menu():
    """生成拍照指引選單"""
    bubble_dict = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                create_text("📷 拍攝指引", weight="bold", size="lg", color="#000000")
            ],
            "backgroundColor": "#B9DCEC",
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                create_text("為了提升藥丸辨識準確度，請依以下建議進行拍攝：", wrap=True, size="sm", color="#555555"),
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "lg",
                    "paddingAll": "12px",
                    "backgroundColor": "#F8F9FA",
                    "cornerRadius": "8px",
                    "contents": [
                        create_text("1. 拍攝清晰、對焦正確的照片", wrap=True, size="sm"),
                        create_text("2. 避免遮擋藥丸上的刻痕或標記", wrap=True, size="sm"),
                        create_text("3. 請盡量拍攝有文字刻痕那一面", wrap=True, size="sm"),
                        create_text("4. 將藥丸置於畫面中央，方便辨識", wrap=True, size="sm"),
                        create_text("5. 確保光線充足，避免陰影", wrap=True, size="sm")
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#4A90E2",
                    "cornerRadius": "8px",
                    "paddingAll": "12px",
                    "action": {
                        "type": "uri",
                        "label": "📷 開啟相機",
                        "uri": "line://nv/camera/"
                    },
                    "contents": [
                        {
                            "type": "text",
                            "text": "📷 開啟相機",
                            "align": "center",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#FFFFFF"
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#5CB79C",
                    "cornerRadius": "8px",
                    "paddingAll": "12px",
                    "action": {
                        "type": "uri",
                        "label": "🖼️ 開啟相簿",
                        "uri": "https://line.me/R/nv/cameraRoll/single"
                    },
                    "contents": [
                        {
                            "type": "text",
                            "text": "🖼️ 開啟相簿",
                            "align": "center",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#FFFFFF"
                        }
                    ]
                }
            ]
        }
    }
    
    bubble = BubbleContainer.new_from_json_dict(bubble_dict)
    return FlexSendMessage(alt_text="拍攝指引", contents=bubble)

# --- 模型說明卡片 ---
def generate_model_info_card():
    """生成模型說明卡片"""
    bubble_dict = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                create_text("📖 模型說明", weight="bold", size="lg", color="#FFFFFF")
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
                        create_text("🎯 單一模型辨識", weight="bold", color="#E65100"),
                        create_text("• 選擇特定模型進行辨識\n• 速度較快\n• 適合快速檢測", size="sm", wrap=True)
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
                        create_text("🚀 多模型同時辨識", weight="bold", color="#2E7D32"),
                        create_text("• 同時使用多個模型\n• 準確度更高\n• 提供多重驗證結果", size="sm", wrap=True)
                    ]
                },
                {
                    "type": "separator"
                },
                create_text("💡建議：如果追求最高準確度，請選擇多模型辨識。", size="xs", color="#666666", wrap=True)
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "⬅️ 返回選單",
                        "data": "action=back_to_model_menu"
                    }
                }
            ]
        }
    }
    
    bubble = BubbleContainer.new_from_json_dict(bubble_dict)
    return FlexSendMessage(alt_text="模型說明", contents=bubble)

# --- 辨識結果卡片，顯示中文藥名 ---
def generate_identification_result_card(detected_pills_info):
    """
    生成「辨識結果」卡片
    :param detected_pills_info: 字典列表，[{'drug_id': '...', 'drug_name_zh': '...'}]
    """
    pill_list_text = ""
    drug_ids_str = ",".join([pill['drug_id'] for pill in detected_pills_info])
    
    for i, pill in enumerate(detected_pills_info, 1):
        # 顯示中英文名稱
        pill_list_text += f"{i}. {pill['drug_name_en']} / {pill['drug_name_zh']}\n"
        

    bubble_dict = {
        "type": "bubble",
        "header": { "type": "box", "layout": "vertical", "contents": [ create_text("🔍 辨識結果", weight="bold", size="lg") ] },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "md",
            "contents": [
                create_text(f"我們從您拍攝的照片中辨識出 {len(detected_pills_info)} 種藥丸："),
                {
                    "type": "box", "layout": "vertical", "margin": "lg", "paddingAll": "12px",
                    "backgroundColor": "#F7FAFC", "cornerRadius": "md",
                    "contents": [create_text(pill_list_text.strip())]
                },
                create_text("是否需要查看這幾種藥丸的詳細資訊？", wrap=True, margin="lg")
            ]
        },
        "footer": {
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "contents": [
                # 將 drug_id 傳遞到 postback data 中
                {"type": "button", "action": {"type": "postback", "label": "是", "data": f"action=get_pill_info&ids={drug_ids_str}"}, "style": "primary"},
                {"type": "button", "action": {"type": "postback", "label": "否", "data": "action=no_pill_info"}, "style": "secondary"}
            ]
        }
    }
    
    bubble = BubbleContainer.new_from_json_dict(bubble_dict)
    return FlexSendMessage(alt_text="辨識結果", contents=bubble)

# --- 藥品詳細資訊卡片，顯示新欄位 ---
def generate_pill_info_carousel(pill_details_list):
    """
    生成一個顯示多個藥品詳細資訊的卡片輪播
    """
    if not pill_details_list:
        return None

    bubbles = []
    for pill in pill_details_list:
        
        image_url = pill.get("image_url")
        if not image_url:
            image_url = "https://scdn.line-apps.com/n/channel_devcenter/img/fx/01_1_cafe.png" 

        # 取得英文和中文名稱
        drug_name_en = pill.get('drug_name_en', '') or '未知英文名'
        drug_name_zh = pill.get('drug_name_zh', '') or '未知藥名'

        bubble = {
            "type": "bubble", "size": "giga",
            "hero": {
                "type": "image", "url": image_url, "size": "full",
                "aspectRatio": "20:13", "aspectMode": "cover"
            },
            "body": {
                "type": "box", "layout": "vertical", "spacing": "lg",
                "contents": [
                    # --- 關鍵修改：使用一個 Box 元件來包含兩個 Text 元件，以實現換行 ---
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            create_text(f"💊 {drug_name_zh}", weight="bold", size="xl"),
                            create_text(f"({drug_name_en})", size="md", color="#666666", margin="sm")
                        ]
                    },
                    { "type": "separator" },
                    create_text("🎯主要用途", weight="bold", color="#4A90E2"),
                    create_text(pill.get('uses') or '暫無資料', wrap=True, size="sm"),
                    { "type": "separator" },
                    create_text("⚠️可能副作用", weight="bold", color="#4A90E2"),
                    create_text(pill.get('side_effects') or '暫無資料', wrap=True, size="sm"),
                    { "type": "separator" },
                    create_text("🚨食物藥物交互作用", weight="bold", color="#4A90E2"),
                    create_text(pill.get('interactions') or '暫無資料', wrap=True, size="sm")
                ]
            }
        }
        bubbles.append(bubble)

    from linebot.models import CarouselContainer
    carousel = CarouselContainer(contents=[BubbleContainer.new_from_json_dict(bubble) for bubble in bubbles])
    return FlexSendMessage(alt_text="藥品詳細資訊", contents=carousel)

def generate_yolo_carousel(results):
    bubbles = []
    for result in results:
        model_name = result.get('model_name', '未知模型')
        
        # 直接生成字典格式的卡片
        bubble_dict = generate_yolo_result_card_v2_dict(result, result.get('pills_info', []))
        
        # 添加 header
        bubble_dict['header'] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                create_text(f"模型: {model_name}", weight="bold", size="lg")
            ]
        }
        bubbles.append(bubble_dict)

    from linebot.models import CarouselContainer
    carousel = CarouselContainer(contents=[BubbleContainer.new_from_json_dict(bubble) for bubble in bubbles])
    return FlexSendMessage(alt_text="多模型辨識結果", contents=carousel)


def generate_yolo_result_card_v2_dict(analysis_result: dict, pills_info_from_db: list):
    """
    生成美化的YOLO辨識結果卡片，包含標註圖片、信賴度、詳細資訊按鈕
    
    :param analysis_result: 從模型回傳的分析結果字典
    :param pills_info_from_db: 從資料庫查詢的藥品資訊列表
    """
    from app.utils.db import DB
    
    predict_image_url = analysis_result.get('predict_image_url')
    detections = analysis_result.get('detections', [])
    elapsed_time = analysis_result.get('elapsed_time', 0)
    model_name = analysis_result.get('model_name', '未知模型')
    
    # 自定義模型顯示名稱
    model_display_names = {
        'yolo12': '🧠 高精度模型 (YOLO12)',
        'yolo11': '⚡ 高效率模型 (YOLO11)', 
        'kevin_model': '🎯 Kevin模型 (RF-DETR)',
        'rf_detr': '🎯 Kevin模型 (RF-DETR)',
        'multi_model': '🚀 多模型綜合辨識'
    }
    
    # 如果有自定義名稱就使用，否則使用原始名稱
    display_name = model_display_names.get(model_name.lower(), model_name)

    # --- 防呆處理：無檢測結果 ---
    if not detections:
        return {
            "type": "bubble",
            "size": "giga",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🤔",
                                "size": "xl",
                                "flex": 0
                            },
                            {
                                "type": "text",
                                "text": "未偵測到藥品",
                                "weight": "bold",
                                "size": "lg",
                                "color": "#FFFFFF",
                                "flex": 1,
                                "margin": "sm"
                            }
                        ]
                    }
                ],
                "backgroundColor": "#FF9800",
                "paddingAll": "20px",
                "cornerRadius": "12px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "paddingAll": "20px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "paddingAll": "12px",
                        "backgroundColor": "#FFF3E0",
                        "cornerRadius": "8px",
                        "contents": [
                            {
                                "type": "text",
                                "text": "💡",
                                "flex": 0,
                                "size": "md"
                            },
                            {
                                "type": "text",
                                "text": "建議：確保圖片清晰、光線充足，將藥丸放在乾淨背景上，避免遮擋，然後重新拍攝。",
                                "flex": 1,
                                "size": "sm",
                                "color": "#E65100",
                                "wrap": True
                            }
                        ]
                    }
                ]
            }
        }

    # --- 資料準備 ---
    # 收集所有檢測到的 drug_id
    detected_drug_ids = set()
    for detection in detections:
        drug_id = detection.get('drug_id')
        if not drug_id:
            # 從 class_name 推斷 drug_id (例如: "ABC123_round" -> "ABC123")
            drug_id = detection.get('class_name', 'unknown').split('_')[0]
        if drug_id and drug_id != 'unknown':
            detected_drug_ids.add(drug_id)
    
    # 使用 drug_id 從資料庫查詢藥品資訊
    drug_info_dict = {}
    if detected_drug_ids:
        drug_info_list = DB.get_pills_details_by_ids(list(detected_drug_ids))
        drug_info_dict = {drug['drug_id']: drug for drug in drug_info_list}
    
    pill_list_components = []
    processed_drug_ids = set()

    for detection in detections:
        # 從 detection 中獲取 drug_id，如果不存在，則從 class_name 推斷
        drug_id = detection.get('drug_id')
        if not drug_id:
            drug_id = detection.get('class_name', 'unknown').split('_')[0]

        # 如果已經處理過這個 drug_id，則跳過以避免在卡片中重複顯示同一種藥
        if drug_id in processed_drug_ids:
            continue
        processed_drug_ids.add(drug_id)

        # 使用 drug_id 從資料庫查詢的資訊獲取藥品名稱
        drug_info = drug_info_dict.get(drug_id)
        if drug_info:
            drug_name_zh = drug_info.get('drug_name_zh', '未知藥品')
            drug_name_en = drug_info.get('drug_name_en', '(N/A)')
        else:
            # 如果資料庫中沒有找到，則使用 class_name 作為備用顯示
            drug_name_zh = detection.get('class_name', '未知藥品')
            drug_name_en = detection.get('class_name_en', '未知藥品')
        
        confidence = detection.get('confidence', 0)
        
        # 使用顏色池，避免黑色
        color_pool = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#F9A825', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        pill_color = detection.get('color')
        if not pill_color or pill_color == '#555555' or pill_color == '#000000':
            pill_color = color_pool[len(pill_list_components) % len(color_pool)]

        # 根據序號選擇背景顏色
        bg_colors = ["#FFF3E0", "#E8F5E8", "#E3F2FD", "#FCE4EC", "#F3E5F5"]
        bg_color = bg_colors[len(pill_list_components) % len(bg_colors)]
        
        pill_component = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "paddingAll": "8px",
            "backgroundColor": bg_color,
            "cornerRadius": "8px",
            "borderWidth": "2px",
            "borderColor": pill_color,
            "margin": "sm",
            "contents": [
                # 左側：藥品信息
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 1,
                    "spacing": "xs",
                    "contents": [
                        create_text(drug_name_zh, weight="bold", size="sm", color=pill_color),
                        create_text(f"({drug_name_en})", size="xs", color="#666666", wrap=True)
                    ]
                },
                # 右側：信賴度圓圈
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 0,
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"{confidence * 100:.0f}",
                                    "color": "#FFFFFF",
                                    "weight": "bold",
                                    "size": "xs",
                                    "align": "center"
                                }
                            ],
                            "width": "32px",
                            "height": "32px",
                            "backgroundColor": pill_color,
                            "cornerRadius": "16px",
                            "justifyContent": "center",
                            "alignItems": "center"
                        }
                    ],
                    "justifyContent": "center"
                }
            ]
        }
        pill_list_components.append(pill_component)

    # 更新 drug_ids_str 的生成方式，以反映實際顯示在卡片上的藥品
    drug_ids_str = ",".join(list(processed_drug_ids))

    # --- 組合完整的美化卡片 ---
    card_dict = {
        "type": "bubble",
        "size": "giga",
        # 頭部信息
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🎯",
                            "size": "xl",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": f"{model_name} 辨識結果",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#FFFFFF",
                            "flex": 1,
                            "margin": "sm"
                        },
                        {
                            "type": "text",
                            "text": f"{len(pills_info_from_db)}",
                            "color": "#FFFFFF",
                            "size": "lg",
                            "weight": "bold",
                            "flex": 0,
                            "align": "center"
                        }
                    ],
                    "alignItems": "center"
                }
            ],
            "backgroundColor": "#4A90E2",
            "paddingAll": "16px",
            "cornerRadius": "12px"
        },
        # 主體內容
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "12px",
            "contents": [
                # 成功提示
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "paddingAll": "10px",
                    "backgroundColor": "#E8F5E8",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "✅",
                            "flex": 0,
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": f"成功辨識出 {len(pills_info_from_db)} 種藥丸",
                            "flex": 1,
                            "size": "sm",
                            "color": "#2E7D32",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": f"⏱️ {elapsed_time:.1f}s",
                            "flex": 0,
                            "size": "xs",
                            "color": "#666666"
                        }
                    ]
                },
                # 分隔線
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#E0E0E0"
                },
                # 藥品列表
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "none",
                    "contents": pill_list_components
                },
                # 分隔線
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#E0E0E0"
                },
                # 詢問提示
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "paddingAll": "10px",
                    "backgroundColor": "#FFF3E0",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "💊",
                            "flex": 0,
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": "需要查看這些藥品的詳細資訊嗎？",
                            "flex": 1,
                            "size": "sm",
                            "color": "#E65100",
                            "wrap": True
                        }
                    ]
                }
            ]
        },
        # 底部按鈕
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "📋 詳細資訊",
                        "data": f"action=get_pill_info&ids={drug_ids_str}"
                    },
                    "style": "primary",
                    "color": "#4A90E2",
                    "height": "md",
                    "flex": 1
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "🔄 重新辨識",
                        "data": "action=back_to_model_menu"
                    },
                    "style": "secondary",
                    "height": "md",
                    "flex": 1
                }
            ]
        },
        "styles": {
            "header": {
                "separator": False
            },
            "body": {
                "separator": False
            },
            "footer": {
                "separator": False
            }
        }
    }
    
    # 安全地添加 hero 圖片（如果 URL 有效）
    if predict_image_url and predict_image_url.startswith('https://') and len(predict_image_url) > 10:
        card_dict["hero"] = {
            "type": "image",
            "url": predict_image_url,
            "size": "full",
            "aspectRatio": "16:9",
            "aspectMode": "cover",
            "action": {"type": "uri", "uri": predict_image_url}
        }
    
    return card_dict

def generate_yolo_result_card_v2(analysis_result: dict, pills_info_from_db: list):
    """
    生成美化的YOLO辨識結果卡片，包含標註圖片、信賴度、詳細資訊按鈕
    
    :param analysis_result: 從模型回傳的分析結果字典
    :param pills_info_from_db: 從資料庫查詢的藥品資訊列表
    """
    predict_image_url = analysis_result.get('predict_image_url')
    detections = analysis_result.get('detections', [])
    elapsed_time = analysis_result.get('elapsed_time', 0)
    model_name = analysis_result.get('model_name', '未知模型')
    
    # 自定義模型顯示名稱
    model_display_names = {
        'yolo12': '🧠 高精度模型 (YOLO12)',
        'yolo11': '⚡ 高效率模型 (YOLO11)', 
        'kevin_model': '🎯 Kevin模型 (RF-DETR)',
        'rf_detr': '🎯 Kevin模型 (RF-DETR)',
        'multi_model': '🚀 多模型綜合辨識'
    }
    
    # 如果有自定義名稱就使用，否則使用原始名稱
    display_name = model_display_names.get(model_name.lower(), model_name)

    # --- 防呆處理：無檢測結果 ---
    if not detections or not predict_image_url:
        return {
            "type": "bubble",
            "size": "giga",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🤔",
                                "size": "xl",
                                "flex": 0
                            },
                            {
                                "type": "text",
                                "text": "未偵測到藥品",
                                "weight": "bold",
                                "size": "lg",
                                "color": "#FFFFFF",
                                "flex": 1,
                                "margin": "sm"
                            }
                        ]
                    }
                ],
                "backgroundColor": "#FF9800",
                "paddingAll": "20px",
                "cornerRadius": "12px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "paddingAll": "20px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "paddingAll": "12px",
                        "backgroundColor": "#FFF3E0",
                        "cornerRadius": "8px",
                        "contents": [
                            {
                                "type": "text",
                                "text": "💡",
                                "flex": 0,
                                "size": "md"
                            },
                            {
                                "type": "text",
                                "text": "建議：確保圖片清晰、光線充足，將藥丸放在乾淨背景上，避免遮擋，然後重新拍攝。",
                                "flex": 1,
                                "size": "sm",
                                "color": "#E65100",
                                "wrap": True
                            }
                        ]
                    }
                ]
            }
        }

    # --- 資料準備 ---
    confidence_map = {}
    color_map = {}
    for det in detections:
        class_name = det['class_name']
        confidence = det['confidence']
        color = det.get('color', '#555555')
        if class_name not in confidence_map or confidence > confidence_map[class_name]:
            confidence_map[class_name] = confidence
            color_map[class_name] = color

    drug_ids_str = ",".join([pill['drug_id'] for pill in pills_info_from_db])

    # --- 建立美化的藥品列表元件 ---
    pill_list_components = []
    for i, pill in enumerate(pills_info_from_db):
        drug_id = pill['drug_id']
        drug_id_prefix = drug_id[:10]
        drug_name_zh = pill.get('drug_name_zh', '未知藥品')
        drug_name_en = pill.get('drug_name_en', '(N/A)')
        
        # 尋找對應的信賴度和顏色
        confidence = 0
        # 使用顏色池，避免黑色
        color_pool = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        pill_color = color_pool[i % len(color_pool)]
        
        for detected_id, conf in confidence_map.items():
            if detected_id.startswith(drug_id_prefix) or drug_id_prefix.startswith(detected_id[:10]):
                confidence = conf
                break
                
        for detected_id, color in color_map.items():
            if detected_id.startswith(drug_id_prefix) or drug_id_prefix.startswith(detected_id[:10]):
                pill_color = color
                break

        # 根據序號選擇背景顏色
        bg_colors = ["#FFF3E0", "#E8F5E8", "#E3F2FD", "#FCE4EC", "#F3E5F5"]
        bg_color = bg_colors[i % len(bg_colors)]
        
        pill_component = {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "paddingAll": "8px",
            "backgroundColor": bg_color,
            "cornerRadius": "8px",
            "borderWidth": "2px",
            "borderColor": pill_color,
            "margin": "sm",
            "contents": [
                # 左側：藥品信息
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 1,
                    "spacing": "xs",
                    "contents": [
                        create_text(drug_name_zh, weight="bold", size="sm", color=pill_color),
                        create_text(f"({drug_name_en})", size="xs", color="#666666", wrap=True)
                    ]
                },
                # 右側：信賴度圓圈
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 0,
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"{confidence * 100:.0f}",
                                    "color": "#FFFFFF",
                                    "weight": "bold",
                                    "size": "xs",
                                    "align": "center"
                                }
                            ],
                            "width": "32px",
                            "height": "32px",
                            "backgroundColor": pill_color,
                            "cornerRadius": "16px",
                            "justifyContent": "center",
                            "alignItems": "center"
                        }
                    ],
                    "justifyContent": "center"
                }
            ]
        }
        pill_list_components.append(pill_component)

    # --- 組合完整的美化卡片 ---
    return {
        "type": "bubble",
        "size": "giga",
        # 頂部標註圖片
        "hero": {
            "type": "image",
            "url": predict_image_url,
            "size": "full",
            "aspectRatio": "4:3",
            "aspectMode": "cover",
            "action": {"type": "uri", "uri": predict_image_url}
        },
        # 頭部信息
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🎯",
                            "size": "xl",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": f"{model_name} 辨識結果",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#FFFFFF",
                            "flex": 1,
                            "margin": "sm"
                        },
                        {
                            "type": "text",
                            "text": f"{len(pills_info_from_db)}",
                            "color": "#FFFFFF",
                            "size": "lg",
                            "weight": "bold",
                            "flex": 0,
                            "align": "center"
                        }
                    ],
                    "alignItems": "center"
                }
            ],
            "backgroundColor": "#4A90E2",
            "paddingAll": "16px",
            "cornerRadius": "12px"
        },
        # 主體內容
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "16px",
            "contents": [
                # 成功提示
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "paddingAll": "10px",
                    "backgroundColor": "#E8F5E8",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "✅",
                            "flex": 0,
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": f"成功辨識出 {len(pills_info_from_db)} 種藥丸",
                            "flex": 1,
                            "size": "sm",
                            "color": "#2E7D32",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": f"⏱️ {elapsed_time:.1f}s",
                            "flex": 0,
                            "size": "xs",
                            "color": "#666666"
                        }
                    ]
                },
                # 分隔線
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#E0E0E0"
                },
                # 藥品列表
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "none",
                    "contents": pill_list_components
                },
                # 分隔線
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#E0E0E0"
                },
                # 詢問提示
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "paddingAll": "10px",
                    "backgroundColor": "#FFF3E0",
                    "cornerRadius": "8px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "💊",
                            "flex": 0,
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": "需要查看這些藥品的詳細資訊嗎？",
                            "flex": 1,
                            "size": "sm",
                            "color": "#E65100",
                            "wrap": True
                        }
                    ]
                }
            ]
        },
        # 底部按鈕
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "📋 查看詳細資訊",
                        "data": f"action=get_pill_info&ids={drug_ids_str}"
                    },
                    "style": "primary",
                    "color": "#4A90E2",
                    "height": "md",
                    "flex": 1
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "🔄 重新辨識",
                        "data": "action=back_to_model_menu"
                    },
                    "style": "secondary",
                    "height": "md",
                    "flex": 1
                }
            ]
        },
        "styles": {
            "header": {
                "separator": False
            },
            "body": {
                "separator": False
            },
            "footer": {
                "separator": False
            }
        }
    }