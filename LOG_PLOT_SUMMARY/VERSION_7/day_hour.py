import re
import sys
import matplotlib.pyplot as plt
import pandas as pd
import tkinter as tk
from tkinter import filedialog

# 0. פתיחת חלונית לבחירת קובץ הלוג
root = tk.Tk()
root.withdraw()  # הסתרת החלון הראשי של tkinter

log_file_path = filedialog.askopenfilename(
    title="בחר קובץ לוג",
    filetypes=[
        ("Log & Text files", "*.txt *.log"),
        ("All files", "*.*")
    ]
)

# בדיקה שנבחר קובץ
if not log_file_path:
    print("לא נבחר קובץ. היציאה מהתוכנית.")
    sys.exit()

print(f"נבחר הקובץ: {log_file_path}")

# 1. טעינת הנתונים מקובץ הלוג
timestamps = []
# ביטוי רגולרי לחילוץ זמן מתוך שורות בלוג שמכילות מדידת כוח סוס / שאיבה
log_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - your horsepower is:")

with open(log_file_path, "r", encoding="utf-8") as f:
    for line in f:
        match = log_pattern.match(line)
        if match:
            timestamps.append(match.group(1))

# בדיקה שנמצאו נתונים תואמים בקובץ
if not timestamps:
    print("לא נמצאו שורות התואמות לפורמט המבוקש בקובץ שנבחר.")
    sys.exit()

# 2. יצירת DataFrame והמרת התאריכים
df = pd.DataFrame(timestamps, columns=["datetime"])
df["datetime"] = pd.to_datetime(df["datetime"])

# 3. סינון לפי התאריכים המבוקשים: 1, 2, ו-3 באוגוסט (למשל לשנת 2026)
df = df[
    (df["datetime"].dt.month == 8)
    & (df["datetime"].dt.day.isin([1, 2, 3]))
    & (df["datetime"].dt.year == 2026)
]

if df.empty:
    print("לא נמצאו נתונים עבור התאריכים 1-3 באוגוסט 2026.")
    sys.exit()

# חילוץ תאריך (ללא שעה) ושעה בלבד
df["Date"] = df["datetime"].dt.strftime("%Y-%m-%d")
df["Hour"] = df["datetime"].dt.hour

# 4. יצירת טבלת ציר (Pivot Table) של ספירת האירועים לפי שעה ותאריך
pivot_df = (
    df.groupby(["Hour", "Date"]).size().unstack(fill_value=0)
)

# הוספת שעות חסרות (אם יש שעות שבהן לא היו אירועים כלל) כדי להבטיח ציר X מלא (0-23)
pivot_df = pivot_df.reindex(range(24), fill_value=0)

# 5. יצירת גרף העמודות
fig, ax = plt.subplots(figsize=(14, 6))

# הציור מקבץ באופן אוטומטי 3 עמודות לכל שעה
pivot_df.plot(kind="bar", ax=ax, width=0.8)

# עיצוב הגרף
ax.set_title("Number of Events per Hour (Aug 1 - Aug 3)", fontsize=14)
ax.set_xlabel("Hour of Day", fontsize=12)
ax.set_ylabel("Event Count", fontsize=12)
ax.set_xticklabels(range(24), rotation=0)
ax.grid(axis="y", linestyle="--", alpha=0.7)
plt.legend(title="Date")

plt.tight_layout()
plt.show()