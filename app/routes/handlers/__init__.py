# app/routes/handlers/__init__.py

# 确保所有处理器都能被正确导入
from . import prescription_handler
from . import reminder_handler

try:
    from . import family_handler
except ImportError:
    family_handler = None

try:
    from . import pill_handler
except ImportError:
    pill_handler = None