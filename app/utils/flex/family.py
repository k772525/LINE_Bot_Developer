# --- 請用此最終版本【完整覆蓋】您的 app/utils/flex/family.py ---

from linebot.models import (
    FlexSendMessage, BubbleContainer, CarouselContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    PostbackAction, MessageAction, URIAction,
    QuickReply, QuickReplyButton
)
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from flask import current_app

def create_family_binding_menu():
    """產生家人綁定功能的專業選單。"""
    bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='👨‍👩‍👧‍👦 家人綁定與管理', weight='bold', size='lg', color='#1F2D3D', align='center')
            ],
            background_color='#B9DCEC',
            padding_all='16px'
        ),
        body=BoxComponent(
            layout='vertical', padding_all='20px', spacing='lg',
            contents=[
                TextComponent(text='透過邀請碼建立家庭健康管理網路', color='#64748B', size='sm', align='center', wrap=True, margin='md'),
                BoxComponent(
                    layout='vertical', spacing='md', margin='lg',
                    contents=[
                                                BoxComponent(
                            layout='vertical',
                            padding_top='lg',
                            padding_bottom='lg',
                            padding_start='lg',
                            padding_end='lg',
                            background_color='#d0f0c0',
                            corner_radius='md',
                            action=PostbackAction(label='🎫 產生邀請碼', data='action=gen_code'),
                            contents=[
                                TextComponent(
                                    text='🎫 產生邀請碼',
                                    color='#057033',
                                    align='center',
                                    weight='bold',
                                    size='lg'
                                )
                            ]
                        ),
                        
                        # 查詢家人按鈕

                        BoxComponent(
                            layout='vertical',
                            padding_top='lg',
                            padding_bottom='lg',
                            padding_start='lg',
                            padding_end='lg',
                            background_color='#CBEEF3',
                            corner_radius='md',
                            action=PostbackAction(label='👥 管理我的家人', data='action=query_family'),
                            contents=[
                                TextComponent(
                                    text='👥 管理我的家人',
                                    color='#20538F',
                                    align='center',
                                    weight='bold',
                                    size='lg'
                                )
                            ]
                        ),
                    ]
                ),
                SeparatorComponent(margin='lg'),
                BoxComponent(
                    layout='vertical', spacing='xs', margin='md',
                    contents=[
                        TextComponent(text='💡 小提示', size='sm', weight='bold', color='#374151'),
                        TextComponent(text='• 邀請碼有效期為10分鐘。', size='xs', color='#6B7280', margin='xs'),
                        TextComponent(text='• 家人輸入「綁定 [邀請碼]」即可開始流程。', size='xs', color='#6B7280', wrap=True),
                        TextComponent(text='• 綁定後即可為家人設定用藥提醒與藥歷。', size='xs', color='#6B7280', wrap=True)
                    ]
                )
            ]
        )
    )
    return FlexSendMessage(alt_text="家人綁定選單", contents=bubble)

def create_invite_code_flex(code: str):
    """
    【最終修正版】產生分享邀請碼的 Flex Message，並在分享內容中包含可點擊的快捷連結。
    """
    bot_id = current_app.config['YOUR_BOT_ID']
    
    # 1. 準備要自動填入的指令文字
    oa_message_text = f"綁定 {code}"
    # 2. 對指令文字進行 URL 編碼
    oa_message_encoded = quote(oa_message_text)
    # 3. 組成【快捷連結】
    binding_url = f"https://line.me/R/oaMessage/{bot_id}/?{oa_message_encoded}"

    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).astimezone(timezone(timedelta(hours=8)))
    expires_at_str = expires_at.strftime("%H:%M")

    # 4. 準備包含【快捷連結】的完整分享訊息
    share_message = f"""🏠 健康藥管家邀請

您好！我想邀請您加入我的健康藥管家。

📱 請點擊下方連結完成綁定：
{binding_url}

或直接在聊天室輸入：
綁定 {code}

⏰ 邀請碼有效期限至 {expires_at_str}"""
    bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            padding_all='20px',
            spacing='lg',
            contents=[
                # 標題區域 emoji 跟文字分兩行
                TextComponent(text='✉️家人邀請碼', weight='bold', size='xl', color='#1F2937', align='center'),
                # 邀請碼顯示區域
                BoxComponent(
                    layout='vertical',
                    background_color='#F8FAFC',
                    corner_radius='12px',
                    padding_all='16px',
                    margin='md',
                    contents=[
                        TextComponent(text='邀請碼', size='sm', color='#64748B', align='center'),
                        TextComponent(text=f"{code}", weight='bold', size='xxl', color='#2667ff', align='center', margin='sm'),
                        TextComponent(text=f"有效期限至 {expires_at_str}", size='xs', color='#64748B', align='center', margin='sm')
                    ]
                ),
                # 分享按鈕區域
                BoxComponent(
                    layout='vertical',
                    spacing='sm',
                    margin='lg',
                    contents=[
                        BoxComponent(
                            layout='vertical',
                            padding_all='xl',
                            background_color='#d0f0c0',
                            corner_radius='md',
                            action=URIAction(label='📲 立即分享給家人', uri=f"https://line.me/R/share?text={quote(share_message)}"),
                            contents=[
                                TextComponent(
                                    text='📲 立即分享給家人',
                                    color='#057033',
                                    align='center',
                                    weight='bold',
                                    size='lg'
                                )
                            ]
                        )
                    ]
                ),
                SeparatorComponent(margin='lg'),
                BoxComponent(
                    layout='vertical',
                    spacing='xs',
                    margin='md',
                    contents=[
                        TextComponent(text='💡 使用說明', size='sm', weight='bold', color='#374151'),
                        TextComponent(text='1. 點擊「立即分享」按鈕傳送完整邀請訊息', size='xs', color='#6B7280', margin='xs'),
                        TextComponent(text='2. 或請家人直接輸入：綁定 ' + code, size='xs', color='#6B7280'),
                        TextComponent(text='3. 邀請碼10分鐘後自動失效', size='xs', color='#EF4444', margin='xs')
                    ]
                )
            ]
        )
    )
    return FlexSendMessage(alt_text="家人邀請碼已產生", contents=bubble)

def create_binding_confirmation_flex(code: str):
    """產生邀請碼確認的專業 Flex Message。"""
    bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            padding_all='20px',
            spacing='lg',
            contents=[
                # 標題區域
                TextComponent(text='🔐綁定確認', weight='bold', size='xl', color='#1F2937', flex=1,align='center'),

                # 邀請碼顯示區域
                BoxComponent(
                    layout='vertical',
                    background_color='#E9FCFF',
                    corner_radius='12px',
                    padding_all='16px',
                    margin='md',
                    contents=[
                        TextComponent(text='✉️', size='sm', align='center'),
                        TextComponent(text='收到邀請碼', size='sm', color='#20538F', align='center'),
                        TextComponent(text=f"{code}", weight='bold', size='xl', color="#0060CE", align='center', margin='sm'),
                        SeparatorComponent(margin='sm'),
                        TextComponent(text='確定要與此使用者建立綁定關係嗎？', size='sm', color="#000000", align='center'),
                    ]
                ),

                # 按鈕區域
                BoxComponent(
                    layout='horizontal',
                    spacing='sm',
                    margin='lg',
                    contents=[
                        BoxComponent(
                            layout='vertical',
                            padding_all='lg',
                            background_color='#d0f0c0',
                            corner_radius='md',
                            action=PostbackAction(label='✅ 確認綁定', data=f'action=confirm_bind&code={code}'),
                            flex=1,
                            contents=[
                                TextComponent(
                                    text='✅ 確認綁定',
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
                            action=PostbackAction(label='❌ 取消', data='action=cancel_bind'),
                            flex=1,
                            contents=[
                                TextComponent(
                                    text='❌ 取消',
                                    color='#BA181B',
                                    align='center',
                                    weight='bold',
                                    size='md'
                                )
                            ]
                        )
                    ]
                ),
                
                # 安全提示
                SeparatorComponent(margin='lg'),
                BoxComponent(
                    layout='vertical',
                    background_color='#FEFAD7',
                    corner_radius='12px',
                    padding_all='16px',
                    margin='md',
                    contents=[
                        TextComponent(text='🛡️ 安全提示', size='sm', weight='bold', color='#7E4802'),
                        TextComponent(text='• 請確認邀請碼來源可信', size='xs', color='#7E4802', margin='xs'),
                        TextComponent(text='• 綁定後對方可為您設定提醒', size='xs', color='#7E4802'),
                        TextComponent(text='• 您也可以為對方設定提醒', size='xs', color='#7E4802')
                    ]
                )
            ]
        )
    )
    return FlexSendMessage(alt_text="邀請碼綁定確認", contents=bubble)

def create_family_manager_carousel(family_list: list):
    """產生管理已綁定家人的專業輪播 Flex Message。"""
    if not family_list:
        return FlexSendMessage(alt_text="家人管理", contents=BubbleContainer(
            body=BoxComponent(
                layout='vertical', padding_all='20px', spacing='lg',
                contents=[
                    TextComponent(text='👥 家人管理', weight='bold', size='xl', color='#1F2937', align='center'),
                    TextComponent(text='尚未綁定家人，開始邀請家人加入您的健康管理網路吧！', size='sm', color='#6B7280', wrap=True, margin='md', align='center'),
                        BoxComponent(
                        layout='vertical',
                        padding_top='lg',
                        padding_bottom='lg',
                        padding_start='lg',
                        padding_end='lg',
                        background_color='#d0f0c0',
                        corner_radius='md',
                    action=PostbackAction(label='🎫 產生邀請碼', data='action=gen_code'),
        contents=[
            TextComponent(
                text='🎫 產生邀請碼',
                color='#057033',
                align='center',
                weight='bold',
                size='lg'
            )
        ]
    ),
        #             ButtonComponent(
        #                 action=PostbackAction(label='🎫 產生邀請碼', data='action=gen_code'),
        #                 style='primary', color='#10B981', margin='lg'
        #             )
                ]
            )
         ))

    bubbles = []
    for member in family_list:
        nickname = member['relation_type']
        display_name = member.get('recipient_name', '家人')
        bubble = BubbleContainer(
            body=BoxComponent(
                layout='vertical',
                paddingAll='20px',
                spacing='lg',
                contents=[
                    # 家人資訊區域
                    BoxComponent(
                        layout='vertical',
                        background_color='#E9FCFF',
                        corner_radius='12px',
                        padding_all='16px',
                        contents=[

                            TextComponent(text=nickname, weight='bold', size='xl', align='center', color='#1F2937', margin='sm'),
                            TextComponent(text=f'姓名：{display_name}', size='sm', align='center', color='#64748B', margin='xs')
                        ]
                    ),
                    
                    # 操作按鈕區域
                    BoxComponent(
                        layout='vertical',
                        spacing='sm',
                        margin='lg',
                        contents=[
                            BoxComponent(
                                layout='vertical',
                                padding_all='lg',
                                background_color='#d0f0c0',
                                corner_radius='md',
                                action=PostbackAction(label='✏️ 修改稱謂', data=f"action=edit_nickname&nickname={nickname}"),
                                contents=[
                                    TextComponent(
                                        text='✏️ 修改稱謂',
                                        color='#057033',
                                        align='center',
                                        weight='bold',
                                        size='lg'
                                    )
                                ]
                            ),
                            BoxComponent(
                                layout='vertical',
                                padding_all='lg',
                                background_color='#FCD5CE',
                                corner_radius='md',
                                margin='sm',
                                action=PostbackAction(label='🔓 解除綁定', data=f"action=delete_binding&nickname={nickname}"),
                                contents=[
                                    TextComponent(
                                        text='🔓 解除綁定',
                                        color='#BA181B',
                                        align='center',
                                        weight='bold',
                                        size='lg'
                                    )
                                ]
                            )
                        ]
                    ),
                    
                    # 提示說明
                    SeparatorComponent(margin='lg'),
                    BoxComponent(
                        layout='vertical',
                        spacing='xs',
                        margin='sm',
                        contents=[
                            TextComponent(text='💡 提示', size='xs', weight='bold', color='#374151'),
                            TextComponent(text='• 修改稱謂不會影響現有提醒', size='xs', color='#6B7280', margin='xs'),
                            TextComponent(text='• 解除綁定後無法為對方設定提醒', size='xs', color='#6B7280')
                        ]
                    )
                ]
            )
        )
        bubbles.append(bubble)
    
    # 在輪播最後添加美化的邀請更多家人卡片
    add_invite_bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            padding_all='20px',
            spacing='lg',
            justify_content='center',
            align_items='center',
            contents=[
                # 主要圖示區域
                BoxComponent(
                    layout='vertical',
                    background_color="#FFFFFF",
                    corner_radius='16px',
                    padding_all='20px',
                    contents=[
                        TextComponent(text='邀請更多家人', weight='bold', size='xl', align='center', color='#0369A1', margin='md'),
                        TextComponent(text='擴展您的家庭健康管理網路', size='md', align='center', color='#0C4A6E', wrap=True, margin='sm')
                    ]
                ),
                SeparatorComponent(margin='md'),
                # 說明文字
                BoxComponent(
                    layout='vertical',
                    spacing='xs',
                    margin='md',
                    contents=[
                        TextComponent(text='💡 邀請步驟說明', size='sm', weight='bold', color='#374151', align='center'),
                        TextComponent(text='• 點擊下方按鈕產生邀請碼', size='xs', color='#6B7280', align='center', margin='xs'),
                        TextComponent(text='• 分享邀請訊息給家人完成綁定', size='xs', color='#6B7280', align='center')
                    ]
                ),
                
                # 操作按鈕
                BoxComponent(
                    layout='vertical',
                    padding_all='lg',
                    background_color='#CBEEF3',
                    corner_radius='md',
                    action=PostbackAction(label='🎫 產生邀請碼', data='action=gen_code'),
                    contents=[
                        TextComponent(
                            text='🎫 產生邀請碼',
                            color='#20538F',
                            align='center',
                            weight='bold',
                            size='xl'
                        )
                    ]
                )
            ]
        )
    )
    bubbles.append(add_invite_bubble)
    
    return FlexSendMessage(alt_text="家人管理清單", contents=CarouselContainer(contents=bubbles))

def create_relation_quick_reply():
    """建立稱謂選擇的快速回覆按鈕。"""
    items = [
        QuickReplyButton(action=PostbackAction(label="爸爸", data="relation:爸爸", text="我選擇了「爸爸」")),
        QuickReplyButton(action=PostbackAction(label="媽媽", data="relation:媽媽", text="我選擇了「媽媽」")),
        QuickReplyButton(action=PostbackAction(label="兒子", data="relation:兒子", text="我選擇了「兒子」")),
        QuickReplyButton(action=PostbackAction(label="女兒", data="relation:女兒", text="我選擇了「女兒」")),
        QuickReplyButton(action=PostbackAction(label="其他", data="relation:other"))
    ]
    return QuickReply(items=items)