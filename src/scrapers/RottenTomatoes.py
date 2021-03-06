import json
from re import findall
from urllib.parse import quote
from time import sleep
from jellyfish import jaro_distance

BASE_URL = 'https://www.rottentomatoes.com'
SEARCH_URL = f'{BASE_URL}/api/private/v2.0/search?q='

from src.functions import getJSON, get

# Searches in rottentomatoes by title and returns an url
def searchRT(type, title, year):
    dictType = {'movie': 'movies', 'tv': 'tvSeries'}
    dictTitle = {'movie': 'name', 'tv': 'title'}
    dictYear = {'movie': 'year', 'tv': 'startYear'}
    dictUrl = {'movie': 'm', 'tv': 'tv'}

    rq = getJSON(SEARCH_URL + title.lower().replace(' ', '+'))
    if rq:
        max = 0
        maxUrl = ''
        for media in rq[dictType[type]]:
            dist = jaro_distance(title.lower(), media[dictTitle[type]].lower())
            if max < dist:
                max = dist
                maxUrl = media['url']
    
        if max > 0.85: return maxUrl # Treshold to match name
    return False

# Internal function to parse ratings from page content
def _parseTvRatings(text):
    res = {'ratings': {}, 'certifications': []}
    RT = findall('tomatometer-container[^%]*tomatometer[^\d]*(\d+)%', text)
    RTCF = findall('tomatometer-container[^%]*certified_fresh', text)
    RTA = findall('audience-score-container[^%]*audience-score[^\d]*(\d+)%', text)
    if len(RTCF) > 0: res['certifications'] = ['RT-CF']
    if len(RT) > 0: 
        res['ratings']['RT'] = {'icon': 'RT-CF' if len(RTCF) > 0 else 'RT' if int(RT[0]) >= 60 else 'RT-LS', 'value': str(int(RT[0]) / 10).replace('.0', '')} 
    if len(RTA) > 0: 
        res['ratings']['RTA'] = {'icon': 'RTA' if int(RTA[0]) >= 60 else 'RTA-LS', 'value': str(int(RTA[0]) / 10).replace('.0', '')} 
    return res

# Scraps ratings for show and gets seasons urls
def getRTTVRatings(url):
    rq = get(BASE_URL + url)
    res = {'ratings': {}, 'certifications': [], 'statusCode': rq.status_code, 'seasons': {}}
    sleep(1) # RT gets angry
    if rq.status_code != 200: return res
    
    tmp = _parseTvRatings(rq.text)
    res['ratings'] = tmp['ratings']
    res['certifications'] = tmp['certifications']

    for sn in findall('(' + url.replace('/', '\/') + '\/s(\d{1,3}))"', rq.text): # Gets url for each season
        res['seasons'][int(sn[1])] = sn[0]
    
    return res

def getRTSeasonRatings(url):
    ret = {}
    rq = get(BASE_URL + url)
    ret['statusCode'] = rq.status_code

    if ret['statusCode'] == 200:
        rt = _parseTvRatings(rq.text)
        ret['ratings'] = rt['ratings']
        ret['certifications'] = rt['certifications']
    
        rq = get(BASE_URL + '/napi' + url + '/episodes')
        if rq.status_code == 200:
            ret['episodes'] = [(int(ep['episodeNumber']), url + '/' + ep['vanityUrl'].rpartition('/')[2]) for ep in json.loads(rq.text)]
        else: ret['statusCode'] = rq.status_code
        
    return ret

def getRTEpisodeRatings(url):
    rq = get(BASE_URL + url)
    sleep(1) # RT gets angry
    return {'statusCode': rq.status_code, 'ratings': _parseTvRatings(rq.text)['ratings'] if rq.status_code == 200 else {}}

def getRTMovieRatings(url):
    rq = get(BASE_URL + url)
    res = {'ratings': {}, 'certifications': [], 'statusCode': rq.status_code}
    sleep(1) # RT gets angry :)
    if rq.status_code != 200: return res
    sc = findall(r'<score-board[^>]*>', rq.text)
    if len(sc) == 0: return res
    
    if 'certified-fresh' in sc[0]: res['certifications'] = ['RT-CF'] # Certified fresh

    rt = findall(r'tomatometerscore="(\d+)"', sc[0])
    # Sets icon to RT-CF, RT, or RT-LS acording to value
    if len(rt) == 1: 
        res['ratings']['RT'] = {'icon': 'RT-CF' if len(res['certifications']) > 0 else 'RT' if int(rt[0]) >= 60 else 'RT-LS', 'value': "%.1f" % (float(rt[0]) / 10)}
    rta = findall(r'audiencescore="(\d+)"', sc[0])
    if len(rta) == 1: 
        res['ratings']['RTA'] = {'icon': 'RTA' if int(rta[0]) >= 60 else 'RTA-LS', 'value': "%.1f" % (float(rta[0]) / 10)} 
    
    for rating in res['ratings']:
        if res['ratings'][rating]['value'] == '10.0': res['ratings'][rating]['value'] = '10'
    return res