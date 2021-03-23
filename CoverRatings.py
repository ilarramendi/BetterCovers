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
from datetime import datetime, timedelta
from urllib.parse import quote

overWrite = '-o' in sys.argv
config = {}
minVotes = 5

if '-a' in sys.argv:
    config['omdbApi'] = sys.argv[sys.argv.index('-a') + 1]
    #with open('./config.json', 'w') as js: json.dump({'omdbApi': apiKey}, js)
elif exists('./config.json'):
    with open('./config.json', 'r') as js: config = json.load(js)
else: 
    print('Please supply an api key with: -a apiKey')
    sys.exit()

def getConfigEnabled(conf):
    for cf in conf:
        if conf[cf]: return True
    return False

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

def addMediaInfoToImage(img, info, cfg, y):
    hAlign = cfg['alignment']['horizontal']
    height = cfg['imageHeight']
    config = cfg['config']
    padding = cfg['padding']
    space = cfg['space']

    x = img.size[0] - padding if hAlign == 'right' else padding
    if info[0] != "HDR":
        if config[info[1]]:
            with Image.open(resource_path('media/' + info[1] + '.png')) as im: 
                im.thumbnail((100, height), Image.ANTIALIAS)
                img.paste(im, (x - (im.size[0] if hAlign == 'right' else 0), y), im)
                x += (im.size[0] + space) * (-1 if hAlign == 'right' else 1)
    elif info[1] == "UHD" and config['UHD-HDR']:
        with Image.open(resource_path('media/UHD-HDR.png')) as im: 
            im.thumbnail((100, height), Image.ANTIALIAS)
            img.paste(im, (x - (im.size[0] if hAlign == 'right' else 0), y), im)
            x += (im.size[0] + space) * (-1 if hAlign == 'right' else 1)
    else:
        if config['HDR']:
            with Image.open(resource_path('media/HDR.png')) as im:
                im.thumbnail((100, height), Image.ANTIALIAS)
                img.paste(im, (x - (im.size[0] if hAlign == 'right' else 0), y), im)
                x += (im.size[0] + space) * (-1 if hAlign == 'right' else 1)
        if config[info[1]]:
            with Image.open(resource_path('media/' + info[1] + '.png')) as im: 
                im.thumbnail((100, height), Image.ANTIALIAS)
                img.paste(im, (x - (im.size[0] if hAlign == 'right' else 0), y), im)
                x += (im.size[0] + space) * (-1 if hAlign == 'right' else 1)
    if config[info[2]]:
        with Image.open(resource_path('media/' + info[2] + '.png')) as im:
                im.thumbnail((100, height), Image.ANTIALIAS)
                img.paste(im, (x - (im.size[0] if hAlign == 'right' else 0), y), im)    

def addRatingsToImage(img, ratings, cfg):
    vAlign = cfg['alignment']['vertical']
    hAlign = cfg['alignment']['horizontal']
    textHeight = cfg['textHeight']
    borderHeight = cfg['borderHeight']
    imgHeight = cfg['imageHeight']
    textColor = cfg['textColor']
    borderColor = cfg['borderColor']
    padding = cfg['padding']
    space = cfg['space']
    config = cfg['config']
    
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    recsize = (
        (0, img.size[1] - borderHeight if vAlign == 'bottom' else 0),
        (img.size[0], img.size[1] if vAlign == 'bottom' else borderHeight)) 
    ImageDraw.Draw(overlay).rectangle(recsize, fill=borderColor)
    res = Image.alpha_composite(img, overlay).convert("RGB")
    font = ImageFont.truetype(resource_path("media/font.ttf"), textHeight)
    draw = ImageDraw.Draw(res)

    le = (300 - padding) // len(ratings) 
    x = padding if hAlign == 'center' else 300 if hAlign == 'right' else 0
    
    #for rt in ratings if hAlign != 'right' else reversed(ratings):
    for rt in ratings:
        if config[rt]:
            im = Image.open(resource_path('media/' + rt + ".png")) 
            im.thumbnail((150, imgHeight), Image.ANTIALIAS)
            tsize = draw.textsize(ratings[rt], font)[0]
            sp = (le - im.size[0] - tsize - space) // 2
            imgPos = (
                x + sp if hAlign == 'center' else (x + space) if hAlign == 'left' else x - tsize - space * 2 - im.size[0],
                (res.size[1] - imgHeight - (borderHeight - imgHeight) // 2) if vAlign == 'bottom' else (borderHeight - imgHeight) // 2)
            res.paste(im, imgPos, im)
            txtPos = (
                x + sp + im.size[0] + space if hAlign == 'center' else x + space * 2 + im.size[0] if hAlign == 'left' else imgPos[0] + im.size[0] + space,
                res.size[1] - textHeight - (borderHeight - textHeight) // 2 - 1 if vAlign == 'bottom' else (borderHeight - textHeight) // 2 - 1)
            draw.text(txtPos, ratings[rt], textColor, font=font)
            x = x + le if hAlign == 'center' else txtPos[0] + tsize if hAlign == 'left' else imgPos[0]
    return res

def downloadImage(src, retry):
    i = 0
    while i < retry:
        try: return Image.open(get(src, stream=True).raw).convert("RGBA")
        except Exception as e:
            print(e,'xd')
            sleep(0.5)
        i += 1
    print('\033[91mFailed to download:', url, '\033[0m')
    return False

def avg(lst):
    return "{:.1f}".format(sum(lst) / len(lst)) if len(lst) > 0 else 0

def getSeasonsMetadata(imdbid, tmdbid, seasons):
    metadata = {}
    for path, sn in seasons:
        res = getJSON('https://api.themoviedb.org/3/tv/' + tmdbid + '/season/' + str(sn) + '?api_key=c13bbebafbd3dad0e281c6241304aeff&language=en')
        if not res:
            print('Error getting info for season:', sn)
            continue
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

        if season != {'episodes': {}, 'ratings': {}, 'path': path}: metadata[sn] = season
    #print(json.dumps(metadata, indent=4, sort_keys=True))
    return metadata

def getSeasons(folder):
    rs = glob(join(folder, '*'))
    seasons = []
    for fl in rs:
        res = findall('(.*\/[Ss]eason[ ._-](\d{1,3}))', fl)
        if len(res) == 1: seasons.append(res[0])
    return seasons

def createImages(metadata, type, folder):
    if 'cover' in metadata:
        if (not exists(join(folder, 'poster.jpg')) or overWrite):
            startTime = datetime.now()
            img = downloadImage('https://image.tmdb.org/t/p/w342' + metadata['cover'] if metadata['cover'][0] == '/' else metadata['cover'], 5)
            if img:
                if getConfigEnabled(config[type]['ratings']['config']) and len(metadata['ratings']) > 0:
                    img = addRatingsToImage(img, metadata['ratings'], config[type]['ratings'])
                if type == 'movie' and getConfigEnabled(config[type]['mediainfo']['config']):
                    mediaFiles = []
                    for ex in ['mkv', 'mp4']: mediaFiles += glob(file + '/*.' + ex)
                    if len(mediaFiles) > 0:
                        minfo = getMediaInfo(mediaFiles[0])
                        if minfo: addMediaInfoToImage(img, minfo, config[type], 
                                    config[type]['ratings']['borderHeight'] + config[type]['space'] if config[type]['ratings']['alignment']['vertical'] == 'top' and len(metadata['ratings']) > 0 else 5)
                action = 'overwriten' if exists(file + '/poster.jpg') else 'saved'
                img.save(join(folder, 'poster.jpg'))
                diff = datetime.now() - startTime
                print('\033[92mCover image ' + action + ' for: ' + metadata['title'] + ' in ' + str(diff.seconds * 1000 + diff.microseconds // 1000) + 'ms\033[0m')
        else: print('cover exists, not overwtiting')
    if type == 'tv' and getConfigEnabled(config['season']['ratings']['config']):
        for sn in sorted(metadata['seasons'], key=int):
            startTime = datetime.now()
            season = metadata['seasons'][sn]
            out = join(season['path'], 'poster.jpg')
            if (not exists(out) or overWrite):
                if 'cover' in season:
                    if len(season['ratings']) > 0:
                        img = downloadImage('https://image.tmdb.org/t/p/w342' + season['cover'] if season['cover'][0] == '/' else season['cover'], 5)
                        if img: img = addRatingsToImage(img, season['ratings'], config['season']['ratings'])
                
                    action = 'overwriten' if exists(out) else 'saved'
                    img.save(out)
                    diff = datetime.now() - startTime
                    print('\033[92mCover image ' + action + ' for: ' + metadata['title'] + ' Season ' + sn + ' in ' + str(diff.seconds * 1000 + diff.microseconds // 1000) + 'ms\033[0m')
            else: print('cover exists, not overwtiting')
                       
def processFolder(folder):
    seasons = getSeasons(folder)
    type = 'tv' if len(seasons) > 0 else 'movie'
    name, year = getMediaName(folder)
    metadata = getMetadata(name, type, year)
    #print(json.dumps(metadata, indent=4, sort_keys=True))
    if type == 'tv' and 'tmdbid' in metadata: 
        metadata['seasons'] = getSeasonsMetadata(metadata['imdbid'] if 'imdbid' in metadata else False, metadata['tmdbid'], seasons)
    createImages(metadata, type, folder)
    #print(json.dumps(metadata, indent=10, sort_keys=True))

files = sorted(glob([pt for pt in sys.argv[1:] if '/' in pt][0]))
lenFiles = str(len(files))
for index, file in  enumerate(files): 
    #print('[' + str(index + 1) + '/' + lenFiles + ']')
    processFolder(file)
