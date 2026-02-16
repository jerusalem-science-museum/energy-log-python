
import pandas as pd
import matplotlib.pyplot as plt
import os

# ===== PARAMS =====
ADVANCED_THRESHOLD_S = 3.0  # > 3 sec => compteur avancé
SW_LIST = ["SW1", "SW2", "SW3", "SW4"]

def plot_resume(df_resume: pd.DataFrame, start_dt, end_dt, title: str = "Number of presses per day (general vs advanced)"):
    df_resume = df_resume.copy()
    df_resume["Date"] = pd.to_datetime(df_resume["Date"])
    df_filtered = df_resume[(df_resume["Date"] >= start_dt) & (df_resume["Date"] <= end_dt)].copy()

    if df_filtered.empty:
        print("⚠️ Aucun jour dans l'intervalle spécifié pour le résumé.")
        return None

    df_filtered["DateStr"] = df_filtered["Date"].dt.strftime("%Y-%m-%d")
    df_filtered = df_filtered.set_index("DateStr")

    plt.figure(figsize=(14, 6))
    cols = [c for c in ["General", "Advanced"] if c in df_filtered.columns]
    if not cols:
        print("⚠️ Colonnes 'General' / 'Advanced' manquantes dans df_resume.")
        return None
    df_filtered[cols].plot(kind="bar", width=0.85)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.grid(axis="y")
    return plt

def save_plot(plt_obj, output_path: str, filename: str = "plot_resume.png"):
    if plt_obj is None:
        return
    os.makedirs(output_path, exist_ok=True)
    out = os.path.join(output_path, filename)
    plt_obj.savefig(out)
    print(f"📊 Graph saved: {out}")
