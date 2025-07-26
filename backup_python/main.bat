@echo off
title Auto Backup DB
call "E:\Code_setup\main_venv\Scripts\activate.bat"
python "E:\Code_setup\python_setup\promark_bots\backup_python\bkp_main.py"
pause