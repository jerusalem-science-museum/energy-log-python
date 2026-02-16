
import os
import re
from pathlib import Path
import pandas as pd
from data_frame import build_df_events, build_df_resume, export_excel, write_summary
from CONST_n_PLOT import plot_resume, save_plot

# Split log line format: "YYYY-MM-DD HH:MM:SS - message"
PAT_SPLIT_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*-\s*(.+)$")

BUTTON_KEY = "button pressed"
MOTOR_KEYWORDS = ["motor activated"]

def _iter_split_files(split_path):
    '''
    split_path peut être:
      - str / Path vers un dossier
      - str / Path vers un fichier .txt
      - list[str|Path] : plusieurs dossiers/fichiers
    '''
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

    seen = set()
    uniq = []
    for f in files:
        fp = str(f.resolve())
        if fp not in seen:
            seen.add(fp)
            uniq.append(f)
    return uniq

def analyze_pendulum_from_split(split_path, start_dt, end_dt, mode="save", output_path=""):
    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)

    split_files = _iter_split_files(split_path)
    if not split_files:
        raise ValueError("Aucun fichier .txt trouvé dans split_path.")

    events = []
    for fpath in split_files:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = PAT_SPLIT_LINE.match(line)
                if not m:
                    continue
                dt = pd.to_datetime(m.group(1), errors="coerce")
                if pd.isna(dt):
                    continue
                if dt < start_dt or dt > end_dt:
                    continue

                msg = m.group(2).strip().lower()

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

    df = build_df_events(events).sort_values("DateTime").reset_index(drop=True)
    df_resume = build_df_resume(df)

    plt_obj = plot_resume(df_resume, start_dt, end_dt)

    if mode == "save":
        save_plot(plt_obj, output_path, filename="plot_resume.png")
        write_summary(df, start_dt, end_dt, output_path, project_name="Pendulum")
        export_excel(df, df_resume, output_path, project_name="Pendulum")
    else:
        if plt_obj is not None:
            plt_obj.show()

if __name__ == "__main__":
    analyze_pendulum_from_split(
        split_path=[r"C:\Users\nathans\Downloads\log_2025-09-07_to_2025-09-30.txt", r"C:\Users\nathans\Downloads\log_2025-10-01_to_2025-10-31.txt"],
        start_dt="2025-09-07 00:00:00",
        end_dt="2025-10-31 23:59:59",
        mode="save",
        output_path=os.path.expanduser("~/Downloads")
    )
