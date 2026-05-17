from .chat import chat_router
from .documents import doc_router
from .health import health_router
from .settings import settings_router

__routers__ = [chat_router, doc_router, health_router, settings_router] 