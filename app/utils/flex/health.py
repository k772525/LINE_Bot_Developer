# app/utils/flex/health.py - 升級版本

from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent,
    TextComponent, ButtonComponent, URIAction, SeparatorComponent
)

def generate_health_log_menu(liff_url: str):
    """
    生成美化的「健康紀錄」選單，採用現代化卡片設計風格。
    """
    bubble = BubbleContainer(
        header=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='🏥 健康紀錄管理', weight='bold', size='lg', color='#1F2D3D', align='center')
            ],
            background_color='#B9DCEC',
            padding_all='16px'
        ),
        body=BoxComponent(
            layout='vertical', 
            padding_all='20px', 
            spacing='xl',
            contents=[
                # 功能區域
                BoxComponent(
                    layout='vertical', 
                    margin='lg', 
                    spacing='lg',
                    contents=[
                        # 記錄健康數據
                        BoxComponent(
                            layout='vertical',
                            contents=[
                                TextComponent(
                                    text='📊 記錄健康數據',
                                    color='#333333',
                                    weight='bold',
                                    size='md'
                                ),
                                TextComponent(
                                    text='血壓、血糖、體重、體溫等健康指標',
                                    color='#666666',
                                    size='sm',
                                    margin='xs'
                                )
                            ]
                        ),
                        
                        SeparatorComponent(
                            margin='lg',
                            color='#E8E8E8'
                        ),
                        
                        # 查看歷史趨勢
                        BoxComponent(
                            layout='vertical',
                            contents=[
                                TextComponent(
                                    text='📈 查看歷史趨勢',
                                    color='#333333',
                                    weight='bold',
                                    size='md'
                                ),
                                TextComponent(
                                    text='圖表分析，掌握健康變化',
                                    color='#666666',
                                    size='sm',
                                    margin='xs'
                                )
                            ]
                        ),
                        
                        SeparatorComponent(
                            margin='lg',
                            color='#E8E8E8'
                        ),
                        
                        # 家人健康管理
                        BoxComponent(
                            layout='vertical',
                            contents=[
                                TextComponent(
                                    text='👨‍👩‍👧‍👦 家人健康管理',
                                    color='#333333',
                                    weight='bold',
                                    size='md'
                                ),
                                TextComponent(
                                    text='為家人記錄，關愛更貼心',
                                    color='#666666',
                                    size='sm',
                                    margin='xs'
                                )
                            ]
                        )
                    ]
                ),
                
                # 主要行動按鈕
                BoxComponent(
                    layout='vertical',
                    margin='lg',
                    contents=[
                        BoxComponent(
                            layout='vertical',
                            padding_all='16px',
                            background_color='#CBEEF3',
                            corner_radius='12px',
                            action=URIAction(
                                label='🏥 開始使用健康紀錄',
                                uri=liff_url
                            ),
                            contents=[
                                TextComponent(
                                    text='🏥 開始使用健康紀錄',
                                    color='#20538F',
                                    align='center',
                                    weight='bold',
                                    size='lg'
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    )
    
    return FlexSendMessage(alt_text="健康記錄管理", contents=bubble)