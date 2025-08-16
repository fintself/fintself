import os

from dotenv import load_dotenv

# Cargar variables de entorno desde .env file
load_dotenv(override=True)

# Scraper Configuration
# Enable debug file generation for scrapers. Set to "true" to enable.
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Determines if browser automation runs in headless mode.
# Set to "true", "1", or "yes" for headless, otherwise defaults to non-headless (False).
SCRAPER_HEADLESS_MODE = os.getenv("SCRAPER_HEADLESS_MODE", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Scraper Anti-Detection and Behavior Hyperparameters
SCRAPER_DEFAULT_TIMEOUT = int(os.getenv("SCRAPER_DEFAULT_TIMEOUT", "15000"))  # ms
_slow_mo_env = os.getenv("SCRAPER_SLOW_MO")
SCRAPER_SLOW_MO = (
    int(_slow_mo_env) if _slow_mo_env is not None and _slow_mo_env.isdigit() else 100
)  # ms, default 100
SCRAPER_USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
)
SCRAPER_VIEWPORT_WIDTH = int(os.getenv("SCRAPER_VIEWPORT_WIDTH", "1366"))
SCRAPER_VIEWPORT_HEIGHT = int(os.getenv("SCRAPER_VIEWPORT_HEIGHT", "768"))
SCRAPER_LOCALE = os.getenv("SCRAPER_LOCALE", "es-CL")
SCRAPER_TIMEZONE_ID = os.getenv("SCRAPER_TIMEZONE_ID", "America/Santiago")
SCRAPER_MIN_HUMAN_DELAY_MS = float(
    os.getenv("SCRAPER_MIN_HUMAN_DELAY_MS", "200.0")
)  # ms
SCRAPER_MAX_HUMAN_DELAY_MS = float(
    os.getenv("SCRAPER_MAX_HUMAN_DELAY_MS", "800.0")
)  # ms
