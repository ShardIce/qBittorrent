# -*- encoding: utf-8 -*-
import platform
from jproperties import Properties
import subprocess

configs = Properties()
with open('local.properties', 'rb') as read_prop:
    configs.load(read_prop)
prop_view = configs.items()

if platform.system() == 'Windows':
    TORRENT_PATH=configs.get("torrent_path_win").data
if platform.system() == 'Darwin':
    TORRENT_PATH=configs.get("torrent_path_mac").data
if platform.system() == 'Linux':
    TORRENT_PATH=configs.get("torrent_path_unix").data

SCRIPT_FOLDER = configs.get("scripts_folder").data

# Список скриптов в том порядке, в котором они должны быть импортированы
script_names = [
    "qbitrename.py",
    "compressed_video_files.py",
]

def run_script(script_name):
    completed_message = f"Скрипт {script_name} завершился!"
    subprocess.run(["python", SCRIPT_FOLDER + script_name])
    print(completed_message)

for script_name in script_names:
    run_script(script_name)