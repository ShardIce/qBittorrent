import os
import re
import requests
import logging
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

API_KEY = configs.get('DTMB').data

logging.basicConfig(filename=os.path.join(LOG_SAVE_PATH, 'poster_errors.log'), level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

def check_poster(movie_name):
    for extension in ['jpg', 'webp', 'gif', 'png']:
        filepath = os.path.join(MEDIA_OUTPUT, f'{movie_name}.{extension}')
        if os.path.exists(filepath):
            logging.info("Найден постер: %s", filepath)
            return True
    logging.warning("Постер не найден: %s", movie_name)
    return False

def download_poster(original_movie_name, movie_name): # , year=None): &year={year}
    url = f'https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={movie_name}'
    response = requests.get(url)
    data = response.json()

    if data.get('total_results') == 0:
        return False

    movie_id = data['results'][0]['id']
    url = f'https://api.themoviedb.org/3/movie/{movie_id}/images?api_key={API_KEY}&language=ru-RU&include_image_language=ru,null'
    response = requests.get(url)
    data = response.json()

    if len(data['posters']) == 0:
        return False

    poster_path = data['posters'][0]['file_path']
    url = f'https://image.tmdb.org/t/p/w500{poster_path}'
    response = requests.get(url)

    if response.status_code == 200:
        poster_filename = f'{original_movie_name}.jpg'
        filepath = os.path.join(MEDIA_OUTPUT, poster_filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)

            return True
    else:
        return False

for filename in os.listdir(FILES_INPUT):
    if filename.endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv')):
        # Получаем имя файла без расширения
        movie_name = os.path.splitext(filename)[0]

        original_movie_name = movie_name

        # Удаляем информацию о качестве видео из названия файла
        movie_name = re.sub(r'\b(VHS|SAT|HDTV|IPTV|TV|DVB|CAM|TS|TeleSynch|SCR|Screener|DVDScr|Remux|\d+p|\.\w+)\b', '',
                            movie_name)

        # Удаляем точки
        movie_name = re.sub(r'\b("." \d+p|\.\w+)\b', '', movie_name)

        # Удаляем лишние пробелы в начале и конце строки
        movie_name = movie_name.strip()

        # Извлекаем год из имени файла, если он есть в круглых скобках в конце строки
        year_match = re.search(r'\((19|20)\d{2}\)$', movie_name)
        if year_match:
            year = year_match.group(0).strip('()')
            # Удаляем год из имени файла
            movie_name = re.sub(r'\s*\((19|20)\d{2}\)$', '', movie_name).strip()
        else:
            year = ''

        # Если после '(' в названии файла есть название фильма на латинице, используем его
        if '(' in movie_name:
            match = re.search(r'\(([^()]*[a-zA-Z]+[^()]*)\)', movie_name)
            if match:
                movie_name = match.group(1)

        # Иначе, если в названии файла есть кириллические символы, используем их
        elif re.search('[а-яА-Я]', movie_name):
            movie_name = re.sub(r'\s*\((\d{4})\)$', '', movie_name)

        # Создаем новое имя с годом, если он найден
        if year:
            movie_name = f"{movie_name}"

        if not check_poster(movie_name):
            download_poster(original_movie_name, movie_name)
