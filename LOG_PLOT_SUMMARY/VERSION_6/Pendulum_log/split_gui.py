import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

# ניסיון ייבוא הפונקציה מהקובץ שלך
try:
    from split_log import split_log_by_month_with_datetime
except ImportError:
    # הודעה במקרה שהקובץ split_log.py לא נמצא באותה תיקייה
    pass

def run_split():
    input_file = file_entry.get()
    output_dir = output_entry.get()
    start_str = start_entry.get()
    end_str = end_entry.get()

    if not input_file or not output_dir:
        messagebox.showwarning("Warning", "Please select both file and output folder.")
        return

    try:
        # המרת הטקסט מהממשק לאובייקטים של datetime
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_str, "%Y-%m-%d")

        split_log_by_month_with_datetime(
            file_path=input_file,
            output_dir=output_dir,
            start_dt=start_dt,
            end_dt=end_dt
        )
        messagebox.showinfo("Success", f"Done! Files saved to:\n{output_dir}")
    except ValueError:
        messagebox.showerror("Error", "Date format must be YYYY-MM-DD (e.g., 2026-05-13)")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")

def browse_file():
    filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    file_entry.delete(0, tk.END)
    file_entry.insert(0, filename)

def browse_output():
    directory = filedialog.askdirectory()
    output_entry.delete(0, tk.END)
    output_entry.insert(0, directory)

# יצירת הממשק
root = tk.Tk()
root.title("Science Museum - Pendulum Log Splitter")
root.geometry("550x450")

tk.Label(root, text="Log File Splitter", font=("Arial", 16, "bold")).pack(pady=10)

# בחירת קובץ
tk.Label(root, text="Select Raw LOG file:").pack()
file_frame = tk.Frame(root)
file_frame.pack(pady=5)
file_entry = tk.Entry(file_frame, width=40)
file_entry.pack(side=tk.LEFT, padx=5)
tk.Button(file_frame, text="Browse", command=browse_file).pack(side=tk.LEFT)

# בחירת תיקיית יעד
tk.Label(root, text="Select Output Folder:").pack()
out_frame = tk.Frame(root)
out_frame.pack(pady=5)
output_entry = tk.Entry(out_frame, width=40)
output_entry.pack(side=tk.LEFT, padx=5)
tk.Button(out_frame, text="Browse", command=browse_output).pack(side=tk.LEFT)

# בחירת תאריכים
date_frame = tk.LabelFrame(root, text=" Date Range (YYYY-MM-DD) ", pady=10)
date_frame.pack(pady=20, padx=20, fill="x")

# תאריך התחלה
tk.Label(date_frame, text="Start Date:").grid(row=0, column=0, padx=10)
start_entry = tk.Entry(date_frame)
start_entry.insert(0, "2020-01-01") # ברירת מחדל
start_entry.grid(row=0, column=1, padx=10)

# תאריך סיום
tk.Label(date_frame, text="End Date:").grid(row=1, column=0, padx=10, pady=5)
end_entry = tk.Entry(date_frame)
end_entry.insert(0, datetime.now().strftime("%Y-%m-%d")) # היום כברירת מחדל
end_entry.grid(row=1, column=1, padx=10, pady=5)

# כפתור הפעלה
tk.Button(root, text="START SPLIT", command=run_split, bg="#2196F3", fg="white", font=("Arial", 12, "bold"), width=20).pack(pady=20)

root.mainloop()