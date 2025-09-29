import json
import os
import tempfile
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
    """Saves a list of movements to an XLSX file using an atomic write."""
    tmp_path = None
    try:
        df = _movements_to_dataframe(movements)

        # Create temp file path in destination directory
        dest_dir = os.path.dirname(os.path.abspath(file_path)) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dest_dir, prefix=".tmp-", suffix=".xlsx")
        os.close(fd)  # Close immediately, pandas will create/overwrite it

        # Write Excel to temp path
        with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        # fsync the completed temp file to reduce risk of partial persistence
        with open(tmp_path, "r+b") as f:
            f.flush()
            os.fsync(f.fileno())

        # Atomic replace
        os.replace(tmp_path, file_path)
        tmp_path = None
        logger.info(f"Data saved to XLSX: {file_path}")
    except Exception as e:
        logger.error(f"Error saving to XLSX: {e}", exc_info=True)
        raise OutputError(f"Could not save XLSX file: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def save_to_csv(movements: List[MovementModel], file_path: str):
    """Saves a list of movements to a CSV file using an atomic write."""
    tmp_path = None
    try:
        df = _movements_to_dataframe(movements)

        dest_dir = os.path.dirname(os.path.abspath(file_path)) or "."
        # Use a NamedTemporaryFile to write and fsync safely
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=dest_dir, prefix=".tmp-", suffix=".csv", encoding="utf-8", newline=""
        ) as tmp:
            tmp_path = tmp.name
            df.to_csv(tmp, index=False)
            tmp.flush()
            os.fsync(tmp.fileno())

        os.replace(tmp_path, file_path)
        tmp_path = None
        logger.info(f"Data saved to CSV: {file_path}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}", exc_info=True)
        raise OutputError(f"Could not save CSV file: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def save_to_json(movements: List[MovementModel], file_path: str):
    """Saves a list of movements to a JSON file using an atomic write.

    Writes to a temporary file in the same directory, fsyncs it, and atomically
    replaces the target path to avoid partial reads by external consumers.
    """
    tmp_path = None
    try:
        data = [m.model_dump(mode="json") for m in movements]

        # Ensure destination directory exists (matches prior behavior if already present)
        dest_dir = os.path.dirname(os.path.abspath(file_path)) or "."

        # Create temporary file alongside destination for same-filesystem atomic replace
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=dest_dir, prefix=".tmp-", suffix=".json", encoding="utf-8"
        ) as tmp:
            tmp_path = tmp.name
            json.dump(data, tmp, ensure_ascii=False, indent=4)
            tmp.flush()
            os.fsync(tmp.fileno())

        # Atomic replace
        os.replace(tmp_path, file_path)
        tmp_path = None  # Prevent cleanup removal since it's now the final file
        logger.info(f"Data saved to JSON: {file_path}")
    except Exception as e:
        logger.error(f"Error saving to JSON: {e}", exc_info=True)
        raise OutputError(f"Could not save JSON file: {e}")
    finally:
        # Best-effort cleanup of temp file on failure
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


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
