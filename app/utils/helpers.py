# app/utils/helpers.py

import re
from datetime import date

def convert_minguo_to_gregorian(date_str: str | None) -> str | None:
    """
    將民國年格式的日期字串轉換為西元年 (YYYY-MM-DD) 格式。
    如果轉換失敗或格式不符，則回傳原始字串。
    """
    if not date_str:
        return None
        
    date_str = str(date_str).strip()
    
    # 使用更寬鬆的正則表達式匹配 YYY.MM.DD 或 YYY-MM-DD 等格式
    match = re.match(r'(\d{2,3})[.\s/-年](\d{1,2})[.\s/-月](\d{1,2})', date_str)
    
    if not match:
        # 如果不匹配，檢查是否已經是西元年格式
        try:
            date.fromisoformat(date_str)
            return date_str
        except (ValueError, TypeError):
            return date_str # 無法解析，返回原樣

    try:
        year, month, day = [int(g) for g in match.groups()]
        
        # 如果年份小於 150，我們假設它是民國年
        if year < 150:
            gregorian_year = year + 1911
            return date(gregorian_year, month, day).strftime('%Y-%m-%d')
        
        # 否則，我們假設它本來就是西元年
        return date(year, month, day).strftime('%Y-%m-%d')
        
    except ValueError:
        # 如果在轉換過程中 (例如 2 月 30 日) 出錯，返回原始字串
        return date_str