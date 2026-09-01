
import pandas as pd
import os
from CONST_n_PLOT import ADVANCED_THRESHOLD_S, SW_LIST

def build_df_cycles(cycles):
    return pd.DataFrame(cycles)

def build_df_resume(df_cycles: pd.DataFrame):
    if df_cycles.empty:
        return pd.DataFrame(columns=["Date", "General", "Advanced"])

    df = df_cycles.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    resume = df.groupby("Date").agg(
        General=("SW", "count"),
        Advanced=("Advanced", lambda s: (s == "YES").sum())
    ).reset_index()

    for sw in SW_LIST:
        sw_df = df[df["SW"] == sw]
        if sw_df.empty:
            resume[f"{sw}_General"] = 0
            resume[f"{sw}_Advanced"] = 0
            continue

        g = sw_df.groupby("Date").size()
        a = sw_df[sw_df["Advanced"] == "YES"].groupby("Date").size()

        resume[f"{sw}_General"] = resume["Date"].map(g).fillna(0).astype(int)
        resume[f"{sw}_Advanced"] = resume["Date"].map(a).fillna(0).astype(int)

    total_general = int(resume["General"].sum())
    total_advanced = int(resume["Advanced"].sum())

    resume["Total_General"] = [total_general] + [None] * (len(resume) - 1)
    resume["Total_Advanced"] = [total_advanced] + [None] * (len(resume) - 1)
    resume["Threshold_s"] = [ADVANCED_THRESHOLD_S] + [None] * (len(resume) - 1)

    return resume

def export_excel(df_cycles: pd.DataFrame, df_resume: pd.DataFrame, output_path: str, project_name: str):
    os.makedirs(output_path, exist_ok=True)
    out_xlsx = os.path.join(output_path, f"{project_name}_log.xlsx")

    df1 = df_cycles.copy()
    df2 = df_resume.copy()

    for col in ["PushDateTime", "ReleaseDateTime"]:
        if col in df1.columns:
            df1[col] = df1[col].astype(str)
    if "Date" in df1.columns:
        df1["Date"] = df1["Date"].astype(str)
    if "Date" in df2.columns:
        df2["Date"] = df2["Date"].astype(str)

    with pd.ExcelWriter(out_xlsx) as writer:
        df1.to_excel(writer, sheet_name="Raw Cycles", index=False)
        df2.to_excel(writer, sheet_name="Résumé per day", index=False)

    print(f"✅ Excel créé : {out_xlsx}")

def write_summary(df_cycles: pd.DataFrame, start_dt, end_dt, output_path: str, project_name: str):
    os.makedirs(output_path, exist_ok=True)
    out_txt = os.path.join(output_path, f"{project_name}_summary.txt")

    if df_cycles.empty:
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(f"Summary from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}\n")
            f.write("⚠️ Aucun cycle (push+release) détecté dans l’intervalle.\n")
        print(f"📄 Résumé sauvegardé dans {out_txt}")
        return

    df = df_cycles.copy()
    df["PushDateTime"] = pd.to_datetime(df["PushDateTime"])
    df["ReleaseDateTime"] = pd.to_datetime(df["ReleaseDateTime"])
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    df_range = df[(df["PushDateTime"] >= start_dt) & (df["PushDateTime"] <= end_dt)]
    if df_range.empty:
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(f"Summary from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}\n")
            f.write("⚠️ Aucun cycle (push+release) dans l’intervalle.\n")
        print(f"📄 Résumé sauvegardé dans {out_txt}")
        return

    first_dt = df_range["PushDateTime"].min()
    last_dt = df_range["ReleaseDateTime"].max()

    total_general = len(df_range)
    total_advanced = int((df_range["Advanced"] == "YES").sum())

    days_in_split = df_range["Date"].nunique() or 1
    days_calendar = (end_dt.date() - start_dt.date()).days + 1
    diff_days = days_calendar - days_in_split

    avg_general = total_general / days_in_split
    avg_advanced = total_advanced / days_in_split

    dur_mean = float(df_range["Duration_s"].mean())
    dur_max = float(df_range["Duration_s"].max())

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(
            f"Summary from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} "
            f"({days_calendar} days calendar)\n"
        )
        f.write(
            f"Log cycles time range: {first_dt.strftime('%Y-%m-%d')} to {last_dt.strftime('%Y-%m-%d')}\n\n"
        )

        f.write(f"Advanced threshold (seconds): {ADVANCED_THRESHOLD_S}\n\n")

        f.write(f"Total General cycles (push+release): {total_general}\n")
        f.write(f"Total Advanced cycles (> threshold): {total_advanced}\n\n")

        f.write(f"Days present in split-log (unique dates with cycles): {days_in_split}\n")
        f.write(f"Difference (calendar - split-log): {diff_days}\n\n")

        f.write(f"Average General cycles per day: {avg_general:.2f}\n")
        f.write(f"Average Advanced cycles per day: {avg_advanced:.2f}\n\n")

        f.write(f"Duration mean (s): {dur_mean:.2f}\n")
        f.write(f"Duration max (s): {dur_max:.2f}\n")

    print(f"📄 Résumé sauvegardé dans {out_txt}")
