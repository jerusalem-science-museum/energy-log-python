import os
import re
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional
PAT_INIT = re.compile(r"(\d+)\s*ms\s*;\s*Init", re.IGNORECASE)
PAT_TS   = re.compile(r"(\d+)")

DELTA_TIME_MS = 5 * 3600 * 1000
DAY_START_HOUR = 9
DAY_MS = 24 * 3600 * 1000  # 24h en ms


def month_start(d: datetime) -> datetime:
    return d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def month_end(d: datetime) -> datetime:
    if d.month == 12:
        next_month = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month = d.replace(month=d.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    return last_day.replace(hour=23, minute=59, second=59, microsecond=0)


def iterate_month_ranges(start_dt: datetime, end_dt: datetime):
    cur = start_dt
    while cur <= end_dt:
        ms = month_start(cur)
        me = month_end(cur)

        r_start = cur if cur > ms else ms
        r_end = end_dt if end_dt < me else me

        yield (r_start, r_end)

        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            cur = cur.replace(month=cur.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def extract_message(line: str) -> str:
    if ";" in line:
        msg = line.split(";", 1)[1].strip()
    else:
        msg = line.strip()
    msg = msg.replace("\r", "").replace("\n", "").strip()
    return msg.lower()


def day_base_datetime(start_dt: datetime, day_index: int) -> datetime:
    base_date = (start_dt + timedelta(days=day_index)).date()
    return datetime(base_date.year, base_date.month, base_date.day, DAY_START_HOUR, 0, 0)


def split_log_by_month_with_datetime(file_path: str, start_dt, end_dt, output_dir: Optional[str] = None):
    start_dt = pd.to_datetime(start_dt).to_pydatetime()
    end_dt   = pd.to_datetime(end_dt).to_pydatetime()

    if output_dir is None:
        output_dir = os.path.dirname(file_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    # Trouver le premier Init
    first_init_idx = None
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
            if PAT_INIT.search(line):
                first_init_idx = idx
                break
    if first_init_idx is None:
        raise ValueError("Aucun 'Init' trouvé dans le fichier.")

    # Ouvrir fichiers mensuels
    month_files = {}
    for r_start, r_end in iterate_month_ranges(start_dt, end_dt):
        name = f"log_{r_start.strftime('%Y-%m-%d')}_to_{r_end.strftime('%Y-%m-%d')}.txt"
        out_path = os.path.join(output_dir, name)
        month_files[(r_start.date(), r_end.date())] = open(out_path, "w", encoding="utf-8")

    def get_month_writer(d: datetime):
        for (a, b), fh in month_files.items():
            if a <= d.date() <= b:
                return fh
        return None

    # ====== Etat journée (day_index) ======
    day_index = 0
    prev_init_ref = None
    prev_raw_time = None
    consecutive_init = False

    # ====== Ancre temps ======
    anchor_dt = day_base_datetime(start_dt, day_index)  # 09:00 du jour courant
    anchor_ms = None
    last_dt_line = None
    last_ts_seen = None

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
            m = PAT_TS.search(line)
            if not m:
                continue
            raw_time = int(m.group(1))
            is_init = PAT_INIT.search(line) is not None

            if anchor_ms is None:
                anchor_ms = raw_time

            # reboot (timestamp repart en arrière)
            if last_ts_seen is not None and raw_time < last_ts_seen:
                # on CONTINUE depuis le dernier dt calculé, pas retour à 09:00
                if last_dt_line is not None:
                    anchor_dt = last_dt_line
                    anchor_ms = raw_time
                else:
                    anchor_dt = day_base_datetime(start_dt, day_index)
                    anchor_ms = raw_time
            last_ts_seen = raw_time

            # ====== logique day_index via Init ======
            if is_init:
                if idx == first_init_idx or consecutive_init:
                    prev_init_ref = raw_time
                    consecutive_init = True

                    # premier init => 09:00 jour 0 exactement ici
                    if idx == first_init_idx:
                        anchor_dt = day_base_datetime(start_dt, day_index)
                        anchor_ms = raw_time
                else:
                    if prev_raw_time is None:
                        prev_raw_time = raw_time
                    delta = prev_raw_time - prev_init_ref if prev_init_ref is not None else 0

                    if delta > DELTA_TIME_MS:
                        day_index += 1
                        anchor_dt = day_base_datetime(start_dt, day_index)  # 09:00 nouvelle journée
                        anchor_ms = raw_time

                    prev_init_ref = raw_time
                    consecutive_init = True
            else:
                consecutive_init = False

            prev_raw_time = raw_time

            # ====== NOUVEAU: anti-glissement => avancer automatiquement si > 24h ======
            elapsed_ms = raw_time - anchor_ms
            if elapsed_ms >= DAY_MS:
                extra_days = elapsed_ms // DAY_MS
                day_index += extra_days
                anchor_dt = day_base_datetime(start_dt, day_index)  # 09:00 du nouveau jour
                anchor_ms = anchor_ms + extra_days * DAY_MS
                elapsed_ms = raw_time - anchor_ms  # recalc après shift

            if elapsed_ms < 0:
                elapsed_ms = 0

            dt_line = anchor_dt + timedelta(milliseconds=elapsed_ms)
            last_dt_line = dt_line

            logical_date = start_dt + timedelta(days=day_index)
            if logical_date.date() < start_dt.date() or logical_date.date() > end_dt.date():
                continue

            fh = get_month_writer(logical_date)
            if fh is not None:
                msg = extract_message(line)
                fh.write(f"{dt_line.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

    for fh in month_files.values():
        fh.close()

    print("✅ Terminé : plus de date qui recule, 09:00 seulement vraie nouvelle journée.")


if __name__ == "__main__":
    split_log_by_month_with_datetime(
        file_path=r"C:\Users\natou\Desktop\git_Musee\Energy\chliran\LOG\LOG_DATA\2025_10_05_to_2026_02_09\LOG.TXT",
        start_dt="2025-10-05 00:00:00",
        end_dt="2026-02-09 23:59:59",
        output_dir=r"C:\Users\natou\Downloads"
    )








