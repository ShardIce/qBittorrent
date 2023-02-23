import os
from PIL import Image
import subprocess
import logging
import time
import platform
from jproperties import Properties

configs = Properties()
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local.properties'), 'rb') as read_prop:
    configs.load(read_prop)
prop_view = configs.items()

if platform.system() == 'Windows':
    TORRENT_PATH = configs.get("torrent_path_win").data
if platform.system() == 'Darwin':
    TORRENT_PATH = configs.get("torrent_path_mac").data
if platform.system() == 'Linux':
    TORRENT_PATH = configs.get("torrent_path_unix").data

FILES_INPUT = os.path.join(TORRENT_PATH, configs.get("torrent_renamed_dirname").data)  # Ввод переименованных файлов
FILES_OUTPUT = os.path.join(TORRENT_PATH, configs.get("compress_dirname").data) # Вывод сжатых файлов
MEDIA_OUTPUT = os.path.join(TORRENT_PATH, configs.get("media_output_dirname").data)  # Медиафайлы для загруженных постеров
LOG_SAVE_PATH = os.path.join(TORRENT_PATH, configs.get("logs_dirname").data) # Путь к логам

def get_poster_extensions(video_filename):
    poster_extensions = []
    for ext in ['png', 'gif', 'webp']: # изменяем на список необходимых расширений
        poster_path = os.path.join(MEDIA_OUTPUT, os.path.splitext(video_filename)[0] + "." + ext)
        if os.path.exists(poster_path):
            poster_extensions.append(ext)
    return poster_extensions


def compress_video(FILES_INPUT, output_folder):
    # Настройка логирования
    log_path = os.path.join(LOG_SAVE_PATH, "compress_video.log")
    logger = logging.getLogger("compress_video")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    for filename in os.listdir(FILES_INPUT):
        if filename.lower().endswith(('.avi', '.mp4', '.mkv', '.mov', '.flv', '.wmv')): # список расширений можно расширить по необходимости
            video_path = os.path.join(FILES_INPUT, filename)
            filename_utf8 = filename.encode('utf-8')
            output_path = os.path.join(output_folder, os.path.splitext(filename_utf8.decode())[0] + ".mkv")
            poster_extensions = get_poster_extensions(filename)

            if len(poster_extensions) > 0:
                poster_path = os.path.join(MEDIA_OUTPUT, os.path.splitext(filename)[0] + "." + poster_extensions[0])
            else:
                poster_path = os.path.join(MEDIA_OUTPUT, os.path.splitext(filename)[0] + ".jpg")

            logger.info("Video file: %s", filename)
            logger.info("Poster path: %s", poster_path)

            # Старт времени начало сжатия
            start_time = time.time()

            # Сжать видео файл с помощью ffmpeg
            # Сжать видео файл и добавить постер
            command = ["ffmpeg", "-i", video_path, "-i", poster_path, "-c:v", "libx264", "-crf", "23", "-preset",
                       "medium", "-c:a", "copy", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-attach", poster_path,
                       "-metadata:s:t", "mimetype=image/jpeg", "-metadata:s:t", "filename=poster.jpg", "-metadata",
                       "comment=Compressed with Python script", "-map", "0:v", "-map", "0:a", "-ss", "00:00:05", "-t", "00:00:15", "-shortest", output_path]

            try:
                subprocess.call(command)
            except Exception as e:
                logger.error("Error compressing video: %s", str(e), exc_info=True)
                continue

            # Добавление информации в log
            log_info = f"{filename} - size before: {os.path.getsize(video_path)} bytes, " \
                       f"size after: {os.path.getsize(output_path)} bytes"
            logger.info(log_info)

compress_video(FILES_INPUT, FILES_OUTPUT)
