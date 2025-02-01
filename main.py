import logging
from config.config import get_config
from share import var
from logger.logger import AppLog

var.CONFIG = get_config()
var.APP_LOG = AppLog(
    "AppLog", log_level=logging.INFO, timezone=var.CONFIG.general.timezone
)

var.APP_LOG.info("Initializing...")

from db_manager.file_manager import FileManager
from db_manager.event_manager import EventManager
from rag.rag_system import RAGSystem
from cachetools import TTLCache


var.RAG_SYSTEM = RAGSystem(
    openai_api_key=var.CONFIG.openai.api_key,
    db_dir=var.CONFIG.db.vector.dir,
)
var.RAG_SYSTEM.init_vector_store()
var.EVENT_MANAGER = EventManager(var.CONFIG.db.event.path)
var.FILE_MANAGER = FileManager(var.CONFIG.db.file.path)
var.CACHE = TTLCache(
    maxsize=var.CONFIG.cache.general.maxsize, ttl=var.CONFIG.cache.general.ttl
)
var.UNUSED_ID_CACHE = TTLCache(
    maxsize=var.CONFIG.cache.unused_id.maxsize, ttl=var.CONFIG.cache.unused_id.ttl
)

import asyncio
from server.server import serve

if __name__ == "__main__":
    try:
        var.APP_LOG.info("The app is about to start...")
        asyncio.run(serve())
    except KeyboardInterrupt:
        var.APP_LOG.info("Terminatined by user")
    except Exception as e:
        var.APP_LOG.critical(f"Error occurred: {e}")
    finally:
        var.APP_LOG.info("Release resources...")
        var.RAG_SYSTEM.client.close()
        var.EVENT_MANAGER.pool.close_all()
        var.FILE_MANAGER.pool.close_all()
