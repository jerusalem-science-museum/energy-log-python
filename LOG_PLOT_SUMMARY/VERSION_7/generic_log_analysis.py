import os
import re
import shutil
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime

import tempfile
from contextlib import contextmanager

import importlib
import importlib.util
from pathlib import Path

def _import_by_path(mod_name: str, file_path: str):
    """Imports a Python module from a file path (works even without __init__.py)."""
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load module {mod_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _try_import_project(project_dir_name: str, main_py: str, const_py: str = None):
    """Attempts to import as a package (if __init__.py exists), otherwise imports by path."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = os.path.join(base_dir, project_dir_name)

    if not os.path.isdir(proj_dir):
        raise ImportError(
            f"Directory '{project_dir_name}' not found.\n"
            f"Expected at: {proj_dir}\n"
            f"➡️ Place the {project_dir_name} folder in the same directory as the GUI."
        )

    init_py = os.path.join(proj_dir, "__init__.py")

    if os.path.isfile(init_py):
        pkg = project_dir_name
        main_mod = importlib.import_module(f"{pkg}.{Path(main_py).stem}")
        const_mod = importlib.import_module(f"{pkg}.{Path(const_py).stem}") if const_py else None
        return main_mod, const_mod

    main_path = os.path.join(proj_dir, main_py)
    if not os.path.isfile(main_path):
        raise ImportError(f"File not found: {main_path}")
    main_mod = _import_by_path(f"{project_dir_name}_{Path(main_py).stem}", main_path)

    const_mod = None
    if const_py:
        const_path = os.path.join(proj_dir, const_py)
        if not os.path.isfile(const_path):
            raise ImportError(f"File not found: {const_path}")
        const_mod = _import_by_path(f"{project_dir_name}_{Path(const_py).stem}", const_path)

    return main_mod, const_mod

@contextmanager
def _no_matplotlib_show():
    """Prevents plt.show() from opening a window or blocking execution."""
    _orig_show = plt.show
    try:
        plt.show = lambda *a, **k: None
        yield
    finally:
        plt.show = _orig_show

def _concat_log_files(files):
    if not files:
        raise ValueError("files is empty")

    if len(files) == 1:
        return files[0], None

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="concat_log_", suffix=".txt")
    os.close(tmp_fd)

    with open(tmp_path, "w", encoding="utf-8", errors="ignore") as out:
        for fp in files:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                out.write(f.read())
            out.write("\n")

    return tmp_path, tmp_path

def analyze_pendulum_adapter(files, start_dt, end_dt, mode="run", output_dir=None, gui_dir=None):
    if gui_dir is None:
        gui_dir = os.getcwd()

    bad = [f for f in files if not os.path.basename(f).lower().startswith("log_")]
    if bad:
        raise ValueError(
            "Pendulum: The selected files do not appear to be split files.\n"
            "You must first run 'split_log.py' individually, then select the 'log_*.txt' files.\n"
            f"Invalid examples: {', '.join(os.path.basename(x) for x in bad[:3])}"
        )

    main_path = _find_project_file(gui_dir, "Pendulum_log", "main_pendulum.py")
    if not main_path:
        raise ImportError("Could not find 'main_pendulum.py' (Pendulum_log folder not found next to GUI).")

    main_mod = _load_module_from_file_compat("Pendulum_main", main_path)

    with _no_matplotlib_show():
        m = "save" if mode == "save" else "run"
        main_mod.analyze_pendulum(
            split_path=files,
            start_dt=start_dt,
            end_dt=end_dt,
            mode=m,
            output_path=output_dir or ""
        )

    fig = plt.gcf() if plt.get_fignums() else None
    return {"project_name": "Pendulum", "special": True}, fig

def analyze_chliran_adapter(files, start_dt, end_dt, mode="run", output_dir=None, gui_dir=None):
    if gui_dir is None:
        gui_dir = os.getcwd()

    bad = [f for f in files if not os.path.basename(f).lower().startswith("log_")]
    if bad:
        raise ValueError(
            "Chliran: The selected files do not appear to be split files.\n"
            "You must first run split_log.py individually, then select the log_*.txt files.\n"
            f"Invalid examples: {', '.join(os.path.basename(x) for x in bad[:3])}"
        )

    main_path = _find_project_file(gui_dir, "Chliran_log", "main_chliran.py")
    if not main_path:
        raise ImportError("main_chliran.py not found (Chliran_log folder is not in the GUI directory).")

    main_mod = _load_module_from_file_compat("Chliran_main", main_path)

    if mode != "save":
        try:
            const_path = _find_project_file(gui_dir, "Chliran_log", "CONST_n_PLOT.py")
            if const_path:
                const_mod = _load_module_from_file_compat("Chliran_const", const_path)
                if hasattr(const_mod, "DOWNLOAD_DIR"):
                    const_mod.DOWNLOAD_DIR = tempfile.mkdtemp(prefix="chliran_run_")
        except Exception:
            pass
    else:
        if output_dir:
            try:
                const_path = _find_project_file(gui_dir, "Chliran_log", "CONST_n_PLOT.py")
                if const_path:
                    const_mod = _load_module_from_file_compat("Chliran_const_save", const_path)
                    if hasattr(const_mod, "DOWNLOAD_DIR"):
                        const_mod.DOWNLOAD_DIR = output_dir
            except Exception:
                pass

    with _no_matplotlib_show():
        m = "save" if mode == "save" else "run"
        main_mod.analyze_chliran(
            split_path=files,
            start_dt=start_dt,
            end_dt=end_dt,
            mode=m,
            output_path=output_dir or "",
            project_name="Chliran"
        )

    fig = plt.gcf() if plt.get_fignums() else None
    return {"project_name": "Chliran", "special": True}, fig

def run_analysis_dispatch(files, start_dt, end_dt, interval, event_config, project_name):
    proj = str(project_name).strip()
    if proj.lower() == "pendulum":
        return analyze_pendulum_adapter(files, start_dt, end_dt, mode="run", gui_dir=os.path.dirname(__file__))
    if proj.lower() == "chliran":
        return analyze_chliran_adapter(files, start_dt, end_dt, mode="run", gui_dir=os.path.dirname(__file__))

    result = analyze_logs(
        files=files,
        start_dt=start_dt,
        end_dt=end_dt,
        interval=interval,
        event_config=event_config,
        project_name=proj
    )
    if not result:
        return None, None
    fig = plot_counts(result, interval)
    return result, fig

def _find_project_file(gui_dir, project_folder, filename):
    cand1 = os.path.join(gui_dir, project_folder, filename)
    cand2 = os.path.join(gui_dir, project_folder, project_folder, filename)
    if os.path.isfile(cand1):
        return cand1
    if os.path.isfile(cand2):
        return cand2
    return None

def _load_module_from_file_compat(module_name, file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    if "|" in src:
        if "from typing import Optional" not in src:
            src = "from typing import Optional\n" + src
        src = re.sub(r"(\b[a-zA-Z_][a-zA-Z0-9_]*\b)\s*\|\s*None", r"Optional[\1]", src)
        src = re.sub(r"None\s*\|\s*(\b[a-zA-Z_][a-zA-Z0-9_]*\b)", r"Optional[\1]", src)

    spec = importlib.util.spec_from_loader(module_name, loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = file_path

    module_dir = os.path.dirname(os.path.abspath(file_path))
    added_path = False

    local_names = []
    try:
        for fn in os.listdir(module_dir):
            if fn.endswith(".py") and fn != "__init__.py":
                local_names.append(os.path.splitext(fn)[0])
    except Exception:
        local_names = []

    saved_modules = {}
    for name in local_names:
        if name in sys.modules:
            saved_modules[name] = sys.modules[name]
            del sys.modules[name]

    if module_dir and module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        added_path = True

    try:
        exec(compile(src, file_path, "exec"), mod.__dict__)
    finally:
        if added_path:
            try:
                sys.path.remove(module_dir)
            except ValueError:
                pass

        for name in local_names:
            if name in sys.modules:
                del sys.modules[name]
        for name, module_obj in saved_modules.items():
            sys.modules[name] = module_obj

    return mod

def _standardize_outputs(target_dir, proj, start_dt, end_dt):
    start_md = start_dt.strftime("%d_%m")
    end_md = end_dt.strftime("%d_%m")

    std_png = os.path.join(target_dir, f"{proj}_{start_md}_to_{end_md}.png")
    std_txt = os.path.join(target_dir, f"summary_{proj}_{start_md}-{end_md}.txt")
    std_xlsx = os.path.join(target_dir, f"{proj}_{start_md}_to_{end_md}.xlsx")

    def _pick_first(ext):
        files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.lower().endswith(ext)]
        if not files:
            return None
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files[0]

    src_png = _pick_first(".png")
    src_txt = _pick_first(".txt")
    src_xlsx = _pick_first(".xlsx")

    def _copy(src_path, dst_path):
        if not src_path or not os.path.isfile(src_path):
            return
        if os.path.abspath(src_path) == os.path.abspath(dst_path):
            return
        try:
            shutil.copy2(src_path, dst_path)
        except Exception:
            pass

    _copy(src_png, std_png)
    _copy(src_txt, std_txt)
    _copy(src_xlsx, std_xlsx)

    keep = {os.path.abspath(std_png), os.path.abspath(std_txt), os.path.abspath(std_xlsx)}

    non_dated_png = {"plot_resume.png", "plot_counts.png"}
    non_dated_txt = {"summary.txt", f"{proj.lower()}_summary.txt"}
    
    def _is_non_dated_xlsx(name):
        n = name.lower()
        return n.endswith("_log.xlsx") or n in {"log_table.xlsx", "pendulum_log.xlsx", "chliran_log.xlsx"}

    for fn in list(os.listdir(target_dir)):
        fp = os.path.join(target_dir, fn)
        if not os.path.isfile(fp):
            continue
        ab = os.path.abspath(fp)

        if ab in keep:
            continue

        low = fn.lower()

        if low.endswith(".png"):
            if low in non_dated_png or True:
                try:
                    os.remove(fp)
                except Exception:
                    pass

        elif low.endswith(".txt"):
            if low in non_dated_txt or low.endswith("_summary.txt") or True:
                try:
                    os.remove(fp)
                except Exception:
                    pass

        elif low.endswith(".xlsx"):
            if _is_non_dated_xlsx(fn) or True:
                try:
                    os.remove(fp)
                except Exception:
                    pass

    missing = []
    if not os.path.isfile(std_png):
        missing.append("PNG")
    if not os.path.isfile(std_txt):
        missing.append("TXT")
    if not os.path.isfile(std_xlsx):
        missing.append("XLSX")
    if missing:
        raise FileNotFoundError(f"Après sauvegarde, fichiers manquants dans {target_dir}: {', '.join(missing)}")

def save_analysis_dispatch(project_name, files, start_dt, end_dt, interval, target_dir, fig=None, result=None, event_config=None):
    proj = str(project_name).strip()
    if proj.lower() == "pendulum":
        analyze_pendulum_adapter(files, start_dt, end_dt, mode="save", output_dir=target_dir, gui_dir=os.path.dirname(__file__))
        _standardize_outputs(target_dir, 'Pendulum', start_dt, end_dt)
        return

    if proj.lower() == "chliran":
        analyze_chliran_adapter(files, start_dt, end_dt, mode="save", output_dir=target_dir, gui_dir=os.path.dirname(__file__))
        _standardize_outputs(target_dir, 'Chliran', start_dt, end_dt)
        return

    if fig is None or result is None:
        raise ValueError("fig/result manquants pour une sauvegarde classique.")
    start_md = start_dt.strftime("%d_%m")
    end_md = end_dt.strftime("%d_%m")

    png_path = os.path.join(target_dir, f"{proj}_{start_md}_to_{end_md}.png")
    txt_path = os.path.join(target_dir, f"summary_{proj}_{start_md}-{end_md}.txt")

    fig.savefig(png_path)
    write_summary_to_file(result, interval, start_dt, end_dt, txt_path)

DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
HOUR_BEGIN_DAY = 9
MINUTE_BEGIN_DAY = 30
HOUR_END_DAY = 18

def label_title_summary(project):
    return {
        "Rocket Hydrogen": "Rocket ignited",
        "Horsepower": "Ball lifted",
        "Jumping Ring": "Ring jumped!",
        "AirPressure": "Bottle ignited",
        "Light a Fire": "Flames reached:"
    }.get(project, project.lower())

def analyze_logs(files, start_dt, end_dt, interval, event_config, project_name):
    timestamps = []
    lang_eng_ts = []
    lang_heb_ts = []
    lang_arb_ts = []

    ui_restart_counter = 0
    arduino_disconnect_counter = 0
    arduino_error_parsing_counter = 0

    ui_restart_keywords = [
        "Starting Hydrogen Rocket UI",
        "Starting Horse Power UI",
        "Starting Air Pressure UI",
        "Starting Jumping Ring UI",
        "Starting Light a Fire UI"
    ]
    arduino_disconnect_keyword = "Arduino disconnected. Trying to reconnect to Arduino..."

    cmd_charges = []
    charge_pattern = re.compile(r"Sent 'ignite' command to Arduino\. Charge:\s*([0-9.]+)")  

    target_keyword = event_config.get(project_name, "").lower()
    first_dt = None
    last_dt = None

    for file_path in files:
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    timestamp_str = line.split(" - ")[0]
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                    if not (start_dt <= timestamp <= end_dt):
                        continue

                    if first_dt is None or timestamp < first_dt:
                        first_dt = timestamp
                    if last_dt is None or timestamp > last_dt:
                        last_dt = timestamp

                    line_lower = line.lower()

                    charge_match = charge_pattern.search(line)
                    if charge_match:
                        charge_val = float(charge_match.group(1))
                        cmd_charges.append(charge_val)

                    if target_keyword and target_keyword in line_lower:
                        timestamps.append(timestamp)

                    if "your language is: english" in line_lower:
                        lang_eng_ts.append(timestamp)
                    if "your language is: hebrew" in line_lower:
                        lang_heb_ts.append(timestamp)
                    if "your language is: arabic" in line_lower:
                        lang_arb_ts.append(timestamp)

                    if "error parsing data:" in line_lower:
                        arduino_error_parsing_counter += 1

                    if (timestamp.hour > HOUR_BEGIN_DAY or (
                            timestamp.hour == HOUR_BEGIN_DAY and timestamp.minute >= MINUTE_BEGIN_DAY)) and timestamp.hour < HOUR_END_DAY:

                        for keyword in ui_restart_keywords:
                            if keyword.lower() in line_lower:
                                ui_restart_counter += 1
                                break
                        if arduino_disconnect_keyword.lower() in line_lower:
                            arduino_disconnect_counter += 1

                except Exception:
                    pass

    if not timestamps and not lang_eng_ts and not lang_heb_ts and not lang_arb_ts:
        return None

    charge_stats = {
        "max_charge": max(cmd_charges) if cmd_charges else 0.0,
        "min_charge": min(cmd_charges) if cmd_charges else 0.0,
        "avg_charge": (sum(cmd_charges) / len(cmd_charges)) if cmd_charges else 0.0,
        "avg_cmd_charge": (sum(cmd_charges) / len(cmd_charges)) if cmd_charges else 0.0
    }

    return {
        "timestamps": timestamps,
        "lang_eng_ts": lang_eng_ts,
        "lang_heb_ts": lang_heb_ts,
        "lang_arb_ts": lang_arb_ts,
        "First Timestamp": first_dt,
        "Last Timestamp": last_dt,
        "project_name": project_name,
        "ui_restart_count": ui_restart_counter,
        "arduino_disconnect_count": arduino_disconnect_counter,
        "Error parsing data": arduino_error_parsing_counter,
        "charge_stats": charge_stats
    }

def plot_counts(data_dict, interval):
    timestamps = data_dict["timestamps"]
    project_name = data_dict["project_name"]

    if not timestamps:
        print("⚠️ Aucun point de donnée à tracer.")
        return None

    df = pd.DataFrame(timestamps, columns=["datetime"])

    fig, ax = plt.subplots(figsize=(14, 6))

    if interval == "hour":
        df["Date"] = df["datetime"].dt.strftime("%Y-%m-%d")
        df["Hour"] = df["datetime"].dt.hour

        # Group by hour and date
        pivot_df = df.groupby(["Hour", "Date"]).size().unstack(fill_value=0)
        
        # REMOVED: pivot_df = pivot_df.reindex(range(24), fill_value=0)
        # Now pivot_df only includes hours where at least one event occurred.

        pivot_df.plot(kind="bar", ax=ax, width=0.8)

        ax.set_title(f"{project_name} - Events per Hour", fontsize=14)
        ax.set_xlabel("Hour of Day", fontsize=12)
        ax.set_ylabel("Event Count", fontsize=12)
        
        # Display only the active hours as tick labels
        ax.set_xticklabels(pivot_df.index, rotation=0)
        
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        ax.legend(title="Date")
    else:
        df["Date"] = df["datetime"].dt.strftime("%Y-%m-%d")
        counts = df.groupby("Date").size()

        counts.plot(kind="bar", ax=ax, color="skyblue", edgecolor="black")
        ax.set_title(f"{project_name} - Events per Day", fontsize=14)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Event Count", fontsize=12)
        ax.set_xticklabels(counts.index, rotation=45, ha="right")
        ax.grid(axis="y", linestyle="--", alpha=0.7)

    fig.tight_layout()
    return fig

def write_summary_to_file(data_dict, interval, start_dt, end_dt, filename):
    first_dt = data_dict["First Timestamp"]
    last_dt = data_dict["Last Timestamp"]
    timestamps = data_dict["timestamps"]
    project_name = data_dict["project_name"]
    label_text = label_title_summary(project_name)

    ui_restart_count = data_dict.get("ui_restart_count", 0)
    arduino_disconnect_count = data_dict.get("arduino_disconnect_count", 0)
    arduino_parse_error_count = data_dict.get("Error parsing data", 0)

    if interval == "day":
        total_intervals = max((end_dt.date() - start_dt.date()).days + 1, 1)
    elif interval == "hour":
        delta = end_dt - start_dt
        total_intervals = max(int(delta.total_seconds() // 3600) + 1, 1)
    else:
        total_intervals = 1

    ring_total = len(timestamps)
    eng_total = len(data_dict.get("lang_eng_ts", []))
    heb_total = len(data_dict.get("lang_heb_ts", []))
    arb_total = len(data_dict.get("lang_arb_ts", []))
    total_langs = eng_total + heb_total + arb_total

    ring_avg = ring_total / total_intervals
    eng_avg = eng_total / total_intervals
    heb_avg = heb_total / total_intervals
    arb_avg = arb_total / total_intervals
    total_langs_avg = total_langs / total_intervals

    denom = ring_total + total_langs
    good_runs_pct = (ring_total / denom) * 100 if denom else 0

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Summary from {start_dt} to {end_dt} ({(end_dt - start_dt).days + 1} days)\n")
        f.write(f"Log data time range: {first_dt} to {last_dt} ({(last_dt - first_dt).days + 1} days)\n\n")

        f.write(f"Total {label_text}: {ring_total}\n")
        if project_name != "Light a Fire":
            f.write(f"Total english language: {eng_total}\n")
            f.write(f"Total hebrew language: {heb_total}\n")
            f.write(f"Total arabic language: {arb_total}\n")
            f.write(f"Total language changes: {total_langs}\n\n")

            f.write(f"Average {label_text} per {interval}: {ring_avg:.2f}\n")
            f.write(f"Average english language per {interval}: {eng_avg:.2f}\n")
            f.write(f"Average hebrew language per {interval}: {heb_avg:.2f}\n")
            f.write(f"Average arabic language per {interval}: {arb_avg:.2f}\n")
            f.write(f"Average total language changes per {interval}: {total_langs_avg:.2f}\n\n")
            f.write(f"Good runs: {ring_total} / {denom} ({good_runs_pct:.2f}%)\n")

        if "charge_stats" in data_dict and project_name == "Rocket Hydrogen":
            stats = data_dict["charge_stats"]
            f.write("\n--- Rocket Charge Analysis (Coulombs) ---\n")
            f.write(f"Maximum Charge recorded: {stats.get('max_charge', 0.0):.2f} Coul\n")
            f.write(f"Minimum Charge recorded: {stats.get('min_charge', 0.0):.2f} Coul\n")
            f.write(f"Average Charge overall:  {stats.get('avg_charge', 0.0):.2f} Coul\n")
            f.write(f"Average Charge (Ignite Command):  {stats.get('avg_cmd_charge', 0.0):.2f} Coul\n")

        f.write("\n---\n")
        f.write(f"UI restarts between 09:30 and 18:00: {ui_restart_count}\n")
        f.write(f"Arduino disconnections between 09:30 and 18:00: {arduino_disconnect_count}\n")
        f.write(f"Error parsing data: {arduino_parse_error_count}\n")

    print(f"✅ Summary saved to: {filename}")