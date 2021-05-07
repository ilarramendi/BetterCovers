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
from scrapers.RottenTomatoes import getRTTvRatings, getRTSeasonRatings, getRTEpisodeRatings, getRTMovieRatings, searchRT
from scrapers.IMDB import getRating as getRatingIMDB
from scrapers.Moviemania import getTextlessPosters, getTextlessPostersByName
import xmltodict



workDirectory = "./"
extensions = ['mkv', 'mp4', 'avi']
minVotes = 5
logLevel = 2
coverHTML = ''

def readNFO(file):
    try:
        with open(file, 'r') as f:
            obj = xmltodict.parse(f.read())['movie']
    except:
        return {}
    
    res = {}
    if 'imdbid' in obj: res['IMDBID'] = obj['imdbid']
    if 'tmdbid' in obj: res['TMDBID'] = obj['imdbid']
    return res     
    
def getLanguage(conf, languages, englishUSA):
    for lg in conf.split(','):
        if lg in languages: return 'USA' if lg == 'ENG' and englishUSA else lg
    return False

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
    if len(list) == 0: return ''
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

def getMediaFiles(folder):
    mediaFiles = []
    for ex in extensions: 
        mediaFiles += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex))
    return[fl for fl in mediaFiles if 'trailer' not in fl]

def updateMetadata(metadata, interval, omdbApi, tmdbApi, scrapin):
    if metadata['type'] == 'movie':
        if (datetime.now() - datetime.strptime(metadata['mediainfoDate'], '%d/%m/%Y')) > timedelta(days=interval):
            mediaFiles = getMediaFiles(metadata['path'])
            if len(mediaFiles) == 1:
                metadata['mediainfo'] = getMediaInfo(mediaFiles[0])
                metadata['mediainfoDate'] = datetime.now().strftime("%d/%m/%Y")
        if (datetime.now() - datetime.strptime(metadata['metadataDate'], '%d/%m/%Y')) >= timedelta(days=interval):
            getMetadata(metadata, omdbApi, tmdbApi, scrapin)
    else: log('Episode metadata update TODO', 0, 3) # TODO metadata update
   
def getMetadata(mt, omdbApi, tmdbApi, scraping):
    mt['metadataDate'] = datetime.now().strftime("%d/%m/%Y")
    mt['ratings'] = {}
    mt['ageRating'] = 'NR'
    mt['certifications'] = []
    
    if tmdbApi != '': 
        result = False  
        if 'TMDBID' not in mt['ids']:
            if 'IMDBID' in mt['ids']:
                res = getJSON('https://api.themoviedb.org/3/find/' + mt['ids']['IMDBID'] + '?api_key=' + tmdbApi + '&language=en-US&external_source=imdb_id')
                if res and len(res[mt['type'] + '_results']) == 1:  
                    mt['ids']['TMDBID'] = str(res[mt['type'] + '_results'][0]['id'])
            else:  
                res = getJSON('https://api.themoviedb.org/3/search/' + mt['type'] + '?api_key=' + tmdbApi + '&language=en&page=1&include_adult=false&append_to_response=releases,external_ids&query=' + quote(mt['title']) + ('&year=' + mt['year'] if mt['year'] else ''))
                if res and 'results' in res and len(res['results']) > 0: 
                    mt['ids']['TMDBID'] = str(res['results'][0]['id'])
        if 'TMDBID' in mt['ids']: # this is ok
            res = getJSON('https://api.themoviedb.org/3/' + mt['type'] + '/' + mt['ids']['TMDBID'] + '?api_key=' + tmdbApi + '&language=en&append_to_response=releases,external_ids')
            if res: result = res

        if result:
            if 'poster_path' in result and result['poster_path']:
                mt['cover'] = 'https://image.tmdb.org/t/p/original' + result['poster_path']
            if 'backdrop_path' in result and result['backdrop_path']: 
                mt['backdrop'] = 'https://image.tmdb.org/t/p/original' + result['backdrop_path']
            if 'vote_average' in result and result['vote_average'] != 0:
                mt['ratings']['TMDB'] = {'icon': 'TMDB', 'value': str(result['vote_average'])}
            if 'imdb_id' in result['external_ids'] and 'IMDBID' not in mt['ids']:
                mt['ids']['IMDBID'] = result['external_ids']['imdb_id']
            
            if 'releases' in result and 'countries' in result['releases']:
                for rl in result['releases']['countries']:
                    if rl['iso_3166_1'] == 'US':
                        if rl['certification'] != '': mt['ageRating'] = rl['certification']
                        break
            
            if 'title' in res: mt['title'] = res['title']
            elif 'name' in res: mt['title'] = res['name'] 
        
        else: log('No results found on TMDB for: ', 3, 1)
          
    if len(omdbApi) > 0 and ('IMDBID' in mt['ids'] or 'title' in mt):
        url = 'http://www.omdbapi.com/?apikey=' + omdbApi + '&tomatoes=true'
        url += '&i=' + mt['ids']['IMDBID'] if 'IMDBID' in mt['ids'] else '&t=' + quote(mt['title'].replace(' ', '+')) + ('&y=' + mt['year'] if mt['year'] else '')
        res = getJSON(url)
        if res:
            if 'cover' not in mt and 'Poster' in res and res['Poster'] != 'N/A':
                mt['cover'] = res['Poster']
            if 'Metascore' in res and res['Metascore'] != 'N/A':
                mt['ratings']['MTC'] = {'icon': 'MTC', 'value': str(int(res['Metascore']) / 10).rstrip('0').rstrip('.')}
            if 'imdbRating' in res and res['imdbRating'] != 'N/A':
                mt['ratings']['IMDB'] = {'icon': 'IMDB', 'value': res['imdbRating'].rstrip('0').rstrip('.')}
            if 'Ratings' in res:
                for rt in res['Ratings']:
                    if rt['Source'] == 'Rotten Tomatoes' and rt['Value'] != 'N/A':
                        mt['ratings']['RT'] = {'icon': 'RT' if int(rt['Value'][:-1]) >= 60 else 'RT-LS', 'value': str(int(rt['Value'][:-1]) / 10).rstrip('0').rstrip('.')}
                        break
            if 'Title' in res and 'title' not in mt and not mt['title']: mt['title'] = res['Title']
        else: log('No results found on OMDB for: ' + name + ('(' + year + ')' if year else ''), 3, 1)
    
    if scraping['textlessPosters'] and 'TMDBID' in mt['ids']:
        posters = getTextlessPosters('https://www.moviemania.io/phone/movie/' + mt['ids']['TMDBID']) 
        if posters and len(posters) > 0: mt['cover'] = posters[0]
        else: log('No textless poster found for: ' + name, 3, 3)
    
    RTURL = scraping['RT'] and searchRT(mt['type'], mt['title'], mt['year'])
    if RTURL:
        RT = getRTMovieRatings(RTURL) if mt['type'] == 'movie' else getRTTvRatings(RTURL)
        if RT:
            for rt in RT['ratings']: mt['ratings'][rt] = RT['ratings'][rt]
            mt['certifications'] = RT['certifications']
            mt['RTURL'] = RTURL
            if mt['type'] == 'tv':
                for sn in RT['seasons']: 
                    if int(sn) in mt['seasons']: mt['seasons'][int(sn)]['RTURL'] = RT['seasons'][sn]
    
    IMDB = scraping['IMDB'] and 'imdbid' in mt and getRatingIMDB(mt['imdbid'])
    if IMDB:
        if 'IMDB' in IMDB:
            mt['ratings']['IMDB'] = {'icon': 'IMDB', 'value': IMDB['IMDB']}
        if 'MTC' in IMDB: 
            mt['ratings']['IMDB'] = {'icon': 'MTC-MS' if IMDB['MTC-MS'] else 'MTC', 'value': IMDB['MTC']}        
        if IMDB['MTC-MS']: certifications.append('MTC-MS')

def getMediaInfo(file, defaultLanguage):
    out = getstatusoutput('ffprobe "' + file + '" -of json -show_entries stream=index,codec_type,codec_name,height,width:stream_tags=language -v quiet')
    out2 = getstatusoutput('ffprobe "' + file + '" -show_streams -v quiet')
    info = {'color': '', 'resolution': '', 'codec': '', 'source': '', 'languages': [] if defaultLanguage == '' else [defaultLanguage]}
    nm = file.lower()
    info['source'] = 'BR' if 'blueray' in nm else 'DVD' if 'dvd' in nm else 'WEBRIP' if 'webrip' in nm else 'WEBDL' if 'web-dl' in nm else ''
    video = False

    if out[0] != 0: 
        log('Error getting media info, exit code: ' + str(out[0]) + '\n' + str(out[1]), 1, 1)
        return info
    
    out = json.loads(out[1])['streams']
    for s in out:
        if s['codec_type'] == 'video':
            video = s
            break
    
    if not video:
        log('No video tracks found for: ' + file, 1, 1)
        return info
    
    info['color'] = 'HDR' if out2[0] == 0 and 'bt2020' in out2[1] else 'SDR'
    info['resolution'] = 'UHD' if video['width'] >= 3840 else 'HD' if video['width'] >= 1920 else 'SD'

    if 'codec_name' in video:
        if video['codec_name'] in ['h264', 'avc']: info['codec'] = 'AVC'
        elif video['codec_name'] in ['h265', 'hevc']: info['codec'] = 'HEVC'
        else: log('Unsupported video codec: ' + video['codec_name'].upper(), 3, 3)
    else: log('Video codec not found for: ' + file, 3, 3)
    
    lng = []
    for s in out:
        if s['codec_type'] == 'audio' and 'tags' in s and 'language' in s['tags']:
            lng.append(s['tags']['language'].upper())
    if lng != []: info['languages'] = lng

    return info

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
    return float("{:.1f}".format(sum(lst) / len(lst)) if len(lst) > 0 else 0)

def getEpisodes(folder, season, getAll): # {int: str,...} => {enumber: epath,...}
    fls = []
    episodes = {}
    for ex in extensions: fls += glob(join(folder, '*.' + ex))
    for fl in fls:
        nm = findall('S0*' + season + 'E0*(\d+)', fl)
        if len(nm) > 0 and (getAll or not exists(fl.rpartition('.')[0] + '.jpg')):
            episodes[int(nm[0])] = fl
    return episodes

def getParentMediainfo(childrens):
    res = {}
    for ch in childrens:
        chi = childrens[ch]
        for pr in chi['mediainfo']:
            if pr not in res: res[pr] = []
            res[pr].append(chi['mediainfo'][pr])
            
    for pr in res:
        if type(res[pr][0]) is str:
            res[pr] = frequent(res[pr])
        else:
            for vl in res[pr][0]:
                for pr2 in res[pr]:
                    if vl not in pr2: 
                        res[pr][0].remove(vl)
                        break
            res[pr] = res[pr][0]
    return res

def getSeasonsMetadata(metadata, omdbApi, tmdbApi, force, overWrite, defaultLanguage):
    mt = metadata
    for sn in mt['seasons']:
        mt['seasons'][sn]['ratings'] = {}
        mt['seasons'][sn]['certifications'] = []
        for ep in mt['seasons'][sn]['episodes']: 
            mt['seasons'][sn]['episodes'][ep]['ratings'] = {}
            mt['seasons'][sn]['episodes'][ep]['ids'] = {}
        
        if len(tmdbApi) > 0 and 'TMDBID' in mt['ids']:
            res = getJSON('https://api.themoviedb.org/3/tv/' + mt['ids']['TMDBID'] + '/season/' + str(sn) + '?api_key=' + tmdbApi + '&language=en')
            if res:
                if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']: mt['seasons'][sn]['cover'] = 'https://image.tmdb.org/t/p/original' + res['poster_path']
                if 'episodes' in res:
                    for ep in res['episodes']:
                        if 'episode_number' not in ep or ep['episode_number'] == 'N/A': continue
                        if ep['episode_number'] not in mt['seasons'][sn]['episodes']: continue
                        if 'still_path' in ep and ep['still_path'] != 'N/A' and ep['still_path']:
                            mt['seasons'][sn]['episodes'][ep['episode_number']]['cover'] = 'https://image.tmdb.org/t/p/original' + ep['still_path']
                        if 'vote_average' in ep and ep['vote_average'] != 'N/A' and 'vote_count' in ep and ep['vote_count'] > minVotes:
                            mt['seasons'][sn]['episodes'][ep['episode_number']]['ratings']['TMDB'] = {'icon': 'TMDB', 'value': float(ep['vote_average'])}
                        if 'id' in ep: 
                            mt['seasons'][sn]['episodes'][ep['episode_number']]['ids']['TMDBID'] = ep['id']
                if 'vote_average' in res: mt['seasons'][sn]['ratings']['TMDB'] = {'icon': 'TMDB', 'value': float(res['vote_average'])} # TODO not working
            else: log('Error getting info on TMDB for: ' + title + ' S' + sn, 3, 1)
        
        if len(omdbApi) > 0 and 'IMDBID' in mt['ids']:
            res = getJSON('http://www.omdbapi.com/?i=' + mt['ids']['IMDBID'] + '&Season=' + str(sn) + '&apikey=' + omdbApi)
            if res and 'Episodes' in res and len(res['Episodes']) > 0:
                rts = []
                for ep in res['Episodes']:
                    if int(ep['Episode']) not in mt['seasons'][sn]['episodes']: continue
                    if 'imdbRating' in ep and ep['imdbRating'] != 'N/A': 
                        mt['seasons'][sn]['episodes'][int(ep['Episode'])]['ratings']['IMDB'] = {'icon': 'IMDB', 'value': float(ep['imdbRating'])}
                        rts.append(float(ep['imdbRating']))
                    if 'imdbID' in ep and ep['imdbID'] != 'N/A':
                        mt['seasons'][sn]['episodes'][int(ep['Episode'])]['ids']['IMDBID'] = ep['imdbID']
                mt['seasons'][sn]['ratings']['IMDB'] = {'icon': 'IMDB', 'value': avg(rts)}
            else: log('Error getting info on OMDB for: ' + title + ' S' + sn, 3, 1)

        if 'RTURL' in mt['seasons'][sn]:
            RT = getRTSeasonRatings(mt['seasons'][sn]['RTURL'])
            if RT:
                for rt in RT['ratings']:
                    mt['seasons'][sn]['ratings'][rt] = RT['ratings'][rt]
                mt['seasons'][sn]['certifications'] = RT['certifications']
                for ep in RT['episodes']:
                    if int(ep) in mt['seasons'][sn]['episodes']:
                        mt['seasons'][sn]['episodes'][int(ep)]['RTURL'] = RT['episodes'][ep]
                        if not mt['seasons'][sn]['episodes'][int(ep)] or overWrite:
                            RTE = getRTEpisodeRatings(RT['episodes'][ep])
                            if RTE:
                                for rte in RTE['ratings']: mt['seasons'][sn]['episodes'][int(ep)]['ratings'][rte] = RTE['ratings'][rte]

        for ep in mt['seasons'][sn]['episodes']:
            if not mt['seasons'][sn]['episodes'][ep]['hasCover'] or force or overWrite or not mt['seasons'][sn]['hasCover'] or not mt['seasons'][sn]['hasBackdrop']:
                mt['seasons'][sn]['episodes'][ep]['mediainfo'] = getMediaInfo(mt['seasons'][sn]['episodes'][ep]['path'], defaultLanguage)
        
        mt['seasons'][sn]['mediainfo'] = getParentMediainfo(mt['seasons'][sn]['episodes'])

    mt['mediainfo'] = getParentMediainfo(mt['seasons'])
    return mt

def getSeasons(folder, coverName, backdropName, title):
    seasons = {}
    for fl in glob(join(folder, '*')):
        res = findall('.*\/[Ss]eason[ ._-](\d{1,3})', fl)
        if len(res) == 1: 
            eps = []
            episodes = {}
            for ex in extensions: eps += glob(join(fl, '*.' + ex))
            for ep in eps: 
                mc = findall('S0*' + res[0] + 'E0*(\d+)', ep)
                if len(mc) == 1: episodes[int(mc[0])] = {'path': ep, 'hasCover': exists(ep.rpartition('.')[0] + '.jpg'), 'type': 'episode', 'title': title + ' Season: ' + res[0] + ' Episode: ' + mc[0]}
            seasons[int(res[0])] = {'path': fl, 'episodes': episodes, 'hasCover': exists(join(fl, coverName)), 'hasBackdrop': exists(join(fl, backdropName)), 'type': 'season', 'title': title + ' Season: ' + res[0]}

    return seasons
  
def tagImage(path):
    with open(path, 'rb') as image:
        img = imgTag(image)
    img["software"] = "BetterCovers"
    img['datetime_original'] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    with open(path, 'wb') as image:
        image.write(img.get_file())

def generateIMage2(task, config, thread):
    st = time.time()
    imageGenerated = task['generateImage'] and generateMediaImage(task['generateImage'], thread)
    if task['generateImage'] and not imageGenerated:
        if task['image']:
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
    HTML = HTML.replace('$IMGSRC', thread + '-sc.png' if imageGenerated else task['image'])

    HTML += '\n<style>\n' + generateCSS(config) + '\n.container {width:' + str(config['width']) + 'px; height:' + str(config['height']) + 'px}\n</style>\n'
    
    rts = ''
    minfo = ''

    for rt in task['ratings']: rts += "<div class = 'ratingContainer'><img src='" + join('..', 'media', 'ratings', task['ratings'][rt]['icon'] + '.png') + "' class='ratingIcon'><label class='ratingText'>" + str(task['ratings'][rt]['value']) + "</label></div>\n"
    for mi in task['mediainfo']:
        if task['mediainfo'][mi] != '':
            pt = join('..', 'media', 'mediainfo' if mi != 'languages' else 'languages', task['mediainfo'][mi] + '.png')
            minfo += "<div class='mediainfoImgContainer'><img src='" + pt + "' class='mediainfoIcon'></div>\n"  

    if task['ageRating'] != '':
        with open(join('..', 'media', 'certifications', task['ageRating'] + '.svg'), 'r') as svg:
            HTML = HTML.replace('<!--CERTIFICATION-->', svg.read())
    
    if task['overlay'] != '':
        with open(join(workDirectory, 'media', 'overlays', task['overlay'] + '.html')) as overlay:
            HTML = overlay.read().replace('<!--CONTAINER-->', HTML)
    
    HTML = HTML.replace('<!--RATINGS-->', rts)
    HTML = HTML.replace('<!--MEDIAINFO-->', minfo)

    with open(join(workDirectory, 'threads', thread + '.html'), 'w') as out:
        out.write(HTML)

    i = 0
    # --no-background
    #command = 'cutycapt --url="file://' + join(workDirectory, 'threads', thread + '.html') + '" --delay=2000 --min-width=500 --min-height=500 --out="' + join(workDirectory, 'threads', thread + '.jpg') + '"'
    command = ['wkhtmltoimage', '--javascript-delay', '2000', '--transparent', 'file://' + join(workDirectory, 'threads', thread + '.html'), join(workDirectory, 'threads', thread + '.jpg')]
    while i < 3 and not call(command, stdout=DEVNULL, stderr=DEVNULL) == 0: i += 1
    if i < 3:
        tagImage(join(workDirectory, 'threads', thread + '.jpg'))
        if call(['mv', '-f', join(workDirectory, 'threads', thread + '.jpg'), task['out']]) == 0:
            log('Succesfully generated ' + ('cover' if task['type'] != 'backdrop' else 'backdrop') + ' image for: ' + task['title'] + ' in ' + str(round(time.time() - st)) + 's', 2, 2)
            return True
        log('Error moving to: ' + task['out'], 3, 3)
    else: log('Error generating image with wkhtmltoimage', 3, 3)
    log('Error generating image for: ' + task['title'], 1, 1)
    return False

def generateMediaImage(path, thread):
    cm = call(['ffmpeg', '-y', '-ss', '5:00', '-i', path, '-vframes', '1', '-q:v', '2', join(workDirectory, 'threads', thread + '-sc.png')], stdout = DEVNULL, stderr = DEVNULL)
    if cm == 0:
        log('Successfully generated screenshot from minute 5:00 with ffmpeg', 3, 3)
        return True
    else:
        log('Error generating screenshot with ffmpeg for: ' + path, 3, 3)
        return False