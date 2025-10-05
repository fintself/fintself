# This file makes the 'cl' directory a Python package.
# It exposes scrapers from this country so they can be imported from other modules.

from .banco_chile import BancoChileScraper
from .cencosud import CencosudScraper
from .estado import BancoEstadoScraper
from .santander import SantanderScraper

__all__ = ["BancoChileScraper", "BancoEstadoScraper", "CencosudScraper", "SantanderScraper"]
