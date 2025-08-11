# This file exposes the main public API, such as `get_scraper`.
from .scrapers import get_scraper
from .core.models import MovementModel

__all__ = ["get_scraper", "MovementModel"]
