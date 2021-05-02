from glob import glob
from re import findall, match
from subprocess import call, getstatusoutput, DEVNULL
from requests import get
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from os import access, W_OK
from os.path import exists, realpath, join
import sys
from datetime import timedelta, datetime
import time
from urllib.parse import quote
import json
from exif import Image as imgTag
from scrapers.RottenTomatoes import searchMovie as searchMovieRT
from scrapers.IMDB import getRating as getRatingIMDB
from scrapers.Moviemania import getTextlessPosters, getTextlessPostersByName

workDirectory = "./"
extensions = ['mkv', 'mp4', 'avi']
minVotes = 5
logLevel = 2

def getLanguage(conf, languages, englishUSA):
    for lg in conf.split(','):
        if lg in languages: return 'USA' if lg == 'ENG' and englishUSA else lg
    return False

def setLogLevel(level):
    global logLevel
    logLevel = level

def log(text, type = 0, level = 2): # 0 = Normal, 1 = Error, 2 = Success, 3 = Warning
    if level <= logLevel:
        msg = '\033[9' + str(type) + 'm' if type != 0 else ''
        msg += text
        msg += '\033[0m' if type != 0 else ''
        print((datetime.now().strftime("[%m/%d/%Y %H:%M:%S] --> ") if logLevel >= 3 else '') + msg)
        with open(join(workDirectory, 'BetterCovers.log'), 'a') as log:
            log.write(datetime.now().strftime("[%m/%d/%Y %H:%M:%S] --> ") + msg + '\n')

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
        log('Problem with api key!\n' +
            'Server Response:\n' +
            response.text,
            1, 0)
        exit()
    if response.status_code != 200 or 'application/json' not in response.headers.get('content-type'): # Wrong response from server
        log('Error connecting to: ' + url + '\nResponse Code: ' + response.status_code, 1, 1)
        log(response.text, 1, 3)
        return False
    try:
        return response.json()
    except Exception as ex:
        log('Error parsing JSON from response:\n' + response.text, 1, 1)
        return False
    
    res = response.json()

def getMetadata(name, type, year, omdbApi, tmdbApi, scraping): # {'ratings': {}, 'type': str, 'cover'?: str, 'backdrop'?: str, 'tmdbid'?: str}
    metadata = {'ratings': {}, "type": type, "certification": "NR"}
    
    if tmdbApi != '': 
        res = getJSON('https://api.themoviedb.org/3/search/' + type + '?api_key=' + tmdbApi + '&language=en&page=1&include_adult=false&append_to_response=releases&query=' + quote(name) + ('&year=' + year if year else ''))
        if res and 'results' in res and len(res['results']) > 0:
            res = res['results'][0]
            if 'poster_path' in res and res['poster_path']:
                metadata['cover'] = 'https://image.tmdb.org/t/p/original' + res['poster_path']
            if 'backdrop_path' in res and res['backdrop_path']: 
                metadata['backdrop'] = 'https://image.tmdb.org/t/p/original' + res['backdrop_path']
            if 'vote_average' in res and res['vote_average'] != 0: metadata['ratings']['TMDB'] = str(res['vote_average'])
            if 'id' in res:
                metadata['tmdbid'] = str(res['id'])
                info = getJSON('https://api.themoviedb.org/3/' + type + '/' + metadata['tmdbid'] + '?append_to_response=releases,external_ids&api_key=' + tmdbApi)
                if info:
                    if 'imdb_id' in info['external_ids'] and info['external_ids']['imdb_id']:
                        metadata['imdbid'] = info['external_ids']['imdb_id']
                    
                    if 'releases' in info and 'countries' in info['releases']:
                        for rl in info['releases']['countries']:
                            if rl['iso_3166_1'] == 'US':
                                if rl['certification'] != '': metadata['certification'] = rl['certification']
                                break
            if 'title' in res: metadata['title'] = res['title']
            elif 'name' in res: metadata['title'] = res['name'] 
        else: log('No results found on TMDB for: ' + name + ('(' + year + ')' if year else ''), 3, 1)
          
    if omdbApi != '':
        url = 'http://www.omdbapi.com/?apikey=' + omdbApi + '&tomatoes=true'
        url += '&i=' + metadata['imdbid'] if 'imdbid' in metadata else '&t=' + quote((metadata['title'] if 'title' in metadata else name).replace(' ', '+')) + ('&y=' + year if year else '')
        res = getJSON(url)
        if res:
            if 'cover' not in metadata and 'Poster' in res and res['Poster'] != 'N/A':
                metadata['cover'] = res['Poster']
            if 'Metascore' in res and res['Metascore'] != 'N/A': 
                metadata['ratings']['MTC'] = str(int(res['Metascore']) / 10).rstrip('0').rstrip('.')
            if 'imdbRating' in res and res['imdbRating'] != 'N/A': metadata['ratings']['IMDB'] = res['imdbRating'].rstrip('0').rstrip('.')
            if 'Ratings' in res:
                for rt in res['Ratings']:
                    if rt['Source'] == 'Rotten Tomatoes' and rt['Value'] != 'N/A':
                        metadata['ratings']['RT'] = str(int(rt['Value'][:-1]) / 10).rstrip('0').rstrip('.')
                        break
            if 'Title' in res: metadata['title'] = res['Title']
        else: log('No results found on OMDB for: ' + name + ('(' + year + ')' if year else ''), 3, 1)
    
    if scraping['textlessPosters']:
        posters = getTextlessPosters('https://www.moviemania.io/phone/movie/' + metadata['tmdbid']) if 'tmdbid' in metadata else getTextlessPosters('Movies', name, year) 
        if posters and len(posters) > 0: metadata['cover'] = posters[0]
        else: log('No textless poster found for: ' + name, 3, 3)
    
    rt = scraping['RT'] and searchMovieRT(name, year)
    if rt:
        for sc in ['RT', 'RTA']:
            if sc in rt:
                metadata['ratings'][sc] = str(int(rt[sc]) / 10).replace('.0', '')
        if rt['CF'] and 'RT' in metadata['ratings']:
            metadata['ratings']['RTCF'] = metadata['ratings']['RT']
            del metadata['ratings']['RT']

    IMDB = scraping['IMDB'] and 'imdbid' in metadata and getRatingIMDB(metadata['imdbid'])
    if IMDB:
        if 'IMDB' in IMDB: metadata['ratings']['IMDB'] = IMDB['IMDB']
        if 'MTC' in IMDB: metadata['ratings']['MTC'] = IMDB['MTC']
        if IMDB['MTC-MS'] and 'MTC' in metadata['ratings']:
            metadata['ratings']['MTC-MS'] = metadata['ratings']['MTC']
            del metadata['ratings']['MTC']
        
    return metadata

def getMediaInfo(file): # {"metadata": [str], "language": [str]}?
    out = getstatusoutput('ffprobe "' + file + '" -of json -show_entries stream=index,codec_type,codec_name,height,width:stream_tags=language -v quiet')
    out2 = getstatusoutput('ffprobe "' + file + '" -show_streams -v quiet')
    if out[0] == 0 and out2[0] == 0:
        out = json.loads(out[1])['streams']
        video = False
        for s in out:
            if s['codec_type'] == 'video':
                video = s
                break
        if video:
            info = []
            info.append('HDR' if 'bt2020' in out2[1] else 'SDR')
            info.append('UHD' if video['width'] >= 3840 else 'HD' if video['width'] >= 1920 else 'SD')

            if 'codec_name' in video:
                if video['codec_name'] == 'h264': 
                    info.append('AVC')
                elif video['codec_name'] in ['hevc', 'avc']:
                    info.append(video['codec_name'].upper())
                else:
                    log('Unsupported video codec: ' + video['codec_name'].upper(), 3, 3)
                    info.append('UNKNOWN')
            else:
                log('Video codec not found for: ' + file, 3, 3)
                info.append('UNKNOWN')
            
            lang = []
            for s in out:
                if s['codec_type'] == 'audio' and 'tags' in s and 'language' in s['tags']:
                    lang.append(s['tags']['language'].upper())

            return {"metadata": info, "language": lang}
        else:
            log('No video tracks found for: ' + file, 1, 1)
            return False
    else: 
        log('Error getting media info, exit code: ' + str(out[0]) + ' ' + str(out2[0]), 1, 1)
        log('Mediainfo output:\n' + out[1] +
            '\nOutput 2:\n' + out2[1], 3, 3)
        return False

def downloadImage(url, retry, src): # Boolean
    i = 0
    while i < retry:
        try:
            Image.open(get(url, stream=True).raw).save(src)
            return True
        except Exception as e:
            log('Failed to download image from: ' + url + ' trying again', 3, 3)
            sleep(0.5)
        i += 1
    log('Failed to download image from: ' + url, 1, 1)
    return False

def avg(lst):
    return "{:.1f}".format(sum(lst) / len(lst)) if len(lst) > 0 else 0

def getEpisodes(folder, season, getAll): # {int: str,...} => {enumber: epath,...}
    fls = []
    episodes = {}
    for ex in extensions: fls += glob(join(folder, '*.' + ex))
    for fl in fls:
        nm = findall('S0*' + season + 'E0*(\d+)', fl)
        if len(nm) > 0 and (getAll or not exists(fl.rpartition('.')[0] + '.jpg')):
            episodes[int(nm[0])] = fl
    return episodes

def getSeasonsMetadata(imdbid, tmdbid, seasons, omdbApi, tmdbApi, episodeMediainfo, title, missingCover, overWrite): # {'seasons': {int: {'episodes': {}, 'ratings': {}, 'path': str, 'mediainfo'?: [str]}}, 'mediainfo'?: [str]}
    metadata = {}
    for path, sn in seasons:
        season = {'episodes': {}, 'ratings': {}, 'path': path}
        eps = getEpisodes(path, sn, missingCover or overWrite or not exists(path + '/folder.jpg'))
        if len(eps) == 0 and exists(path + '/folder.jpg') and exists(path + '/backdrop.jpg') and not overWrite:
            log('All image exist for: ' + title + ' S' + sn, 3, 3)
            continue
        for ep in eps:
            season['episodes'][ep] = {'path': eps[ep], 'ratings': {}}
        
        if tmdbApi != '' and tmdbid:
            res = getJSON('https://api.themoviedb.org/3/tv/' + tmdbid + '/season/' + str(sn) + '?api_key=' + tmdbApi + '&language=en')
            if res:
                if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']: season['cover'] = 'https://image.tmdb.org/t/p/original' + res['poster_path']
                if 'episodes' in res and len(res['episodes']) > 0:
                    for ep in res['episodes']:
                        if 'episode_number' not in ep or ep['episode_number'] == 'N/A': continue
                        if ep['episode_number'] in season['episodes']:
                            if 'still_path' in ep and ep['still_path'] != 'N/A' and ep['still_path']:
                                season['episodes'][ep['episode_number']]['cover'] = 'https://image.tmdb.org/t/p/original' + ep['still_path']
                            if 'vote_average' in ep and ep['vote_average'] != 'N/A' and 'vote_count' in ep and ep['vote_count'] > minVotes:
                                season['episodes'][ep['episode_number']]['ratings']['TMDB'] = float(ep['vote_average'])
            else: log('Error getting info on TMDB for: ' + title + ' S' + sn, 3, 1)
        
        if omdbApi != '' and imdbid:
            res = getJSON('http://www.omdbapi.com/?i=' + imdbid + '&Season=' + sn + '&apikey=' + omdbApi)
            if res and 'Episodes' in res and len(res['Episodes']) > 0:
                for ep in res['Episodes']:
                    if 'Episode' in ep and ep['Episode'].isdigit() and int(ep['Episode']) in season['episodes']:
                        episode = int(ep['Episode'])
                        if 'imdbRating' in ep and ep['imdbRating'] != 'N/A': 
                            season['episodes'][episode]['ratings']['IMDB'] = float(ep['imdbRating'])
                        if 'imdbID' in ep and ep['imdbID'] != 'N/A':
                            season['episodes'][episode]['imdbid'] = ep['imdbID']
            else: log('Error getting info on OMDB for: ' + title + ' S' + sn, 3, 1)
        
        avr = avg([season['episodes'][ep]['ratings']['IMDB'] for ep in season['episodes'] if 'IMDB' in season['episodes'][ep]['ratings']])
        if avr != 0: season['ratings']['IMDB'] = avr
        avr = avg([season['episodes'][ep]['ratings']['TMDB'] for ep in season['episodes'] if 'TMDB' in season['episodes'][ep]['ratings']])
        if avr != 0: season['ratings']['TMDB'] = avr
        if episodeMediainfo: # TODO move this to a function
            mediaFiles = []
            for ex in extensions: mediaFiles += glob(join(path, '*.' + ex)) # TODO call getEpisodes instead of this
            for fl in mediaFiles:
                ep = findall('[Ss]\d{1,3}[Ee](\d{1,4})', fl) 
                if len(ep) > 0 and int(ep[0]) in season['episodes']:
                    ep = int(ep[0])
                    minfo = getMediaInfo(fl)   
                    if minfo:
                        season['episodes'][ep]['mediainfo'] = minfo['metadata']
                        season['episodes'][ep]['language'] = minfo['language']
        if season != {'episodes': {}, 'ratings': {}, 'path': path}: metadata[sn] = season

    return metadata

def getSeasons(folder):
    rs = glob(join(folder, '*'))
    seasons = []
    for fl in rs:
        res = findall('(.*\/[Ss]eason[ ._-](\d{1,3}))', fl)
        if len(res) == 1: seasons.append(res[0])
    return seasons
  
def tagImage(path):
    with open(path, 'rb') as image:
        img = imgTag(image)
    img["software"] = "BetterCovers"
    img['datetime_original'] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    with open(path, 'wb') as image:
        image.write(img.get_file())

def generateImage(config, ratings, certification, language, mediainfo, url, thread, coverHTML, path, mediaFile):
    st = time.time()
    imageGenerated = mediaFile and generateMediaImage(mediaFile, join(workDirectory, 'threads', thread + '-sc.png'))
    if mediaFile and not imageGenerated:
        if url:
            log('Error generating screenshot with ffmpeg, using downloaded image instead', 3, 3)
        else:
            log('Error generating screenshot with ffmpeg', 1, 1)
            return False
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
    HTML = HTML.replace('$IMGSRC', thread + '-sc.png' if imageGenerated else url)

    HTML += '\n<style>\n' + generateCSS(config) + '.container {width:' + str(config['width']) + 'px; height:' + str(config['height']) + 'px}\n</style>'
    
    rts = ''
    minfo = ''

    if ratings:
        for rt in ratings: rts += "<div class = 'ratingContainer'><img src='" + join('..', 'media', 'ratings', rt + '.png') + "' class='ratingIcon'><label class='ratingText'>" + str(ratings[rt]) + "</label></div>\n"
    if mediainfo:
        for mi in mediainfo: minfo += "<div class='mediainfoImgContainer'><img src='" + join('..', 'media', 'mediainfo', mi + '.png') + "' class='mediainfoIcon'></div>\n"  
    if language:
        minfo += "<div class='mediainfoImgContainer'><img src='" + join('..', 'media', 'languages', language + '.png') + "' class='mediainfoIcon'></div>\n"
    if certification:
        with open(join('..', 'media', 'certifications', certification + '.svg'), 'r') as svg:
            HTML = HTML.replace('<!--CERTIFICATION-->', svg.read())
    HTML = HTML.replace('<!--RATINGS-->', rts)
    HTML = HTML.replace('<!--MEDIAINFO-->', minfo)
    with open(join(workDirectory, 'threads', thread + '.html'), 'w') as out:
        out.write(HTML)

    i = 0
    command = 'cutycapt --url="file://' + join(workDirectory, 'threads', thread + '.html') + '" --delay=1000 --min-width=' + str(config['width']) + ' --min-height=' + str(config['height']) + ' --out="' + join(workDirectory, 'threads', thread + '.jpg') + '"'
    while i < 3 and not call(command, shell=True, stdout=DEVNULL, stderr=DEVNULL) == 0: i += 1
    if i < 3:
        tagImage(join(workDirectory, 'threads', thread + '.jpg'))
        if not call(['mv', '-f', join(workDirectory, 'threads', thread + '.jpg'), path]) == 0:
            log('Error moving to: ' + path, 3, 3)
            return False
        return True
    else: 
        log('Error generating image with cutycapt', 3, 3)
        return False

def generateMediaImage(path, out):
    cm = call(['ffmpeg', '-y', '-ss', '5:00', '-i', path, '-vframes', '1', '-q:v', '2', out], stdout = DEVNULL, stderr = DEVNULL)
    if cm == 0:
        log('Successfully generated screenshot from minute 5:00 with ffmpeg', 3, 3)
        return True
    else:
        log('Error generating screenshot with ffmpeg for: ' + path, 3, 3)
        return False