# app/utils/flex/member.py

from linebot.models import (
    FlexSendMessage, BubbleContainer, CarouselContainer, BoxComponent,
    TextComponent, ButtonComponent, SeparatorComponent,
    PostbackAction, MessageAction
)

def create_deletable_members_flex(deletable_members: list, user_id: str = None):
    """
    【新增 & 樣式復刻】建立可刪除提醒對象的專業 Flex Message
    """
    if not deletable_members:
        return FlexSendMessage(alt_text="刪除提醒對象", contents=BubbleContainer(
            body=BoxComponent(layout='vertical', padding_all='20px', spacing='lg', contents=[
                TextComponent(text='🗑️ 刪除提醒對象', weight='bold', size='xl', align='center'),
                SeparatorComponent(margin='md'),
                BoxComponent(
                    layout='vertical', background_color='#FEF3C7', corner_radius='12px',
                    padding_all='16px', margin='lg',
                    contents=[
                        TextComponent(text='📝', size='xxl', align='center'),
                        TextComponent(text='沒有可刪除的對象', weight='bold', size='lg', align='center', color='#92400E', margin='md'),
                        TextComponent(text='您目前沒有自己建立的提醒對象可以刪除。', size='sm', align='center', color='#92400E', wrap=True, margin='sm')
                    ]
                ),
                SeparatorComponent(margin='lg'),
                BoxComponent(layout='vertical', spacing='xs', margin='md', contents=[
                    TextComponent(text='💡 說明', size='sm', weight='bold', color='#374151'),
                    TextComponent(text='• 此處只能刪除手動建立的對象。', size='xs', color='#6B7280', margin='xs', wrap=True),
                    TextComponent(text='• 綁定的家人請至「家人綁定與管理」解除。', size='xs', color='#6B7280', wrap=True)
                ])
            ])
        ))

    bubbles = []
    for member in deletable_members:
        # 獲取該成員的提醒筆數
        reminder_count = 0
        if user_id:
            from app.services import reminder_service
            reminders = reminder_service.ReminderService.get_reminders_for_member(user_id, member['member'])
            reminder_count = len(reminders) if reminders else 0
        
        # 根據提醒筆數顯示不同文字
        if reminder_count == 0:
            reminder_text = "無用藥提醒"
            reminder_color = "#8D94A2"
        else:
            reminder_text = f"共{reminder_count}筆提醒"
            reminder_color = "#059669"
        
        bubble = BubbleContainer(
            body=BoxComponent(layout='vertical', padding_all='20px', spacing='md', contents=[
                BoxComponent(
                    layout='vertical', background_color='#FEF2F2', corner_radius='12px',
                    padding_all='16px',
                    contents=[
                        # TextComponent(text='👤', size='xl', align='center'),
                        TextComponent(text=member['member'], weight='bold', size='xl', align='center', color='#B91C1C', margin='sm'),
                        TextComponent(text='(自建對象)', size='xs', align='center', color='#B91C1C', margin='xs')
                    ]
                ),
                SeparatorComponent(margin='md'),
                BoxComponent(
                    layout='vertical',
                    contents=[
                        TextComponent(text=f'📝目前提醒用藥：{reminder_text}', size='sm', align='start', color='#333333', weight='bold')
                    ]
                ),
                SeparatorComponent(margin='lg'),
                TextComponent(text='⚠️ 刪除警告', size='sm', color='#B91C1C', align='start', wrap=True),
                TextComponent(text='刪除後將同時移除所有相關提醒，此操作無法復原！', size='sm', color='#B91C1C', align='start', wrap=True),
                BoxComponent(
                    layout='vertical',
                    padding_all='lg',
                    background_color='#FCD5CE',
                    corner_radius='md',
                    action=PostbackAction(label='🗑️ 確認刪除', data=f"action=delete_member_profile_confirm&member_id={member['id']}"),
                    margin='lg',
                    contents=[
                        TextComponent(
                            text='🗑️ 確認刪除',
                            color='#BA181B',
                            align='center',
                            weight='bold',
                            size='md'
                        )
                    ]
                )
            ])
        )
        bubbles.append(bubble)

    return FlexSendMessage(alt_text="刪除提醒對象", contents=CarouselContainer(contents=bubbles))
