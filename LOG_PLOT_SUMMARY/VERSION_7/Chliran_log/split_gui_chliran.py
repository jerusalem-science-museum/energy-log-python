import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

# --- PATH CONFIGURATION ---
# Add the current script directory to sys.path to ensure 'split_log' can be imported
# regardless of where the script is launched from.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

try:
    # Import the core splitting logic from the sibling file 'split_log.py'
    from split_log import split_log_by_month_with_datetime
except ImportError:
    messagebox.showerror("Import Error", "Could not find 'split_log.py' in the script directory.")

def run_split():
    """
    Main execution function: Retrieves user input from the GUI, 
    validates dates, and triggers the log splitting process.
    """
    input_file = file_entry.get()
    output_dir = output_entry.get()
    start_str = start_entry.get()
    end_str = end_entry.get()

    # Basic validation to ensure required paths are provided
    if not input_file or not output_dir:
        messagebox.showwarning("Input Required", "Please select both a source file and an output folder.")
        return

    try:
        # Call the processing function from split_log.py.
        # Note: split_log_by_month_with_datetime handles string-to-datetime 
        # conversion internally using pandas.
        split_log_by_month_with_datetime(
            file_path=input_file,
            output_dir=output_dir,
            start_dt=start_str,
            end_dt=end_str
        )
        messagebox.showinfo("Success", f"Processing complete!\nFiles saved to:\n{output_dir}")
    except Exception as e:
        # Catch any runtime errors (Permission denied, file corruption, etc.)
        messagebox.showerror("Processing Error", f"An error occurred during execution:\n{e}")

def browse_file():
    """Opens a file dialog to select the raw LOG.TXT file."""
    filename = filedialog.askopenfilename(
        title="Select Chliran Raw Log File",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if filename:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, filename)

def browse_output():
    """Opens a directory dialog to select the destination folder."""
    directory = filedialog.askdirectory(title="Select Output Folder")
    if directory:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, directory)

# --- GUI LAYOUT ---
root = tk.Tk()
root.title("Science Museum - Chliran Log Splitter")
root.geometry("550x480")

# Header Section
tk.Label(root, text="Chliran Log Splitter", font=("Arial", 16, "bold"), fg="#1976D2").pack(pady=15)

# File Selection UI
tk.Label(root, text="Select Raw LOG.TXT from SD Card:", font=("Arial", 10)).pack(anchor="w", padx=45)
file_frame = tk.Frame(root)
file_frame.pack(pady=5)
file_entry = tk.Entry(file_frame, width=45)
file_entry.pack(side=tk.LEFT, padx=5)
tk.Button(file_frame, text="Browse", command=browse_file, width=10).pack(side=tk.LEFT)

# Output Selection UI
tk.Label(root, text="Destination Folder:", font=("Arial", 10)).pack(anchor="w", padx=45, pady=(10, 0))
out_frame = tk.Frame(root)
out_frame.pack(pady=5)
output_entry = tk.Entry(out_frame, width=45)

# CROSS-PLATFORM COMPATIBILITY: Automatically set default output to the user's Downloads folder
user_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
output_entry.insert(0, user_downloads)

output_entry.pack(side=tk.LEFT, padx=5)
tk.Button(out_frame, text="Browse", command=browse_output, width=10).pack(side=tk.LEFT)

# Date Configuration Section
date_frame = tk.LabelFrame(root, text=" Date Range Settings (YYYY-MM-DD) ", pady=10, padx=10)
date_frame.pack(pady=20, padx=40, fill="x")

# Start Date Input
tk.Label(date_frame, text="Start Date:").grid(row=0, column=0, sticky="w")
start_entry = tk.Entry(date_frame)
start_entry.insert(0, "2025-09-07") # Default start for the Chliran exhibit
start_entry.grid(row=0, column=1, padx=20, pady=5)

# End Date Input
tk.Label(date_frame, text="End Date:").grid(row=1, column=0, sticky="w")
end_entry = tk.Entry(date_frame)
end_entry.insert(0, "2026-05-13") # Default end for the Chliran exhibit
end_entry.grid(row=1, column=1, padx=20, pady=5)

# Execution Button
tk.Button(
    root, 
    text="START PROCESSING", 
    command=run_split, 
    bg="#388E3C", 
    fg="white", 
    font=("Arial", 12, "bold"), 
    height=2, 
    width=25
).pack(pady=20)

# Footer Note
tk.Label(root, text="Museum Technical Tool - Chliran Log Analysis", fg="gray").pack(side=tk.BOTTOM, pady=10)

if __name__ == "__main__":
    root.mainloop()