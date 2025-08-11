import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from .logging import logger


def parse_chilean_amount(amount_str: Optional[str]) -> Decimal:
    """Parses a Chilean-formatted amount string into a Decimal.

    Handles currency symbols ($, USD), thousand separators (.),
    decimal separators (,), and signs. It's designed to be robust
    against common formatting variations.

    Args:
        amount_str (Optional[str]): The string to parse.

    Returns:
        Decimal: The parsed amount. Returns 0 if the string is invalid.
    """
    if not amount_str:
        return Decimal("0")

    # Clean string: remove currency symbols, whitespace, etc.
    cleaned_str = amount_str.strip()
    # Also remove any whitespace from the string.
    cleaned_str = re.sub(r"(?i)USD|\$|\s", "", cleaned_str)

    # Handle multiple hyphens from string concatenation (e.g., f"-{'-100'}")
    if cleaned_str.startswith("--"):
        cleaned_str = cleaned_str[1:]

    # Standardize separators: In Chile/Europe, '.' is for thousands, ',' for decimals.
    # If a comma is present, we assume it's the decimal separator.
    if "," in cleaned_str:
        cleaned_str = cleaned_str.replace(".", "")  # Remove thousand separators
        cleaned_str = cleaned_str.replace(",", ".")  # Set decimal separator
    else:
        # No comma means any dots are thousand separators
        cleaned_str = cleaned_str.replace(".", "")

    if not cleaned_str:
        return Decimal("0")

    try:
        return Decimal(cleaned_str)
    except InvalidOperation:
        logger.warning(f"Could not parse amount: '{amount_str}'. Returning 0.")
        return Decimal("0")


def parse_chilean_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses a Chilean-formatted date string into a datetime object.

    Handles full dates (DD/MM/YYYY) and partial dates (DD/MM), assuming
    the current year for the latter. If a partial date is in the future,
    it assumes the previous year.

    Args:
        date_str (Optional[str]): The date string to parse.

    Returns:
        Optional[datetime]: The parsed datetime object, or None if it fails.
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    # Common Chilean formats with year
    full_date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]
    for fmt in full_date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # Try parsing DD/MM format
    try:
        # Assumes DD/MM format and current year
        parsed_date = datetime.strptime(f"{date_str}/{datetime.now().year}", "%d/%m/%Y")
        # If the parsed date is in the future, it likely belongs to the previous year
        if parsed_date > datetime.now():
            parsed_date = parsed_date.replace(year=parsed_date.year - 1)
        return parsed_date
    except ValueError:
        pass

    logger.warning(f"Could not parse date: '{date_str}'. Unknown format.")
    return None
