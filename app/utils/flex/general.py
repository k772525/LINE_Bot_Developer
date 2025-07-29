# app/utils/flex/general.py

from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    MessageAction, PostbackAction, URIAction
)

def create_main_menu():
    """
    產生整合後的主選單 FlexMessage。
    包含「用藥提醒」和「家人綁定」兩大功能。
    """
    bubble = BubbleContainer(
        body=BoxComponent(
            layout='vertical',
            padding_all='20px',
            spacing='xl',
            contents=[
                TextComponent(text='家庭健康小幫手', weight='bold', size='xl', align='center', color='#333333'),
                TextComponent(text='管理藥單、提醒與家人綁定', align='center', size='sm', color='#666666', margin='md'),
                SeparatorComponent(margin='xl'),
                BoxComponent(
                    layout='vertical',
                    spacing='md',
                    margin='lg',
                    contents=[
                        BoxComponent(
                            layout='vertical',
                            padding_all='md',
                            background_color='#007BFF',  # 藍色背景
                            corner_radius='md',
                            action=PostbackAction(label='🤖 掃描新藥單', data='action=start_scan_flow'),
                            contents=[
                                TextComponent(
                                    text='🤖 掃描新藥單',
                                    color='#FFFFFF',  # 白色文字
                                    align='center',
                                    weight='bold',
                                    size='md')
                                ]
                            ),
                        BoxComponent(
                            layout='vertical',
                            padding_all='md',
                            background_color='#17A2B8',  # 青色背景
                            corner_radius='md',
                            action=PostbackAction(label='📂 查詢個人藥歷', data='action=start_query_flow'),
                            margin='sm',
                            contents=[
                                TextComponent(
                                    text='📂 查詢個人藥歷',
                                    color='#FFFFFF',  # 白色文字
                                    align='center',
                                    weight='bold',
                                    size='md')
                                ]
                            ),
                        SeparatorComponent(margin='lg'),
                        BoxComponent(
                            layout='vertical',
                            padding_all='md',
                            background_color='#d0f0c0',  # 綠色背景
                            corner_radius='md',
                            action=MessageAction(label='🔔 用藥提醒管理', text='用藥提醒管理'),
                            contents=[
                                TextComponent(
                                    text='🔔 用藥提醒管理',
                                    color='#057033',  # 綠色文字
                                    align='center',
                                    weight='bold',
                                    size='md')
                                ]
                            ),
                        BoxComponent(
                            layout='vertical',
                            padding_all='md',
                            background_color='#CBEEF3',  # 藍色背景
                            corner_radius='md',
                            action=MessageAction(label='👨‍👩‍👧‍👦 家人綁定與管理', text='家人綁定與管理'),
                            margin='sm',
                            contents=[
                                TextComponent(
                                    text='👨‍👩‍👧‍👦 家人綁定與管理',
                                    color='#20538F',  # 藍色文字
                                    align='center',
                                    weight='bold',
                                    size='md')
                                ]
                            ),
                        BoxComponent(
                            layout='vertical',
                            padding_all='md',
                            background_color='#FF6B6B',  # 紅色背景
                            corner_radius='md',
                            action=MessageAction(label='💊 藥丸辨識', text='藥丸辨識'),
                            margin='sm',
                            contents=[
                                TextComponent(
                                    text='💊 藥丸辨識',
                                    color='#FFFFFF',  # 白色文字
                                    align='center',
                                    weight='bold',
                                    size='md')
                                ]
                            ),
                        BoxComponent(
                            layout='vertical',
                            padding_all='md',
                            background_color='#28A745',  # 綠色背景
                            corner_radius='md',
                            action=MessageAction(label='📊 健康記錄管理', text='健康記錄管理'),
                            margin='sm',
                            contents=[
                                TextComponent(
                                    text='📊 健康記錄管理',
                                    color='#FFFFFF',  # 白色文字
                                    align='center',
                                    weight='bold',
                                    size='md')
                                ]
                            ),
                        BoxComponent(
                            layout='vertical',
                            padding_all='md',
                            background_color='#6C757D',  # 灰色背景
                            corner_radius='md',
                            action=MessageAction(label='⚙️ 設定', text='設定'),
                            margin='sm',
                            contents=[
                                TextComponent(
                                    text='⚙️ 設定',
                                    color='#FFFFFF',  # 白色文字
                                    align='center',
                                    weight='bold',
                                    size='md')
                                ]
                            ),
                    ]
                )
            ]
        )
    )
    return FlexSendMessage(alt_text="功能主選單", contents=bubble)

def create_simple_confirmation(alt_text: str, title: str, text: str, confirm_label: str, confirm_data: str, cancel_label: str = "取消", cancel_data: str = "action=cancel_task"):
    """
    產生一個通用的確認對話框 Flex Message。
    """
    return FlexSendMessage(
        alt_text=alt_text,
        contents=BubbleContainer(
            body=BoxComponent(
                layout='vertical',
                spacing='lg',
                contents=[
                    TextComponent(text=title, weight='bold', size='lg', color="#FF4F4F", align='center'),
                    TextComponent(text=text, wrap=True, margin='lg', align='center'),
                    BoxComponent(
                        layout='horizontal',
                        margin='xxl',
                        spacing='sm',
                        contents=[
                            ButtonComponent(
                                action=PostbackAction(label=cancel_label, data=cancel_data),
                                flex=1,
                                style='secondary'
                            ),
                            ButtonComponent(
                                action=PostbackAction(label=confirm_label, data=confirm_data),
                                flex=1,
                                style='primary',
                                color='#FF4F4F'
                            )
                        ]
                    )
                ]
            )
        )
    )

def create_liff_button(button_text: str, liff_url: str, alt_text: str = "LIFF 按鈕"):
    """
    產生一個 LIFF 按鈕的 Flex Message。
    """
    return FlexSendMessage(
        alt_text=alt_text,
        contents=BubbleContainer(
            body=BoxComponent(
                layout='vertical',
                spacing='md',
                padding_all='lg',
                contents=[
                    TextComponent(
                        text=alt_text,
                        weight='bold',
                        size='lg',
                        align='center',
                        color='#333333'
                    ),
                    ButtonComponent(
                        action=URIAction(label=button_text, uri=liff_url),
                        style='primary',
                        color='#007BFF',
                        margin='lg'
                    )
                ]
            )
        )
    )