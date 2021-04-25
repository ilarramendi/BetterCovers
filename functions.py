from glob import glob
from re import findall, match
from subprocess import call, getstatusoutput, DEVNULL
from requests import get
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from os import access, W_OK
from os.path import exists, realpath, join
import sys 
from datetime import timedelta
import time
from urllib.parse import quote
import json
extensions = ['mkv', 'mp4', 'avi']
minVotes = 5


def generateCSS(config):
    minfo = config['mediainfo']
    rts = config['ratings']
    
    body = 'body {\n'
    
    body += '--mediainfoContainerMargin: ' + minfo['space'] + ';\n'
    body += '--mediainfoPadding: ' + minfo['padding'] + ';\n'
    body += '--mediainfoBColor: ' + minfo['color'] + ';\n' 
    body += '--mediainfoIconSize: ' + minfo['imgSize'] + ';\n'
    
    body += '--ratingContainerMargin: ' + rts['space'] + ';\n'
    body += '--ratingIconMargin: ' + rts['iconSpace'] + ';\n'
    body += '--ratingsContainerPadding: ' + rts['padding'] + ';\n'
    body += '--ratingsContainerBColor: ' + rts['color'] + ';\n'
    body += '--ratingIconSize: ' + rts['imgSize'] + ';\n'
    body += '--ratingTextColor: ' + rts['textColor'] + ';\n'
    body += '--ratingTextFontFamily: ' + rts['fontFamily'] + ';\n'
    body += '--ratingTextFontSize: ' + rts['fontSize'] + ';\n'

    body += '}'

    return body

def resource_path(name):
    pt = join(realpath(__file__).rpartition('/')[0], name)
    if exists(pt): 
        return pt
    try:
        return join(sys._MEIPASS, name)
    except Exception: 
        print('\033[91mMissing file:', name, '\033[0m')
        call(['pkill', '-f', 'BetterCovers'])

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
    return num 

def getJSON(url): # JSON?
    response = get(url)
    if response.status_code == 401: # API hit limit
        print('\033[91mDaily Api Limit Reached!!!!!\033[0m')
        call(['pkill', '-f', 'BetterCovers'])
    if response.status_code != 200 or 'application/json' not in response.headers.get('content-type'): # Wrong response from server
        print('\033[91mError connecting, code:', response.status_code, url, '\033[0m')
        return False
    try:
        return response.json()
    except Exception as ex:
        print(ex)
        return False
    
    res = response.json()

def getMetadata(name, type, year, omdbApi, tmdbApi): # {'ratings': {}, 'type': str, 'cover'?: str, 'backdrop'?: str, 'tmdbid'?: str}
    metadata = {'ratings': {}, "type": type}
    if tmdbApi != '': 
        res = getJSON('https://api.themoviedb.org/3/search/' + type + '?api_key=' + tmdbApi + '&language=en&page=1&include_adult=false&query=' + quote(name) + ('&year=' + year if year else ''))
        if res and 'results' in res and len(res['results']) > 0:
            res = res['results'][0]
            if 'poster_path' in res and res['poster_path']:
                metadata['cover'] = 'https://image.tmdb.org/t/p/original' + res['poster_path']
            if 'backdrop_path' in res and res['backdrop_path']: metadata['backdrop'] = 'https://image.tmdb.org/t/p/original' + res['backdrop_path']
            if 'vote_average' in res: metadata['ratings']['TMDB'] = str(res['vote_average'])
            if 'id' in res:
                metadata['tmdbid'] = str(res['id'])
                ids = getJSON('https://api.themoviedb.org/3/' + type + '/' + metadata['tmdbid'] + '/external_ids?api_key=' + tmdbApi)
                if ids and 'imdb_id' in ids and ids['imdb_id']: metadata['imdbid'] = ids['imdb_id']
            if 'title' in res: metadata['title'] = res['title']
            elif 'name' in res: metadata['title'] = res['name'] 
        else: print('No results found on TMDB for:', name, year if year else '')
          
    if omdbApi != '':
        url = 'http://www.omdbapi.com/?apikey=' + omdbApi + '&tomatoes=true'
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
            #print(json.dumps(res, indent = 5))
            if 'Title' in res: metadata['title'] = res['Title']
        else: print('No results found on OMDB for:', name, year if year else '')
    return metadata

def getMediaInfo(file): # [str]?
    out = getstatusoutput('mediainfo "' + file + '" --Inform="Video;%colour_primaries%,%Width%x%Height%,%Format%"')
    if out[0] == 0: 
        rt = out[1].split(',')
        if len(rt) < 3: return False
        rt[0] = 'HDR' if rt[0] == 'BT.2020' else 'SDR'
        res = rt[1].split('x')
        if len(res) != 2: return False
        rt[1] = 'UHD' if (res[0] == '3840' or res[1] == '2160') else 'HD' if (res[0] == '1920' or res[1] == '1080') else 'SD'
        if rt[2] != 'HEVC' and rt[2] != 'AVC': rt[2] = 'UNDEFINED'
        return rt[:3]
    else: 
        print('\033[91Error getting media info, Is mediainfo installed?\n', out[1], '\033[0m')
        return False

def getMediaName(folder): # [str?, str?] => [name, year]
    inf = findall("\/([^\/]+)[ \.]\(?(\d{4})\)?", folder)
    if len(inf) == 0: inf = findall("\/([^\/]+)$", folder)
    else: return [inf[0][0].translate({'.': ' ', '_': ' '}), inf[0][1]]
    if len(inf) == 0:
        print('\033[93mCant parse name from: ' + folder + '\033[0m')
        return [False, False]
    return inf + [False]

def downloadImage(url, retry, src): # Boolean
    i = 0
    while i < retry:
        try:
            Image.open(get(url, stream=True).raw).save(src)
            return True
        except Exception as e:
            sleep(0.5)
        i += 1
    print('\033[91mFailed to download:', url, '\033[0m')
    return False

def avg(lst):
    return "{:.1f}".format(sum(lst) / len(lst)) if len(lst) > 0 else 0

def getEpisodes(folder, season): # {int: str,...} => {enumber: epath,...}
    fls = []
    episodes = {}
    for ex in extensions: fls += glob(join(folder, '*.' + ex))
    for fl in fls:
        nm = findall('S0*' + season + 'E0*(\d+)', fl)
        if len(nm) > 0:
            episodes[int(nm[0])] = fl
    return episodes

def getSeasonsMetadata(imdbid, tmdbid, seasons, omdbApi, tmdbApi, episodeMediainfo, minvotes, title): # {'seasons': {int: {'episodes': {}, 'ratings': {}, 'path': str, 'mediainfo'?: [str]}}, 'mediainfo'?: [str]}
    metadata = {'seasons': {}}
    for path, sn in seasons:
        season = {'episodes': {}, 'ratings': {}, 'path': path}
        eps = getEpisodes(path, sn)
        for ep in eps:
            season['episodes'][ep] = {'path': eps[ep], 'ratings': {}}
        
        if tmdbApi != '' and tmdbid:
            res = getJSON('https://api.themoviedb.org/3/tv/' + tmdbid + '/season/' + str(sn) + '?api_key=' + tmdbApi + '&language=en')
            if res:
                if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']: season['cover'] = 'https://image.tmdb.org/t/p/original' + res['poster_path']
                if 'episodes' in res:
                    for ep in res['episodes']:
                        if 'episode_number' not in ep or ep['episode_number'] == 'N/A': continue
                        if ep['episode_number'] in season['episodes']:
                            if 'still_path' in ep and ep['still_path'] != 'N/A' and ep['still_path']:
                                season['episodes'][ep['episode_number']]['cover'] = 'https://image.tmdb.org/t/p/original' + ep['still_path']
                            if 'vote_average' in ep and ep['vote_average'] != 'N/A' and 'vote_count' in ep and ep['vote_count'] > minVotes:
                                season['episodes'][ep['episode_number']]['ratings']['TMDB'] = float(ep['vote_average'])
                        else: print('\033[93mEpisode missing from disk:', title, 'season', sn, 'episode', ep['episode_number'], '\033[0m')
            else: print('Error getting info on TMDB for', title, 'season', sn)
        
        if omdbApi != '' and imdbid:
            res = getJSON('http://www.omdbapi.com/?i=' + imdbid + '&Season=' + sn + '&apikey=' + omdbApi)
            if res and 'Episodes' in res:
                for ep in res['Episodes']:
                    if 'Episode' in ep and ep['Episode'].isdigit() and int(ep['Episode']) in season['episodes']:
                        episode = int(ep['Episode'])
                        if 'imdbRating' in ep and ep['imdbRating'] != 'N/A': 
                            season['episodes'][episode]['ratings']['IMDB'] = float(ep['imdbRating'])
                        if 'imdbID' in ep and ep['imdbID'] != 'N/A':
                            season['episodes'][episode]['imdbid'] = ep['imdbID']
            else: print('Error info on OMDB for', title, 'season', sn)
        
        avr = avg([season['episodes'][ep]['ratings']['IMDB'] for ep in season['episodes'] if 'IMDB' in season['episodes'][ep]['ratings']])
        if avr != 0: season['ratings']['IMDB'] = avr
        avr = avg([season['episodes'][ep]['ratings']['TMDB'] for ep in season['episodes'] if 'TMDB' in season['episodes'][ep]['ratings']])
        if avr != 0: season['ratings']['TMDB'] = avr
        if episodeMediainfo:
            mediaFiles = []
            res = []
            codec = []
            hdr = []
            for ex in extensions: mediaFiles += glob(join(path, '*.' + ex))
            for fl in mediaFiles:
                ep = findall('[Ss]\d{1,3}[Ee](\d{1,4})', fl)
                if len(ep) > 0 and int(ep[0]) in season['episodes']:
                    ep = int(ep[0])
                    minfo = getMediaInfo(fl)   
                    if minfo:
                        hdr.append(minfo[0])
                        res.append(minfo[1])
                        codec.append(minfo[2])
                        season['episodes'][ep]['mediainfo'] = minfo
            if len(hdr) > 0 and len(res) > 0 and len(codec) > 0:
                season['mediainfo'] = [frequent(hdr), frequent(codec), frequent(res)]
        if season != {'episodes': {}, 'ratings': {}, 'path': path}: metadata['seasons'][sn] = season

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
    return metadata

def getSeasons(folder):
    rs = glob(join(folder, '*'))
    seasons = []
    for fl in rs:
        res = findall('(.*\/[Ss]eason[ ._-](\d{1,3}))', fl)
        if len(res) == 1: seasons.append(res[0])
    return seasons
  
def generateImage(config, ratings, mediainfo, url, thread, coverHTML, path, mediaFile):
    st = time.time()
    img = downloadImage(url, 4, join(resource_path('threads/' + str(thread)), 'cover.png')) if not mediaFile else generateMediaImage(mediaFile, thread)
    #print('d', timedelta(seconds=round(time.time() - st)))
    st = time.time()
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
    
    HTML +='<link rel="stylesheet" href="' + resource_path('cover.css') + '">'
    HTML += '\n<style>\n' + generateCSS(config) + '.container {width:' + str(config['width']) + 'px}\n</style>'
    
    rts = ''
    minfo = ''

    if ratings:
        for rt in ratings: rts += "<div class = 'ratingContainer'><img src='" + resource_path('media/' + rt + '.png') + "' class='ratingIcon'><label class='ratingText'>" + str(ratings[rt]) + "</label></div>\n"
    if mediainfo:
        for mi in mediainfo: minfo += "<div class='mediainfoImgContainer'><img src='" + resource_path('media/' + mi + '.png') + "' class='mediainfoIcon'></div>\n"  
    
    HTML = HTML.replace('<!--RATINGS-->', rts)
    HTML = HTML.replace('<!--MEDIAINFO-->', minfo)
    with open(resource_path('threads/' + str(thread)) + '/tmp.html', 'w') as out:
        out.write(HTML)
    st = time.time()
    
    cm = call(['cutycapt --url="file://' + resource_path(join('threads', str(thread), 'tmp.html')) + '" --delay=1000 --min-width=100 --min-height=100 --out="' + resource_path(join('threads', str(thread))) + '/tmp.jpg"'], shell=True)            
    #print('p', timedelta(seconds=round(time.time() - st)))
    if cm == 0:
       return call(['mv', '-f', resource_path(join('threads', str(thread), 'tmp.jpg')), path]) == 0
    return False

def generateSeasonsImages(name, seasons, config, thread, coverHTML):
    for sn in seasons:
        st = time.time()
        season = seasons[sn]
        if exists(join(season['path'], 'poster.jpg')) and not access(join(season['path'], 'poster.jpg'), W_OK): 
            print('\033[91mCant write to:', join(season['path'], 'poster.jpg'), '\033[0m')
        elif 'cover' in season and generateImage(config, season['ratings'], season['mediainfo'], season['cover'], thread, coverHTML):
            call(['mv', '-f', resource_path(join('threads', str(thread), 'tmp.jpg')), join(season['path'], 'poster.jpg')])
            print('\033[92m[' + str(thread) + '] Succesfully generated cover for', name, 'season', sn, 'in', timedelta(seconds=round(time.time() - st)), '\033[0m')
        else: print('error generating image for season:', sn)

def generateMediaImage(path, thread):
    out = join(resource_path('threads/' + str(thread)), 'cover.png')
    return call(['ffmpeg', '-y', '-ss', '5:00', '-i', path, '-vframes', '1', '-q:v', '2', out], stdout = DEVNULL, stderr = DEVNULL) == 0