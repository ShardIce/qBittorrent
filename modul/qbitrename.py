# -*- encoding: utf-8 -*-
import os
import re
import requests
import csv
from os.path import dirname, abspath
from bs4 import BeautifulSoup
import platform
from jproperties import Properties

configs = Properties()
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'local.properties'), 'rb') as read_prop:
    configs.load(read_prop)
prop_view = configs.items()

if platform.system() == 'Windows':
    TORRENT_PATH=configs.get("torrent_path_win").data
if platform.system() == 'Darwin':
    TORRENT_PATH=configs.get("torrent_path_mac").data
if platform.system() == 'Linux':
    TORRENT_PATH=configs.get("torrent_path_unix").data

FILES_INPUT = os.path.join(TORRENT_PATH, configs.get("torrent_completed_dirname").data) # Input files of completed downloads
FILES_OUTPUT = os.path.join(TORRENT_PATH, configs.get("torrent_renamed_dirname").data) # Output renamed files
TORRENT_INPUT = os.path.join(TORRENT_PATH, configs.get("torrent_input_dirname").data) # Torrent files, named as content (torrent-client is saving them if it set)
TORRENT_OUTPUT = os.path.join(TORRENT_PATH, configs.get("torrent_output_dirname").data) # Processed torrent files will be moved here
MEDIA_OUTPUT = os.path.join(TORRENT_PATH, configs.get("media_output_dirname").data) # Media files for downloaded posters
names = os.path.join(TORRENT_PATH, configs.get("names_filename").data) # Table with old and new filenames for history

def read_csv (names):
    with open(names, "r") as f:
        reader = csv.reader(f, delimiter=';', quoting=csv.QUOTE_NONE)
        for row in reader:
            print(row)
    
def write_csv (names, original, catalog):
    with open(names, 'a', newline='') as f:
        writer = csv.DictWriter(f, delimiter=';', fieldnames=['local','catalog'])
        writer.writerow({'local':original, 'catalog':catalog})

def get_torrents(filename):
    # Find torrent files in directory and get full path for them
    filepath = os.path.join(TORRENT_INPUT, filename + '.torrent')
    if not os.path.exists(filepath):
        print('\x1b[6;30;42m' + 'Skiped, torrent file is not found: "%s' % filepath + '\x1b[0m')
        return None
    return filepath

def get_torrentdata(filename):
    # Find torrent tracker and select parser
    torrent_file_path = get_torrents(filename)
    if not torrent_file_path:
        return None
    tracker_url = get_tracker_url(torrent_file_path)
    if not tracker_url:
        return None
    if 'rutracker' in tracker_url:
        return parse_rutracker(tracker_url)
    if 'arjlover' in tracker_url:
        return parse_arjlover(tracker_url)
    if 'kinozal' in tracker_url:
        return parse_kinozal(tracker_url)

def get_tracker_url(torrent_file_path):
    # Get tracker url from torrent file
    try:
        torrentFile = open(torrent_file_path, 'r', encoding='ascii', errors='replace')
        fileData = torrentFile.read()
        torrentFile.close()
        tracker_urlLen, tracker_url = re.search(r'comment([0-9]{2}):(.+)', fileData).groups()
        tracker_url = re.search(r'(.{' + tracker_urlLen + '})', tracker_url).groups()[0]
        return tracker_url
    except:
        print('\x1b[6;30;41m' + 'Error! Cannot extract tracker url from torrent file %s' % torrent_file_path + '\x1b[0m')
        return None

def prepare_torrents(path):
    for filename in os.listdir(path):
        filename_base, filename_ext = os.path.splitext(os.path.basename(filename))
        if filename_ext == '.torrent':
            try:
                torrent_file = open(os.path.join(path, filename), 'r', encoding='ascii', errors='replace') # may be 'utf-8' in some cases
                torrent_data = torrent_file.read()
                torrent_file.close()
                torrent_name = re.search(r'name[0-9]{2}:(.*)[0-9]{2}:piece', torrent_data, re.UNICODE).groups()[0]
                if filename != torrent_name:
                    print('Renaming: '+filename)
                    rename_file(os.path.join(path, filename), os.path.join(path, torrent_name+'.torrent'))
            except:
                print('\x1b[6;30;41m' + 'Error! Cannot extract file name from torrent file %s' % filename + '\x1b[0m')

def parse_rutracker(tracker_url):
    # Rutracker.org parser
    # Get html page
    try:
        html = BeautifulSoup(requests.get(tracker_url).text, 'html.parser')
    except:
        print('\x1b[6;30;41m' + 'Error! Cannot load page %s' % tracker_url + '\x1b[0m')
        return None
    title = html.title.string
    # Get movie name
    try:
        movie_name = re.search(r' ?([а-яА-ЯёЁ0-9 .,:!№\?&\-–\'\"’`<>«»]+) \/?', title, re.UNICODE).groups()[0]
    except:
        movie_name = title
        print('\x1b[6;30;43m' + 'Warning! Cannot parse russian name from title: %s' % title + '\x1b[0m')
    # Get movie original name
    try:
        movie_original = re.search(r'\/ ([a-zA-ZÀ-ž0-9 .,:&№\!\?\-–\'\"’`<>«»]+) \/?\(?', title, re.UNICODE).groups()[0]
    except:
        movie_original = ''
    # Get movie year
    try:
        movie_year = re.search(r'\[([0-9]{4})', title, re.UNICODE).groups()[0]
    except:
        movie_year = ''
        print('\x1b[6;30;43m' + 'Warning! Cannot parse year from title: %s' % title + '\x1b[0m')
    # Get movie quality/edition
    try:
        movie_quality = re.search(r'(VHS|SAT|HDTV|IPTV|TV|DVB|CAM|Cam|TS|TeleSynch|WEB|SCR|Screener|DVDScr|Remux)', title, re.UNICODE).groups()[0]
        if movie_quality == 'WEB':
            movie_quality = 'Web'
        if movie_quality == 'CAM':
            movie_quality = 'Cam'
        if (movie_quality == 'SCR' or movie_quality == 'Screener' or movie_quality == 'DVDScr'):
            movie_quality = 'Scr'
        if (movie_quality == 'TeleSynch' or movie_quality == 'TeleCine' or movie_quality == 'Telesync'):
            movie_quality = 'TS'
    except:
        movie_quality = ''
    try:
        movie_resolution = re.search(r'(720p|1080p|1080i)', title, re.UNICODE).groups()[0]
    except:
        movie_resolution = ''
    movie_edition = ''
    if ('цветная' in title.lower() or 'колориз' in title.lower() or 'раскрашен' in title.lower()):
        movie_edition = 'Color'
    if ('режиссерская' in title.lower() or 'режиссёрская' in title.lower() or 'Director' in title.lower()):
        movie_edition = 'DC'
    if 'расширенная' in title.lower() or 'extended' in title.lower():
        movie_edition = 'EC'
    if 'специальная' in title.lower() or 'special' in title.lower():
        movie_edition = 'SE'
    if 'широкоэкран' in title.lower() or 'widescreen' in title.lower():
        movie_edition = 'WS'
    if 'полноэкран' in title.lower() or 'fullscreen' in title.lower():
        movie_edition = 'FS'
    if 'unrated' in title.lower():
        movie_edition = 'Unrated'
    # Post-processing of names
    movie_name = re.sub(r'[:–]', ' -', movie_name, 0, re.UNICODE)
    movie_name = prepare_name(movie_name)
    movie_original = re.sub(r'[\-–]', ' ', movie_original, 0, re.UNICODE)
    movie_original = prepare_name(movie_original)
    if movie_original != '':
        movie_original = movie_original+'.'
    if movie_quality != '':
        movie_quality = '.'+movie_quality
    if movie_edition != '':
        movie_edition = '.'+movie_edition
    if movie_resolution != '':
        movie_resolution = '.'+movie_resolution
    if movie_year != '':
        movie_filename = movie_name+' ('+movie_original+movie_year+movie_resolution+movie_quality+movie_edition+')'
    else:
        movie_filename = movie_name
    # Download cover
    try:
        image_url = html.find('div', {'class':'post_body'}).find('var', {'class':'postImg postImgAligned img-right'}).get('title')
        download(MEDIA_OUTPUT, movie_filename, image_url)
    except:
        print('\x1b[6;30;44m' + 'Image cover is not found for: "%s' % movie_filename + '\x1b[0m')
    return movie_filename

def parse_arjlover(tracker_url):
    # Arjlover.net parser
    # Get html page
    try:
        html = BeautifulSoup(requests.get(tracker_url).text, 'html.parser')
    except:
        print('\x1b[6;30;41m' + 'Error! Cannot load page %s' % tracker_url + '\x1b[0m')
        return None
    # Get movie name
    movie_name = html.title.text
    # Get part numbers of series
    try:
        movie_name, movie_part = re.search(r'(.*)\ \((\ ?\d?\d?)\/\d?\d?\)', movie_name).groups()
        movie_part = re.sub(r'\ ', '', movie_part, 0, re.UNICODE)
        movie_part = ' - part' + movie_part
    except:
        movie_part = ''
    # Get all links from the page
    links = []
    for link in html.findAll('a', attrs={'href': re.compile("^http://")}):
        links.append(link.get('href'))
    # Get years from sub-pages of animation and names with years of movies
    movie_year = ''
    for link in links:
        if 'animator.ru' in link:
            try:
                subhtml = requests.get(link).text
                movie_year = re.search(r'year=([0-9]{4})', subhtml).groups()[0]
            except:
                print('\x1b[6;30;43m' + 'Warning! Cannot parse year of: %s' % movie_name + '\x1b[0m')
        if 'forum.arjlover.net' in link:
            try:
                subhtml = requests.get(link).text
                movie_year = re.search(r', ([0-9]{4})', subhtml).groups()[0]
            except:
                print('\x1b[6;30;43m' + 'Warning! Cannot parse year of: %s' % movie_name + '\x1b[0m')
        if 'kino-teatr.ru' in link:
            try:
                subhtml = BeautifulSoup(requests.get(link).text, 'html.parser')
                #movie_name = subhtml.find('meta', attrs={'property':'og:title'}).get('content')
                movie_name = subhtml.find('h1', attrs={'itemprop':'name'}).string
            except:
                print('\x1b[6;30;43m' + 'Warning! Cannot parse name with year of: %s' % movie_name + '\x1b[0m')
    # Post-processing of names
    movie_name = re.sub(r'[:–]', ' -', movie_name, 0, re.UNICODE)
    movie_name = prepare_name(movie_name)
    if movie_year != '':
        movie_filename = movie_name + ' (' + movie_year + ')' + movie_part
    else:
        movie_filename = movie_name + movie_part
    return movie_filename

def parse_kinozal(tracker_url):
    # Kinozal.tv parser (DRAFT)
    # Get html page
    try:
        html = BeautifulSoup(requests.get(tracker_url).text, 'html.parser')
    except:
        print('\x1b[6;30;41m' + 'Error! Cannot load page %s' % tracker_url + '\x1b[0m')
        return None
    title = html.title.string
    # Get movie name
    try:
        movie_name = re.search(r' ?([а-яА-ЯёЁ0-9 .,:!\?&\-–\'\"’`]+) \/?', title, re.UNICODE).groups()[0]
    except:
        movie_name = title
        print('\x1b[6;30;43m' + 'Warning! Cannot parse russian name from title: %s' % title + '\x1b[0m')
    # Get movie original name
    try:
        movie_original = re.search(r'\/ ([a-zA-ZÀ-ž0-9 .,:!?&\-–\'\"’`]+) \/?\(?', title, re.UNICODE).groups()[0]
    except:
        movie_original = ''
        print('\x1b[6;30;42m' + 'No original name found in title: %s' % title + '\x1b[0m')
    # Get movie year
    try:
        movie_year = re.search(r'\/\ ([0-9]{4})\ \/', title, re.UNICODE).groups()[0]
    except:
        movie_year = ''
        print('\x1b[6;30;43m' + 'Warning! Cannot parse year from title: %s' % title + '\x1b[0m')
    # Get movie quality/edition
    try:
        movie_quality = re.search(r'(VHS|SAT|HDTV|TV|DVB|CAM|Cam|WEB)', title, re.UNICODE).groups()[0]
    except:
        movie_quality = ''
    try:
        movie_resolution = re.search(r'(720p|1080p|1080i)', title, re.UNICODE).groups()[0]
    except:
        movie_resolution = ''
    # Post-processing of names
    if movie_original == movie_year:
        movie_original = ''
    movie_name = re.sub(r'[:–]', ' -', movie_name, 0, re.UNICODE)
    movie_name = prepare_name(movie_name)
    movie_original = re.sub(r'[\-–]', ' ', movie_original, 0, re.UNICODE)
    movie_original = prepare_name(movie_original)
    if movie_original != '':
        movie_original = movie_original + '.'
    if movie_quality != '':
        movie_quality = '.'+ movie_quality
    if movie_resolution != '':
        movie_resolution = '.'+ movie_resolution
    if movie_year != '':
        movie_filename = movie_name+' ('+movie_original+movie_year+movie_resolution+movie_quality+')'
    else:
        movie_filename = movie_name
    return movie_filename

def prepare_name(name):
    try:
        # Remove special symbols
        name = re.sub(r'[\\/\"\*\?\!\&<>«»\.\,\:]+', '', name, 0, re.UNICODE)
        # Replace unusual apostrophes
        name = re.sub(r'[`’]', '\'', name, 0, re.UNICODE)
        # Remove repeating spaces
        name = re.sub(r'[ ]+', ' ', name, 0, re.UNICODE)
        name = name.strip()
    except:
        print('\x1b[6;30;41m' + 'Error! Cannot prepare file name %s' % name + '\x1b[0m')
        return None
    return name

def prepare_filename(filename, movie_filename):
    # Get full filename
    if os.path.isdir(os.path.join(FILES_INPUT, filename)):
        ext = ''
    else:
        base, ext = os.path.splitext(filename)
    new_filename = movie_filename + ext
    return new_filename

def create_link(src, dst):
    os.symlink(src, dst)

def rename_file(src, dst):
    if os.path.isfile(dst):
        print('\x1b[6;30;43m' + 'Warning! File already exists: %s' % dst + '\x1b[0m')
    else:
        try:
            os.rename(src, dst)
        except OSError as error:
            print('\x1b[6;30;41m' + 'Error! Cannot rename/move file, %s' % error + '\x1b[0m')

def extract_dir(src, dst):
    """
    src - full path of the directory, parsed from the torrent file
    dst - new name of the movie, parsed from the torrent webpage
    """
    listFiles = sorted(os.listdir(src))
    # Find few video files with similar size, small files are ignored
    parts_video = [f for f in listFiles if re.search(r'.*\.(avi|mkv|mp4|mpg|mov|divx|wmv|ts)$', f)]
    parts_video_size = []
    for part in parts_video:
        parts_video_size.append(os.stat(os.path.join(src, part)).st_size)
    for part in parts_video:
        if round( max(parts_video_size) / os.stat(os.path.join(src, part)).st_size ) > 2:
            parts_video.remove(part)
            print('\x1b[6;30;42m' + 'It is a small videofile, check it manually: %s' % part + '\x1b[0m')
    # Find subtitle files of srt and then other formats, english subtitles are ignored
    parts_subs = [f for f in listFiles if re.search(r'.*\.(srt|SRT)$', f)]
    if len(parts_subs) == 0:
        parts_subs = [f for f in listFiles if re.search(r'.*\.(ass|ASS)$', f)]
    if len(parts_subs) == 0:
        parts_subs = [f for f in listFiles if re.search(r'.*\.(idx|IDX)$', f)]
    if len(parts_subs) == 0:
        parts_subs = [f for f in listFiles if re.search(r'.*\.(sub|SUB)$', f)]
    for part in parts_subs:
        if ('.en' in part.lower() or 'en.' in part.lower() or 'eng.' in part.lower()):
            parts_subs.remove(part)
    # Large collections and complex releases with different videos and subtitles are not processed and must be renamed manually or cleared before next launch
    if len(parts_video) > 4 or (len(parts_subs) != len(parts_video) and len(parts_subs) > 0):
        parts_video = []
        parts_subs = []
        print('\x1b[6;30;43m' + 'It is a collection or complex release, check it manually: %s' % src + '\x1b[0m')
    # Rename and move video files, parts are processed
    part_number = 1
    for part in parts_video:
        part_base, part_ext = os.path.splitext(os.path.basename(part))
        if len(parts_video)!=1:
            dstNew = dst + ' - part' + str(part_number)
        else:
            dstNew = dst
        partNew = dstNew + part_ext
        try:
            rename_file(os.path.join(src,part), os.path.join(FILES_OUTPUT,partNew))
        except:
            print('\x1b[6;30;41m' + 'Error! Cannot rename file from %s to %s' % (part, dstNew) + '\x1b[0m')
        part_number += 1
    # Rename and move subtitle files, parts are processed
    part_number = 1
    for part in parts_subs:
        part_base, part_ext = os.path.splitext(os.path.basename(part))
        if len(parts_subs)!=1:
            dstNew = dst + ' - part' + str(part_number)
        else:
            dstNew = dst
        partNew = dstNew + part_ext
        try:
            rename_file(os.path.join(src,part), os.path.join(FILES_OUTPUT,partNew))
        except:
            print('\x1b[6;30;41m' + 'Error! Cannot rename file from %s to %s' % (part, dstNew) + '\x1b[0m')
        part_number += 1
    # Delete the directory if it empty
    try:
        os.rmdir(src)
    except:
        print('\x1b[6;30;42m' + 'Directory is not empty, check it manually: %s' % src + '\x1b[0m')

def download(dir, name, url):
    r = requests.get(url)
    path = os.path.join(dir, name + re.search(r'(.\w\w\w\w?)$', url).groups()[0])
    with open(path, 'wb') as f:
        f.write(r.content)

def main():
    print('Hello, Find downloads in "%s":' % FILES_INPUT)
    prepare_torrents(TORRENT_INPUT)
    file_count = 0
    process_count = 0
    for filename in os.listdir(FILES_INPUT):
        file_count = file_count + 1
        print('Process a file: "%s"' % filename)
        movie_filename = get_torrentdata(filename)
        if movie_filename is None:
            continue
        new_filename = prepare_filename(filename, movie_filename)
        if new_filename:
            old_filepath = os.path.join(FILES_INPUT, filename)
            new_filepath = os.path.join(FILES_OUTPUT, new_filename)
            if os.path.isdir(old_filepath):
                extract_dir(old_filepath, new_filename)
            elif os.path.isfile(old_filepath):
                rename_file(old_filepath, new_filepath)
                rename_file(os.path.join(TORRENT_INPUT, filename+'.torrent'), os.path.join(TORRENT_OUTPUT, filename+'.torrent'))
                #create_link(new_filepath,old_filepath)
                #write_csv(names, filename, new_filename)
            else:
                print('\x1b[6;30;41m' + 'Error! It is a special file (socket, FIFO, device file)' + '\x1b[0m')
            process_count = process_count + 1
    print("%d files were processed from %d total found files" % (process_count, file_count))

if __name__ == "__main__":
    main()
