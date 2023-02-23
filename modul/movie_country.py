import os
import re
import telegram
import asyncio
import logging
from imdb import IMDb
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

FILES_INPUT = os.path.join(TORRENT_PATH, configs.get("compress_dirname").data)  # Сжатые фильмы
BASE_PATH = os.path.join(TORRENT_PATH, configs.get("mediateka_path_country").data)  # Вывод переименованных файлов
LOG_SAVE_PATH = os.path.join(TORRENT_PATH, configs.get("logs_dirname").data)

ia = IMDb()

COUNTRY_PATHS = {
    configs.get("EuroMovie").data: BASE_PATH + r'\\' + configs.get("euro_movie").data,
    configs.get("AsianMovie").data: BASE_PATH + r'\\' + configs.get("asian_movie").data,
    configs.get("RusMovie").data: BASE_PATH + r'\\' + configs.get("rus_movie").data
}

async def main():
    logging.basicConfig(filename=os.path.join(LOG_SAVE_PATH, 'movie_country_errors.log'), level=logging.ERROR)
    for filename in os.listdir(FILES_INPUT):
        if filename.endswith(('.mp4', '.mkv', '.avi', '.mov', '.wmv')):
            name, ext = os.path.splitext(filename)
            match = re.search(r'\((\d{4})\)|\.(\d{4})\.', name)
            if match:
                year = match.group(1) or match.group(2)
                name = name.replace(match.group(0), '').strip()
            else:
                year = None

            # Добавляем логирование поиска фильмов
            logging.info(f'Searching for movie: {name}, year: {year}')

            try:
                search = ia.search_movie(name)
                if year:
                    search = [s for s in search if str(s.get('year', '')).startswith(year)]
                if not search:
                    continue
                result = search[0]

                ia.update(result, 'main')
                country = result.get('countries', [])[0]

                # Проверяем, что название фильма на кириллице
                if not bool(re.search('[а-яА-Я]', name)):
                    continue

                for countries, path in COUNTRY_PATHS.items():
                    if country in countries:
                        country_path = path
                        break
                else:
                    country_path = os.path.join(FILES_INPUT, configs.get("other_movie").data)

                if not os.path.exists(country_path):
                    os.makedirs(country_path)

                old_path = os.path.join(FILES_INPUT, filename)
                new_path = os.path.join(country_path, filename)
                os.rename(old_path, new_path)

                bot = telegram.Bot(configs.get('APITG').data)
                await bot.send_message(chat_id=configs.get('TGGROUP').data, text=f'Фильм "{name}" добавлен в папку {os.path.basename(country_path)}.')
            except Exception as e:
                # Записываем ошибки в лог-файл
                logging.error(f'Error processing {filename}: {e}')

                # При возникновении ошибок, копируем файл в папку "Errors"
                errors_path = os.path.join(FILES_INPUT, 'Errors')
                if not os.path.exists(errors_path):
                    os.makedirs(errors_path)
                old_path = os.path.join(FILES_INPUT, filename)
                new_path = os.path.join(errors_path, filename)
                os.rename(old_path, new_path)

asyncio.run(main())
