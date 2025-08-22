import json
from decimal import Decimal
from typing import List

import pandas as pd

from fintself.core.exceptions import OutputError
from fintself.core.models import MovementModel
from fintself.utils.logging import logger


def _movements_to_dataframe(movements: List[MovementModel]) -> pd.DataFrame:
    """Converts a list of MovementModel to a Pandas DataFrame."""
    if not movements:
        return pd.DataFrame()

    data = [m.model_dump() for m in movements]
    for row in data:
        for key, value in row.items():
            if isinstance(value, Decimal):
                row[key] = float(value)
    return pd.DataFrame(data)


def save_to_xlsx(movements: List[MovementModel], file_path: str):
    """Saves a list of movements to an XLSX file."""
    try:
        df = _movements_to_dataframe(movements)
        df.to_excel(file_path, index=False, engine="openpyxl")
        logger.info(f"Data saved to XLSX: {file_path}")
    except Exception as e:
        logger.error(f"Error saving to XLSX: {e}", exc_info=True)
        raise OutputError(f"Could not save XLSX file: {e}")


def save_to_csv(movements: List[MovementModel], file_path: str):
    """Saves a list of movements to a CSV file."""
    try:
        df = _movements_to_dataframe(movements)
        df.to_csv(file_path, index=False, encoding="utf-8")
        logger.info(f"Data saved to CSV: {file_path}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}", exc_info=True)
        raise OutputError(f"Could not save CSV file: {e}")


def save_to_json(movements: List[MovementModel], file_path: str):
    """Saves a list of movements to a JSON file."""
    try:
        data = [m.model_dump(mode="json") for m in movements]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Data saved to JSON: {file_path}")
    except Exception as e:
        logger.error(f"Error saving to JSON: {e}", exc_info=True)
        raise OutputError(f"Could not save JSON file: {e}")


def get_output_data(movements: List[MovementModel], output_format: str) -> str:
    """
    Returns the data in the specified format (JSON string or CSV string).
    """
    if not movements:
        return ""

    if output_format == "json":
        return json.dumps(
            [m.model_dump(mode="json") for m in movements], ensure_ascii=False, indent=4
        )
    elif output_format == "csv":
        df = _movements_to_dataframe(movements)
        return df.to_csv(index=False)
    else:
        raise ValueError(
            f"Output format '{output_format}' not supported for direct return."
        )
