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
from scrapers.RottenTomatoes import getRTRatings, getRTSeasonRatings, getRTEpisodeRatings, searchRT
from scrapers.IMDB import getIMDBRating
from scrapers.Moviemania import getTextlessPosters, getTextlessPostersByName
from scrapers.letterboxd import searchLB, getLBRatings
import xmltodict
from math import sqrt


workDirectory = "./"
extensions = ['mkv', 'mp4', 'avi']
minVotes = 5
logLevel = 2
coverHTML = ''
mediainfoUpdateInterval = 30 # TODO use config file

def getName(folder):
    inf = findall("\/([^\/]+)[ \.]\(?(\d{4})\)?", folder)
    if len(inf) == 0: 
        inf = findall("\/([^\/]+)$", folder)
        if len(inf) == 0:
            log('Cant parse name from: ' + folder, 3, 1)
            return [False, False]
        else: return [inf[0], False]
    else: return [inf[0][0].translate({'.': ' ', '_': ' '}), inf[0][1]]

def getUpdateInterval(releaseDate):
    return min(120, sqrt(max((datetime.now() - datetime.strptime(releaseDate, '%d/%m/%Y')).days, 0) * 4 + 1))

def readNFO(file):
    try:
        with open(file, 'r') as f:
            obj = xmltodict.parse(f.read())['movie']
    except:
        return {}
    
    res = {}
    if 'imdbid' in obj: res['IMDBID'] = obj['imdbid']
    if 'tmdbid' in obj: res['TMDBID'] = obj['tmdbid']
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
            log.write('[' + ['Info', 'Error', 'Success', 'Warning'][level] + datetime.now().strftime("][%m/%d/%Y %H:%M:%S] --> ") + text + '\n')

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

def getMetadata(mt, omdbApi, tmdbApi, scraping, defaultLanguage, forceSeasons):
    print('0', time.time())
    sc = False
    if 'metadataDate' not in mt: mt['metadataDate'] = '1/1/1999'
    if 'mediainfoDate' not in mt: mt['mediainfoDate'] = '1/1/1999'
    if 'releaseDate' not in mt: mt['releaseDate'] = datetime.now().strftime("%d/%m/%Y")
    if 'productionCompanies' not in mt: mt['productionCompanies'] = []
    if 'certifications' not in mt: mt['certifications'] = []
    if 'ageRating' not in mt: mt['ageRating'] = 'NR'
    if 'ratings' not in mt: mt['ratings'] = {}

    # Get general show metadata
    if (datetime.now() - datetime.strptime(mt['metadataDate'], '%d/%m/%Y')) >= timedelta(days=getUpdateInterval(mt['releaseDate'])):
        tsks = []
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
                sc = True
                if 'poster_path' in result and result['poster_path']:
                    mt['cover'] = 'https://image.tmdb.org/t/p/original' + result['poster_path']
                if 'backdrop_path' in result and result['backdrop_path']: 
                    mt['backdrop'] = 'https://image.tmdb.org/t/p/original' + result['backdrop_path']
                if 'vote_average' in result and result['vote_average'] != 0:
                    mt['ratings']['TMDB'] = {'icon': 'TMDB', 'value': str(result['vote_average'])}
                if 'imdb_id' in result['external_ids'] and 'IMDBID' not in mt['ids']:
                    mt['ids']['IMDBID'] = result['external_ids']['imdb_id']
                if 'last_air_date' in result and result['last_air_date']:
                    mt['releaseDate'] = datetime.strptime(result['last_air_date'], '%Y-%m-%d').strftime("%d/%m/%Y") # TODO change this on new episodes
                elif 'release_date' in result and result['release_date']:
                    mt['releaseDate'] = datetime.strptime(result['release_date'], '%Y-%m-%d').strftime("%d/%m/%Y")
                if 'releases' in result and 'countries' in result['releases']:
                    for rl in result['releases']['countries']:
                        if rl['iso_3166_1'] == 'US':
                            if rl['certification'] != '': mt['ageRating'] = rl['certification']
                            break
                
                if 'title' in res: mt['title'] = res['title']
                elif 'name' in res: mt['title'] = res['name'] 
                
                if 'production_companies' in res:
                    for pc in res['production_companies']:
                        if pc['logo_path']: mt['productionCompanies'].append({'id': pc['id'], 'name': pc['name'], 'logo': 'https://image.tmdb.org/t/p/original' + pc['logo_path']})
            else: log('No results found on TMDB for: ', 3, 1)
            
        if len(omdbApi) > 0 and ('IMDBID' in mt['ids'] or 'title' in mt): # TODO add release date from omdb
            url = 'http://www.omdbapi.com/?apikey=' + omdbApi + '&tomatoes=true'
            url += '&i=' + mt['ids']['IMDBID'] if 'IMDBID' in mt['ids'] else '&t=' + quote(mt['title'].replace(' ', '+')) + ('&y=' + mt['year'] if mt['year'] else '')
            res = getJSON(url)
            if res:
                sc = True
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
        print('2', time.time())
        
        if scraping['textlessPosters'] and 'TMDBID' in mt['ids']:
            posters = getTextlessPosters('https://www.moviemania.io/phone/movie/' + mt['ids']['TMDBID'])
            if posters and len(posters) > 0: mt['cover'] = posters[0]
            else: log('No textless poster found for: ' + name, 3, 3)
        
        if scraping['RT'] and searchRT(mt): getRTRatings(mt)
        print('3', time.time())
        
        if scraping['IMDB'] and 'IMDBID' in mt['ids']: getIMDBRating(mt)
        print('4', time.time())

        LB = mt['type'] == 'movie' and scraping['LB'] and searchLB(mt)
        if LB: getLBRatings(mt)
        print('5', time.time())

        if sc: mt['metadataDate'] = datetime.now().strftime("%d/%m/%Y")
    else: log('No need to update metadata for: ' + mt['title'], 3, 3)

    # Get meediainfo if movie
    if mt['type'] == 'movie':
        if (datetime.now() - datetime.strptime(mt['mediainfoDate'], '%d/%m/%Y')) >= timedelta(days=mediainfoUpdateInterval): 
            mediaFiles = getMediaFiles(mt['path'])
            if len(mediaFiles) >= 1:
                success, mt['mediainfo'] = getMediaInfo(mediaFiles[0], defaultLanguage)
                mt['mediaFile'] = mediaFiles[0]
                if success: mt['mediainfoDate'] = datetime.now().strftime("%d/%m/%Y")   
            else: log('No media file found on: ' + metadata['path'], 3, 3)
        else: log('No need to update mediainfo for: ' + mt['title'], 3, 3)
    else: # Get metadata and mediainfo for seasons if tv
        for sn in mt['seasons']:
            getSeasonMetadata(sn, mt['seasons'][sn], mt['ids'], mt['productionCompanies'], omdbApi, tmdbApi, sn in forceSeasons)
            getSeasonMediainfo(mt['seasons'][sn], defaultLanguage)
        mt['mediainfo'] = getParentMediainfo(mt['seasons'])

def getMediaInfo(file, defaultLanguage):
    out = getstatusoutput('ffprobe "' + file + '" -of json -show_entries stream=index,codec_type,codec_name,height,width:stream_tags=language -v quiet')
    out2 = getstatusoutput('ffprobe "' + file + '" -show_streams -v quiet')
    info = {'color': '', 'resolution': '', 'codec': '', 'source': '', 'languages': [] if defaultLanguage == '' else [defaultLanguage]}
    nm = file.lower()
    info['source'] = 'BR' if ('bluray' in nm or 'bdremux' in nm) else 'DVD' if 'dvd' in nm else 'WEBRIP' if 'webrip' in nm else 'WEBDL' if 'web-dl' in nm else ''
    video = False

    if out[0] != 0: 
        log('Error getting media info for: "' + file + '", exit code: ' + str(out[0]) + '\n' + str(out[1]), 1, 1)
        return (False, info)
    
    out = json.loads(out[1])['streams']
    for s in out:
        if s['codec_type'] == 'video':
            video = s
            break
    
    if not video:
        log('No video tracks found for: ' + file, 1, 1)
        return (False, info)
    
    info['color'] = 'HDR' if out2[0] == 0 and 'bt2020' in out2[1] else 'SDR'
    info['resolution'] = 'UHD' if video['width'] >= 3840 else 'QHD' if video['width'] >= 2560 else 'HD' if video['width'] >= 1920 else 'SD'

    if 'codec_name' in video:
        if video['codec_name'] in ['h264', 'avc']: info['codec'] = 'AVC'
        elif video['codec_name'] in ['h265', 'hevc']: info['codec'] = 'HEVC'
        else: log('Unsupported video codec: ' + video['codec_name'].upper(), 3, 3)
    else: log('Video codec not found for: ' + file, 3, 3)
    
    for s in out:
        if s['codec_type'] == 'audio' and 'tags' in s and 'language' in s['tags']:
            info['languages'].append(s['tags']['language'].upper())
    lng = []
    for lang in info['languages']:
        if lang not in lng: lng.append(lang)
    info['languages'] = lng
    
    return (True, info)

def downloadImage(url, retry, src): # Unused, probably will be used in the future for image cache
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
    return "{:.1f}".format(sum([float(vl) for vl in lst]) / len(lst)) if len(lst) > 0 else "0"

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

def getSeasonMetadata(sn, season, ids, productionCompanies, omdbApi, tmdbApi, force):
    if force or (datetime.now() - datetime.strptime(season['metadataDate'], '%d/%m/%Y')) >= timedelta(days=getUpdateInterval(season['releaseDate'])):
        log('Updating metadata for: ' + season['title'], 3, 3)
        sc = False
        season['productionCompanies'] = productionCompanies
        for ep in season['episodes']: 
            season['episodes'][ep]['productionCompanies'] = productionCompanies

        if len(tmdbApi) > 0 and 'TMDBID' in ids:
            res = getJSON('https://api.themoviedb.org/3/tv/' + ids['TMDBID'] + '/season/' + sn + '?api_key=' + tmdbApi + '&language=en')
            if res:
                sc = True
                if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']: season['cover'] = 'https://image.tmdb.org/t/p/original' + res['poster_path']
                if 'episodes' in res:
                    for ep in res['episodes']:
                        if 'episode_number' not in ep or ep['episode_number'] == 'N/A': continue
                        num = str(ep['episode_number'])
                        if num not in season['episodes']: continue
                        if 'still_path' in ep and ep['still_path'] != 'N/A' and ep['still_path']:
                            season['episodes'][num]['cover'] = 'https://image.tmdb.org/t/p/original' + ep['still_path']
                        if 'vote_average' in ep and ep['vote_average'] != 'N/A' and 'vote_count' in ep and ep['vote_count'] > minVotes:
                            season['episodes'][num]['ratings']['TMDB'] = {'icon': 'TMDB', 'value': "{:.1f}".format(float(ep['vote_average']))}
                        if 'id' in ep: 
                            season['episodes'][num]['ids']['TMDBID'] = ep['id']
                rts = [season['episodes'][ep]['ratings']['TMDB']['value'] for ep in season['episodes'] if 'TMDB' in season['episodes'][ep]['ratings']]
                if len(rts) > 0:
                    season['ratings']['TMDB'] = {'icon': 'TMDB', 'value': avg(rts)}
            else: log('Error getting info on TMDB for: ' + title + ' S' + sn, 3, 1)
        
        if len(omdbApi) > 0 and 'IMDBID' in ids:
            res = getJSON('http://www.omdbapi.com/?i=' + ids['IMDBID'] + '&Season=' + sn + '&apikey=' + omdbApi)
            if res and 'Episodes' in res and len(res['Episodes']) > 0:
                sc = True
                rts = []
                for ep in res['Episodes']:
                    if ep['Episode'] not in season['episodes']: continue
                    if 'imdbRating' in ep and ep['imdbRating'] != 'N/A': 
                        season['episodes'][ep['Episode']]['ratings']['IMDB'] = {'icon': 'IMDB', 'value': float(ep['imdbRating'])}
                        rts.append(float(ep['imdbRating']))
                    if 'imdbID' in ep and ep['imdbID'] != 'N/A':
                        season['episodes'][ep['Episode']]['ids']['IMDBID'] = ep['imdbID']
                season['ratings']['IMDB'] = {'icon': 'IMDB', 'value': avg(rts)}
            else: log('Error getting info on OMDB for: ' + title + ' S' + sn, 3, 1)

        if 'RTURL' in season:
            sc = True
            RT = getRTSeasonRatings(season['RTURL'])
            if RT:
                for rt in RT['ratings']:
                    season['ratings'][rt] = RT['ratings'][rt]
                season['certifications'] = RT['certifications']
                for ep in RT['episodes']:
                    if ep in season['episodes']:
                        season['episodes'][ep]['RTURL'] = RT['episodes'][ep]
                        RTE = getRTEpisodeRatings(RT['episodes'][ep])
                        if RTE:
                            for rte in RTE['ratings']: season['episodes'][ep]['ratings'][rte] = RTE['ratings'][rte]

        if sc: season['metadataDate'] = datetime.now().strftime("%d/%m/%Y")

def getSeasonMediainfo(season, defaultLanguage):
    for ep in season['episodes']:
        if (datetime.now() - datetime.strptime(season['episodes'][ep]['mediainfoDate'], '%d/%m/%Y')) > timedelta(days=mediainfoUpdateInterval):
            success, season['episodes'][ep]['mediainfo'] = getMediaInfo(season['episodes'][ep]['mediaFile'], defaultLanguage)
            if success: season['episodes'][ep]['mediainfoDate'] = datetime.now().strftime("%d/%m/%Y")
    
    season['mediainfo'] = getParentMediainfo(season['episodes'])

def updateSeasons(coverName, backdropName, episodeName, mt):
    ret = []
    sns = {}
    for fl in glob(join(mt['path'], '*')):
        res = findall('.*\/[Ss]eason[ ._-](\d{1,3})$', fl)
        if len(res) == 1:
            sns[str(int(res[0]))] = {
                'path': fl,
                'episodes': {}, 
                'hasBackdrop': all([exists(join(fl, cv)) for cv in backdropName.split(',')]), 
                'type': 'season', 
                'title': mt['title'] + ' (Season: ' + res[0] + ')',
                'ids': {},
                'ratings': {},
                'metadataDate': '1/1/1999',
                'mediainfo': {},
                'certifications': [],
                'ageRating': 'NR',
                'releaseDate': datetime.now().strftime("%d/%m/%Y")
            }

            eps = []
            for ex in extensions: eps += glob(join(fl, '*.' + ex))
            for ep in eps: 
                mc = findall('S0*' + res[0] + 'E0*(\d+)', ep)
                if len(mc) == 1:
                    sns[str(int(res[0]))]['episodes'][str(int(mc[0]))] = {
                        'mediaFile': ep,
                        'path': ep.rpartition('/')[0],
                        'type': 'episode',
                        'title': mt['title'] + ' (Season: ' + res[0] + ' Episode: ' + mc[0] + ')',
                        'ids': {},
                        'ratings': {},
                        'mediainfoDate': '1/1/1999',
                        'metadataDate': '1/1/1999',
                        'mediainfo': {},
                        'certifications': {},
                        'ageRating': 'NR',
                        'releaseDate': datetime.now().strftime("%d/%m/%Y")}

    if 'seasons' not in mt: 
        mt['seasons'] = sns
        ret = [sn for sn in sns]
    else:
        for sn in sns:
            if sn not in mt['seasons'] or sns[sn]['path'] != mt['seasons'][sn]['path']: 
                mt['seasons'][sn] = sns[sn]
                ret = True
            else:
                for ep in sns[sn]['episodes']:
                    if ep not in mt['seasons'][sn]['episodes'] or sns[sn]['episodes'][ep]['path'] != sns[sn]['episodes'][ep]['path']:
                        mt['seasons'][sn]['episodes'][ep] = sns[sn]['episodes'][ep]
                        if sn not in ret: ret.append(sn)
        
        for sn in mt['seasons']:
            if sn not in sns:
                del mt['seasons'][sn]
            else:
                for ep in mt['seasons'][sn]['episodes']:
                    if ep not in sns[sn]['episodes']: 
                        del mt['seasons'][sn]['episodes'][ep]
    return ret

def tagImage(path):
    with open(path, 'rb') as image:
        img = imgTag(image)
    img["software"] = "BetterCovers"
    img['datetime_original'] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    with open(path, 'wb') as image:
        image.write(img.get_file())

def processTask(task, config, thread):
    st = time.time()
    imageGenerated = task['generateImage'] and generateMediaImage(task['generateImage'], thread)
    if task['generateImage'] and not imageGenerated:
        if task['image']:
            log('Error generating screenshot with ffmpeg, using downloaded image instead', 3, 3)
        else:
            log('Error generating screenshot with ffmpeg', 1, 1)
            return False
    try:
        with open(join(workDirectory, 'media', 'covers', task['cover'] + '.html')) as html:
            HTML = html.read()
    except:
        log('Error opening: ' + join(workDirectory, 'media', 'covers', task['cover'] + '.html'), 1, 0)
        return False

    rts = ''
    minfo = ''
    pcs = ''
    cert = ''
    
    for rt in task['ratings']: 
        rts += "<div class = 'ratingContainer ratings-" + rt + "'><img src= '" + join('..', 'media', 'ratings', task['ratings'][rt]['icon'] + '.png') + "' class='ratingIcon'/><label class='ratingText'>" + str(task['ratings'][rt]['value']) + "</label></div>\n\t\t"
    for mi in task['mediainfo']:
        if task['mediainfo'][mi] != '':
            pt = join('..', 'media', 'mediainfo' if mi != 'languages' else 'languages', task['mediainfo'][mi] + '.png')
            minfo += "<div class='mediainfoImgContainer mediainfo-" + task['mediainfo'][mi] + "'><img src= '" + pt + "' class='mediainfoIcon'></div>\n\t\t\t"  
    for pc in task['productionCompanies']:
        pcs += "<div class='pcWrapper producionCompany-" + str(pc['id']) +  "'><img src='" + pc['logo'] + "' class='producionCompany'/></div>\n\t\t\t\t"
    for cr in task['certifications']:
        cert += '<img src= "' + join('..', 'media', 'ratings', cr + '.png') + '" class="certification"/>'

    if task['ageRating'] != '':
        with open(join(workDirectory, 'media', 'ageRatings', task['ageRating'] + '.svg'), 'r') as svg:
            HTML = HTML.replace('<!--AGERATING-->', svg.read())
    
    HTML = HTML.replace('$IMGSRC', thread + '-sc.png' if imageGenerated else task['image'])
    HTML = HTML.replace('<!--TITLE-->', task['title'])
    HTML = HTML.replace('<!--RATINGS-->', rts)
    HTML = HTML.replace('<!--MEDIAINFO-->', minfo)
    HTML = HTML.replace('<!--PRODUCTIONCOMPANIES-->', pcs)
    HTML = HTML.replace('<!--CERTIFICATIONS-->', cert)

    with open(join(workDirectory, 'threads', thread + '.html'), 'w') as out:
        out.write(HTML)
    
    i = 0
    command = ['wkhtmltoimage', '--cache-dir', join(workDirectory, 'cache'), '--javascript-delay', '2000', '--enable-local-file-access', '--transparent', 'file://' + join(workDirectory, 'threads', thread + '.html'), join(workDirectory, 'threads', thread + '.png')]
    while i < 3 and not call(command, stdout=DEVNULL, stderr=DEVNULL) == 0: i += 1
    if i < 3:
        # tagImage(join(workDirectory, 'threads', thread + '.png'))
        for fl in task['out']:
            cm = call(['cp', '-f', join(workDirectory, 'threads', thread + '.png'), fl])
            if cm != 0:
                log('Error moving to: ' + fl, 3, 3)
                return False  
        log('Succesfully generated ' + ('cover' if task['type'] != 'backdrop' else 'backdrop') + ' image for: ' + task['title'] + ' in ' + str(round(time.time() - st)) + 's', 2, 2)
        return True 
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

def getCover(mt, covers):
    def ratingsOk(ratings):
        for rt in ratings:
            if rt not in mt['ratings']: return False
            value = float(ratings[rt][1:])
            rating = float(mt['ratings'][rt]['value'])
            if ratings[rt][0] == '>':
                if rating <= value: return False
            elif rating >= value: return False
        return True
    
    def arrayOk(cover, metadata):
        for pr in cover:
            if pr not in metadata: return False
        return True

    def mediainfoOk(mediainfo):
        for pr in mediainfo:
            if pr == 'languages':
                if not arrayOk(mediainfo['languages'], mt['mediainfo']['languages']):
                    return False
            elif mediainfo[pr] != mt['mediainfo'][pr]: return False
        return True
    
    def ageRatingOk(rating):
        order = ['G', 'PG', 'PG-13', 'R', 'NC-17', 'NR']
        if order.indexOf(rating) < order.indexof(mt['ageRating']): return False

    for cover in covers:
        if 'type' not in cover or cover['type'] == '*' or mt['type'] in cover['type'].split(','):
            if 'ratings' not in cover or ratingsOk(cover['ratings']): 
                if 'mediainfo' not in cover or mediainfoOk(cover['mediainfo']):
                    if 'ageRating' not in cover or ageRatingOk(cover['ageRating']):
                        if 'productionCompanies' not in cover or arrayOk(cover['productionCompanies'], [pc['id'] for pc in mt['productionCompanies']]):
                            return cover['cover']
    return 'newCover'        