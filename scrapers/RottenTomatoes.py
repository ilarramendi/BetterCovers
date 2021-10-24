from requests import get
import json
from re import findall
from urllib.parse import quote
from time import sleep

SEARCH_URL = 'https://www.rottentomatoes.com/api/private/v2.0/search?q='
BASE_URL = 'https://www.rottentomatoes.com'

# TODO replace search url with scrapping because of api limits
# Searches in rottentomatoes by title and returns an url
def searchRT(type, title, year):
    rq = get(SEARCH_URL + title.lower().replace(' ', '+'))
    if rq.status_code == 403: print('Rotten tomatoes api limit reached!')
    sleep(2) # RT gets angry
    if rq.status_code != 200: return False
    try:
        rs = rq.json()
    except:
        return False  
    dictType = {'movie': 'movies', 'tv': 'tvSeries'}
    dictTitle = {'movie': 'name', 'tv': 'title'}
    dictYear = {'movie': 'year', 'tv': 'startYear'}
    dictUrl = {'movie': 'm', 'tv': 'tv'}

    if dictType[type] in rs:
        for mv in rs[dictType[type]]:
            if title.lower() == mv[dictTitle[type]].lower() and (not year or not mv[dictYear[type]] or abs(year - mv[dictYear[type]]) <= 1):
                rt = findall('\/' + dictUrl[type] + '\/[^/]+', mv['url'])
                if len(rt) == 1: return rt[0].replace('_', '-')
    return False

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

def getRTTVRatings(url):
    rq = get(BASE_URL + url)
    res = {'ratings': {}, 'certifications': [], 'statusCode': rq.status_code, 'seasons': {}}
    sleep(2) # RT gets angry
    if rq.status_code != 200: return res
    
    tmp = _parseTvRatings(rq.text)
    res['ratings'] = tmp['ratings']
    res['certifications'] = tmp['certifications']

    for sn in findall('(' + url.replace('/', '\/') + '\/s(\d{1,3}))"', rq.text): # Gets url for each season
        res['seasons'][int(sn[1])] = sn[0]
    
    return res

def getRTSeasonRatings(url):
    rq = get(BASE_URL + url)
    ret = {'statusCode': rq.status_code, 'episodes': {}}
    sleep(2) # RT gets angry
    if rq.status_code == 200:
        rt = _parseTvRatings(rq.text)
        ret['ratings'] = rt['ratings']
        ret['certifications'] = rt['certifications']
        eps = findall('href="' + url.rpartition('/')[2] + '(\/e(\d{1,3}))">View Details', rq.text)
        for ep in eps[:int(len(eps)/2)]: ret['episodes'][int(ep[1])] = url + ep[0] # Grab half of the results
            
    
    return ret

def getRTEpisodeRatings(url):
    rq = get(BASE_URL + url)
    sleep(1) # RT gets angry
    return {'statusCode': rq.status_code, 'ratings': _parseTvRatings(rq.text)['ratings'] if rq.status_code == 200 else {}}
    
def getRTMovieRatings(url):
    rq = get(BASE_URL + url)
    res = {'ratings': {}, 'certifications': [], 'statusCode': rq.status_code}
    sleep(2) # RT gets angry
    if rq.status_code != 200: return res
    sc = findall('<score-board[^>]*>', rq.text)
    if len(sc) == 0: return res
    
    if 'certified-fresh' in sc[0]: res['certifications'] = ['RT-CF'] # Certified fresh

    rt = findall('tomatometerscore="(\d+)"', sc[0])
    # Sets icon to RT-CF, RT, or RT-LS acording to value
    if len(rt) == 1: 
        res['ratings']['RT'] = {'icon': 'RT-CF' if len(res['certifications']) > 0 else 'RT' if int(rt[0]) >= 60 else 'RT-LS', 'value': str(float(rt[0]) / 10).replace('.0', '')}
    rta = findall('audiencescore="(\d+)"', sc[0])
    if len(rta) == 1: 
        res['ratings']['RTA'] = {'icon': 'RTA' if int(rta[0]) >= 60 else 'RTA-LS', 'value': str(float(rta[0]) / 10).replace('.0', '')} 
    return res