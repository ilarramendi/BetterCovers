import time
import sys
import requests
import json

from threading import Lock, Thread
from re import findall
from random import random
from os.path import join
from math import sqrt
from glob import glob
from datetime import datetime, timedelta

logLevel = 2
showColor = True

logLock = Lock()
wkhtmltoimage = ''
mediaExtensions = ['mkv', 'mp4', 'avi', 'm2ts'] # Type of extensions to look for media files
workDirectory = ''

# Returns all media files inside a folder except for trailers
def getMediaFiles(folder):
    mediaFiles = []
    for ex in mediaExtensions: 
        mediaFiles += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex))
    return[fl for fl in mediaFiles if 'trailer' not in fl]

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
def checkDate(lastUpdate, releaseDate):
    return (datetime.now() - lastUpdate) >= timedelta(days=getUpdateInterval(releaseDate))

# Returns an update interval, interval increases based on how old is the media
# Change release date on new episode release
def getUpdateInterval(releaseDate):
    return min(120, sqrt(max((datetime.now() - releaseDate).days, 0) * 4 + 1)) # 0 to 120 days

# Logs to file and STDOUT with a specific level and color
def log(text, type, level): # 0 = Success, 1 = Normal, 2 = Warning, 3 = Error
    if level <= logLevel:
        print((datetime.now().strftime("[%m/%d/%Y %H:%M:%S] --> ") if logLevel > 2 else '') + (['\033[92m', '\033[37m', '\033[93m', '\033[91m'][type] if showColor else '') + text + '\033[0m')
        with open(join(workDirectory, 'BetterCovers.log'), 'a') as log:
            log.write('[' + ['Info   ', 'Error  ', 'Success', 'Warning'][type] + datetime.now().strftime("][%m/%d/%Y %H:%M:%S] --> ") + text + '\n')

# returns a tuple of the name and year from file, if year its not found returns false in year
def getName(folder):
    fl = (folder[:-1] if folder[-1] == '/' else folder).rpartition('/')[2]

    inf = findall("(?:^([^(]+) \(?(\d{4})\)?)|(^[^[\(]+)", fl)
    if len(inf) == 1: 
        if inf[0][2] == '':
            return [inf[0][0].translate({'.': ' ', '_': ' '}), int(inf[0][1])]
        else: return [inf[0][2].translate({'.': ' ', '_': ' '}), None]
    else:
        log('Name not found for: ' + fl, 3, 1)
        return [None, None]

#Makes a https request to a url and returns a JSON object if successfull
def getJSON(url, headers = {}):
    response = get(url, headers = headers)

    if 'application/json' in response.headers.get('content-type'):
        try:
            return response.json()
        except Exception as ex: log('Error parsing JSON from response:\n' + response.text, 1, 1)
    return False

# Return how much time passed since start
def timediff(start):
    return str(timedelta(seconds=round(time.time() - start)))

# Returns the average float as a string from a list of numbers
def avg(lst):
    return "%.1f" % (sum([float(vl) for vl in lst]) / len(lst))

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