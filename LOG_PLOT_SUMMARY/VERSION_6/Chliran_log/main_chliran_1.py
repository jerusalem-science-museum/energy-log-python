
import os
#import sys
import re
from pathlib import Path
import pandas as pd
#sys.path.append(os.path.dirname(__file__))
from parse_dt_utils import parse_dt
from data_frame import build_df_cycles, build_df_resume, export_excel, write_summary
from CONST_n_PLOT import plot_resume, save_plot, ADVANCED_THRESHOLD_S, SW_LIST

PAT_SPLIT_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*-\s*(.+)$")

PAT_SW = re.compile(r"\b(sw[1-4])\b", re.IGNORECASE)
PAT_PUSH = re.compile(r"\b(push|pressed|down)\b", re.IGNORECASE)
PAT_RELEASE = re.compile(r"\b(release|released|up)\b", re.IGNORECASE)

def _iter_split_files(split_path):
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

def _classify_action(msg: str):
    m_sw = PAT_SW.search(msg)
    if not m_sw:
        return None, None
    sw = m_sw.group(1).upper()

    is_push = bool(PAT_PUSH.search(msg))
    is_rel = bool(PAT_RELEASE.search(msg))

    if is_rel and not is_push:
        return sw, "release"
    if is_push and not is_rel:
        return sw, "push"
    if is_rel and is_push:
        return sw, "release"
    return None, None

def analyze_chliran(split_path, start_dt, end_dt, mode="run", output_path="", project_name="Chliran"):
    start_dt = parse_dt(start_dt, "start_dt")
    end_dt = parse_dt(end_dt, "end_dt")

    split_files = _iter_split_files(split_path)
    if not split_files:
        raise ValueError("Aucun fichier .txt trouvé dans split_path.")

    ev = []
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

                msg = m.group(2).strip()
                sw, action = _classify_action(msg)
                if sw is None:
                    continue
                if sw not in SW_LIST:
                    continue

                ev.append((dt, sw, action, msg))

    if not ev:
        raise ValueError("Aucun événement SW (push/release) détecté dans l’intervalle.")

    ev.sort(key=lambda x: x[0])

    pending_push = {sw: None for sw in SW_LIST}  # sw -> (push_dt, push_msg)

    cycles = []
    for dt, sw, action, msg in ev:
        if action == "push":
            pending_push[sw] = (dt, msg)
        elif action == "release":
            if pending_push[sw] is None:
                continue
            push_dt, push_msg = pending_push[sw]
            pending_push[sw] = None

            duration_s = (dt - push_dt).total_seconds()
            advanced = "YES" if duration_s >= float(ADVANCED_THRESHOLD_S) else "NO"

            cycles.append({
                "SW": sw,
                "PushDateTime": push_dt,
                "ReleaseDateTime": dt,
                "Duration_s": duration_s,
                "Advanced": advanced,
                "Date": push_dt.date(),
                "PushMsg": push_msg,
                "ReleaseMsg": msg
            })

    if not cycles:
        raise ValueError("Aucun cycle complet (push + release) détecté.")

    df_cycles = build_df_cycles(cycles).sort_values("PushDateTime").reset_index(drop=True)
    df_resume = build_df_resume(df_cycles)

    plt_obj = plot_resume(df_resume, start_dt, end_dt, title=f"{project_name} - presses per day (general vs advanced)")

    if mode == "save":
        save_plot(plt_obj, output_path, filename="plot_resume.png")
        write_summary(df_cycles, start_dt, end_dt, output_path, project_name=project_name)
        export_excel(df_cycles, df_resume, output_path, project_name=project_name)
    else:
        if plt_obj is not None:
            plt_obj.show()

if __name__ == "__main__":
    analyze_chliran(
        split_path=r"C:\Users\nathans\Downloads\log_2025-10-05_to_2025-10-31.txt",
        start_dt="2025-10-05 00:00:00",
        end_dt="2025-10-07 23:59:59",
        mode="save",
        output_path=os.path.expanduser("~/Downloads"),
        project_name="Chliran"
    )
