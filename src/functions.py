import urllib.request
import sys
import requests
import json
from time import time
from threading import Thread
from subprocess import call, getstatusoutput, DEVNULL
from re import findall
from random import random
from os.path import join, exists
from math import sqrt
from jellyfish import jaro_distance
from glob import glob
from exif import Image as exifImage
from datetime import datetime, timedelta
from base64 import b64decode

logLevel = 2
showColor = True

logFile = '' # Used for logging
imageCache = ''

# Returns all media files inside a folder except for trailers
def getMediaFiles(folder, mediaExtensions):
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
        colors = ['\033[92m', '\033[37m', '\033[93m', '\033[91m']
        typestr = f"[{['SUCCESS', 'INFO   ', 'WARNING', 'ERROR  '][type]}]" 

        print(f"[{datetime.now().strftime('%m/%d/%Y %H:%M:%S')}]{colors[type] if showColor else typestr} --> {text}\033[0m")
        with open(logFile, 'a') as log:
            log.write(f"{typestr}[{datetime.now().strftime('%m/%d/%Y %H:%M:%S')}] --> {text}\n")

# returns a tuple of the name and year from file, if year its not found returns false in year
def getName(folder):
    fl = (folder[:-1] if folder[-1] == '/' else folder).rpartition('/')[2]

    inf = findall("(?:^([^(]+) \(?(\d{4})\)?)|(^[^[\(]+)", fl)
    if len(inf) == 1: 
        if inf[0][2] == '':
            return [inf[0][0].translate({'.': ' ', '_': ' '}), int(inf[0][1])]
        else: return [inf[0][2].translate({'.': ' ', '_': ' '}), None]
    else:
        log(f"Name not found for: {fl}", 3, 1)
        return [None, None]

#Makes a https request to a url and returns a JSON object if successfull
def getJSON(url, headers = {}):
    response = get(url, headers = headers)

    if 'application/json' in response.headers.get('content-type'):
        try:
            return response.json()
        except Exception as ex: log(f"Error parsing JSON from response:\n{response.text}", 1, 1)
    return False

# Return how much time passed since start
def timediff(start, seconds=True):
    sec = time() - start
    return "{:.2f}".format(sec) if seconds else timedelta(seconds=round(sec))

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

# Process metadata
def process(metadata, template, thread, workDirectory, chromium, image, languagesOrder, size):
    if not template: return False
    
    st = time()
    try:
        with open(join(workDirectory, 'templates', template["template"])) as html:
            HTML = html.read()
    except:
        log('Error opening: ' + join(workDirectory, 'templates', template["template"]), 3, 1)
        return False
    
    for rt in metadata.ratings:
        HTML = HTML.replace(f"<!--{rt}-->", f"<div class='ratingContainer {rt} {metadata.ratings[rt]['icon']}'><img src='../assets/ratings/{metadata.ratings[rt]['icon']}.png' class='ratingIcon'/><label class='ratingText'>{metadata.ratings[rt]['value']}</label></div>")
    
    UHDHDR = ('UHD-HDR' not in template or template['UHD-HDR']) and metadata.media_info.color == 'HDR' or metadata.media_info.resolution == 'UHD'
    for mi in ['source', 'color', 'codec', 'resolution']:
        value = getattr(metadata.media_info, mi)
        if UHDHDR:
            value = 'UHD-HDR' if mi == 'color' else False if mi == 'resolution' else value

        if value: 
            HTML = HTML.replace(f"<!--{mi}-->", f"<div class='mediaInfoImgContainer {mi} {value}'><img src='../assets/mediainfo/{value}.png' class='mediainfoIcon'></div>")
    for language in languagesOrder:
        if language in metadata.media_info.languages:
            HTML = HTML.replace(f"<!--language-->", f"<div class='mediaInfoImgContainer language {language}'><img src='../assets/language/{language}.png' class='mediainfoIcon'></div>")
            break
    
    pcs = ''
    for pc in metadata.production_companies:
        pcs += f"<img src='{pc['logo']}' class='producionCompany PC_{pc['id']}'/>\n\t\t\t\t"
    HTML = HTML.replace('<!--PRODUCTIONCOMPANIES-->', pcs)
    
    for cr in metadata.certifications:
        HTML = HTML.replace(f"<!--{cr}-->", f"<img src='../assets/certifications/{cr}.png' class='certification' />")

    try:
        with open(join(workDirectory, 'assets/ageRatings', metadata.age_rating + '.svg'), 'r') as svg:
            HTML = HTML.replace('<!--AGERATING-->', svg.read())
    except:
        log(f"missing assets/ageRatings/{metadata.age_rating}.svg", 3, 1)
    
    HTML = HTML.replace('$IMGSRC', image) # TODO fix for image generation here
    HTML = HTML.replace('<!--TITLE-->', metadata.title)

    # Write new html file to disk
    with open(join(workDirectory, 'threads', thread + '.html'), 'w') as out:
        out.write(HTML)

    # Generate image
    i = 0
    imgSrc = join(workDirectory, 'threads', thread) + '.jpg'

    command = [chromium, '--headless', '--no-sandbox', '--disable-gpu', f"{join(workDirectory, 'threads', thread)}.html", f"--screenshot={imgSrc}", f"--window-size={size}"]
    out = call(command, stdout=DEVNULL, stderr=DEVNULL) # 
    if out == 0:
        # Tag image
        #with open(imgSrc, 'rb') as image: img = exifImage(image)
        # img["software"] = f"BetterCovers: {metadata.hash}" # TODO fix
        #img["datetime_original"] = str(datetime.now())
        #with open(imgSrc, 'wb') as image: image.write(img.get_file())
        # Copy to final location
        for fl in template["out"]:
            out = f"{metadata.folder}/{fl.replace('$NAME', metadata.path.rpartition('/')[2].rpartition('.')[0])}"
            if call(['cp', '-f', imgSrc, out]) != 0:
                log(f"Error moving to: {out}", 3, 1)
                return False

        return True
    else: log(f"Error generating image for: {metadata.title}, {out}", 3, 1)

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
                log(f"Api limit reached for: {site}", 3, 2)
                return rq
            elif rq.status_code == 404:
                log(f"Resource not found in: {url}", 2, 3)
                return rq
            else: log(f"Error accessing {site} ({rq.status_code})", 3 if n == 2 else 2, 3 if n == 2 else 4)
        except requests.exceptions.ConnectionError:
            ret.status_code = 401
            log(f"Too many requests to: {site}, try lowering amount of workers!", 3, 3) # TODO change this
        except: 
            log(f"Unknown error trying to access: {url}", 3, 2)
            ret.status_code = 777
        
        delay += 5 + random() * 5 # 5 to 10 seconds
        n += 1
    return ret

def getImage(name):
    out = f"{imageCache}/{name.decode('ascii')}.jpg"
    if not exists(out):
        urllib.request.urlretrieve(b64decode(name).decode('ascii'), out) # TODO retry if fails
    return out