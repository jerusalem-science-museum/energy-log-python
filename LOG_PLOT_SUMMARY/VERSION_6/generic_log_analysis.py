import os
import re
import shutil
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import sys
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime



# =========================
# Special projects adapters
# =========================
import tempfile
from contextlib import contextmanager


import importlib
import importlib.util
from pathlib import Path

def _import_by_path(mod_name: str, file_path: str):
    """Importe un module Python depuis un chemin de fichier (marche même sans __init__.py)."""
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger le module {mod_name} depuis {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _try_import_project(project_dir_name: str, main_py: str, const_py: str = None):
    """Essaie d'importer comme package (si __init__.py) sinon par chemin."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = os.path.join(base_dir, project_dir_name)

    if not os.path.isdir(proj_dir):
        raise ImportError(
            f"Dossier '{project_dir_name}' introuvable.\n"
            f"Attendu ici: {proj_dir}\n"
            f"➡️ Mets le dossier {project_dir_name} à côté du GUI."
        )

    init_py = os.path.join(proj_dir, "__init__.py")

    # 1) package import
    if os.path.isfile(init_py):
        pkg = project_dir_name
        main_mod = importlib.import_module(f"{pkg}.{Path(main_py).stem}")
        const_mod = importlib.import_module(f"{pkg}.{Path(const_py).stem}") if const_py else None
        return main_mod, const_mod

    # 2) import par chemin (pas besoin de __init__.py)
    main_path = os.path.join(proj_dir, main_py)
    if not os.path.isfile(main_path):
        raise ImportError(f"Fichier introuvable: {main_path}")
    main_mod = _import_by_path(f"{project_dir_name}_{Path(main_py).stem}", main_path)

    const_mod = None
    if const_py:
        const_path = os.path.join(proj_dir, const_py)
        if not os.path.isfile(const_path):
            raise ImportError(f"Fichier introuvable: {const_path}")
        const_mod = _import_by_path(f"{project_dir_name}_{Path(const_py).stem}", const_path)

    return main_mod, const_mod


@contextmanager
def _no_matplotlib_show():
    """
    Empêche plt.show() d'ouvrir une fenêtre ou de bloquer (utile dans le GUI).
    """
    _orig_show = plt.show
    try:
        plt.show = lambda *a, **k: None
        yield
    finally:
        plt.show = _orig_show

def _concat_log_files(files):
    """
    Concatène plusieurs logs en un seul fichier temporaire (garde l'ordre).
    Retourne (path_to_use, temp_to_cleanup_or_None).
    """
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
    """
    Pendulum (SANS split dans le GUI):
      - 'files' doit être une liste de fichiers split: log_YYYY-MM-DD_to_YYYY-MM-DD.txt
      - on appelle directement Pendulum_log/main_pendulum.py
    """
    if gui_dir is None:
        gui_dir = os.getcwd()

    bad = [f for f in files if not os.path.basename(f).lower().startswith("log_")]
    if bad:
        raise ValueError(
            "Pendulum: les fichiers sélectionnés ne ressemblent pas à des fichiers split.\n"
            "Tu dois d'abord exécuter split_log.py individuellement, puis sélectionner les fichiers log_*.txt.\n"
            f"Exemples invalides: {', '.join(os.path.basename(x) for x in bad[:3])}"
        )

    main_path = _find_project_file(gui_dir, "Pendulum_log", "main_pendulum.py")
    if not main_path:
        raise ImportError("main_pendulum.py introuvable (dossier Pendulum_log pas à côté du GUI).")

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
    """
    Chliran (SANS split dans le GUI):
      - 'files' doit être une liste de fichiers split: log_YYYY-MM-DD_to_YYYY-MM-DD.txt
      - on appelle directement Chliran_log/main_chliran.py
    """
    if gui_dir is None:
        gui_dir = os.getcwd()

    bad = [f for f in files if not os.path.basename(f).lower().startswith("log_")]
    if bad:
        raise ValueError(
            "Chliran: les fichiers sélectionnés ne ressemblent pas à des fichiers split.\n"
            "Tu dois d'abord exécuter split_log.py individuellement, puis sélectionner les fichiers log_*.txt.\n"
            f"Exemples invalides: {', '.join(os.path.basename(x) for x in bad[:3])}"
        )

    main_path = _find_project_file(gui_dir, "Chliran_log", "main_chliran.py")
    if not main_path:
        raise ImportError("main_chliran.py introuvable (dossier Chliran_log pas à côté du GUI).")

    main_mod = _load_module_from_file_compat("Chliran_main", main_path)

    # Run: éviter DOWNLOAD_DIR="" (WinError 3)
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
    """
    Point d'entrée unique pour le GUI.
    Retourne (result_dict, fig)
    - Pour projects "classiques" => result_dict = output analyze_logs, fig = plot_counts(...)
    - Pour Pendulum/Chliran => result_dict = {"special":True,...}, fig = figure matplotlib créée par leur code
    """
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
    """
    Supporte 2 layouts:
      gui_dir/project_folder/filename
      gui_dir/project_folder/project_folder/filename
    Retourne le path trouvé ou None.
    """
    cand1 = os.path.join(gui_dir, project_folder, filename)
    cand2 = os.path.join(gui_dir, project_folder, project_folder, filename)
    if os.path.isfile(cand1):
        return cand1
    if os.path.isfile(cand2):
        return cand2
    return None



def _load_module_from_file_compat(module_name, file_path):
    """
    Charge un .py via chemin (sans package).
    Compat Python 3.9: remplace les annotations 'X | None' par Optional[X].
    IMPORTANT:
      - ajoute temporairement le dossier du fichier à sys.path (imports locaux)
      - isole les imports en nettoyant temporairement sys.modules des modules locaux
        (évite conflit data_frame.py entre Chliran et Pendulum quand on lance l'un après l'autre)
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    # Patch union types (Python 3.10+) -> Optional[...] for Python 3.9
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

    # Collect local module names in this folder (e.g., data_frame, CONST_n_PLOT, etc.)
    local_names = []
    try:
        for fn in os.listdir(module_dir):
            if fn.endswith(".py") and fn != "__init__.py":
                local_names.append(os.path.splitext(fn)[0])
    except Exception:
        local_names = []

    # Temporarily remove those names from sys.modules to avoid cross-project caching
    saved_modules = {}
    for name in local_names:
        if name in sys.modules:
            saved_modules[name] = sys.modules[name]
            del sys.modules[name]

    # Also remove common matplotlib caches that can keep old figures (safe)
    # (not strictly required; leave as-is)

    if module_dir and module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        added_path = True

    try:
        exec(compile(src, file_path, "exec"), mod.__dict__)
    finally:
        # restore sys.path
        if added_path:
            try:
                sys.path.remove(module_dir)
            except ValueError:
                pass

        # restore sys.modules
        for name in local_names:
            if name in sys.modules:
                del sys.modules[name]
        for name, module_obj in saved_modules.items():
            sys.modules[name] = module_obj

    return mod

def _split_raw_logs(project_folder, raw_files, start_dt, end_dt, out_dir, gui_dir):
    """
    Lance split_log_by_month_with_datetime sur chaque raw log,
    puis retourne la liste des fichiers split *.txt créés dans out_dir.
    """
    split_path = _find_project_file(gui_dir, project_folder, "split_log.py")
    if not split_path:
        raise FileNotFoundError(f"split_log.py introuvable pour {project_folder}")

    split_mod = _load_module_from_file_compat(f"{project_folder}_split_log", split_path)
    if not hasattr(split_mod, "split_log_by_month_with_datetime"):
        raise AttributeError(f"{project_folder}/split_log.py ne contient pas split_log_by_month_with_datetime")

    os.makedirs(out_dir, exist_ok=True)
    for rf in raw_files:
        split_mod.split_log_by_month_with_datetime(
            file_path=rf,
            start_dt=start_dt,
            end_dt=end_dt,
            output_dir=out_dir
        )

    # récupérer les fichiers split
    out_files = []
    for fn in os.listdir(out_dir):
        if fn.lower().endswith(".txt") and fn.lower().startswith("log_"):
            out_files.append(os.path.join(out_dir, fn))
    out_files.sort()
    return out_files


def _newest_file_by_ext(folder, ext):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(ext)]
    if not files:
        return None
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]



def _standardize_outputs(target_dir, proj, start_dt, end_dt):
    """
    Après sauvegarde Pendulum/Chliran :
    - garantit 1 PNG + 1 TXT + 1 XLSX au NOM STANDARD (daté)
    - supprime tous les doublons (fichiers non datés) qui ont été générés par leurs scripts
    """
    start_md = start_dt.strftime("%d_%m")
    end_md = end_dt.strftime("%d_%m")

    std_png = os.path.join(target_dir, f"{proj}_{start_md}_to_{end_md}.png")
    std_txt = os.path.join(target_dir, f"summary_{proj}_{start_md}-{end_md}.txt")
    std_xlsx = os.path.join(target_dir, f"{proj}_{start_md}_to_{end_md}.xlsx")

    # 1) Trouver au moins un fichier de chaque type et créer les versions standard
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

    # 2) Supprimer tous les doublons non standard (non datés / autres noms)
    # On garde UNIQUEMENT les 3 fichiers standard + le dossier split_logs (et autres sous-dossiers)
    keep = {os.path.abspath(std_png), os.path.abspath(std_txt), os.path.abspath(std_xlsx)}

    # patterns "non datés" typiques des scripts
    non_dated_png = {"plot_resume.png", "plot_counts.png"}
    non_dated_txt = {"summary.txt", f"{proj.lower()}_summary.txt"}  # e.g. chliran_summary.txt
    # excel: *_log.xlsx, log_table.xlsx, pendulum_log.xlsx, chliran_log.xlsx
    def _is_non_dated_xlsx(name):
        n = name.lower()
        return n.endswith("_log.xlsx") or n in {"log_table.xlsx", "pendulum_log.xlsx", "chliran_log.xlsx"}

    for fn in list(os.listdir(target_dir)):
        fp = os.path.join(target_dir, fn)
        if not os.path.isfile(fp):
            continue
        ab = os.path.abspath(fp)

        # always keep standard
        if ab in keep:
            continue

        low = fn.lower()

        # delete all other PNG/TXT/XLSX that match non-dated patterns OR simply same extension duplicates
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

    # 3) Check final
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
    """
    Sauvegarde dans target_dir.
    - Pendulum => appelle son analyse en mode save (Excel + plot + summary)
    - Chliran => redirige DOWNLOAD_DIR puis appelle son analyse (Excel + plots + summary)
    - Autres => sauvegarde fig + summary via write_summary_to_file (comme avant)
    """
    proj = str(project_name).strip()
    if proj.lower() == "pendulum":
        analyze_pendulum_adapter(files, start_dt, end_dt, mode="save", output_dir=target_dir, gui_dir=os.path.dirname(__file__))
        _standardize_outputs(target_dir, 'Pendulum', start_dt, end_dt)
        return

    if proj.lower() == "chliran":
        analyze_chliran_adapter(files, start_dt, end_dt, mode="save", output_dir=target_dir, gui_dir=os.path.dirname(__file__))
        _standardize_outputs(target_dir, 'Chliran', start_dt, end_dt)
        return

    # Cas "classiques"
    if fig is None or result is None:
        raise ValueError("fig/result manquants pour une sauvegarde classique.")
    start_md = start_dt.strftime("%d_%m")
    end_md = end_dt.strftime("%d_%m")

    png_path = os.path.join(target_dir, f"{proj}_{start_md}_to_{end_md}.png")
    txt_path = os.path.join(target_dir, f"summary_{proj}_{start_md}-{end_md}.txt")

    fig.savefig(png_path)
    write_summary_to_file(result, interval, start_dt, end_dt, txt_path)


# Dossier de sauvegarde par défaut : Téléchargements de l'utilisateur
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
HOUR_BEGIN_DAY = 9
MINUTE_BEGIN_DAY = 30
HOUR_END_DAY = 18

def get_time_key(timestamp, interval):
    return timestamp.strftime("%Y-%m-%d %H:00") if interval == "hour" else timestamp.strftime("%Y-%m-%d")

def detect_project_name(file_path):
    patterns = {
        "Rocket Hydrogen": "The rocket has ignited",
        "Horsepower": "your horsepower is",
        "Jumping Ring": "Ring jumped!",
        "AirPressure": "The Bottle flew!",
        "Light a Fire": "Peak temperature reached:"
    }
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.read()
            for name, keyword in patterns.items():
                if keyword.lower() in lines.lower():
                    return name
    except Exception:
        pass
    return "project"  # fallback


def label_title_summary(project):
    return {
        "Rocket Hydrogen": "Rocket ignited",
        "Horsepower": "Ball lifted",
        "Jumping Ring": "Ring jumped!",
        "AirPressure": "Bottle ignited",
        "Light a Fire": "Flames reached:"
    }.get(project, project.lower())


def analyze_logs(files, start_dt, end_dt, interval, event_config, project_name):
    counters = {label: defaultdict(int) for label in event_config}
    language_eng_counter = defaultdict(int)
    language_heb_counter = defaultdict(int)
    language_arb_counter = defaultdict(int)

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
    #arduino_disconnect_keyword = "Error reading from serial, Arduino probably disconnected"
    arduino_disconnect_keyword = "Arduino disconnected. Trying to reconnect to Arduino..."

    any_data_found = False
    first_dt = None
    last_dt = None

    for file_path in files:
        print(f"\nReading file: {file_path}")
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}", file=sys.stderr)
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

                    time_key = get_time_key(timestamp, interval)
                    line_lower = line.lower()

                    for label, keyword in event_config.items():
                        if keyword.lower() in line_lower:
                            counters[label][time_key] += 1
                            any_data_found = True

                    if "your language is: english" in line_lower:
                        language_eng_counter[time_key] += 1
                        any_data_found = True
                    if "your language is: hebrew" in line_lower:
                        language_heb_counter[time_key] += 1
                        any_data_found = True
                    if "your language is: arabic" in line_lower:
                        language_arb_counter[time_key] += 1
                        any_data_found = True

                    if "Error parsing data:".lower() in line_lower:
                        arduino_error_parsing_counter += 1
                        any_data_found = True

                    if (timestamp.hour > HOUR_BEGIN_DAY or (
                            timestamp.hour == HOUR_BEGIN_DAY and timestamp.minute >= MINUTE_BEGIN_DAY)) and timestamp.hour < HOUR_END_DAY:

                        for keyword in ui_restart_keywords:
                            if keyword.lower() in line_lower:
                                ui_restart_counter += 1
                                break
                        if arduino_disconnect_keyword.lower() in line_lower:
                            arduino_disconnect_counter += 1

                except Exception:
                    print(f"Skipping line (parse error): {line.rstrip()}", file=sys.stderr)

    if not any_data_found:
        return None

    counters["Language: English"] = language_eng_counter
    counters["Language: Hebrew"] = language_heb_counter
    counters["Language: Arabic"] = language_arb_counter

    return {
        "counters": counters,
        "First Timestamp": first_dt,
        "Last Timestamp": last_dt,
        "project_name": project_name,
        "ui_restart_count": ui_restart_counter,
        "arduino_disconnect_count": arduino_disconnect_counter,
        "Error parsing data": arduino_error_parsing_counter
    }



def plot_counts(data_dict, interval):
    """
    Crée la figure du graphique mais NE SAUVE PAS.
    Le GUI décidera où sauver.
    """
    counters = data_dict["counters"]
    project_name = data_dict["project_name"]

    all_keys = sorted(set().union(*[counter.keys() for counter in counters.values()]))
    if not all_keys:
        print("⚠️ Aucun point de donnée à tracer.")
        return None

    x = np.arange(len(all_keys))
    offset = 0

    fig, ax = plt.subplots(figsize=(12, 6))

    if project_name != "Light a Fire":
        lang_labels = ["Language: English", "Language: Hebrew", "Language: Arabic"]
        bar_width = 0.2
    else:
        lang_labels = []
        bar_width = 0.5

    for label in [project_name] + lang_labels:
        if label in counters:
            counts = [counters[label].get(k, 0) for k in all_keys]
            ax.bar(x + offset, counts, width=bar_width, label=label)
            offset += bar_width

    if project_name != "Light a Fire":
        ax.set_xticks(x + bar_width * len(counters) / 2.5)
    else:
        ax.set_xticks(x)

    ax.set_xticklabels(all_keys, rotation=45, ha="right")
    ax.set_ylabel("Count")
    ax.set_xlabel("Hour" if interval == "hour" else "Date")
    ax.set_title("Log Event Counts")
    ax.legend()
    ax.grid(True, axis='y')
    fig.tight_layout()

    print("✅ Figure créée (non sauvegardée)")
    return fig


def write_summary_to_file(data_dict, interval, start_dt, end_dt, filename):
    """
    Même résumé que write_summary original,
    mais on écrit DANS filename (choisi par le GUI).
    """
    def total(counter):
        return sum(counter.values())

    first_dt = data_dict["First Timestamp"]
    last_dt = data_dict["Last Timestamp"]
    counters = data_dict["counters"]
    project_name = data_dict["project_name"]
    label_text = label_title_summary(project_name)

    ui_restart_count = data_dict.get("ui_restart_count", 0)
    arduino_disconnect_count = data_dict.get("arduino_disconnect_count", 0)
    arduino_parse_error_count = data_dict.get("Error parsing data", 0)

    if interval == "day":
        total_intervals = (end_dt.date() - start_dt.date()).days + 1
    elif interval == "hour":
        delta = end_dt - start_dt
        total_intervals = int(delta.total_seconds() // 3600) + 1
    else:
        total_intervals = 1  # fallback


    ring_total = total(counters.get(project_name, defaultdict(int)))
    eng_total = total(counters.get("Language: English", defaultdict(int)))
    heb_total = total(counters.get("Language: Hebrew", defaultdict(int)))
    arb_total = total(counters.get("Language: Arabic", defaultdict(int)))
    total_langs = eng_total + heb_total + arb_total

    ring_avg = ring_total / total_intervals if total_intervals else 0
    eng_avg = eng_total / total_intervals if total_intervals else 0
    heb_avg = heb_total / total_intervals if total_intervals else 0
    arb_avg = arb_total / total_intervals if total_intervals else 0
    total_langs_avg = total_langs / total_intervals if total_intervals else 0

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

        f.write("\n---\n")
        f.write(f"UI restarts between 09:30 and 18:00: {ui_restart_count}\n")
        f.write(f"Arduino disconnections between 09:30 and 18:00: {arduino_disconnect_count}\n")
        f.write(f"Error parsing data: {arduino_parse_error_count}\n")

    print(f"✅ Summary saved to: {filename}")
