# Museum Energy Log Analyzer

A centralized Python GUI for analyzing and visualizing energy consumption logs from various museum exhibits (e.g., Pendulum, Chliran).

## 🚀 Overview
This tool allows museum staff to process raw logs from multiple sources—including **SD cards, Linux-based systems, and Raspberry Pi controllers**. 

It splits raw data into organized daily/monthly files and generates analytical plots. The application serves as a wrapper for multiple sub-projects, ensuring a consistent workflow across different hardware exhibits and operating systems.

## 📁 Project Structure
\energy\energy-log-python\LOG_PLOT_SUMMARY\VERSION_6\
* **`LAUNCH_GUI.py`**: The main entry point. Use this to select exhibits and run analysis.
* **`Chliran_log/`**: Contains logic and GUI for the Chliran exhibit logs.
* **`Pendulum_log/`**: Contains logic and GUI for the Pendulum exhibit logs.
* **`.bat` files**: Shortcut scripts to launch the tools directly on Windows without opening a terminal.

## 🛠 Installation & Setup
1.  **Requirement**: Ensure Python 3.10+ is installed.
2.  **Dependencies**: Install the required libraries:
    ```bash
    pip install pandas matplotlib
    ```
3.  **Folder Location**: Ensure the exhibit folders (`Chliran_log`, `Pendulum_log`) are located in the same directory as `LAUNCH_GUI.py`.

## 📖 How to Use

### 1. Preparation (Splitting Raw Logs)
Raw logs from SD cards (often named `LOG.TXT`) are usually unsorted. You must split them before analysis:
* Open the main GUI (`LAUNCH_GUI.py`).
* Select the exhibit (e.g., **Chliran**).
* Click **"Open Split Tool"**.
* Select your raw file and a destination folder (e.g., Downloads).
* The tool will generate files named `log_YYYY-MM-DD.txt`.

### 2. Analysis & Plotting
* In the main GUI, select the exhibit.
* Click **"Load Files"** and select the *split* files created in the previous step.
* Click **"Run Analysis"** to generate the charts.

## ⚠️ Important Notes
* **Permission Error**: If you see "Permission Denied", make sure the log file is not open in Excel or another text editor.
* **Date Format**: The system expects dates in `YYYY-MM-DD` format.
* **File Naming**: Do not manually rename the split files,
