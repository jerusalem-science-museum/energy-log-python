
import pandas as pd

_DT_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
]

def parse_dt(value, name="date"):
    if isinstance(value, pd.Timestamp):
        return value
    if value is None:
        raise ValueError(f"{name} is None")
    s = str(value).strip()

    try:
        return pd.to_datetime(s, errors="raise")
    except Exception:
        pass

    for fmt in _DT_FORMATS:
        try:
            return pd.to_datetime(s, format=fmt, errors="raise")
        except Exception:
            continue

    raise ValueError(
        f"{name} invalide: '{s}'.\n"
        f"Formats acceptés: YYYY-MM-DD [HH:MM:SS] ou DD-MM-YYYY [HH:MM:SS] ou DD/MM/YYYY [HH:MM:SS].\n"
        f"Ex: 2026-10-31 23:59:59  (ou 31-10-2026 23:59:59)"
    )
