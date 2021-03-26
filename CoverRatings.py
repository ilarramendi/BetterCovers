from glob import glob
from re import findall, match
from subprocess import call, getstatusoutput
from requests import get
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from os import access, W_OK
from os.path import exists, abspath, join
import json
import sys
from datetime import timedelta
import time
from urllib.parse import quote
from threading import Thread

overWrite = '-o' in sys.argv
threads = 4 if not '-w' in sys.argv else int(sys.argv[sys.argv.index('-w') + 1])
config = {}
minVotes = 5
extensions = ['mkv', 'mp4']

if '-a' in sys.argv:
    config['omdbApi'] = sys.argv[sys.argv.index('-a') + 1]
    #with open('./config.json', 'w') as js: json.dump({'omdbApi': apiKey}, js)
elif exists('./config.json'):
    with open('./config.json', 'r') as js: config = json.load(js)
else: 
    print('Please supply an api key with: -a apiKey')
    sys.exit()

with open('./cover.html', 'r') as fl: coverHTML = fl.read()

def getConfigEnabled(conf):
    for cf in conf:
        if conf[cf]: return True
    return False

def frequent(list):
    count = 0
    no = list[0]
    for i in list:
        current_freq = list.count(i)
        if (current_freq > count):
            count = current_freq
            num = i
    print(list, num)
    return num 

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = abspath(".")
    return join(base_path, relative_path)

def getJSON(url):
    response = get(url)
    if response.status_code == 401: # API hit limit
        print('\033[91mDaily Api Limit Reached!!!!!\033[0m')
        sys.exit()
    if response.status_code != 200 or 'application/json' not in response.headers.get('content-type'): # Wrong response from server
        print('\033[91mError connecting, code:', response.status_code, '\033[0m')
        if response.status_code != 404: 
            print(url)
            print(response.text)
        return False
    try:
        return response.json()
    except Exception as ex:
        print(ex)
        return False
    
    res = response.json()

def getMetadata(name, type, year):
    metadata = {'ratings': {}}
    if config['tmdbAPI'] != '': 
        res = getJSON('https://api.themoviedb.org/3/search/' + type + '?api_key=' + config['tmdbAPI'] + '&language=en&page=1&include_adult=false&query=' + quote(name) + ('&year=' + year if year else ''))
        if res and 'results' in res and len(res['results']) > 0:
            res = res['results'][0]
            if 'poster_path' in res and res['poster_path']:
                metadata['cover'] = res['poster_path']
            if 'backdrop_path' in res: metadata['backdrop'] = res['backdrop_path']
            if 'vote_average' in res: metadata['ratings']['TMDB'] = str(res['vote_average'])
            if 'id' in res:
                metadata['tmdbid'] = str(res['id'])
                ids = getJSON('https://api.themoviedb.org/3/' + type + '/' + metadata['tmdbid'] + '/external_ids?api_key=' + config['tmdbAPI'])
                if ids and 'imdb_id' in ids and ids['imdb_id']: metadata['imdbid'] = ids['imdb_id']
            if 'title' in res: metadata['title'] = res['title']
            elif 'name' in res: metadata['title'] = res['name'] 
        else: print('No results found on TMDB for:', name, year if year else '')
          
    if config['omdbApi'] != '':
        url = 'http://www.omdbapi.com/?apikey=' + config['omdbApi'] + '&tomatoes=true'
        url += '&i=' + metadata['imdbid'] if 'imdbid' in metadata else '&t=' + quote((metadata['title'] if 'title' in metadata else name).replace(' ', '+')) + ('&y=' + year if year else '')
        res = getJSON(url)
        if res:
            if 'cover' not in metadata and 'Poster' in res and res['Poster'] != 'N/A':
                metadata['cover'] = res['Poster']
            if 'Metascore' in res and res['Metascore'] != 'N/A': 
                metadata['ratings']['MTS'] = str(int(res['Metascore']) / 10)
            if 'imdbRating' in res and res['imdbRating'] != 'N/A': metadata['ratings']['IMDB'] = res['imdbRating']
            if 'Ratings' in res:
                for rt in res['Ratings']:
                    if rt['Source'] == 'Rotten Tomatoes' and rt['Value'] != 'N/A':
                        metadata['ratings']['RT'] = str(int(rt['Value'][:-1]) / 10)
                        break
            if 'Title' in res: metadata['title'] = res['Title']
        else: print('No results found on OMDB for:', name, year if year else '')
    return metadata

def getMediaInfo(file):
    out = getstatusoutput('mediainfo "' + file + '" --Inform="Video;%colour_primaries%,%Width%x%Height%,%Format%,"')
    if out[0] == 0: 
        rt = out[1].split(',')
        if len(rt) < 3: return False
        rt[0] = 'HDR' if rt[0] == 'BT.2020' else 'SDR'
        res = rt[1].split('x')
        if len(res) != 2: return False
        rt[1] = 'UHD' if (res[0] == '3840' or res[1] == '2160') else 'HD' if (res[0] == '1920' or res[1] == '1080') else 'SD'
        return rt[:3]
    else: 
        print('\033[91Error getting media info, Is mediainfo installed?\n', out[1], '\033[0m')
        return False

def getMediaName(folder):
    inf = findall("\/([^\/]+)[ \.]\(?(\d{4})\)?$", folder)
    if len(inf) == 0: inf = findall("\/([^\/]+)$", folder)
    else: return inf[0]
    if len(inf) == 0:
        print('\033[93mCant parse name from: ' + file + '\033[0m')
        return (False, False)
    return inf + [False]

def downloadImage(url, retry, src):
    i = 0
    while i < retry:
        try:
            img = Image.open(get(url, stream=True).raw).save(src)
            return True
        except Exception as e:
            print(e,'xd')
            sleep(0.5)
        i += 1
    print('\033[91mFailed to download:', url, '\033[0m')
    return False

def avg(lst):
    return "{:.1f}".format(sum(lst) / len(lst)) if len(lst) > 0 else 0

def getSeasonsMetadata(imdbid, tmdbid, seasons):
    metadata = {'seasons': {}}
    for path, sn in seasons:
        res = getJSON('https://api.themoviedb.org/3/tv/' + tmdbid + '/season/' + str(sn) + '?api_key=c13bbebafbd3dad0e281c6241304aeff&language=en')
        if not res:
            print('Error getting info on TMDB for season:', sn)
        season = {'episodes': {}, 'ratings': {}, 'path': path}
        #print(json.dumps(res, indent=4, sort_keys=True))
        if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']: season['cover'] = res['poster_path']
        if 'episodes' in res:
            for ep in res['episodes']:
                episode = {'ratings': {}}
                if 'episode_number' not in ep or ep['episode_number'] == 'N/A': continue
                if 'still_path' in ep and ep['still_path'] != 'N/A': episode['cover'] = ep['still_path']
                if 'vote_average' in ep and ep['vote_average'] != 'N/A' and 'vote_count' in ep and ep['vote_count'] > minVotes:
                    #print(json.dumps(ep, indent=4, sort_keys=True))
                    episode['ratings']['TMDB'] = float(ep['vote_average'])
                if episode != {'ratings': {}}: season['episodes'][ep['episode_number']] = episode
        if config['omdbApi'] != '' and imdbid:
            res = getJSON('http://www.omdbapi.com/?i=' + imdbid + '&Season=' + sn + '&apikey=' + config['omdbApi'])
            if res and 'Episodes' in res:
                for ep in res['Episodes']:
                    if 'Episode' in ep and ep['Episode'].isdigit() and int(ep['Episode']) in season['episodes']:
                        episode = int(ep['Episode'])
                        #if 'Episode' in res and res['Episode'] != 'N/A' and 'imdbRating' in res['Episodes'][ep] and res['Episodes'][ep]['imdbRating'] != 'N/A':
                        #    season['episodes'][ep]['ratings']['IMDB'] = res['Episodes'][ep]['imdbRating']
                        if 'imdbRating' in ep and ep['imdbRating'] != 'N/A': 
                            season['episodes'][episode]['ratings']['IMDB'] = float(ep['imdbRating'])
                        if 'imdbID' in ep and ep['imdbID'] != 'N/A':
                            season['episodes'][episode]['imdbid'] = ep['imdbID']
            else: print('Error getting episodes for season:', sn)
        avr = avg([season['episodes'][ep]['ratings']['IMDB'] for ep in season['episodes'] if 'IMDB' in season['episodes'][ep]['ratings']])
        if avr != 0: season['ratings']['IMDB'] = avr
        avr = avg([season['episodes'][ep]['ratings']['TMDB'] for ep in season['episodes'] if 'TMDB' in season['episodes'][ep]['ratings']])
        if avr != 0: season['ratings']['TMDB'] = avr
        if getConfigEnabled(config['tv']['mediainfo']['config']) or getConfigEnabled(config['season']['mediainfo']['config']) or getConfigEnabled(config['episode']['mediainfo']['config']):
            mediaFiles = []
            res = []
            codec = []
            hdr = []
            for ex in extensions: mediaFiles += glob(join(path, '*.' + ex))
            #print(json.dumps(season['episodes'], indent=4, sort_keys=True))
            for fl in mediaFiles:
                ep = findall('[Ss]\d{1,3}[Ee](\d{1,4})', fl)
                if len(ep) > 0 and int(ep[0]) in season['episodes']:
                    ep = int(ep[0])
                    minfo = getMediaInfo(fl)   
                    hdr.append(minfo[0])
                    res.append(minfo[1])
                    codec.append(minfo[2])
                    season['episodes'][ep]['mediainfo'] = minfo
            if len(hdr) > 0 and len(res) > 0 and len(codec) > 0:
                season['mediainfo'] = [frequent(hdr), frequent(codec), frequent(res)]
        if season != {'episodes': {}, 'ratings': {}, 'path': path}: metadata['seasons'][sn] = season
    #print(json.dumps(metadata, indent=4, sort_keys=True))
    res = []
    codec = []
    hdr = []
    for mt in metadata['seasons']:
        if 'mediainfo' in metadata['seasons'][mt]:
            minfo = metadata['seasons'][mt]['mediainfo']
            hdr.append(minfo[0])
            res.append(minfo[1])
            codec.append(minfo[2])
    if len(hdr) > 0 and len(res) > 0 and len(codec) > 0: metadata['mediainfo'] = [frequent(hdr), frequent(codec), frequent(res)]
    #print(json.dumps(metadata, indent=4, sort_keys=True))
    return metadata

def getSeasons(folder):
    rs = glob(join(folder, '*'))
    seasons = []
    for fl in rs:
        res = findall('(.*\/[Ss]eason[ ._-](\d{1,3}))', fl)
        if len(res) == 1: seasons.append(res[0])
    return seasons
  
def generateImage(config, ratings, mediainfo, url, thread):
    st = time.time()
    img = downloadImage(url, 4, './threads/' + str(thread) + '/cover.png')
    #print('d', timedelta(seconds=round(time.time() - st)))
    if not img: return False
    HTML = coverHTML
    dictionary = {
        'top': '$horizontal $start',
        'bottom': '$horizontal $end',
        'left': '$vertical $start',
        'right': '$vertical $end'
    }

    align = dictionary[config['ratings']['position']].replace('$', 'r')
    align += ' ra' + config['ratings']['alignment'] + ' '
    align += dictionary[config['mediainfo']['position']].replace('$', 'm')
    align += ' ma' + config['mediainfo']['alignment']
    HTML = HTML.replace('containerClass', align)
    
    rts = ''
    minfo = ''

    HTML += '\n<style>\n' + generateCSS(config) + '\n</style>'

    for rt in ratings: rts += "<div class = 'ratingContainer'><img src= '../../media/" + rt + ".png' class='ratingIcon'><label class='ratingText'>" + ratings[rt] + "</label></div>\n"
    for mi in mediainfo: minfo += "<div class='mediainfoImgContainer'><img src= '../../media/" + mi + ".png' class='mediainfoIcon'></div>\n"  
    HTML = HTML.replace('<!--RATINGS-->', rts)
    HTML = HTML.replace('<!--MEDIAINFO-->', minfo)
    with open('./threads/' + str(thread) + '/tmp.html', 'w') as out:
        out.write(HTML)
    st = time.time()

    
    #print('g', timedelta(seconds=round(time.time() - st)))        
    return 0 == call(['cutycapt --url="file:///home/ilarramendi/scripts/Cover-Ratings/threads/' + str(thread) + '/tmp.html" --delay=1000 --min-width=600 --out="./threads/' + str(thread) + '/tmp.jpg"'], shell=True)            

def processFolder(folder, thread):
    st = time.time()
    seasons = getSeasons(folder)
    type = 'tv' if len(seasons) > 0 else 'movie'
    name, year = getMediaName(folder)

    #print(name, '(' + year + ')' if year else '')
    if not overWrite and type == 'movie' and exists(join(folder, 'poster.jpg')):
        return print('Poster exists')
    
    #print('Downloading metadata for:', name)
    metadata = getMetadata(name, type, year)
    if 'cover' not in metadata: return print('\033[93mCover image not found :C\033[0m')
    
    if type == 'movie' and getConfigEnabled(config['movie']['mediainfo']['config']):
        mediaFiles = []
            
        for ex in extensions: mediaFiles += glob(join(folder, '*.' + ex))
        if len(mediaFiles) > 0:
            #print('Getting media info for:', name)
            minfo = getMediaInfo(mediaFiles[0])
            if minfo:
                metadata['mediainfo'] = minfo
            else: print('Error getting metadata!')
        else: print('No video files found!')
    elif type == 'tv' and 'tmdbid' in metadata:
        print('Getting seasons metadata and mediainfo for:', name)
        sns = getSeasonsMetadata(metadata['imdbid'] if 'imdbid' in metadata else False, metadata['tmdbid'], seasons)
        metadata['seasons'] = sns['seasons']
        if 'mediainfo' in sns: metadata['mediainfo'] = sns['mediainfo'] 
    
    #print(json.dumps(metadata, indent=10, sort_keys=True))
    #print('Generating cover for:', name)
    st2 = time.time()
    img = generateImage(
        config['movie'],
        metadata['ratings'] if 'ratings' in metadata else [],
        metadata['mediainfo'] if 'mediainfo' in metadata else [],
        'https://image.tmdb.org/t/p/original' + metadata['cover'],
        thread
    )
    if img: 
        call(['mv', './threads/' + str(thread) + '/tmp.jpg', join(folder, 'poster.jpg')])
        print('\033[92m[' + str(thread) + '] Succesfully generated cover for', name, 'in', timedelta(seconds=round(time.time() - st)), timedelta(seconds=round(time.time() - st2)), '\033[0m')
    else: print('\033[91mError generating image\033[0m')

def generateCSS(config):
    minfo = config['mediainfo']
    rts = config['ratings']
    
    body = 'body {\n'
    
    body += '--mediainfoContainerMargin: ' + minfo['space'] + ';\n'
    body += '--mediainfoPadding: ' + minfo['padding'] + ';\n'
    body += '--mediainfoBColor: ' + minfo['color'] + ';\n' 
    body += '--mediainfoIconWidth: ' + minfo['imgWidth'] + ';\n'
    
    body += '--ratingContainerMargin: ' + rts['space'] + ';\n'
    body += '--ratingIconMargin: ' + rts['iconSpace'] + ';\n'
    body += '--ratingsContainerPadding: ' + rts['padding'] + ';\n'
    body += '--ratingsContainerBColor: ' + rts['color'] + ';\n'
    body += '--ratingIconWidth: ' + rts['imgWidth'] + ';\n'
    body += '--ratingTextColor: ' + rts['textColor'] + ';\n'
    body += '--ratingTextFontFamily: ' + rts['fontFamily'] + ';\n'
    body += '--ratingTextFontSize: ' + rts['fontSize'] + ';\n'

    body += '}'

    return body

path = [pt for pt in sys.argv[1:] if '/' in pt][0]
files = sorted(glob(path)) if '*' in path else [path]
lenThread = len(files) // threads
thrs = []

if not exists('./threads'): call(['mkdir', './threads'])

# Start threads
i = 0
while i < threads:
    i += 1
    if not exists('./threads/' + str(i)): call(['mkdir', './threads/' + str(i)])
    fn = lambda i: [processFolder(fl, i) for fl in files[(i - 1) * lenThread:i * lenThread]]
    thread = Thread(target=fn, args=(i,))
    thread.start()
    thrs.append(thread)

if not exists('./threads/' + str(i)): call(['mkdir', './threads/' + str(i)])
thread = Thread(target=lambda i: [processFolder(fl, i) for fl in files[i * lenThread:]], args=(i,))
thread.start()
thrs.append(thread)

for th in thrs: th.join()
call(['rm', './threads', '-r'])
