"""
@description: this file contains global variables
"""

from __future__ import annotations
from share.types import TYPE_CHECKING

if TYPE_CHECKING:
    from logger.logger import AppLog
    from db_manager.file_manager import FileManager
    from db_manager.event_manager import EventManager
    from rag.rag_system import RAGSystem
    from share.types import Config
    from cachetools import TTLCache

CONFIG: Config = None
APP_LOG: AppLog = None

RAG_SYSTEM: RAGSystem = None

EVENT_MANAGER: EventManager = None
FILE_MANAGER: FileManager = None

CACHE: TTLCache = None
UNUSED_ID_CACHE: TTLCache = None
