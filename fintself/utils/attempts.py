import json
import os
from datetime import datetime, timezone

from fintself import settings
from fintself.utils.logging import logger


def _state_dir_and_path():
    path = settings.ATTEMPT_STATE_PATH
    directory = os.path.dirname(path) or "."
    return directory, path


def _load_state() -> dict:
    directory, path = _state_dir_and_path()
    try:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(path):
            return {"attempts": {}}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load attempt state from {path}: {e}")
        return {"attempts": {}}


def _save_state(state: dict) -> None:
    _, path = _state_dir_and_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Could not save attempt state to {path}: {e}")


def get_consecutive_failures(bank_id: str) -> int:
    state = _load_state()
    return int(state.get("attempts", {}).get(bank_id, {}).get("consecutive_failures", 0))


def increment_consecutive_failures(bank_id: str) -> int:
    state = _load_state()
    attempts = state.setdefault("attempts", {})
    bank_state = attempts.setdefault(bank_id, {})
    new_count = int(bank_state.get("consecutive_failures", 0)) + 1
    bank_state["consecutive_failures"] = new_count
    bank_state["last_error_ts"] = datetime.now(timezone.utc).isoformat()
    # default to False if not present
    bank_state.setdefault("alert_sent", False)
    _save_state(state)
    return new_count


def reset_consecutive_failures(bank_id: str) -> None:
    state = _load_state()
    attempts = state.setdefault("attempts", {})
    bank_state = attempts.setdefault(bank_id, {})
    bank_state["consecutive_failures"] = 0
    bank_state["alert_sent"] = False
    bank_state.pop("last_error_ts", None)
    _save_state(state)


def is_alert_sent(bank_id: str) -> bool:
    state = _load_state()
    return bool(state.get("attempts", {}).get(bank_id, {}).get("alert_sent", False))


def mark_alert_sent(bank_id: str) -> None:
    state = _load_state()
    attempts = state.setdefault("attempts", {})
    bank_state = attempts.setdefault(bank_id, {})
    bank_state["alert_sent"] = True
    _save_state(state)

