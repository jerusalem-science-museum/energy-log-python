
from CONST_n_PLOT import *
import pandas as pd
import os

def build_df_events(events):
    return pd.DataFrame(events)

def build_df_resume(df: pd.DataFrame):
    grouped = df.groupby(["Date", "Motor_Activated"]).size().unstack(fill_value=0)
    grouped = grouped.rename(columns={"NO": "NO ACTION", "YES": "MOTOR ON"})

    total_on = grouped.get("MOTOR ON", pd.Series(dtype=float)).sum()
    total_off = grouped.get("NO ACTION", pd.Series(dtype=float)).sum()
    total_all = total_on + total_off

    df_resume = pd.DataFrame({
        "Date": grouped.index,
        "MOTOR ON": grouped.get("MOTOR ON", 0),
        "NO ACTION": grouped.get("NO ACTION", 0),
        "Total with Motor": [total_on] + [None] * (len(grouped) - 1),
        "Total NO ACTION": [total_off] + [None] * (len(grouped) - 1),
        "Total": [total_all] + [None] * (len(grouped) - 1)
    })
    return df_resume

def export_excel(df: pd.DataFrame, df_resume: pd.DataFrame, output_path: str, project_name: str):
    os.makedirs(output_path, exist_ok=True)
    out_xlsx = os.path.join(output_path, f"{project_name}_log.xlsx")

    df_to_save = df.copy()
    df_resume_to_save = df_resume.copy()
    df_to_save["DateTime"] = df_to_save["DateTime"].astype(str)
    df_to_save["Date"] = df_to_save["Date"].astype(str)
    df_resume_to_save["Date"] = df_resume_to_save["Date"].astype(str)

    with pd.ExcelWriter(out_xlsx) as writer:
        df_to_save.to_excel(writer, sheet_name="Raw Data", index=False)
        df_resume_to_save.to_excel(writer, sheet_name="Résumé per day", index=False)

    print(f"✅ Excel créé : {out_xlsx}")

def write_summary(df: pd.DataFrame, start_dt, end_dt, output_path: str, project_name: str):
    os.makedirs(output_path, exist_ok=True)
    out_txt = os.path.join(output_path, f"{project_name}_summary.txt")

    df = df.copy()
    df["DateTime"] = pd.to_datetime(df["DateTime"])
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    df_range = df[(df["DateTime"] >= start_dt) & (df["DateTime"] <= end_dt)]
    if df_range.empty:
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(f"Summary from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}\n")
            f.write("⚠️ Aucun événement dans l’intervalle de temps spécifié.\n")
        print(f"📄 Résumé sauvegardé dans {out_txt}")
        return

    first_dt = df_range["DateTime"].min()
    last_dt = df_range["DateTime"].max()

    motor_on_total = (df_range["Motor_Activated"] == "YES").sum()
    no_action_total = (df_range["Motor_Activated"] == "NO").sum()
    total_events = len(df_range)

    days_in_split = df_range["Date"].nunique() or 1
    days_calendar = (end_dt.date() - start_dt.date()).days + 1
    diff_days = days_calendar - days_in_split

    motor_on_avg = motor_on_total / days_in_split
    no_action_avg = no_action_total / days_in_split
    total_avg = total_events / days_in_split

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(
            f"Summary from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} "
            f"({days_calendar} days calendar)\n"
        )
        f.write(
            f"Log data time range: {first_dt.strftime('%Y-%m-%d')} to {last_dt.strftime('%Y-%m-%d')} "
            f"({(last_dt.date() - first_dt.date()).days + 1} days)\n\n"
        )

        f.write(f"Total MOTOR activated: {motor_on_total}\n")
        f.write(f"Total MOTOR NO ACTION: {no_action_total}\n")
        f.write(f"Total actions: {total_events}\n\n")

        f.write(f"Days present in split-log (unique dates with events): {days_in_split}\n")
        f.write(f"Difference (calendar - split-log): {diff_days}\n\n")

        f.write(f"Average MOTOR activated per day: {motor_on_avg:.2f}\n")
        f.write(f"Average MOTOR NO ACTION per day: {no_action_avg:.2f}\n")
        f.write(f"Average total actions per day: {total_avg:.2f}\n")

    print(f"📄 Résumé sauvegardé dans {out_txt}")
