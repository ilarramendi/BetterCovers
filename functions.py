import json
import sys
import time
from copy import deepcopy
from datetime import datetime, timedelta
from glob import glob
from hashlib import md5
from math import sqrt
from os import W_OK, access
from os.path import exists, join, realpath
from random import random
from re import findall, match
from subprocess import DEVNULL, call, getstatusoutput
from threading import Lock, Thread
from time import sleep
from urllib.parse import quote

import requests
from exif import Image as exifImage

import scrapers.IMDB
from scrapers.letterboxd import getLBRatings, searchLB
from scrapers.MetaCritic import getMetacriticScore
from scrapers.RottenTomatoes import (getRTEpisodeRatings, getRTMovieRatings,
                                     getRTSeasonRatings, getRTTVRatings,
                                     searchRT)
from scrapers.Trakt import getTraktRating
from scrapers.TVTime import *

logLevel = 2

logLock = Lock()
wkhtmltoimage = ''
mediaExtensions = ['mkv', 'mp4', 'avi', 'm2ts'] # Type of extensions to look for media files
workDirectory = ''
minVotes = 3
ratingsOrder = ['TMDB', 'IMDB', 'Trakt', 'LB', 'RT', 'RTA', 'MTC', 'TVTime']
mediainfoOrder = ['color', 'resolution', 'languages', 'codec', 'source']

# Returns all media files inside a folder except for trailers
def getMediaFiles(folder):
    mediaFiles = []
    for ex in mediaExtensions: 
        mediaFiles += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex))
    return[fl for fl in mediaFiles if 'trailer' not in fl]

# Updates seasons and episodes from disk, adds new and removes missing
def updateSeasons(metadata):
    sns = {}
    for folder in glob(join(metadata['path'].translate({91: '[[]', 93: '[]]'}), '*')): # For all files inside tv show directory
        sn = findall('.*\/[Ss]eason[ ._-](\d{1,3})$', folder) # Gets season number
        if len(sn) == 1: # If its a season
            sn = int(sn[0])
            sns[sn] = { # Add to new seasons array
                'URLS': {},
                'type': 'season', 
                'title': metadata['title'] + ' (S:' + str(sn) + ')',
                'releaseDate': datetime.now().strftime("%m/%d/%Y"),# If release date is not found use date added for calculating metadata update
                'ratings': {}, 
                'productionCompanies': {},
                'path': folder,
                'ids': {}, 
                'episodes': {},
                'covers': [],
                'certifications': [],
                'backdrops': []
            }

            eps = []
            for ex in mediaExtensions: eps += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex)) # Finds all media files inside season
            for ep in eps: 
                epn = findall('S0*' + str(sn) + 'E0*(\d+)', ep) 
                if len(epn) == 1: # If its an episode from the same season
                    epn = int(epn[0])
                    sns[sn]['episodes'][epn] = { # Adds episode to season
                        'URLS': {},
                        'type': 'episode',
                        'title': metadata['title'] + ' (S:' + str(sn) + ' E:' + str(epn).zfill(len(str(len(eps)))) + ')', # Fills with 0 acording to the maximum number of episodes (can fail with absolute numered episodes)    
                        'releaseDate': datetime.now().strftime("%m/%d/%Y"), # If release date is not found use date added for calculating metadata update
                        'ratings': {}, 
                        'path': ep,
                        'ids': {}, 
                        'covers': [],
                        'certifications': []
                    }
    
    if len(sns) == 0: return False
    if 'seasons' not in metadata: metadata['seasons'] = sns # If show has not seasons add all
    else:
        for sn in sns:
            if sn not in metadata['seasons'] or sns[sn]['path'] != metadata['seasons'][sn]['path']: # If its a new season or path changed add season
                metadata['seasons'][sn] = sns[sn]
            else:
                for ep in sns[sn]['episodes']:
                    if ep not in metadata['seasons'][sn]['episodes'] or sns[sn]['episodes'][ep]['path'] != sns[sn]['episodes'][ep]['path']: # if its a new episode or path changed add episode
                        metadata['seasons'][sn]['episodes'][ep] = sns[sn]['episodes'][ep]
        seasonsDel = []

        for sn in metadata['seasons']:
            if sn not in sns: seasonsDel.append(sn)# Deletes all season from metadata that are missing from disk
            else:
                episodesDel = []
                for ep in metadata['seasons'][sn]['episodes']:
                    if ep not in sns[sn]['episodes']: episodesDel.append(ep) # Deletes all episodes from season in metadata that are missing from disk         
                for ep in episodesDel:
                    del metadata['seasons'][sn]['episodes'][ep]
        for sn in seasonsDel:
            del metadata['seasons'][sn]
    return True

# Returns ids for a .NFO file
def readNFO(file): # TODO can this be done with tv shows??
    try:
        with open(file, 'r') as f:
            obj = parsexml(f.read())
            print(obj)
            obj = obj['movie']
            
    except:
        return {}
    
    res = {}
    if 'imdbid' in obj: res['IMDBID'] = obj['imdbid']
    if 'tmdbid' in obj: res['TMDBID'] = obj['tmdbid']
    return res     
    
# Check if metadata should be updated based on update date and release date
def checkDate(dateString, releaseDate):
    return (datetime.now() - datetime.strptime(dateString, '%d/%m/%Y')) >= timedelta(days=getUpdateInterval(releaseDate))

# Updates metadata from APIS and SCRAPERS
def getMetadata(metadata, omdbApi, tmdbApi, scraping, preferedImageLanguage):  
    
    # Gets metadata from TMDB api
    def _getTMDB():
        if 'TMDBDate' not in metadata or checkDate(metadata['TMDBDate'], metadata['releaseDate']):
            start = time.time()
            
            if 'TMDBID' not in metadata['ids'] and 'IMDBID' in metadata['ids']: # If missing TMDB id search by IMDBID
                res = getJSON('https://api.themoviedb.org/3/find/' + metadata['ids']['IMDBID'] + '?api_key=' + tmdbApi + '&language=' + preferedImageLanguage + '&external_source=imdb_id')
                if res and len(res[metadata['type'] + '_results']) == 1:  
                    metadata['ids']['TMDBID'] = str(res[metadata['type'] + '_results'][0]['id'])
                else: log("No results found searching by IMDB id in TMDB: " + metadata['ids']['IMDBID'], 2, 5)
            
            if 'TMDBID' not in metadata['ids']: # If still missing TMDB id search by title
                res = getJSON('https://api.themoviedb.org/3/search/' + metadata['type'] + '?api_key=' + tmdbApi + '&language=en&page=1&include_adult=false&append_to_response=releases,external_ids&query=' + quote(metadata['title']) + ('&year=' + str(metadata['year']) if metadata['year'] else ''))
                if res and 'results' in res:
                    for result in res['results']:
                        if result['name'].lower() == metadata['title'].lower():
                            metadata['ids']['TMDBID'] = str(result['id'])
                            break
                    else: log("No results found searching by title in TMDB: " + metadata['title'], 3, 4)
                else: log("No results found searching by title in TMDB: " + metadata['title'], 3, 4)

            if 'TMDBID' in metadata['ids']: # If TMDB id is found get results
                result = getJSON('https://api.themoviedb.org/3/' + metadata['type'] + '/' + metadata['ids']['TMDBID'] + '?api_key=' + tmdbApi + '&language=en&append_to_response=releases,external_ids,videos,production_companies,images')
                if result: # If TMDB returns results fill all results in metadata
                    # TODO set year if found in result
                    if 'vote_average' in result and result['vote_average'] != 0:
                        metadata['ratings']['TMDB'] = {'icon': 'TMDB', 'value': str(result['vote_average'])}
                    if 'imdb_id' in result['external_ids'] and result['external_ids']['imdb_id'] and 'IMDBID' not in metadata['ids']:
                        metadata['ids']['IMDBID'] = result['external_ids']['imdb_id']
                    if 'last_air_date' in result and result['last_air_date']:
                        metadata['releaseDate'] = datetime.strptime(result['last_air_date'], '%Y-%m-%d').strftime("%d/%m/%Y") # TODO change this on new episodes
                    elif 'release_date' in result and result['release_date']:
                        metadata['releaseDate'] = datetime.strptime(result['release_date'], '%Y-%m-%d').strftime("%d/%m/%Y")
                    if 'releases' in result and 'countries' in result['releases']:
                        for rl in result['releases']['countries']:
                            if rl['iso_3166_1'] == 'US':
                                if rl['certification'] != '': metadata['ageRating'] = rl['certification']
                                break
                    if 'results' in result['videos']:
                        for vd in result['videos']['results']:
                            if vd['site'] == 'YouTube' and vd['type'] == 'Trailer':
                                for tr in metadata['trailers']:
                                    if tr['id'] == vd['key']: break
                                else: metadata['trailers'].append({'id': vd['key'], 'name': vd['name'], 'language': vd['iso_639_1'].upper(), 'resolution': vd['size']})

                    if 'title' in result: metadata['title'] = result['title']
                    elif 'name' in result: metadata['title'] = result['name'] 
                    if 'production_companies' in result:
                        for pc in result['production_companies']:
                            if pc['logo_path']: 
                                for prc in metadata['productionCompanies']: 
                                    if prc['id'] == pc['id']: break
                                else:
                                    metadata['productionCompanies'].append({'id': pc['id'], 'name': pc['name'], 'logo': 'https://image.tmdb.org/t/p/original' + pc['logo_path']})
                    
                    for prop in result['images']:
                        mtProp = prop if prop != 'posters' else 'covers'
                        for image in result['images'][prop]:
                            imgSrc = 'https://image.tmdb.org/t/p/original' + image['file_path']
                            
                            for img in metadata[mtProp]:
                                if img['src'] == imgSrc: break
                            else: metadata[mtProp].append({
                                    'src': imgSrc,
                                    'height': image['height'],
                                    'language': image['iso_639_1'],
                                    'source': 'TMDB'})

                    metadata['TMDBDate'] = datetime.now().strftime("%d/%m/%Y")
                    log('Finished getting TMDB metadata for: ' + metadata['title'] + ' in: ' + timediff(start), 1, 3)
                else: log('TMDB id found but no results found for: ' + metadata['title'], 3, 4)
            else: log("TMDB id not found for: " + metadata['title'], 3, 4)
        else: log('No need to update TMDB metadata for: ' + metadata['title'], 1, 3)
    
    # Gets suplemetary metadata from OMDB api
    def _getOMDB():   
        if len(omdbApi) > 0 and ('IMDBID' in metadata['ids'] or 'title' in metadata): # TODO add release date from omdb 
            if 'OMDBDate' not in metadata or checkDate(metadata['OMDBDate'], metadata['releaseDate']):
                start = time.time()
                url = 'http://www.omdbapi.com/?apikey=' + omdbApi + '&tomatoes=true'
                url += '&i=' + metadata['ids']['IMDBID'] if 'IMDBID' in metadata['ids'] else '&t=' + quote(metadata['title'].replace(' ', '+')) + ('&y=' + str(metadata['year']) if metadata['year'] else '')
                res = getJSON(url)
                if res:
                    if 'Poster' in res and res['Poster'] != 'N/A': # Only set cover if missing (OMDB covers are hit or miss)
                        for img in metadata['covers']:
                            if img['src'] == res['Poster']: break
                        else: metadata['covers'].append({
                                'src': res['Poster'],
                                'height': 0,
                                'language': 'en',
                                'source': 'OMDB'})
                    
                    if 'Metascore' in res and res['Metascore'] != 'N/A':
                        metadata['ratings']['MTC'] = {'icon': 'MTC', 'value': "%.1f" % (int(res['Metascore']) / 10)}
                    
                    if 'imdbRating' in res and res['imdbRating'] != 'N/A':
                        metadata['ratings']['IMDB'] = {'icon': 'IMDB', 'value': "%.1f" % float(res['imdbRating'])}
                    
                    if 'Ratings' in res:
                        for rt in res['Ratings']:
                            if rt['Source'] == 'Rotten Tomatoes' and rt['Value'] != 'N/A':
                                metadata['ratings']['RT'] = {'icon': 'RT' if int(rt['Value'][:-1]) >= 60 else 'RT-LS', 'value': str(int(rt['Value'][:-1]) / 10).rstrip('0').rstrip('.')}
                                break
                    
                    if 'imdbID' in res and 'IMDBID' not in metadata['ids'] and res['imdbID'] != 'N/A':
                        metadata['ids']['IMDBID'] = res['imdbID'] 

                    metadata['OMDBDate'] = datetime.now().strftime("%d/%m/%Y")
                    log('Finished getting OMDB metadata for: ' + metadata['title'] + ' in: ' + timediff(start), 1, 3)
                else: log('No results found on OMDB for: ' + metadata['title'], 2, 4)
            else: log('No need to update OMDB metadata for: ' + metadata['title'], 1, 3)
    
    # Gets textless posters from MOVIEMANIA
    #
    #def _getMovieMania(): # TODO fix this or delete
    #    if scraping['textlessPosters'] and 'TMDBID' in metadata['ids']:
    #        if 'textlessPDate' not in metadata or checkDate(metadata['textlessPDate'], metadata['releaseDate']):
    #                posters = getTextlessPosters('https://www.moviemania.io/phone/movie/' + metadata['ids']['TMDBID'])
    #                if posters and len(posters) > 0: 
    #                    metadata['cover'] = posters[0]
    #                    metadata['textlessPDate'] = datetime.now().strftime("%d/%m/%Y")
    #                else: log('No textless poster found for: ' + name, 3, 3)
    #        else: log('No need to update OMDB metadata for: ' + metadata['title'], 1, 4)
  
    # Get RT ratings, certifications and url for media and seasons if needed
    def _getRT():
        if scraping['RT']: 
            if 'RTDate' not in metadata or checkDate(metadata['RTDate'], metadata['releaseDate']):
                start = time.time()
                url = searchRT(metadata['type'], metadata['title'], metadata['year'], getJSON)
                if url: # if roten tomatoes url is found
                    metadata['URLS']['RT'] = url
                    rt = getRTMovieRatings(url, get) if metadata['type'] == 'movie' else getRTTVRatings(url, get)
                    if rt['statusCode'] == 403: return log('Rotten tomatoes api limit reached!', 3, 1)
                    
                    for rating in rt['ratings']: metadata['ratings'][rating] = rt['ratings'][rating]
                    
                    if 'RT-CF' in rt['certifications']:
                        if 'RT-CF' not in metadata['certifications']: metadata['certifications'].append('RT-CF')
                    elif 'RT-CF' in metadata['certifications']:
                        metadata['certifications'].remove('RT-CF')
                    
                    if 'seasons' in rt:
                        for sn in rt['seasons']:
                            if sn in metadata['seasons']: metadata['seasons'][sn]['URLS']['RT'] = rt['seasons'][sn]
                    
                    if len(rt['ratings']) > 0 or ('seasons' in rt and len(rt['seasons']) > 0):
                        metadata['RTDate'] = datetime.now().strftime("%d/%m/%Y")
                        log('Finished getting RT metadata for: ' + metadata['title'] + ' in: ' + timediff(start), 1, 3)
                    else: log('No ratings found on RottenTomatoes for: ' + metadata['title'], 2, 4)
                else: log('No results found on RottenTomatoes for: ' + metadata['title'], 2, 4)
            else: log('No need to update RottenTomatoes metadata for: ' + metadata['title'], 1, 3)
    
    # Gets IMBD and MTC scores and certifications from IMBD
    def _getIMDB():
        if scraping['IMDB'] and 'IMDBID' in metadata['ids']:
            if 'IMDBDate' not in metadata or checkDate(metadata['IMDBDate'], metadata['releaseDate']): 
                start = time.time()
                imdb = scrapers.IMDB.getIMDBRating(metadata['ids']['IMDBID'])
                if imdb:
                    metadata['IMDBDate'] = datetime.now().strftime("%d/%m/%Y")
                    metadata['ratings']['IMDB'] = {'icon': 'IMDB', 'value': imdb[0]}
                    log('Found IMDB rating in dataset for: ' + metadata['title'] + ': ' + str(imdb[0]) + ', in: ' + timediff(start), 1, 3)
                else: log('No result found in DATASET for: ' + metadata['title'], 2, 4)
                
                if metadata['type'] == 'tv': # TODO run this again when episodes are added
                    eps = scrapers.IMDB.getEpisodesIMDBID(metadata['ids']['IMDBID'])
                    for ep in eps: # Get episodes ids
                        if int(ep[1]) in metadata['seasons'] and int(ep[2]) in metadata['seasons'][int(ep[1])]['episodes']:
                            metadata['seasons'][int(ep[1])]['episodes'][int(ep[2])]['ids']['IMDBID'] = str(ep[0])
            else: log('No need to update IMDB metadata for: ' + metadata['title'], 1, 3)
    
    # Gets movie ratings from letterboxd
    def _getLB():
        if metadata['type'] == 'movie' and scraping['LB']:
            if 'LBDate' not in metadata or checkDate(metadata['LBDate'], metadata['releaseDate']):
                start = time.time()
                LB = searchLB(metadata['ids']['IMDBID'] if 'IMDBID' in metadata['ids'] else False, metadata['title'], metadata['year'], get)
                if LB: 
                    metadata['URLS']['LB'] = LB
                    LB = getLBRatings(LB, get)
                    if LB: 
                        metadata['ratings']['LB'] = LB
                        metadata['LBDate'] = datetime.now().strftime("%d/%m/%Y")
                        log('Found LetterBox rating for: ' + metadata['title'] + ': ' + LB['value'] + ', in: ' + timediff(start), 1, 3)
                else: log('No results found in LetterBox for: ' + metadata['title'], 2, 4)
            else: log('No need to update Letterbox metadata for: ' + metadata['title'], 1, 3)
   
    # Get episode and season ratings from TVTime (all in only one request)
    def _getTVTime():
        if metadata['type'] == 'tv' and scraping['TVTime']:
            if 'TVTimeDate' not in metadata or checkDate(metadata['TVTimeDate'], metadata['releaseDate']):
                start = time.time()
                tvTime = searchTVTime(metadata['title'], metadata['year'], getJSON)
                if tvTime:
                    metadata['ids']['TVTimeID'] = tvTime['id']
                    if tvTime['image'] not in metadata['covers']:
                        metadata['covers'].append(tvTime['image'])
                    ratings = getTVTimeRatings(metadata['ids']['TVTimeID'], getJSON)
                    if ratings:
                        for season in ratings:
                            for episode in season:
                                seasonNumber = int(episode['season_number'])
                                episodeNumber = int(episode['number'])
                                if seasonNumber in metadata['seasons'] and episodeNumber in metadata['seasons'][seasonNumber]['episodes']:
                                    metadata['seasons'][seasonNumber]['episodes'][episodeNumber]['ratings']['TVTime'] = {'icon': 'TVTime', 'value': "%.1f" % episode['ratings']}      
                            
                        rtsTotal = [] # Get ratings average for show and seasons from episodes
                        for season in metadata['seasons']:
                            rts = []
                            for ep in metadata['seasons'][season]['episodes']:
                                episode = metadata['seasons'][season]['episodes'][ep]
                                if 'TVTime' in episode['ratings']:
                                    rts.append(episode['ratings']['TVTime']['value'])
                                    rtsTotal.append(episode['ratings']['TVTime']['value'])
                            if len(rts): metadata['seasons'][season]['ratings']['TVTime'] = {'icon': 'TVTime', 'value': avg(rts)}
                        if len(rtsTotal): metadata['ratings']['TVTime'] = {'icon': 'TVTime', 'value': avg(rtsTotal)}
                        
                        log('Finished getting TVTime metadata for: ' + metadata['title'] + ' in: ' + timediff(start), 1, 3)
                        metadata['TVTimeDate'] = datetime.now().strftime("%d/%m/%Y")  
                    else: log('No episode ratings found in TVTime for: ' + metadata['title'], 2, 4)
                else: log('No result found in TVTime for: ' + metadata['title'], 2, 4)
            else: log('No need to update TVTime metadata for: ' + metadata['title'], 1, 3)
    
    # TODO do this for seasons and episodes?
    # Gets ratings from metaCritic
    def _getMetaCritic():
        if scraping['MetaCritic'] and 'IMDBID' in metadata['ids']:
            if 'MTCDate' not in metadata or checkDate(metadata['MTCDate'], metadata['releaseDate']):
                start = time.time()
                sc = getMetacriticScore(metadata['ids']['IMDBID'], get)
                if sc:
                    metadata['ratings']['MTC'] = {'icon': 'MTC-MS' if sc['MTC-MS'] else 'MTC', 'value': sc['rating']}
                    if sc['MTC-MS']:
                        if 'MTC-MS' not in metadata['certifications']: metadata['certifications'].append('MTC-MS')
                    elif 'MTC-MS' in metadata['certifications']:
                        metadata['certifications'].remove('MTC-MS')
                    
                    metadata['MTCDate'] = datetime.now().strftime("%d/%m/%Y")
                    log('Finished getting MetaCritic ratings for: ' + metadata['title'] + ' in: ' + timediff(start), 1, 3)
                else: log('Error getting MetaCritic ratings for: ' + metadata['title'], 2, 4)
            else: log('No need to update MetaCritic metadata for: ' + metadata['title'], 1, 3)
    
    # Gets ratings from Trakt
    def _getTrakt():
        if scraping['Trakt'] and 'TMDBID' in metadata['ids']:
            if 'TraktDate' not in metadata or checkDate(metadata['TraktDate'], metadata['releaseDate']):
                start = time.time()
                rt = getTraktRating(metadata['ids']['TMDBID'], get)
                if rt:
                    metadata['ratings']['Trakt'] = {'icon': 'Trakt', 'value': rt}
                    metadata['TraktDate'] = datetime.now().strftime("%d/%m/%Y")
                    log('Finished getting Trakt ratings for: ' + metadata['title'] + ' in: ' + timediff(start), 1, 3)
                else: log('Error getting Trakt ratings for: ' + metadata['title'], 2, 4)
            else: log('No need to update Trakt metadata for: ' + metadata['title'], 1, 3)
    
    tsks = []

    _getTMDB() # Get general information first

    for fn in [_getOMDB, _getRT, _getIMDB, _getLB, _getTVTime, _getMetaCritic, _getTrakt]: # Starts rest of the tasks
        tsks.append(Thread(target=fn, args=()))
        tsks[-1].start()
    for tsk in tsks: tsk.join() # Wait for tasks to finish

    if metadata['type'] == 'tv': # TODO get specific production companies for eachg epiosode
        for sn in metadata['seasons']: metadata['seasons'][sn]['productionCompanies'] = metadata['productionCompanies']

    metadata['metadataDate'] = datetime.now().strftime("%d/%m/%Y") # TODO Update only if any change was succesfull

# Returns an update interval, interval increases based on how old is the media
# Change release date on new episode release
def getUpdateInterval(releaseDate):
    return min(120, sqrt(max((datetime.now() - datetime.strptime(releaseDate, '%d/%m/%Y')).days, 0) * 4 + 1)) # 0 to 120 days

# Logs to file and STDOUT with a specific level and color
def log(text, type, level): # 0 = Success, 1 = Normal, 2 = Warning, 3 = Error
    if level <= logLevel:
        print((datetime.now().strftime("[%m/%d/%Y %H:%M:%S] --> ") if logLevel > 2 else '') + ['\033[92m', '\033[37m', '\033[93m', '\033[91m'][type] + text + '\033[0m')
        with open(join(workDirectory, 'BetterCovers.log'), 'a') as log:
            log.write('[' + ['Info   ', 'Error  ', 'Success', 'Warning'][type] + datetime.now().strftime("][%m/%d/%Y %H:%M:%S] --> ") + text + '\n')

# returns a tuple of the name and year from file, if year its not found returns false in year
def getName(folder):
    fl = (folder[:-1] if folder[-1] == '/' else folder).rpartition('/')[2]

    inf = findall("(?:^([^(]+) \(?(\d{4})\)?)|(^[^[\(]+)", fl)
    if len(inf) == 1: 
        if inf[0][2] == '':
            return [inf[0][0].translate({'.': ' ', '_': ' '}), int(inf[0][1])]
        else: return [inf[0][2].translate({'.': ' ', '_': ' '}), False]
    else:
        log('Name not found for: ' + fl, 3, 1)
        return [False, False]

#Makes a https request to a url and returns a JSON object if successfull
def getJSON(url, headers = {}):
    response = get(url, headers = headers)

    if 'application/json' in response.headers.get('content-type'):
        try:
            return response.json()
        except Exception as ex: log('Error parsing JSON from response:\n' + response.text, 1, 1)
    return False

# Gets mediainfo for a specific file
def getMediaInfo(metadata, defaultAudioLanguage, mediainfoUpdateInterval):
    if 'mediainfoDate' not in metadata or (datetime.now() - datetime.strptime(metadata['mediainfoDate'], '%d/%m/%Y')) > timedelta(days=mediainfoUpdateInterval):
        if 'mediainfo' not in metadata: metadata['mediainfo'] = {'languages': []}
        # TODO Add extra characters that have problems here
        cmd = 'ffprobe "' + metadata['path'].translate({36: '\$'}) + '" -of json -show_entries stream=index,codec_type,codec_name,height,width:stream_tags=language -v quiet'
        cmd2 = 'ffprobe "' + metadata['path'].translate({36: '\$'}) + '" -show_streams -v quiet'
        out = getstatusoutput(cmd)
        out2 = getstatusoutput(cmd2)
        
        # Source
        nm = metadata['path'].lower()
        metadata['mediainfo']['source'] = 'BR' if ('bluray' in nm or 'bdremux' in nm) else 'DVD' if 'dvd' in nm else 'WEBRIP' if 'webrip' in nm else 'WEBDL' if 'web-dl' in nm else 'UNKNOWN'

        if out[0] != 0: return log('Error getting media info for: "' + metadata['title'] + '", exit code: ' + str(out[0]) + '\n Command: ' + cmd, 3, 1)
        if out2[0] != 0: return log('Error getting media info for: "' + metadata['title'] + '", exit code: ' + str(out2[0]) + '\n Command: ' + cmd2, 3, 1)
             
        
        # Get first video track
        video = False
        streams = json.loads(out[1])['streams']
        for s in streams:
            if s['codec_type'] == 'video':
                video = s
                break
        
        if not video: return log('Error getting media info, no video tracks found for: ' + metadata['title'], 3, 1)
        
        # Color space (HDR or SDR)
        metadata['mediainfo']['color'] = 'HDR' if 'bt2020' in out2[1] else 'SDR'
        
        # Resolution
        metadata['mediainfo']['resolution'] = 'UHD' if video['width'] >= 3840 else 'QHD' if video['width'] >= 2560 else 'HD' if video['width'] >= 1920 else 'SD'

        # Video codec
        if 'codec_name' in video:
            if video['codec_name'] in ['h264', 'avc']: metadata['mediainfo']['codec'] = 'AVC'
            elif video['codec_name'] in ['h265', 'hevc']: metadata['mediainfo']['codec'] = 'HEVC'
            else:
                log('Unsupported video codec: ' + video['codec_name'].upper(), 2, 4)
                metadata['mediainfo']['codec'] = 'UNKNOWN'
        else:
            log('Video codec not found for: ' + metadata['title'], 2, 4)
            metadata['mediainfo']['codec'] = 'UNKNOWN'
        
        # Audio languages
        for s in streams:
            if s['codec_type'] == 'audio' and 'tags' in s and 'language' in s['tags'] and s['tags']['language'].upper() not in metadata['mediainfo']['languages']:
                metadata['mediainfo']['languages'].append(s['tags']['language'].upper())
        if len(metadata['mediainfo']['languages']) == 0:
            metadata['mediainfo']['languages'] = [defaultAudioLanguage] # TODO make this optional
            log('No audio lenguage found for: ' + metadata['title'] + ', using default language: ' + defaultAudioLanguage, 2, 4)
        
        metadata['mediainfoDate'] = datetime.now().strftime("%d/%m/%Y")
    else: return log('No need to update Media Info for: ' + metadata['title'], 1, 3)
        
# Returns all tasks for a given entry on the db (covers and backdrops)
def generateTasks(type, metadata, overwrite, config, templates):
    tsks = []
    img = metadata['path']  # Extract images from media file TODO fix image extraction
    if not(type in ['episode', 'backdrop'] and config['extractImage']):
        imgType = 'covers' if type != 'backdrop' else 'backdrops' 
        
        if len(metadata[imgType]) == 0: 
            log('Missing ' + imgType[:-1] + ' image for: ' + metadata['title'], 3, 3)
            return []
        else: img = metadata[imgType][0]['src']
    
    tsk = {
        'image':  img,
        'out': [],
        'type': type,
        'title': metadata['title'],
        'mediainfo': {},
        'ratings': {},
        'template': getTemplate(metadata, templates, type == 'backdrop'), # Selects html template
        'certifications': [],
        'productionCompanies': [],
        'useExistingImage': config['useExistingImage'] # Generate covers with the existing poster instead of downloading
        }
    
    # Adds configured mediainfo properties to task
    if 'mediainfo' in metadata:
        for pr in metadata['mediainfo']:
            if pr != 'languages':
                vl = metadata['mediainfo'][pr]
                if vl != 'UNKNOWN' and config['mediainfo'][pr][vl]: tsk['mediainfo'][pr] = vl # if mediainfo property is enabled
            else:
                for lg in config['mediainfo']['audio'].split(','): # Selects the first configured language found in the file
                    if lg in metadata['mediainfo']['languages']:
                        tsk['mediainfo'][pr] = lg
                        break
        
        # Replaces UHD and HDR for UHD-HDR if enabled
        if 'color' in metadata['mediainfo'] and 'resolution' in metadata['mediainfo']:
            if metadata['mediainfo']['color'] == 'HDR' and metadata['mediainfo']['resolution'] == 'UHD' and config['mediainfo']['color']['UHD-HDR']:
                tsk['mediainfo']['color'] = 'UHD-HDR'
                del tsk['mediainfo']['resolution']

    # Adds configured ratings to the task 
    for rt in metadata['ratings']:
        if config['ratings'][rt]: 
            tsk['ratings'][rt] = deepcopy(metadata['ratings'][rt])
            if config['usePercentage']:
                tsk['ratings'][rt]['value'] = str(int(float(tsk['ratings'][rt]['value']) * 10)) + '%'
    
    # Adds configured certifications
    for cr in metadata['certifications']:
        if config['certifications'][cr]: tsk['certifications'].append(cr)

    # Adds age rating if enabled
    if 'ageRating' in metadata:
        if config['ageRatings'][metadata['ageRating']]: tsk['ageRating'] = metadata['ageRating']
    elif config['ageRatings']['NR']: tsk['ageRating'] = 'NR'
    # Adds enabled production companies
    for pc in metadata['productionCompanies']:
        if config['productionCompaniesBlacklist']:
            if pc['id'] not in config['productionCompanies']: tsk['productionCompanies'].append(pc)
        elif pc['id'] in config['productionCompanies']: tsk['productionCompanies'].append(pc)

    
    tskCopy = deepcopy(tsk) # Generate hash of task to compare with the previously generated image
    del tskCopy['out']
    tskHash = md5(json.dumps(tskCopy, sort_keys=True).encode('utf8')).hexdigest()
    # Add paths to for images to generate if file dosnt exist, overwrite or automatic and hash different
    path = metadata['path'] if metadata['type'] in ['season', 'tv'] else metadata['path'].rpartition('/')[0]
    name = metadata['path'].rpartition('/')[2] if metadata['type'] in ['season', 'tv'] else metadata['path'].rpartition('/')[2].rpartition('.')[0]
    for pt in [join(path, pt) for pt in config['output'].replace('$NAME', name).split(';')]:
        if not exists(pt) or overwrite: tsk['out'].append(pt)
        elif tskHash != getHash(pt): tsk['out'].append(pt)
        else: log('No need to update image in: "' + pt + '"', 1, 3)

    if len(tsk['out']) > 0: tsks.append(tsk)
    if type in ['movie', 'tv']: tsks.extend(generateTasks('backdrop', metadata, overwrite, config['backdrop'], templates))
    
    return tsks

# Returns what html template should be used
def getTemplate(metadata, templates, backdrop):
    def _ratingsOk(ratings):
        for rt in ratings:
            if rt not in metadata['ratings']: return False
            value = float(ratings[rt][1:])
            rating = float(metadata['ratings'][rt]['value'])
            if ratings[rt][0] == '>':
                if rating <= value: return False
            elif rating >= value: return False
        return True
    
    def _companiesOk(companies):
        pc = [pc['id'] for pc in metadata['productionCompanies']]
        for pr in companies:
            if pr not in pc: return False
        return True

    def _mediainfoOk(mediainfo):
        for pr in mediainfo:
            if pr == 'languages':
                if not arrayOk(mediainfo['languages'], metadata['mediainfo']['languages']):
                    return False
            elif mediainfo[pr] != metadata['mediainfo'][pr]: return False
        return True
    
    def _ageRatingOk(rating):
        order = ['G', 'PG', 'PG-13', 'R', 'NC-17', 'NR']
        if order.indexOf(rating) < order.indexof(metadata['ageRating']): return False

    # TODO add type_backdrop to readme
    type = (metadata['type'] + '_backdrop') if backdrop else metadata['type'] # type if its a backdrop
    for template in templates: # Returns the first matching template
        if 'type' not in template or type in template['type'].split(';'):
            if 'ratings' not in template or _ratingsOk(template['ratings']): 
                if 'mediainfo' not in template or _mediainfoOk(template['mediainfo']):
                    if 'ageRating' not in template or _ageRatingOk(template['ageRating']):
                        if 'productionCompanies' not in template or _companiesOk(template['productionCompanies']):
                            return template['cover']
    
    return 'backdrop' if backdrop or metadata['type'] == 'episode' else 'cover'  # default templates if no custom match found

# Return the task hash stored inside generated images
def getHash(file):
    with open(file, 'rb') as image:
        img = exifImage(image)
        if img.has_exif and 'software' in img.list_all() and 'BetterCovers:' in img['software']:
            return img['software'].split(':')[1]
    return ''

# Stores task hash and datetime inside images exif
def tagImage(file, hash):
    img = False
    with open(file, 'rb') as image:
        img = exifImage(image)

    img["software"] = "BetterCovers:" + hash
    img['datetime_original'] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")

    with open(file, 'wb') as image:
        image.write(img.get_file())

# Return how much time passed since start
def timediff(start):
    return str(timedelta(seconds=round(time.time() - start)))

# Same as getMetadata but for seasons, also gets episode metadata since its get from the same request
def getSeasonMetadata(number, season, showIDS, omdbApi, tmdbApi):
    for ep in season['episodes']: season['episodes'][ep]['productionCompanies'] = season['productionCompanies']
    
    # Get season and episode poster, episodes ratings and TMDBID from TMDB
    def _getTMDB():
        if 'TMDBID' in showIDS:
            if 'TMDBDate' not in season or checkDate(season['TMDBDate'], season['releaseDate']):
                start = time.time()
                res = getJSON('https://api.themoviedb.org/3/tv/' + showIDS['TMDBID'] + '/season/' + str(number) + '?api_key=' + tmdbApi + '&language=en&append_to_response=releases,external_ids,videos,production_companies,images')
                if res:
                    if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']:
                        imgSrc = 'https://image.tmdb.org/t/p/original' + res['poster_path']
                        for img in season['covers']:
                            if img['src'] == imgSrc: break
                        else: season['covers'].append({
                                'src': imgSrc,
                                'height': 0,
                                'language': 'en',
                                'source': 'TMDB'})

                    if 'episodes' in res:
                        rts = []
                        for episode in res['episodes']:
                            episodeNumber = int(episode['episode_number'])
                            if 'episode_number' not in episode or episode['episode_number'] == 'N/A': 
                                continue # Continue if no episode number
                            if episodeNumber not in season['episodes']: 
                                continue # Continue if episode is not in season
                           
                            episodeMetadata = season['episodes'][episodeNumber]
                            if 'still_path' in episode and episode['still_path'] != 'N/A' and episode['still_path']: 
                                imgSrc = 'https://image.tmdb.org/t/p/original' + episode['still_path']
                                for img in episodeMetadata['covers']:
                                    if img['src'] == imgSrc: break
                                else: episodeMetadata['covers'].append({'src': imgSrc, 'height': 0, 'language': 'en', 'source': 'TMDB'})
                            
                            if 'vote_average' in episode and episode['vote_average'] != 'N/A' and 'vote_count' in episode and episode['vote_count'] > minVotes:
                                episodeMetadata['ratings']['TMDB'] = {'icon': 'TMDB', 'value': "%.1f" % float(episode['vote_average'])}
                                rts.append(float(episode['vote_average']))
                            if 'id' in episode: 
                                episodeMetadata['ids']['TMDBID'] = str(episode['id'])
                            if 'air_date' in episode and episode['air_date'] != '':
                                episodeMetadata['releaseDate'] = datetime.strptime(episode['air_date'], '%Y-%m-%d').strftime("%d/%m/%Y")
                        # Set season rating as avergage of all episodes ratings
                        if len(rts) > 0: season['ratings']['TMDB'] = {'icon': 'TMDB', 'value': avg(rts)}
                    
                    if 'air_date' in res and len(res['air_date']) > 0:
                        season['releaseDate'] = datetime.strptime(res['air_date'], '%Y-%m-%d').strftime("%d/%m/%Y")    
                    
                    if 'images' in res:
                        for prop in res['images']:
                            mtProp = prop if prop != 'posters' else 'covers'
                            for image in res['images'][prop]:
                                imgSrc = 'https://image.tmdb.org/t/p/original' + image['file_path']
                                
                                for img in season[mtProp]:
                                    if img['src'] == imgSrc: break
                                else: season[mtProp].append({
                                        'src': imgSrc,
                                        'height': image['height'],
                                        'language': image['iso_639_1'],
                                        'source': 'TMDB'})

                    season['TMDBDate'] = datetime.now().strftime("%d/%m/%Y")
                    
                    log('Finished getting TMDB metadata for: ' + season['title'] + ' in: ' + timediff(start), 1, 3)
                else: log('Error getting info on TMDB for: ' + season['title'], 3, 4)
            else: log('No need to update TMDB metadata for: ' + season['title'], 1, 3)
    
    # Get IMDB ratings and ids for episodes
    def _getOMDB():  
        start = time.time()
        if len(omdbApi) > 0 and 'IMDBID' in showIDS:
            if 'OMDBDate' not in season or checkDate(season['OMDBDate'], season['releaseDate']):
                res = getJSON('http://www.omdbapi.com/?i=' + showIDS['IMDBID'] + '&Season=' + str(number) + '&apikey=' + omdbApi)
                if res and 'Episodes' in res and len(res['Episodes']) > 0: # TODO get more data here
                    rts = []
                    for ep in res['Episodes']:
                        if int(ep['Episode']) not in season['episodes']: continue
                        
                        if 'imdbRating' in ep and ep['imdbRating'] != 'N/A' and float(ep['imdbRating']) > 0: 
                            season['episodes'][int(ep['Episode'])]['ratings']['IMDB'] = {'icon': 'IMDB', 'value': "%.1f" % float(ep['imdbRating'])}
                            rts.append(float(ep['imdbRating']))
                        
                        if 'imdbID' in ep and ep['imdbID'] != 'N/A':
                            season['episodes'][int(ep['Episode'])]['ids']['IMDBID'] = ep['imdbID']
                        
                    season['OMDBDate'] = datetime.now().strftime("%d/%m/%Y")
                    if len(rts) > 0: season['ratings']['IMDB'] = {'icon': 'IMDB', 'value': avg(rts)}
                    log('Finished getting OMDB metadata for: ' + season['title'] + ' in: ' + timediff(start), 1, 3)
                else: log('Error getting info on OMDB for: ' + season['title'], 3, 4)
            else: log('No need to update OMDB metadata for: ' + season['title'], 1, 3)
    
    # Ger RT ratings and certifications for season and episodes
    def _getRT():
        start = time.time()
        if 'RT' in season['URLS']:
            if 'RTDate' not in season or checkDate(season['RTDate'], season['releaseDate']):
                RT = getRTSeasonRatings(season['URLS']['RT'], get)
                if RT['statusCode'] == 200: # Get episodes urls and ratings
                    for ep in RT['episodes']: # Set episodes RT url
                        if ep[0] in season['episodes']: 
                            episode = season['episodes'][ep[0]]
                            episode['URLS']['RT'] = ep[1]
                            if 'RTDate' not in episode or checkDate(episode['RTDate'], season['releaseDate']):
                                start2 = time.time()
                                RTE = getRTEpisodeRatings(ep[1], get)
                                if RTE['statusCode'] == 401:
                                    log('Rotten Tomatoes limit reached!', 3, 1)
                                    break
                                elif RTE['statusCode'] == 200:
                                    for rt in RTE['ratings']: 
                                        episode['ratings'][rt] = RT['ratings'][rt]
                                        log('Found ' + rt + ' rating in RottenTomatoes for: ' + episode['title'] + ' in: ' + timediff(start2), 1, 4)
                                    if len(RTE['ratings']) == 0:
                                        log('No ratings found on RT for: ' + episode['title'], 2, 4)
                                else: log('Error getting episode ratings from RT for: ' + episode['title'], 2, 4)
                            else: log('No need to update RT metadata for: ' + episode['title'], 1, 4)

                    for rt in RT['ratings']: season['ratings'][rt] = RT['ratings'][rt]
                    if 'RT-CF' in RT['certifications']:
                        if 'RT-CF' not in season['certifications']: season['certifications'].append('RT-CF')
                    elif 'RT-CF' in season['certifications']: season['certifications'].remove('RT-CF')
                    
                    season['RTDate'] = datetime.now().strftime("%d/%m/%Y")      
                    log('Finished getting RT metadata for: ' + season['title'] + ' in: ' + timediff(start), 1, 3)
                elif RT['statusCode'] == 403: return log('RottenTomatoes API limit reached!', 3, 1)
                else: log('Error geting metadata from RottenTomatoes: ' + str(RT['statusCode']), 2, 4)            
            else: log('No need to update TMDB metadata for: ' + season['title'], 1, 3)

    # Gets episode and season ratings from TVTime
    def _getTVTime():
        if 'TVTimeDate' not in season or checkDate(season['TVTimeDate'], season['releaseDate']):
            start = time.time()
            success = False
            rts = []
            for episode in season['episodes']:
                if 'TVTime' in season['episodes'][episode]['URLS']:
                    start2 = time.time()
                    rating = getTVTimeEpisodeRating(season['episodes'][episode]['URLS']['TVTime'], get)
                    if rating:
                        season['episodes'][episode]['ratings']['TVTime'] = {'icon': 'TVTime', 'value': rating}
                        rts.append(float(rating))
                        success = True
                        log('Found rating in TvTime for ' + season['episodes'][episode]['title'] + ': ' + rating + ' in: ' + timediff(start2), 0, 4)
                    else: log('Error getting rating in TvTime for: ' + season['episodes'][episode]['title'], 2, 4)
            if success:
                log('Finished getting TVTime metadata for: ' + season['title'] + ' in: ' + timediff(start), 1, 5)
                season['TVTimeDate'] = datetime.now().strftime("%d/%m/%Y")
                season['ratings']['TVTime'] = {'icon': 'TVTime', 'value': avg(rts)}
            else: log('Error getting TVTime metadata for: ' + season['title'], 2, 3)
        else: log('No need to update TVTime metadata for: ' + season['title'], 1, 4)
    
    # Gets ratings from Trakt
    def _getTrakt():
        if 'TMDBID' in season['ids']:
            if 'TraktDate' not in season or checkDate(season['TraktDate'], season['releaseDate']):
                start = time.time()
                rt = getTraktRating(season['ids']['TMDBID'], get)
                if rt:
                    season['ratings']['Trakt'] = {'icon': 'Trakt', 'value': rt}
                    season['TraktDate'] = datetime.now().strftime("%d/%m/%Y")
                    log('Found rating in Trakt for ' + season['title'] + ': ' + rt + ' in: ' + timediff(start), 1, 3)
                else: log('Error getting Trakt ratings for: ' + season['title'], 2, 4)
            else: log('No need to update Trakt metadata for: ' + season['title'], 1, 3)
        
        for ep in season['episodes']:
            eps = season['episodes'][ep]
            if 'TMDBID' in eps['ids']:
                if 'TraktDate' not in eps or checkDate(eps['TraktDate'], season['releaseDate']):
                    start = time.time()
                    rt = getTraktRating(eps['ids']['TMDBID'], get)
                    if rt:
                        eps['ratings']['Trakt'] = {'icon': 'Trakt', 'value': rt}
                        eps['TraktDate'] = datetime.now().strftime("%d/%m/%Y")
                        log('Found rating in Trakt for ' + eps['title'] + ': ' + rt + ' in: ' + timediff(start), 1, 3)
                    else: log('Error getting Trakt ratings for:' + eps['title'], 2, 4)
                else: log('No need to update Trakt metadata for: ' + eps['title'], 1, 3)
        
    tsks = []
    for fn in [_getTMDB, _getOMDB, _getRT, _getTrakt]:
        tsks.append(Thread(target=fn, args=()))
        tsks[-1].start()
    for tsk in tsks: tsk.join()

    season['metadataDate'] = datetime.now().strftime("%d/%m/%Y")

# Returns the average float as a string from a list of numbers
def avg(lst):
    return "%.1f" % (sum([float(vl) for vl in lst]) / len(lst))

# Returns season mediainfo as the most common values of all episodes mediainfo
def getSeasonMediainfo(season, defaultAudioLanguage, mediainfoUpdateInterval):
    start = time.time()
    for ep in season['episodes']: getMediaInfo(season['episodes'][ep], defaultAudioLanguage, mediainfoUpdateInterval)
    
    info = getParentMediainfo(season['episodes'])
    if info: season['mediainfo'] = info

# Returns the parent (episodes > season or seasons > tv) mediainfo as the most common values from the childrens mediainfo 
def getParentMediainfo(childrens):
    res = {}
    for ch in childrens:
        chi = childrens[ch]
        if 'mediainfo' in chi:
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

    return res if res != {} else False

# Returns the most common element of a list
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

# Generates an image from a task
def processTask(task, thread):
    st = time.time()
    # TODO image generation
    try:
        with open(join(workDirectory, 'media', 'templates', task['template'] + '.html')) as html:
            HTML = html.read()
    except:
        log('Error opening: ' + join(workDirectory, 'media', 'templates', task['template'] + '.html'), 3, 1)
        return False

    rts = ''
    minfo = ''
    pcs = ''
    cert = ''

    for rt in sorted(task['ratings'].keys(), key=lambda v: ratingsOrder.index(v)): # Creates ratings html
        rts += "<div class = 'ratingContainer ratings-" + rt + "'><img src= '" + join('..', 'media', 'ratings', task['ratings'][rt]['icon'] + '.png') + "' class='ratingIcon'/><label class='ratingText'>" + task['ratings'][rt]['value'].replace('10.0', '10') + "</label></div>\n\t\t"
    for mi in sorted(task['mediainfo'].keys(), key=lambda v: mediainfoOrder.index(v)): # Creates mediainfo html
        pt = join('..', 'media', 'mediainfo' if mi != 'languages' else 'languages', task['mediainfo'][mi] + '.png')
        minfo += "<div class='mediainfoImgContainer mediainfo-" + task['mediainfo'][mi] + "'><img src= '" + pt + "' class='mediainfoIcon'></div>\n\t\t\t"  
    for pc in task['productionCompanies']: # Creates productin companies html
        pcs += "<div class='pcWrapper producionCompany-" + str(pc['id']) +  "'><img src='" + pc['logo'] + "' class='producionCompany'/></div>\n\t\t\t\t"
    for cr in task['certifications']: # Creates certifications html
        cert += '<img src= "' + join('..', 'media', 'ratings', cr + '.png') + '" class="certification"/>'

    if 'ageRating' in task: # Grabs age ratings svg file
        with open(join(workDirectory, 'media', 'ageRatings', task['ageRating'] + '.svg'), 'r') as svg:
            HTML = HTML.replace('<!--AGERATING-->', svg.read())
    
    # Replace generated code for tags inside template
    HTML = HTML.replace('$IMGSRC', task['image']) # TODO fix for image generation here
    HTML = HTML.replace('<!--TITLE-->', task['title'])
    HTML = HTML.replace('<!--RATINGS-->', rts)
    HTML = HTML.replace('<!--MEDIAINFO-->', minfo)
    HTML = HTML.replace('<!--PRODUCTIONCOMPANIES-->', pcs)
    HTML = HTML.replace('<!--CERTIFICATIONS-->', cert)

    # Write new html file to disk
    with open(join(workDirectory, 'threads', thread + '.html'), 'w') as out:
        out.write(HTML)

    # Get task hash
    tskCopy = deepcopy(task)
    del tskCopy['out']
    hash = md5(json.dumps(tskCopy, sort_keys=True).encode('utf8')).hexdigest()

    # Generate image
    i = 0
    command = wkhtmltoimage + ' --cache-dir "' + join(workDirectory, 'cache') + '" --enable-local-file-access  "file://' + join(workDirectory, 'threads', thread + '.html') + '" "' + join(workDirectory, 'threads', thread + '.jpg') + '"'
    out = getstatusoutput(command)
    if out[0] == 0:
        tagImage(join(workDirectory, 'threads', thread + '.jpg'), hash)
        for fl in task['out']:
            cm = call(['cp', '-f', join(workDirectory, 'threads', thread + '.jpg'), fl])
            if cm != 0:
                log('Error moving to: ' + fl, 3, 1)
                return False  
        log('Succesfully generated ' + ('cover' if task['type'] != 'backdrop' else 'backdrop') + ' image for: ' + task['title'] + ' in ' + str(round(time.time() - st)) + 's', 0, 1)
        return True 
    else: log('Error generating image with wkhtmltoimage for: ' + task['title'], 3, 1)
    log('Error generating image for: ' + task['title'], 3, 1)
    return False

# Generates metadata entry for new folder
def scannFolder(folder):
    metadata = {
        'URLS': {},
        'trailers': [],
        'releaseDate': datetime.now().strftime("%d/%m/%Y"),
        'ratings': {},
        'productionCompanies': [],
        'path': folder,
        'logos': [],
        'ids': {},
        'covers': [],
        'certifications': [],
        'backdrops': [],
        'ageRating': 'NR'
        }
    
    mediaFiles = getMediaFiles(folder) # finds media files inside folder
    metadata['title'], metadata['year'] = getName(folder) # Parse title and year from folder
    if len(mediaFiles) == 0: metadata['type'] = 'tv'
    else: 
        metadata['type'] = 'movie' # Movie
        metadata['path'] = mediaFiles[0]
    metadata['releaseDate'] = datetime.now().strftime("%m/%d/%Y") # If release date is not found use date added for calculating metadata update

    # Get info from NFO
    nfo = join(folder, 'tvshow.nfo') if metadata['type'] == 'tv' else (mediaFiles[0].rpartition('.')[0] + '.nfo') if len(mediaFiles) > 0 else join(folder, 'FALSE')
    if exists(nfo): metadata['ids'] = readNFO(nfo) # Gets ids from NFO file if exists

    metadata['ids'] = {}
    # Get IMDBID from title
    imdbid = findall('imdbid=(tt\d+)', metadata['path'])
    if len(imdbid) == 1: 
        metadata['ids']['IMDBID'] = imdbid[0]
    # Get TMDBID from title
    tmdbid = findall('tmdbid=(\d+)', metadata['path'])
    if len(tmdbid) == 1: 
        metadata['ids']['TMDBID'] = tmdbid[0]

    return metadata

# Custom requests.get implementation with progressive random delay, retries and error catching
def get(url, headers = {}):
    ret = requests.Response()
    site = url.split('/')[2]
    delay = 0 
    n = 0
    while n < 3:
        try:
            rq = requests.get(url, headers=headers)
            if rq.status_code == 200: return rq
            elif rq.status_code == 401:
                log('Api limit reached for: ' + site, 3, 2)
                return rq
            elif rq.status_code == 404:
                log('Resource not found in: ' + url, 2, 3)
                return rq
            else: log('Error accessing ' + site + ' (' + str(rq.status_code) + ')', 3 if n == 2 else 2, 3 if n == 2 else 4)
        except requests.exceptions.ConnectionError:
            ret.status_code = 401
            log('Too many requests to: ' + site + ', try lowering amount of workers!', 3, 3)
        except: 
            log('Unknown error trying to access: ' + url, 3, 2)
            ret.status_code = 777
        
        delay += 5 + random() * 5 # 5 to 10 seconds
        n += 1
    return ret





