import os
from pathlib import Path
from datetime import datetime
import pandas as pd

from data_frame import build_df_events, build_df_resume, export_excel, write_summary
from CONST_n_PLOT import plot_resume, save_plot

# Split log line format: "YYYY-MM-DD HH:MM:SS - message"
# We avoid regex + pd.to_datetime per line for performance.
BUTTON_KEY = "button pressed"
MOTOR_KEYWORDS = ["motor activated"]

# Filenames produced by split_log.py:
#   log_YYYY-MM-DD_to_YYYY-MM-DD.txt
PAT_SPLIT_FILENAME = "log_"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _iter_split_files(split_path):
    """
    split_path peut être:
      - str / Path vers un dossier
      - str / Path vers un fichier .txt
      - list[str|Path] : plusieurs dossiers/fichiers
    """
    if isinstance(split_path, (list, tuple, set)):
        items = list(split_path)
    else:
        items = [split_path]

    files = []
    for item in items:
        p = Path(item)
        if p.is_dir():
            files.extend(sorted(p.glob("*.txt")))
        elif p.is_file():
            files.append(p)
        else:
            raise FileNotFoundError(f"split_path introuvable: {p}")

    # unique
    seen = set()
    uniq = []
    for f in files:
        fp = str(f.resolve())
        if fp not in seen:
            seen.add(fp)
            uniq.append(f)
    return uniq


def _parse_file_date_range(filename: str):
    """
    Parse 'log_YYYY-MM-DD_to_YYYY-MM-DD.txt' -> (date_start, date_end) as datetime.date
    Retourne (None, None) si format inattendu.
    """
    name = os.path.basename(filename)
    if not (name.startswith("log_") and "_to_" in name):
        return None, None
    try:
        core = name[:-4] if name.lower().endswith(".txt") else name
        # core: log_2025-09-07_to_2025-09-30
        a = core.split("log_", 1)[1]
        start_s, end_s = a.split("_to_", 1)
        d1 = datetime.strptime(start_s, "%Y-%m-%d").date()
        d2 = datetime.strptime(end_s, "%Y-%m-%d").date()
        return d1, d2
    except Exception:
        return None, None


def analyze_pendulum(split_path, start_dt, end_dt, mode="save", output_path=""):
    """
    Optimisé:
      - ignore les fichiers split hors intervalle via le nom du fichier
      - parse datetime via datetime.strptime(line[:19]) (beaucoup plus rapide que pd.to_datetime)
      - break dès qu'on dépasse end_dt (sur fichiers chronologiques)
      - pas de readlines() (streaming)
    """
    # Normalize to python datetime
    start_dt = pd.to_datetime(start_dt).to_pydatetime()
    end_dt = pd.to_datetime(end_dt).to_pydatetime()

    split_files = _iter_split_files(split_path)
    if not split_files:
        raise ValueError("Aucun fichier .txt trouvé dans split_path.")

    events = []

    for fpath in split_files:
        # Skip file if filename date range doesn't overlap
        f_start, f_end = _parse_file_date_range(str(fpath))
        if f_start and f_end:
            if f_end < start_dt.date() or f_start > end_dt.date():
                continue

        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line:
                    continue
                line = line.strip()
                if not line:
                    continue

                # Fast parse: first 19 chars are timestamp
                # Expect: "YYYY-MM-DD HH:MM:SS - ..."
                if len(line) < 22:
                    continue
                ts = line[:19]
                try:
                    dt = datetime.strptime(ts, DATE_FMT)
                except Exception:
                    continue

                # Early skip / break
                if dt < start_dt:
                    continue
                if dt > end_dt:
                    # split files should be chronological; we can stop reading this file
                    break

                # Fast message extract
                # split on first " - "
                parts = line.split(" - ", 1)
                if len(parts) != 2:
                    continue
                msg = parts[1].strip().lower()

                if BUTTON_KEY not in msg:
                    continue

                motor = any(k in msg for k in MOTOR_KEYWORDS)

                events.append({
                    "DateTime": dt,
                    "Date": dt.date(),
                    "Motor_Activated": "YES" if motor else "NO",
                    "Message": msg
                })

    if not events:
        raise ValueError("Aucun événement 'button pressed' trouvé dans l’intervalle.")

    # DataFrames
    df = build_df_events(events).sort_values("DateTime").reset_index(drop=True)
    df_resume = build_df_resume(df)

    # Plot (plot_resume filtre déjà par dates)
    plt_obj = plot_resume(df_resume, start_dt, end_dt)

    if mode == "save":
        save_plot(plt_obj, output_path, filename="plot_resume.png")
        write_summary(df, start_dt, end_dt, output_path, project_name="Pendulum")
        export_excel(df, df_resume, output_path, project_name="Pendulum")
    else:
        if plt_obj is not None:
            plt_obj.show()


if __name__ == "__main__":
    analyze_pendulum(
        split_path=[r"C:\Users\nathans\Downloads\log_2025-09-07_to_2025-09-30.txt", r"C:\Users\nathans\Downloads\log_2025-10-01_to_2025-10-31.txt"],
        start_dt="2025-09-07 00:00:00",
        end_dt="2025-09-17 23:59:59",
        mode="save",
        output_path=os.path.expanduser("~/Downloads")
    )
