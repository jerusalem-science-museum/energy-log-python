import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import generic_log_analysis as glan
import subprocess

lst_project = [
    "Rocket Hydrogen",
    "Horsepower",
    "Jumping Ring",
    "AirPressure",
    "Light a Fire",
    "Chliran",
    "Pendulum",
]


class LogAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Log Analyzer")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # états
        self.log_file_paths = []
        self.file_name_var = tk.StringVar(value="No files selected")
        self.start_date = tk.StringVar()
        self.start_time = tk.StringVar(value="00:00:00")
        self.end_date = tk.StringVar()
        self.end_time = tk.StringVar(value="23:59:59")
        self.interval = tk.StringVar(value="day")
        self.exhibits = tk.StringVar(value="Horsepower")

        # ce qu'on garde du dernier run
        self.last_figure = None
        self.last_result = None
        self.last_project_name = None
        self.last_start_dt = None
        self.last_end_dt = None
        self.plot_window = None

        self.create_widgets()

 

    def create_widgets(self):
        padding = {'padx': 10, 'pady': 5}

        # fichier
        ttk.Label(self.root, text="Log File(s):").grid(row=0, column=0, sticky="w", **padding)
        self.log_file_path_label = ttk.Label(self.root, text="No file selected", width=50)
        self.log_file_path_label.grid(row=0, column=1, sticky="w", **padding)
        ttk.Button(self.root, text="Browse...", command=self.browse_file).grid(row=0, column=3, **padding)

        # dates
        ttk.Label(self.root, text="Start Date:").grid(row=1, column=0, sticky="w", **padding)
        self.start_date_entry = DateEntry(self.root, textvariable=self.start_date, date_pattern='dd-mm-yyyy')
        self.start_date_entry.grid(row=1, column=1, sticky="w", **padding)

        ttk.Label(self.root, text="Hour start:").grid(row=1, column=2, sticky="e", **padding)
        ttk.Entry(self.root, textvariable=self.start_time, width=10).grid(row=1, column=3, sticky="w", **padding)

        ttk.Label(self.root, text="End Date:").grid(row=2, column=0, sticky="w", **padding)
        self.end_date_entry = DateEntry(self.root, textvariable=self.end_date, date_pattern='dd-mm-yyyy')
        self.end_date_entry.grid(row=2, column=1, sticky="w", **padding)

        ttk.Label(self.root, text="Hour end:").grid(row=2, column=2, sticky="e", **padding)
        ttk.Entry(self.root, textvariable=self.end_time, width=10).grid(row=2, column=3, sticky="w", **padding)

        # interval + exhibit
        ttk.Label(self.root, text="Interval:").grid(row=3, column=0, sticky="w", **padding)
        interval_menu = ttk.Combobox(self.root, textvariable=self.interval,
                                     values=["day", "hour"], state="readonly")
        interval_menu.grid(row=3, column=1, sticky="w", **padding)

        ttk.Label(self.root, text="Exhibits:").grid(row=3, column=2, sticky="e", **padding)
        exhibits_menu = ttk.Combobox(self.root, textvariable=self.exhibits,
                                     values=lst_project, state="readonly")
        exhibits_menu.grid(row=3, column=3, sticky="w", **padding)

        # bouton run
        ttk.Button(self.root, text="Run Analysis", command=self.run_analysis).grid(
            row=4, column=0, columnspan=4, pady=15
        )

        # bouton save
        self.save_button = ttk.Button(self.root, text="Save…", command=self.save_both)
        self.save_button.grid(row=5, column=0, columnspan=4, pady=5)
        self.save_button.state(["disabled"])

        """Create warning label for raw log file Pendulum"""
        self.pend_note = tk.Label(self.root, 
                                 text="⚠️ Note: RAW files from SD must be converted via SPLIT_GUI before loading.",
                                 fg="red", 
                                 font=("Arial", 10, "bold"),
                                 wraplength=500)

        exhibits_menu.bind("<<ComboboxSelected>>", self.check_pendulum_selection)

        # Create warning label (Hidden by default)
        self.pend_note = tk.Label(
            self.root, 
            text="⚠️ Note: RAW files from SD must be converted via SPLIT_GUI before loading.", 
            fg="red", 
            font=("Arial", 10, "bold"),
            wraplength=550
        )

        # New: Add the button to launch SPLIT_GUI (Hidden by default)
        self.split_button = ttk.Button(
            self.root, 
            text="Open SPLIT_GUI Tool", 
            command=self.open_split_tool
        )

    def check_pendulum_selection(self, event=None):
        if self.exhibits.get() == "Pendulum":
            # Show the note
            self.pend_note.grid(row=6, column=0, columnspan=4, pady=(10, 0))
            # Show the button right under it
            self.split_button.grid(row=7, column=0, columnspan=4, pady=5)
        else:
            # Hide both if another project is selected
            self.pend_note.grid_forget()
            self.split_button.grid_forget()

    def open_split_tool(self):
        """Launches the SPLIT_GUI script using the current Python interpreter."""
        try:
            # sys.executable ensures it uses the same Python version running the current script
            script_path = os.path.join(BASE_DIR, "Pendulum_log", "split_gui.py")
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            messagebox.showerror("Launch Error", f"Could not start split_gui.py:\n{e}")

    def browse_file(self):
        paths = filedialog.askopenfilenames(
            title="Select log file(s)",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if paths:
            self.log_file_paths = list(paths)
            names = [os.path.basename(f) for f in self.log_file_paths]
            display_text = ", ".join(names)
            
            self.log_file_path_label.config(text=f"Selected: {display_text}")

    def run_analysis(self):
        proj = self.exhibits.get()

        # reset
        self.last_figure = None
        self.last_result = None
        self.last_project_name = None
        self.last_start_dt = None
        self.last_end_dt = None
        self.save_button.state(["disabled"])

        # parse dates
        try:
            start_dt = datetime.strptime(self.start_date.get() + " " + self.start_time.get(), "%d-%m-%Y %H:%M:%S")
            end_dt = datetime.strptime(self.end_date.get() + " " + self.end_time.get(), "%d-%m-%Y %H:%M:%S")
        except ValueError:
            messagebox.showerror("Invalid Input", "Datetime format must be YYYY-MM-DD HH:MM:SS")
            return

        if not self.log_file_paths:
            messagebox.showerror("No file", "Please select at least one log file.")
            return

        # config events (projets "classiques")
        event_config = {
            "Rocket Hydrogen": "The rocket has ignited",
            "Horsepower": "your horsepower is",
            "Jumping Ring": "Ring jumped!",
            "AirPressure": "The Bottle flew!",
            "Light a Fire": "Peak temperature reached:"
        }

        # === Dispatcher : gère aussi Pendulum/Chliran ===
        try:
            result, fig = glan.run_analysis_dispatch(
                files=self.log_file_paths,
                start_dt=start_dt,
                end_dt=end_dt,
                interval=self.interval.get(),
                event_config=event_config,
                project_name=proj
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error during analysis: {e}")
            return

        if not result:
            messagebox.showinfo("No Data", "No data found in the specified time range.")
            return

        # affiche plot
        if fig is not None:
            self.handle_plot_result(fig)
        else:
            self.try_show_current_matplotlib()

        # store last run for saving
        self.last_figure = fig
        self.last_result = result
        self.last_project_name = proj
        self.last_start_dt = start_dt
        self.last_end_dt = end_dt

        self.save_button.state(["!disabled"])
    def handle_plot_result(self, fig):
        if fig is None:
            if plt.get_fignums():
                fig = plt.gcf()
            else:
                return

        # détruire ancienne fenêtre
        if self.plot_window is not None and tk.Toplevel.winfo_exists(self.plot_window):
            self.plot_window.destroy()

        self.plot_window = tk.Toplevel(self.root)
        self.plot_window.title("Analysis plot")
        canvas = FigureCanvasTkAgg(fig, master=self.plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def try_show_current_matplotlib(self):
        if plt.get_fignums():
            fig = plt.gcf()
            self.handle_plot_result(fig)
            self.save_button.state(["!disabled"])

    def save_both(self):
        """
        1. L'utilisateur choisit un dossier parent
        2. On crée dedans un dossier {project}_{DD_MM}_to_{DD_MM}
        3. On met dedans:
           - (classiques) PNG + summary TXT
           - (Pendulum / Chliran) ce que leurs scripts sauvegardent (Excel + plots + summary)
        """
        if self.last_project_name is None or self.last_start_dt is None or self.last_end_dt is None:
            messagebox.showerror("Save", "No analysis to save.")
            return

        proj = self.last_project_name
        start_dt = self.last_start_dt
        end_dt = self.last_end_dt
        start_md = start_dt.strftime("%d_%m")
        end_md = end_dt.strftime("%d_%m")

        parent_dir = filedialog.askdirectory(title="Select folder where to create the analysis folder")
        if not parent_dir:
            return

        folder_name = f"{proj}_{start_dt.strftime('%d-%m-%Y')}_to_{end_dt.strftime('%d-%m-%Y')}"
        target_dir = os.path.join(parent_dir, folder_name)

        if os.path.exists(target_dir):
            use_it = messagebox.askyesno("Folder exists", f"The folder '{folder_name}' already exists.\nUse it and overwrite files inside?")
            if not use_it:
                return
        else:
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Folder error", f"Could not create folder:\n{e}")
                return

        try:
            glan.save_analysis_dispatch(
                project_name=proj,
                files=self.log_file_paths,
                start_dt=start_dt,
                end_dt=end_dt,
                interval=self.interval.get(),
                target_dir=target_dir,
                fig=self.last_figure,
                result=self.last_result
            )
            messagebox.showinfo("Save Complete", "The analysis has been saved successfully.")
        except Exception as e:
            messagebox.showerror("Save", f"Could not save analysis:\n{e}")
    def on_close(self):
        self.root.quit()
        self.root.destroy()

    

if __name__ == "__main__":
    root = tk.Tk()
    window_width = 650
    window_height = 320
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int((screen_width - window_width) / 2)
    y = int((screen_height - window_height) / 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
   

    app = LogAnalyzerGUI(root)
    root.mainloop()
