# -*- encoding: utf-8 -*-
import os
import logging
import csv
import platform
from jproperties import Properties
import subprocess
import time
from datetime import timedelta
import telegram

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

input_path = os.path.join(TORRENT_PATH, configs.get("torrent_renamed_dirname").data)
output_path = os.path.join(TORRENT_PATH, configs.get("torrent_renamed_dirname").data)
MEDIA_OUTPUT = os.path.join(TORRENT_PATH, configs.get("media_output_dirname").data)
CSV_SAVE_PATH = os.path.join(TORRENT_PATH, configs.get("torrent_renamed_dirname").data, "compress_video.csv")

# настройка логирования
log_path = os.path.join(TORRENT_PATH, configs.get("torrent_renamed_dirname").data, "my_log_file.log")
logging.basicConfig(filename=log_path, level=logging.ERROR)

# Настройки ffmpeg
num_processors = 4
memory = 10
codec = 'libx264'  # Нужный нам кодек. Увидеть все введите в косоли ffmpeg -codecs рабочий: libx265, libx264, hevc h264_nvenc
qscale = 1  # Значение 1 соответствует самому лучшему качеству, а 31 — самому худшему.
format_video = 'mkv'  # поменять контейнер c формат m4v на mkv
crf = 24  # Cтепень сжатия. Чем меньше число, тем лучше качество, но больше размер.

# Настройки бота для телеграмм
telegram_bot_token = 'telegram_bot_token'
telegram_chat_id = 'telegram_chat_id'

# Проверьте, является ли файл видеофайлом
def is_video_file(filename):
    video_file_extensions = [".mp4", ".avi", ".mkv", ".mov", ".wmv"]
    return any(filename.endswith(extension) for extension in video_file_extensions)

# Сжать видео файл
def compress_video(filename):
    input_file = os.path.join(input_path, filename)
    output_folder = os.path.join(output_path, os.path.splitext(filename)[0])
    file_name_path = f"{output_folder}/compressed-{filename}"
    image_poster = os.path.join(MEDIA_OUTPUT, os.path.splitext(filename)[0] + '.jpg')

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist")
        return filename, 0, 0

    # Проверьте, является ли входной файл видеофайлом
    if not is_video_file(filename):
        return filename, 0, 0

    # Создайте выходную папку, если она не существует
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Получаем размер исходного файла
    input_size = round(os.path.getsize(input_file) / (10 ** 9), 3)

    # Старт времени начало сжатия
    start_time = time.time()

    # Сжать видеофайл с помощью указанного кодека -an -map 0:a -g 30
    cmd = f"ffmpeg -loop 1 -i \"{image_poster}\" \"{input_file}\" -c:v {codec} -c:a copy -threads {num_processors} -crf {crf} -q:v {qscale} -f matroska -y \"{file_name_path}\""
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Конец измерения времени сжатия
    end_time = time.time()

    # Расчет времени сжатия
    compression_time = end_time - start_time

    # Запишем данные в формате ЧЧ:ММ:СС
    time_in_hhmmss = str(timedelta(seconds=compression_time)).split(".")[0]
    print(time_in_hhmmss)

    # Проверьте наличие ошибок во время сжатия
    if result.returncode != 0:
        print(f"Error: Failed to compress {filename}")
        print(result.stderr.decode())
        return filename, 0, 0, time_in_hhmmss

    # Получаем размер выходных файлов
    output_size = round(os.path.getsize(file_name_path) / (10 ** 9), 3)

     # Удалить исходный файл
    # os.remove(input_file)

    return filename, input_size, output_size, time_in_hhmmss

async def send_telegram_notification(filename, time_in_hhmmss):
    try:
        bot = telegram.Bot(token=telegram_bot_token)
        time_delta = timedelta(hours=0, minutes=0, seconds=0)
        time_list = time_in_hhmmss.split(":")
        if len(time_list) == 3:
            time_delta = timedelta(hours=int(time_list[0]), minutes=int(time_list[1]), seconds=int(time_list[2]))
        elif len(time_list) == 2:
            time_delta = timedelta(hours=0, minutes=int(time_list[0]), seconds=int(time_list[1]))
        elif len(time_list) == 1:
            time_delta = timedelta(hours=0, minutes=0, seconds=int(time_list[0]))
        else:
            raise ValueError(f"Invalid time format: {time_in_hhmmss}")
        total_seconds = time_delta.total_seconds()
        message = f"Видео было успешно сжато! \n{filename} \nВремя сжатия: \n{str(timedelta(seconds=total_seconds))}"
        await bot.send_message(chat_id=telegram_chat_id, text=message)
    except Exception as e:
        logging.error(f"Error occurred while sending telegram notification for file {filename}: {str(e)}")

# Сохраните информацию о сжатом видео в файл CSV.
def save_to_csv(data):
    try:
        with open(CSV_SAVE_PATH, "a", encoding="UTF-8", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=',')

            # Проверьте, существует ли файл CSV
            if os.path.exists(CSV_SAVE_PATH) and os.path.getsize(CSV_SAVE_PATH) == 0:
                writer.writerow(["Filename", "Input Size (GB)", "Output Size (GB)", "Compression Time"])

            writer.writerows(data)
            # csvfile.close()

    except Exception as e:
        print(f"Error: Failed to write to CSV file {CSV_SAVE_PATH}. Error: {e}")

if __name__ == "__main__":
    import asyncio

    # Получить список всех видеофайлов во входном пути
    video_files = [file for file in os.listdir(input_path) if is_video_file(file)]
    compressed_video_data = []

    # Сжать каждый видеофайл
    for file in video_files:
        filename, input_size, output_size, time_in_hhmmss = compress_video(file)
        compressed_video_data.append([filename, input_size, output_size, time_in_hhmmss])

    # Сохраните сжатые видеоданные в файл CSV.
    save_to_csv(compressed_video_data)

    asyncio.run(send_telegram_notification(filename, time_in_hhmmss))

    print("Video compression and saving to CSV file completed.")
