import subprocess
import platform
import sys
import os
import requests

def run_py_in_terminal(file_name):
    full_name = f"{file_name}.py"
    cur_os = platform.system()
    print(f"[INFO] Launching {full_name} in a new terminal window.")

    if cur_os == "Windows":
        venv_activate = r"E:\Code_setup\main_venv\Scripts\activate.bat"
        script_dir = r"E:\Code_setup\python_setup\promark_bots\GEM_BOT"
        full_script_path = f"{script_dir}\\{full_name}"
        # Create a temporary .bat file to launch the script with venv
        bat_file = os.path.join(script_dir, f"run_{file_name}.bat")
        with open(bat_file, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'title {file_name}\n')
            f.write(f'call "{venv_activate}"\n')
            f.write(f'python "{full_script_path}"\n')
            f.write('pause\n')
        os.startfile(bat_file)
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


def check_service():
    url = "http://103.223.15.148:5025//api/services"
    headers = {"Content-Type": "application/json"}
    data = {
        "username": "Promark",
        "password": "Pm#24",
        "project": "Promark Groups",
        "sub_project": "Promark Gem Bots",
        "service": "Gem web scrapping and Data check"
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
    except:
        print('Driver stopped')
        return 'ON', '30'

    if response.status_code == 200 and response.json().get('services'):
        service_data = response.json()['services'][0]
        status = service_data.get('status', 'ON')
        return status

    return 'ON'


def run_in_parallel(file_names):
    if check_service() == 'OFF':
        print("Service Not working...")
        return None
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
