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
_browser_channel_env = os.getenv("SCRAPER_BROWSER_CHANNEL")
SCRAPER_BROWSER_CHANNEL = (
    _browser_channel_env.strip()
    if _browser_channel_env is not None and _browser_channel_env.strip()
    else None
)
_browser_executable_env = os.getenv("SCRAPER_BROWSER_EXECUTABLE")
SCRAPER_BROWSER_EXECUTABLE = (
    _browser_executable_env.strip()
    if _browser_executable_env is not None and _browser_executable_env.strip()
    else None
)
_chrome_user_data_dir_env = os.getenv("SCRAPER_CHROME_USER_DATA_DIR")
SCRAPER_CHROME_USER_DATA_DIR = (
    os.path.expanduser(_chrome_user_data_dir_env.strip())
    if _chrome_user_data_dir_env is not None and _chrome_user_data_dir_env.strip()
    else None
)
_user_agent_env = os.getenv("SCRAPER_USER_AGENT")
if _user_agent_env is None:
    SCRAPER_USER_AGENT = None
else:
    _user_agent_clean = _user_agent_env.strip()
    if not _user_agent_clean or _user_agent_clean.lower() == "auto":
        SCRAPER_USER_AGENT = None
    else:
        SCRAPER_USER_AGENT = _user_agent_clean
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

# Bank-specific filters
# Comma-separated list of Santander credit card last4s to scrape (e.g., "9722,9753").
CL_SANTANDER_CC_LAST4S = [
    s.strip() for s in os.getenv("CL_SANTANDER_CC_LAST4S", "").split(",") if s.strip()
]
