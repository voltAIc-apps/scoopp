import logging
import bleach
from pathlib import Path
import os
import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
LOG_DIR = Path(os.environ.get("LOG_DIR", "./logs"))
LOG_FILE = LOG_DIR / "crawl4ai.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)  # ensure it exists

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

COUNTER_FILE = DATA_DIR / "crawl_id.counter"
if not COUNTER_FILE.exists():
    COUNTER_FILE.write_text("0")

def generate_crawl_id() -> str:
    try:
        current = int(COUNTER_FILE.read_text()) + 1
        COUNTER_FILE.write_text(str(current))
        return f"{current:06d}"
    except Exception as e:
        logging.error(f"Failed to generate crawl ID: {e}")
        raise

def save_markdown(crawl_id: str, content: str):
    file_path = DATA_DIR / f"{crawl_id}.md"
    try:
        file_path.write_text(content)
    except Exception as e:
        logging.error(f"Failed to save file {file_path}: {e}")
        raise
    return file_path

async def crawl_and_store_async(url: str, crawl_id: str, crawl_depth: int = None, crawl_timeout: int = None):
    """Async version using crawl4ai AsyncWebCrawler"""
    import configparser
    import time

    config = configparser.ConfigParser()
    config.read(DATA_DIR / "../crawl.config")
    default_depth = int(config.get("settings", "crawl_depth", fallback="2"))
    default_timeout = int(config.get("settings", "crawl_timeout", fallback="10"))

    depth = crawl_depth if crawl_depth is not None else default_depth
    timeout = crawl_timeout if crawl_timeout is not None else default_timeout

    start_time = time.time()
    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(
                url=url,
                word_count_threshold=10,
                bypass_cache=True,
                page_timeout=timeout * 1000  # Convert seconds to milliseconds
            )
            raw_content = result.markdown if result.success else ""

            if not result.success:
                raise Exception(f"Crawl failed: {result.error_message}")

    except Exception as e:
        logging.error(f"Crawl failed for {crawl_id} with error: {e}")
        raise

    duration = time.time() - start_time
    logging.info(f"Crawl completed for {crawl_id} in {duration:.2f} seconds with timeout={timeout}s")

    # Sanitize the markdown content
    sanitized_content = bleach.clean(
        raw_content,
        tags=["p", "a", "ul", "li", "strong", "em", "code", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote"],
        attributes={"a": ["href"]},
        strip=True
    )
    return save_markdown(crawl_id, sanitized_content)

def crawl_and_store(url: str, crawl_id: str, crawl_depth: int = None, crawl_timeout: int = None):
    """Sync wrapper for backward compatibility"""
    return asyncio.run(crawl_and_store_async(url, crawl_id, crawl_depth, crawl_timeout))
