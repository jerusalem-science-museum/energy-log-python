
import matplotlib.pyplot as plt
import os
import pandas as pd

def plot_resume(df_resume: pd.DataFrame, start_dt, end_dt, title: str = "Number of pushes per day (motor activate)"):
    df_resume = df_resume.copy()
    df_resume["Date"] = pd.to_datetime(df_resume["Date"])
    df_filtered = df_resume[(df_resume["Date"] >= start_dt) & (df_resume["Date"] <= end_dt)].copy()

    if df_filtered.empty:
        print("⚠️ Aucun jour dans l'intervalle spécifié pour le résumé.")
        return None

    df_filtered["DateStr"] = df_filtered["Date"].dt.strftime("%Y-%m-%d")
    df_filtered = df_filtered.set_index("DateStr")

    plt.figure(figsize=(14, 6))
    df_filtered["MOTOR ON"].plot(kind="bar", color="orange", width=0.8)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Number of pushes with motor ON")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.grid(axis='y')
    return plt

def save_plot(plt_obj, output_path: str, filename: str = "plot_resume.png"):
    if plt_obj is None:
        return
    os.makedirs(output_path, exist_ok=True)
    out = os.path.join(output_path, filename)
    plt_obj.savefig(out)
    print(f"📊 Graph saved: {out}")
