# app/utils/flex/reminder.py

from linebot.models import (
    FlexSendMessage, BubbleContainer, CarouselContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    PostbackAction, MessageAction, URIAction
)
from urllib.parse import quote
from flask import current_app

def create_reminder_management_menu():
    """【樣式復刻】產生用藥提醒管理的專業選單 - 包含語音快捷鍵說明輪播。"""
    bubbles = []
    
    # 第一個卡片：用藥提醒管理
    management_bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='🔔 用藥提醒管理', weight='bold', size='lg', color='#1F2D3D', align='center')
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
                        BoxComponent(
                            layout='vertical',
                            padding_all='lg',
                            background_color='#d0f0c0',  # 綠色背景
                            corner_radius='md',
                            action=MessageAction(label='新增提醒 查詢提醒', text='新增/查詢提醒'),
                            contents=[
                                TextComponent(
                                    text='➕新增提醒',
                                    color='#057033',  # 綠色文字
                                    align='center',
                                    weight='bold',
                                    size='lg'),
                                TextComponent(
                                    text='🔍查詢提醒',
                                    color='#057033',  # 綠色文字
                                    align='center',
                                    weight='bold',
                                    size='lg',
                                    margin='xs')
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
    
    # 第二個卡片：語音快捷鍵說明
    voice_guide_bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='🎤 語音快捷鍵說明', weight='bold', size='lg', color='#1F2D3D', align='center')
            ],
            background_color='#FFE4B5',
            padding_all='16px'
        ),
        body=BoxComponent(
            layout='vertical',
            padding_all='18px',
            spacing='md',
            contents=[
                # 語音用藥提醒設定
                BoxComponent(
                    layout='vertical',
                    background_color='#FFF3E0',
                    corner_radius='12px',
                    padding_all='12px',
                    margin='sm',
                    contents=[
                        TextComponent(text='💊 語音用藥提醒設定', weight='bold', size='md', color='#E65100'),
                        TextComponent(text='語音輸入範例：', size='sm', color='#BF360C', margin='xs'),
                        TextComponent(text='"新增用藥提醒，普拿疼，飯後吃，每次一顆"', size='xs', color='#424242', wrap=True, margin='xs'),
                        TextComponent(text='"提醒我每天早上八點吃一顆血壓藥"', size='xs', color='#424242', wrap=True, margin='xs')
                    ]
                ),
                
                # 語音新增家人
                BoxComponent(
                    layout='vertical',
                    background_color='#E8F5E8',
                    corner_radius='12px',
                    padding_all='12px',
                    margin='sm',
                    contents=[
                        TextComponent(text='👨‍👩‍👧‍👦 語音新增家人', weight='bold', size='md', color='#2E7D32'),
                        TextComponent(text='語音輸入範例：', size='sm', color='#1B5E20', margin='xs'),
                        TextComponent(text='"新增提醒對象媽媽"', size='xs', color='#424242', wrap=True, margin='xs'),
                        TextComponent(text='"新增家人爸爸"', size='xs', color='#424242', wrap=True, margin='xs')
                    ]
                ),
                
                # 語音查詢功能
                BoxComponent(
                    layout='vertical',
                    background_color='#E3F2FD',
                    corner_radius='12px',
                    padding_all='12px',
                    margin='sm',
                    contents=[
                        TextComponent(text='🔍 語音查詢功能', weight='bold', size='md', color='#1565C0'),
                        TextComponent(text='語音輸入範例：', size='sm', color='#0D47A1', margin='xs'),
                        TextComponent(text='"查詢本人的用藥提醒"', size='xs', color='#424242', wrap=True, margin='xs'),
                        TextComponent(text='"查詢家人的用藥提醒"', size='xs', color='#424242', wrap=True, margin='xs')
                    ]
                ),
                
                # 使用提示
                BoxComponent(
                    layout='vertical',
                    background_color='#F3E5F5',
                    corner_radius='12px',
                    padding_all='12px',
                    margin='sm',
                    contents=[
                        TextComponent(text='💡 使用提示', weight='bold', size='sm', color='#6A1B9A'),
                        TextComponent(text='• 直接對著手機說話即可', size='xs', color='#424242', margin='xs'),
                        TextComponent(text='• 說話清楚，語速適中', size='xs', color='#424242'),
                        TextComponent(text='• 支援中文語音識別', size='xs', color='#424242')
                    ]
                )
            ]
        )
    )
    
    bubbles.append(management_bubble)
    bubbles.append(voice_guide_bubble)
    
    return FlexSendMessage(alt_text="用藥提醒管理與語音快捷鍵", contents=CarouselContainer(contents=bubbles))

def create_member_management_carousel(members_summary: list, liff_manual_reminder_id: str):
    """
    【邏輯強化 & 樣式復刻】產生資訊高度整合的管理提醒對象輪播。
    """
    if not members_summary:
        return FlexSendMessage(alt_text="提醒對象管理", contents=BubbleContainer(
            body=BoxComponent(layout='vertical', padding_all='20px', spacing='lg', contents=[
                TextComponent(text='👥 提醒對象管理', weight='bold', size='xl', align='center'),
                TextComponent(text='尚未建立任何提醒對象。', size='sm', color='#6B7280', wrap=True, margin='md', align='center'),
                ButtonComponent(
                    action=PostbackAction(label='⊕ 新增第一位對象', data='action=add_member_profile'),
                    style='primary', color='#10B981', margin='lg'
                )
            ])
        ))

    bubbles = []
    members_sorted = sorted(members_summary, key=lambda m: 0 if m['member'] == '本人' else 1)

    for m in members_sorted:
        actions = []
        member_name_encoded = quote(m['member'])

        if m['member'] != '本人':
            actions.append(
                BoxComponent(
                    layout='vertical',
                    padding_all='md',
                    background_color='#d0f0c0',  # 綠色背景
                    corner_radius='md',
                    action=PostbackAction(label='✏️修改名稱', data=f"action=rename_member_profile&member_id={m['id']}"),
                    contents=[
                        TextComponent(
                            text='✏️修改名稱',
                            color='#057033',  # 綠色文字
                            align='center',
                            weight='bold',
                            size='md')
                        ]
                    )
            )
        actions.append(BoxComponent(
            layout='vertical',
            padding_all='md',
            background_color='#CBEEF3',  # 藍色背景
            corner_radius='md',
            action=MessageAction(label='🔍查看提醒', text=m['member']),
            contents=[
                TextComponent(
                    text='🔍查看提醒',
                    color='#20538F',  # 藍色文字
                    align='center',
                    weight='bold',
                    size='md')
                    ]
                )
            )
        
        if m.get('reminders_count', 0) > 0:
            actions.append(BoxComponent(
                layout='vertical',
                padding_all='md',
                background_color='#FEFAD7',  # 黃色背景
                corner_radius='md',
                action=PostbackAction(label='🧹清空此對象提醒', data=f"action=clear_reminders_for_member&member_id={m['id']}"),
                contents=[
                    TextComponent(
                        text='🧹清空此對象提醒',
                        color='#7E4802',  # 黃色文字
                        align='center',
                        weight='bold',
                        size='md')
                    ]
                )
            )
        
        bubble = BubbleContainer(
            body=BoxComponent(
                layout='vertical', spacing='md',
                contents=[
                    TextComponent(text=m['member'], weight='bold', size='xl'),
                    TextComponent(text=f"💊 {m.get('reminders_count', 0)} 筆提醒", size='sm', color='#4CAF50' if m.get('reminders_count', 0) > 0 else '#999999', weight='bold'),
                    TextComponent(text=m.get('reminders_preview', '尚無提醒'), size='xs', color='#666666', wrap=True),
                    SeparatorComponent(margin='lg'),
                    BoxComponent(layout='vertical', spacing='sm', contents=actions)
                ]
            )
        )
        bubbles.append(bubble)
    add_bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            paddingAll='20px',
            spacing='lg',
            justify_content='center',
            align_items='center',
            contents=[
                # 主要圖示區域
                BoxComponent(
                    layout='vertical',
                    backgroundColor='#F0FDF4',  # 淺綠色背景
                    cornerRadius='16px',
                    paddingAll='20px',
                    contents=[
                        TextComponent(text='新增提醒對象', weight='bold', size='xl', align='center', color='#059669', margin='md'),
                        TextComponent(text='為家人或自己建立新的提醒對象', size='md', align='center', color='#065F46', wrap=True, margin='sm')
                    ]
                ),
                SeparatorComponent(margin='md'),
                # 說明文字
                BoxComponent(
                    layout='vertical',
                    spacing='xs',
                    margin='md',
                    contents=[
                        TextComponent(text='💡 可以新增的對象', size='sm', weight='bold', color='#374151', align='center'),
                        TextComponent(text='• 家人稱謂：媽媽、爸爸、奶奶', size='xs', color='#6B7280', align='center', margin='xs'),
                        TextComponent(text='• 自訂名稱：任何您想要的稱呼', size='xs', color='#6B7280', align='center')
                    ]
                ),
                
                # 操作按鈕
                BoxComponent(
                    layout='vertical',
                    padding_all='lg',
                    background_color='#d0f0c0',  # 綠色背景
                    corner_radius='md',
                    action=MessageAction(label='➕ 新增提醒對象', text='新增提醒對象'),
                    contents=[
                        TextComponent(
                            text='➕ 新增提醒對象',
                            color='#057033',  # 綠色文字
                            align='center',
                            weight='bold',
                            size='xl'
                        )
                    ]
                )
            ]
        )
    )
    bubbles.append(add_bubble)
    
    return FlexSendMessage(alt_text="提醒對象管理", contents=CarouselContainer(contents=bubbles))

def create_reminder_list_carousel(member: dict, reminders: list, liff_manual_reminder_id: str, page: int = 1, page_size: int = 8):
    """【樣式復刻】產生特定成員的用藥提醒列表輪播"""
    if not reminders:
        liff_url = f"https://liff.line.me/{liff_manual_reminder_id}?mode=add&member_id={member['id']}"
        return FlexSendMessage(alt_text=f"為 {member['member']} 新增提醒", contents=BubbleContainer(
            body=BoxComponent(layout='vertical', spacing='md', padding_all='20px', contents=[
                TextComponent(text=f"為「{member['member']}」新增提醒", weight='bold', size='lg'),
                TextComponent(text='這位成員還沒有任何提醒！', wrap=True, size='sm', color='#64748B', margin='md'),
                BoxComponent(
                    layout='vertical',
                    padding_all='lg',
                    background_color='#d0f0c0',
                    corner_radius='md',
                    action=URIAction(label='👉點此新增第一筆提醒', uri=liff_url),
                    contents=[
                        TextComponent(
                            text='👉點此新增第一筆提醒',
                            color='#057033',
                            align='center',
                            weight='bold',
                            size='lg'
                        )
                    ]
                )
            ])
        ))

    # 分頁邏輯
    total_reminders = len(reminders)
    total_pages = (total_reminders + page_size - 1) // page_size  # 向上取整
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_reminders)
    current_page_reminders = reminders[start_idx:end_idx]
    
    bubbles = []
    for r in current_page_reminders:
        notified_party_name = r.get('member') 
        time_slots = []
        for i in range(1, 6):
            time_val = r.get(f'time_slot_{i}')
            if time_val:
                # 處理 timedelta 和 datetime.time 物件
                if hasattr(time_val, 'total_seconds'): # timedelta
                    seconds = int(time_val.total_seconds())
                    hours, remainder = divmod(seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    time_slots.append(f"{hours:02d}:{minutes:02d}")
                elif hasattr(time_val, 'strftime'): # datetime.time
                    time_slots.append(time_val.strftime('%H:%M'))
                else: # string
                    time_slots.append(str(time_val))

        time_info = ", ".join(time_slots) if time_slots else "未設定"
        
        edit_liff_url = f"https://liff.line.me/{liff_manual_reminder_id}?mode=edit&reminder_id={r['id']}"
        
        bubble = BubbleContainer(
            body=BoxComponent(layout='vertical', padding_all='16px', spacing='md', contents=[
                TextComponent(text=r.get('drug_name', '未設定藥名'), weight='bold', size='xl'),
                SeparatorComponent(margin='md'),
                BoxComponent(layout='baseline',spacing='md', margin='md', contents=[
                    TextComponent(text='提醒對象 :', color='#aaaaaa', size='md', flex=2),
                    TextComponent(text=notified_party_name, color='#1E90FF', size='md', flex=5, weight='bold')
                ]),
                BoxComponent(layout='vertical', spacing='xs', contents=[
                    TextComponent(text='時間 :', color='#aaaaaa', size='md', flex=2),
                    *[TextComponent(text=f'          {slot}', color='#666666', size='md') for slot in (time_slots if time_slots else ['未設定'])]
                ]),
                BoxComponent(layout='baseline', spacing='sm', contents=[
                    TextComponent(text='劑量 :', color='#aaaaaa', size='md', flex=2),
                    TextComponent(text=r.get('dose_quantity') or '未設定', color='#666666', size='sm', flex=8, wrap=True)
                ]),
                BoxComponent(layout='baseline', spacing='sm', contents=[
                    TextComponent(text='備註 :', color='#aaaaaa', size='md', flex=2),
                    TextComponent(text=r.get('notes') or '無', color='#666666', size='sm', flex=8, wrap=True)
                ]),
            ]),
            footer=BoxComponent(layout='horizontal', spacing='sm', padding_all='8px', 
                                contents=[
                                    BoxComponent(
                                        layout='vertical',
                                        padding_all='lg',
                                        background_color='#d0f0c0',
                                        corner_radius='md',
                                        action=URIAction(label='✏️編輯', uri=edit_liff_url),
                                        contents=[
                                            TextComponent(
                                                text='✏️編輯',
                                                color='#057033',
                                                align='center',
                                                weight='bold',
                                                size='md'
                                            )
                                        ]
                                    ),
                                    BoxComponent(
                                        layout='vertical',
                                        padding_all='lg',
                                        background_color='#FCD5CE',
                                        corner_radius='md',
                                        action=PostbackAction(label='🗑️刪除', data=f"action=delete_reminder&reminder_id={r['id']}"),
                                        contents=[
                                            TextComponent(
                                                text='🗑️刪除',
                                                color='#BA181B',
                                                align='center',
                                                weight='bold',
                                                size='md'
                                            )
                                        ]       
                                    )
                # ButtonComponent(action=URIAction(label='✏️編輯', uri=edit_liff_url), style='primary', color='#3B82F6', flex=1),
                # ButtonComponent(action=PostbackAction(label='🗑️刪除', data=f"action=confirm_delete_reminder&reminder_id={r['id']}"), style='secondary', color='#EF4444', flex=1)
            ])
        )
        bubbles.append(bubble)

    # 添加分頁導航卡片（如果有多頁）
    if total_pages > 1:
        navigation_bubble = create_pagination_bubble(member, page, total_pages, total_reminders)
        bubbles.append(navigation_bubble)
    
    return FlexSendMessage(alt_text=f"{member['member']} 的用藥提醒 (第{page}/{total_pages}頁)", contents=CarouselContainer(contents=bubbles))


def create_pagination_bubble(member: dict, current_page: int, total_pages: int, total_reminders: int):
    """創建分頁導航卡片"""
    member_name = member['member']
    
    # 準備按鈕
    buttons = []
    
    # 上一頁按鈕
    if current_page > 1:
        buttons.append(
            ButtonComponent(
                action=PostbackAction(
                    label="⬅️ 上一頁",
                    data=f"action=view_reminders_page&member={member_name}&page={current_page-1}"
                ),
                style="secondary",
                flex=1
            )
        )
    
    # 下一頁按鈕
    if current_page < total_pages:
        buttons.append(
            ButtonComponent(
                action=PostbackAction(
                    label="下一頁 ➡️",
                    data=f"action=view_reminders_page&member={member_name}&page={current_page+1}"
                ),
                style="secondary",
                flex=1
            )
        )
    
    # 如果只有一個按鈕，添加一個佔位按鈕
    if len(buttons) == 1:
        if current_page == 1:  # 只有下一頁
            buttons.insert(0, 
                ButtonComponent(
                    action=MessageAction(label="📋 管理提醒", text="管理提醒對象"),
                    style="primary",
                    flex=1
                )
            )
        else:  # 只有上一頁
            buttons.append(
                ButtonComponent(
                    action=MessageAction(label="📋 管理提醒", text="管理提醒對象"),
                    style="primary",
                    flex=1
                )
            )
    
    return BubbleContainer(
        body=BoxComponent(
            layout="vertical",
            contents=[
                TextComponent(
                    text="📄 分頁導航",
                    weight="bold",
                    size="lg",
                    color="#1DB446"
                ),
                SeparatorComponent(margin="md"),
                TextComponent(
                    text=f"👤 {member_name}",
                    size="md",
                    margin="md"
                ),
                TextComponent(
                    text=f"📊 共 {total_reminders} 個提醒",
                    size="sm",
                    color="#666666",
                    margin="xs"
                ),
                TextComponent(
                    text=f"📖 第 {current_page} / {total_pages} 頁",
                    size="sm",
                    color="#666666",
                    margin="xs"
                )
            ]
        ),
        footer=BoxComponent(
            layout="horizontal",
            spacing="sm",
            contents=buttons
        ) if buttons else None
    )


def create_reminder_options_menu(member: dict):
    """【樣式復刻】產生提醒選項選單"""
    liff_manual_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
    bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical', padding_all='20px', spacing='lg',
            contents=[
                TextComponent(text=f'為「{member["member"]}」設定提醒', weight='bold', size='xl', color='#1F2937', align='center'),
                TextComponent(text='請選擇要進行的操作：', size='md', color='#64748B', align='center', margin='md'),
                SeparatorComponent(margin='lg'),
                BoxComponent(layout='vertical', spacing='md', margin='lg', contents=[
                    BoxComponent(
                        layout='vertical',
                        padding_top='lg',
                        padding_bottom='lg',
                        padding_start='lg',
                        padding_end='lg',
                        background_color='#d0f0c0',
                        corner_radius='md',
                        action=URIAction(label='✏️ 手動新增提醒', uri=f"https://liff.line.me/{liff_manual_id}?mode=add&member_id={member['id']}"),
                        contents=[
                            TextComponent(
                                text='✏️ 手動新增提醒',
                                color='#057033',
                                align='center',
                                weight='bold',
                                size='lg'
                            )
                        ]
                    ),
                    BoxComponent(
                        layout='vertical',
                        padding_top='lg',
                        padding_bottom='lg',
                        padding_start='lg',
                        padding_end='lg',
                        background_color='#FEFAD7',
                        corner_radius='md',
                        action=PostbackAction(label='💊 從藥歷新增提醒', data=f'action=add_from_prescription&member={quote(member["member"])}'),
                        contents=[
                            TextComponent(
                                text='💊 從藥歷新增提醒',
                                color='#7E4802',
                                align='center',
                                weight='bold',
                                size='lg'
                            )
                        ]
                    ),
                    BoxComponent(
                        layout='vertical',
                        padding_top='lg',
                        padding_bottom='lg',
                        padding_start='lg',
                        padding_end='lg',
                        background_color='#CBEEF3',
                        corner_radius='md',
                        action=PostbackAction(label='📋 查看現有提醒', data=f'action=view_existing_reminders&member={quote(member["member"])}'),
                        contents=[
                            TextComponent(
                                text='📋 查看現有提醒',
                                color='#20538F',
                                align='center',
                                weight='bold',
                                size='lg'
                            )
                        ]
                    )
                ])
            ]
        )
    )
    return FlexSendMessage(alt_text=f"為 {member['member']} 設定提醒", contents=bubble)

def create_prescription_records_carousel(member_name: str, records: list):
    """【樣式復刻】產生該成員的藥歷記錄輪播，供選擇設定提醒"""
    if not records:
        return FlexSendMessage(alt_text=f"{member_name} 沒有藥歷記錄", contents=BubbleContainer(
            body=BoxComponent(layout='vertical', spacing='md', padding_all='20px', contents=[
                TextComponent(text=f"「{member_name}」沒有藥歷記錄", weight='bold', size='lg'),
                TextComponent(text='請先掃描藥單建立藥歷，或選擇手動新增提醒。', wrap=True, size='sm', color='#64748B', margin='md'),
            ])
        ))

    bubbles = []
    liff_id = current_app.config['LIFF_ID_PRESCRIPTION_REMINDER']
    for record in records:
        visit_date = record.get('visit_date')
        if visit_date and hasattr(visit_date, 'strftime'): 
            visit_date = visit_date.strftime('%Y-%m-%d')
        elif visit_date:
            visit_date = str(visit_date)
        else:
            visit_date = '未知日期'
        
        bubble = BubbleContainer(
            body=BoxComponent(layout='vertical', spacing='md', padding_all='16px', contents=[
                TextComponent(text=f"📅 {visit_date or '未知日期'}", weight='bold', size='lg', color='#1F2937'),
                SeparatorComponent(margin='sm'),
                BoxComponent(layout='baseline', spacing='sm', margin='md', contents=[
                    TextComponent(text='診所', color='#64748B', size='sm', flex=2),
                    TextComponent(text=record.get('clinic_name') or '未知診所', color='#374151', size='sm', flex=5, wrap=True)
                ]),
                BoxComponent(layout='baseline', spacing='sm', contents=[
                    TextComponent(text='醫師', color='#64748B', size='sm', flex=2),
                    TextComponent(text=record.get('doctor_name') or '未知醫師', color='#374151', size='sm', flex=5, wrap=True)
                ]),
            ]),
            footer=BoxComponent(layout='vertical', contents=[
                ButtonComponent(
                    action=URIAction(label='設定此藥歷的提醒', uri=f"https://liff.line.me/{liff_id}?mm_id={record['mm_id']}"),
                    style='primary', color='#10B981'
                )
            ])
        )
        bubbles.append(bubble)
    
    return FlexSendMessage(alt_text=f"{member_name} 的藥歷記錄", contents=CarouselContainer(contents=bubbles))