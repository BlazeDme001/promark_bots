import subprocess
import platform
import sys

def run_py_in_terminal(file_name):
    full_name = f"{file_name}.py"
    cur_os = platform.system()
    print(f"[INFO] Launching {full_name} in a new terminal window.")

    if cur_os == "Windows":
        # Use 'start' to open a new Command Prompt window and run the script
        subprocess.Popen([
            "cmd", "/c",
            f"start cmd /k {sys.executable} {full_name}"
        ])
    elif cur_os == "Linux":
        # For GNOME Terminal
        subprocess.Popen([
            "gnome-terminal", "--",
            sys.executable, full_name
        ])
        # For KDE, use "konsole"
        # subprocess.Popen(["konsole", "-e", sys.executable, full_name])
        # For XFCE, use "xfce4-terminal"
        # subprocess.Popen(["xfce4-terminal", "--command", f"{sys.executable} {full_name}"])
    else:
        print(f"[ERROR] Unsupported OS: {cur_os}")

def run_in_parallel(file_names):
    for name in file_names:
        run_py_in_terminal(name)

if __name__ == '__main__':
    file_names = ['main_Web_Camera', 'main_Mini_PC',
                  'main_Audio_Video_Equipment',
                  'main_Table', 'main_Bed',
                  'main_Writing_and_Display_Board',
                  'main_Desk','main_Furniture',
                  'main_Chair','main_Lectern_and_Podium',
                  'main_LED_Display_System']
    run_in_parallel(file_names)
