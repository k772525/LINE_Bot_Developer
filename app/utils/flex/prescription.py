# --- 請用此版本【完整覆蓋】您的 app/utils/flex/prescription.py ---

from linebot.models import (
    FlexSendMessage, BubbleContainer, CarouselContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent, ImageComponent,
    PostbackAction, MessageAction, URIAction, CameraAction,
    QuickReply, QuickReplyButton, TextSendMessage
)
from urllib.parse import quote
from datetime import datetime

def create_prescription_model_choice():
    """建立藥單辨識模型選擇的 Flex 訊息"""
    return {
        "type": "carousel",
        "contents": [
            # 第一張卡片：模型選擇
            {
                "type": "bubble",
                "size": "kilo",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🤖 選擇分析模型",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#333333",
                            "align": "center"
                        }
                    ],
                    "backgroundColor": "#B9DCEC",
                    "paddingAll": "md",
                    "cornerRadius": "8px"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "請選擇要使用的分析方式：",
                            "size": "sm",
                            "color": "#666666",
                            "align": "center",
                            "margin": "md"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "color": "#4ECDC4",
                                    "action": {
                                        "type": "postback",
                                        "label": "🧠 智能分析模式",
                                        "data": "action=prescription_model_select&model=smart_filter"
                                    }
                                },
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "color": "#FF6B6B",
                                    "action": {
                                        "type": "postback",
                                        "label": "⚡ 快速識別模式",
                                        "data": "action=prescription_model_select&model=api_ocr"
                                    },
                                    "margin": "sm"
                                }
                            ],
                            "margin": "md"
                        }
                    ],
                    "paddingAll": "md"
                }
            },
            # 第二張卡片：模型說明
            {
                "type": "bubble",
                "size": "kilo",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📖 模型說明",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#333333",
                            "align": "center"
                        }
                    ],
                    "backgroundColor": "#B9DCEC",
                    "paddingAll": "md",
                    "cornerRadius": "8px"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "🧠 智能分析模式",
                                    "weight": "bold",
                                    "size": "md",
                                    "color": "#4ECDC4"
                                },
                                {
                                    "type": "text",
                                    "text": "• 使用AI智能篩選技術\n• 節省30% TOKEN成本\n• 完整的頻率解析演算法\n• 適合詳細處方籤分析",
                                    "size": "xs",
                                    "color": "#666666",
                                    "wrap": True,
                                    "margin": "sm"
                                }
                            ],
                            "backgroundColor": "#F0F8F8",
                            "paddingAll": "sm",
                            "cornerRadius": "8px"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "⚡ 快速識別模式",
                                    "weight": "bold",
                                    "size": "md",
                                    "color": "#FF6B6B"
                                },
                                {
                                    "type": "text",
                                    "text": "• 使用組員的OCR API\n• 處理速度更快\n• 適合快速識別需求\n• 簡化的分析流程",
                                    "size": "xs",
                                    "color": "#666666",
                                    "wrap": True,
                                    "margin": "sm"
                                }
                            ],
                            "backgroundColor": "#FFF0F0",
                            "paddingAll": "sm",
                            "cornerRadius": "8px",
                            "margin": "md"
                        }
                    ],
                    "paddingAll": "md"
                }
            }
        ]
    }

def create_management_menu(title: str, primary_action_label: str, primary_action_data: str):
    """產生一個與「用藥提醒管理」風格統一的通用管理選單。"""
    bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text=title, weight='bold', size='lg', color='#1F2D3D', align='center')
            ],
            background_color='#B9DCEC',
            padding_all='16px'
        ),
        body=BoxComponent(
            layout='vertical', padding_all='20px', spacing='xl',
            contents=[
                BoxComponent(
                    layout='vertical', margin='lg', spacing='md',
                    contents=[
                        # ButtonComponent(
                            # action=PostbackAction(label=primary_action_label, data=primary_action_data),
                            # style='primary', color='#10B981', height='md'
                        # ),
                        BoxComponent(
                            layout='vertical',
                            background_color='#d0f0c0',
                            corner_radius='md',
                            padding_all='lg',
                            action=PostbackAction(label=primary_action_label, data=primary_action_data),
                            contents=[
                                TextComponent(
                                    text=primary_action_label,
                                    color='#057033',
                                    weight='bold',
                                    align='center',
                                    size='lg'
                                )
                            ]
                        ),
                        BoxComponent(
                            layout='vertical',
                            padding_all='lg',
                            background_color='#CBEEF3',  # 藍色背景
                            corner_radius='md',
                            action=MessageAction(label='✏️ 管理提醒對象', text='管理提醒對象'),
                            contents=[
                                TextComponent(
                                    text='✏️ 管理提醒對象',
                                    color='#20538F',  # 藍色文字
                                    align='center',
                                    weight='bold',
                                    size='lg')
                                ]
                            ),                       
                        BoxComponent(
                            layout='vertical',
                            padding_all='lg',
                            background_color='#FCD5CE',  # 紅色背景
                            corner_radius='md',
                            action=MessageAction(label='🗑️ 刪除提醒對象', text='刪除提醒對象'),
                            contents=[
                                TextComponent(
                                    text='🗑️ 刪除提醒對象',
                                    color='#BA181B',  # 紅色文字
                                    align='center',
                                    weight='bold',
                                    size='lg')
                                ]
                            ),
                    ]
                )
            ]
        )
    )
    return FlexSendMessage(alt_text=title, contents=bubble)


def create_patient_selection_message(members: list, action_prefix: str):
    """產生選擇成員的快速回覆訊息。"""
    if not members:
        members = [{'member': '本人'}]

    items = []
    for patient in members:
        member_name = patient['member']
        if action_prefix == 'scan':
            action = 'select_patient_for_scan'
            displayText = f"為「{member_name}」掃描藥單"
        else: # query
            action = 'list_records'
            displayText = f"為「{member_name}」查詢藥歷"
        
        items.append(QuickReplyButton(
            action=PostbackAction(
                label=member_name, 
                data=f"action={action}&member={quote(member_name)}", 
                text=displayText
            )
        ))
    
    # 移除管理成員按鈕
    
    prompt_text = "請問這份新藥單是給誰的？" if action_prefix == 'scan' else "請問您想查詢誰的藥歷？"
    return TextSendMessage(text=prompt_text, quick_reply=QuickReply(items=items))


def create_upload_instructions(liff_camera_url: str):
    """產生上傳藥單照片的指示。"""
    instruction_card = FlexSendMessage(
        alt_text="上傳藥單照片須知",
        contents=BubbleContainer(
            header=BoxComponent(
                layout="vertical",
                contents=[TextComponent(text="上傳藥單照片須知", weight="bold", size="lg", color="#FFFFFF")],
                backgroundColor="#007BFF"
            ),
            body=BoxComponent(
                layout="vertical", spacing="lg",
                contents=[
                    TextComponent(text="為了讓 AI 能看得更清楚，请您：", weight="bold", wrap=True),
                    BoxComponent(
                        layout="vertical", spacing="sm", margin="md",
                        contents=[
                            TextComponent(text="① 放平藥單，避免摺疊或皺褶。", wrap=True, size="sm"),
                            TextComponent(text="② 完整入鏡，確保藥單四個角都在畫面內。", wrap=True, size="sm"),
                            TextComponent(text="③ 避免反光，注意燈光，別讓陰影遮住文字。", wrap=True, size="sm")
                        ]
                    )
                ]
            )
        )
    )
    
    action_buttons = TextSendMessage(
        text="請選擇拍照方式：",
        quick_reply=QuickReply(items=[
            QuickReplyButton(action=CameraAction(label="📸 開啟相機拍照")),
            QuickReplyButton(action=URIAction(label="📂 從相簿上傳", uri=liff_camera_url))
        ])
    )
    
    return [instruction_card, action_buttons]


def _create_info_row(label: str, value: str):
    return BoxComponent(
        layout="baseline", spacing="sm",
        contents=[
            TextComponent(text=label, color="#aaaaaa", size="sm", flex=2),
            TextComponent(text=value, wrap=True, color="#666666", size="sm", flex=5)
        ]
    )


def generate_analysis_report_messages(analysis_result: dict, frequency_map: dict, liff_edit_id: str, liff_reminder_id: str, member_name: str, is_direct_view=False, source=""):
    """根據 AI 分析結果或資料庫紀錄，產生包含輪播和對應快速回覆的訊息列表。"""
    structured_drugs = analysis_result.get("medications", [])
    if not structured_drugs: 
        return [TextSendMessage(text="分析結果中不包含藥物資訊。")]

    # 【新增】為每個藥品補充圖片資訊和食物藥物交互作用（如果有 matched_drug_id）
    from app.utils.db import DB
    for drug in structured_drugs:
        matched_id = drug.get('matched_drug_id')
        if matched_id:
            # 查詢資料庫獲取完整藥品資訊
            drug_info = DB.get_pills_details_by_ids([matched_id])
            if drug_info and len(drug_info) > 0:
                drug_detail = drug_info[0]
                # 補充圖片 URL
                if not drug.get('image_url'):
                    drug['image_url'] = drug_detail.get('image_url')
                # 補充食物藥物交互作用
                if not drug.get('interactions') and not drug.get('food_drug_interactions'):
                    drug['interactions'] = drug_detail.get('interactions')

    display_date = analysis_result.get('visit_date', "日期未知")
    columns = []

    for drug in structured_drugs:
        if not isinstance(drug, dict): continue
        
        drug_name = drug.get("drug_name_zh") or drug.get("drug_name_en") or "(未命名藥物)"
        main_use = drug.get("main_use") or "請參考藥袋說明"
        side_effects = drug.get("side_effects") or "請參考藥袋說明"
        # 新增食物藥物交互作用
        interactions = drug.get("interactions") or drug.get("food_drug_interactions") or "暫無資料"
        dosage = (drug.get('dose_quantity') or "劑量未知")
        if dosage and hasattr(dosage, 'strip'):
            dosage = dosage.strip()
        else:
            dosage = str(dosage) if dosage is not None else "劑量未知"
        
        count_code = drug.get('frequency_count_code')
        count_text = frequency_map.get(count_code, {}).get('frequency_name', '')
        raw_frequency_text = drug.get('frequency_text')
        frequency = count_text if count_text else (raw_frequency_text or "用法未知")

        # 【新增】條件性添加藥品圖片背景
        bubble_components = {}
        
        # 檢查是否有藥品圖片，如果有則添加 hero 區塊
        image_url = drug.get('image_url')
        if image_url and str(image_url).strip():
            bubble_components['hero'] = ImageComponent(
                url=image_url,
                size="full",
                aspect_ratio="20:13",
                aspect_mode="cover"
            )
        
        # 保持原有的 header 和 body 結構
        bubble_components['header'] = BoxComponent(
            layout="vertical", contents=[
                TextComponent(text="看診日期", color="#000000", size="sm"),
                TextComponent(text=str(display_date), color="#000000", size="lg", weight="bold")
            ], backgroundColor="#007BFF", paddingTop="15px", paddingBottom="15px"
        )
        
        # 準備body內容，可能包含建立者資訊
        body_contents = [
            TextComponent(text=str(drug_name), weight="bold", size="xl", wrap=True),
            SeparatorComponent(margin="lg"),
            BoxComponent(
                layout="vertical", margin="lg", spacing="sm", contents=[
                    _create_info_row("單次劑量", str(dosage)),
                    _create_info_row("用藥頻率", str(frequency)),
                    SeparatorComponent(margin="md"),
                    _create_info_row("主要用途", str(main_use)),
                    _create_info_row("常見副作用", str(side_effects)),
                    SeparatorComponent(margin="md"),
                    # 食物藥物交互作用使用垂直佈局，避免文字被截斷
                    TextComponent(text="食物藥物交互作用", color="#aaaaaa", size="sm"),
                    TextComponent(text=str(interactions), wrap=True, color="#666666", size="sm", margin="xs")
                ]
            )
        ]
        
        # 如果有建立者資訊，添加到底部
        creator_name = analysis_result.get('creator_name')
        if creator_name:
            created_date = analysis_result.get('created_at')
            if created_date:
                created_str = created_date.strftime('%Y-%m-%d') if hasattr(created_date, 'strftime') else str(created_date)[:10]
                body_contents.append(SeparatorComponent(margin="md"))
                body_contents.append(TextComponent(text=f"📝 由 {creator_name} 建立", size="xs", color="#999999", margin="sm"))
        
        bubble_components['body'] = BoxComponent(
            layout="vertical", spacing="md", contents=body_contents
        )
        
        bubble = BubbleContainer(**bubble_components)
        columns.append(bubble)
        
    if not columns: return [TextSendMessage(text="無法產生用藥提醒卡片。")]
    
    carousel_message = FlexSendMessage(alt_text="藥單分析結果", contents=CarouselContainer(contents=columns))
    
    messages_to_send = [carousel_message]
    
    liff_edit_url = f"https://liff.line.me/{liff_edit_id}"
    
    if is_direct_view:
        info_text = f"這是「{member_name}」在 {display_date} 的藥歷詳細內容。"
        prompt_text = "您可以對這筆歷史記錄進行修改，或返回藥歷列表。"
        # 從歷史記錄修改需要先載入為草稿
        mm_id = analysis_result.get('mm_id')
        if mm_id:
            edit_action = PostbackAction(label="✏️ 我要修改", data=f"action=load_record_as_draft&mm_id={mm_id}", text="載入為草稿並修改")
        else:
            edit_action = URIAction(label="✏️ 我要修改", uri=liff_edit_url)
        
        quick_reply_items = [
            QuickReplyButton(action=edit_action),
            QuickReplyButton(action=PostbackAction(label="返回藥歷列表", data=f"action=list_records&member={quote(member_name)}", text="返回藥歷列表")),
            QuickReplyButton(action=PostbackAction(label="❌ 關閉", data="action=cancel_task", text="❌ 關閉"))
        ]
        messages_to_send.extend([TextSendMessage(text=info_text), TextSendMessage(text=prompt_text, quick_reply=QuickReply(items=quick_reply_items))])
    elif source == "manual_edit":
        info_text = "請確認您手動修改後的藥歷內容是否正確。"
        prompt_text = "確認無誤後，請點擊「確認修改」來儲存。"
        quick_reply_items = [
            QuickReplyButton(action=PostbackAction(label="✅ 確認修改，儲存", data="action=confirm_save_final", text="✅ 確認修改，儲存")),
            QuickReplyButton(action=URIAction(label="✏️ 返回編輯", uri=liff_edit_url)),
            QuickReplyButton(action=PostbackAction(label="❌ 放棄修改", data="action=cancel_task", text="❌ 放棄修改"))
        ]
        messages_to_send.extend([TextSendMessage(text=info_text), TextSendMessage(text=prompt_text, quick_reply=QuickReply(items=quick_reply_items))])
    else: # 預設是初次 AI 分析後
        total_count = len(structured_drugs)
        successful_match_count = analysis_result.get('successful_match_count', 0)
        info_text = f"✅ AI 為「{member_name}」辨識出 {total_count} 種藥物 (其中 {successful_match_count} 種成功對應資料庫)。\n\n請滑動卡片確認內容是否正確。"
        prompt_text = "這是為您分析的結果，請確認："
        quick_reply_items = [
            QuickReplyButton(action=PostbackAction(label="✅ 結果正確，儲存", data="action=confirm_save_final", text="✅ 結果正確，儲存")),
            QuickReplyButton(action=URIAction(label="✏️ 我來手動編輯", uri=liff_edit_url)),
            QuickReplyButton(action=PostbackAction(label="📸 重新拍照", data="action=start_camera", text="📸 重新拍照")),
            QuickReplyButton(action=PostbackAction(label="❌ 放棄操作", data="action=cancel_task", text="❌ 放棄操作"))
        ]
        messages_to_send.extend([TextSendMessage(text=info_text), TextSendMessage(text=prompt_text, quick_reply=QuickReply(items=quick_reply_items))])

    return messages_to_send


def create_ask_visit_date_message():
    """當 AI 未能辨識出看診日期時，發送此訊息要求使用者提供。"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    return FlexSendMessage(
        alt_text="請提供看診日期",
        contents=BubbleContainer(
            body=BoxComponent(
                layout="vertical", spacing="md",
                contents=[
                    TextComponent(text="⚠️ 儲存失敗", weight="bold", color="#FF4F4F"),
                    TextComponent(text="我們未能辨識出藥單上的看診日期，請您手動提供，或點擊下方按鈕使用今天的日期。", wrap=True)
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        action=PostbackAction(
                            type="datetimepicker",
                            label="🗓️ 點此選擇日期",
                            data="action=provide_visit_date",
                            mode="date",
                            initial=today_str,
                            max=today_str
                        ),
                        style="primary"
                    )
                ]
            )
        )
    )


def create_set_reminder_flex(mm_id: int, liff_reminder_id: str):
    """產生藥歷儲存成功後，引導使用者設定提醒的 Flex Message"""
    liff_url = f"https://liff.line.me/{liff_reminder_id}?mm_id={mm_id}"
    return FlexSendMessage(
        alt_text="下一步：設定用藥提醒",
        contents=BubbleContainer(
            size="giga",
            body=BoxComponent(
                layout="vertical", spacing="md",
                contents=[
                    TextComponent(text="✅ 藥歷已成功儲存！", weight="bold", size="lg", align="center", color="#1DB446"),
                    TextComponent(text="下一步，讓我們為這些藥物設定提醒時間，確保您或家人能按時服藥。", wrap=True, align="center", size="sm")
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(action=URIAction(label="下一步：設定用藥提醒", uri=liff_url), style="primary", height="sm", color="#28a745")
                ]
            )
        )
    )

def create_records_carousel(member_name: str, records: list):
    """產生歷史藥歷的輪播 Flex Message"""
    if not records:
        return TextSendMessage(text=f"目前找不到成員「{member_name}」的任何藥歷記錄。")

    columns = []
    for record in records:
        body_contents = [
            TextComponent(text=record.get('clinic_name') or '未知診所', weight="bold", size="lg"),
            TextComponent(text=f"看診日期: {record.get('visit_date').strftime('%Y-%m-%d')}" if record.get('visit_date') else '日期未知', size="sm", color="#888888")
        ]
        if record.get('doctor_name'):
            body_contents.append(TextComponent(text=f"醫師: {record.get('doctor_name')}", size="sm", color="#888888"))
        
        # 添加建立者資訊
        creator_name = record.get('creator_name')
        if creator_name:
            created_date = record.get('created_at')
            if created_date:
                created_str = created_date.strftime('%Y-%m-%d') if hasattr(created_date, 'strftime') else str(created_date)[:10]
                body_contents.append(TextComponent(text=f"📝 由 {creator_name} 於 {created_str} 建立", size="xs", color="#999999"))
        
        card = BubbleContainer(
            body=BoxComponent(layout="vertical", spacing="md", contents=body_contents),
            footer=BoxComponent(
                layout="vertical", spacing="sm",
                contents=[
                    ButtonComponent(action=PostbackAction(label="查看詳細藥物", data=f"action=view_record_details&mm_id={record['mm_id']}")),
                    ButtonComponent(style="link", color="#FF6B6B", action=PostbackAction(label="刪除此筆紀錄", data=f"action=confirm_delete_record&mm_id={record['mm_id']}"))
                ]
            )
        )
        columns.append(card)
        
    return FlexSendMessage(
        alt_text=f"{member_name}的藥歷記錄",
        contents=CarouselContainer(contents=columns)
    )