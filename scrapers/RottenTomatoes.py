from requests import get
import json
from re import findall
from urllib.parse import quote

SEARCH_URL = 'https://www.rottentomatoes.com/api/private/v2.0/search?q='
BASE_URL = 'https://www.rottentomatoes.com'

def searchRT(type, title, year = False):
    rq = get(SEARCH_URL + title.lower().replace(' ', '+'))
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
            if title.lower() == mv[dictTitle[type]].lower() and (not year or int(year) == mv[dictYear[type]]):
                mt = findall('\/' + dictUrl[type] + '\/[^/]+', mv['url'])
                return mt[0] if len(mt) == 1 else False
    return False

def _getTvRatings(text):
    res = {'ratings': {}, }
    RT = findall('tomatometer-container[^%]*tomatometer[^\d]*(\d+)%', text)
    RTCF = findall('tomatometer-container[^%]*certified_fresh', text)
    RTA = findall('audience-score-container[^%]*audience-score[^\d]*(\d+)%', text)
    res['certifications'] = ['RT-CF'] if len(RTCF) > 0 else []
    if len(RT) > 0: res['ratings']['RT'] = {'icon': 'RT-CF' if len(RTCF) > 0 else 'RT' if int(RT[0]) >= 60 else 'RT-LS', 'value': str(int(RT[0]) / 10).replace('.0', '')} 
    if len(RTA) > 0: res['ratings']['RTA'] = {'icon': 'RTA' if int(RTA[0]) >= 60 else 'RTA-LS', 'value': str(int(RTA[0]) / 10).replace('.0', '')} 
    return res

def getRTTvRatings(url):
    if not url: return False
    rq = get(BASE_URL + url)
    if rq.status_code != 200: return False
    
    ret = {'seasons': {}}
    rt = _getTvRatings(rq.text)
    ret['ratings'] = rt['ratings']
    ret['certifications'] = rt['certifications']
    for sn in findall('(' + url.replace('/', '\/') + '\/s0*(\d+))"', rq.text):
        ret['seasons'][sn[1]] = sn[0]
    
    return ret

def getRTSeasonRatings(url):
    rq = get(BASE_URL + url)
    if rq.status_code != 200: return False
    
    ret = {'episodes': {}}
    rt = _getTvRatings(rq.text)
    ret['ratings'] = rt['ratings']
    ret['certifications'] = rt['certifications']
    for sn in findall('(' + url.replace('/', '\/') + '\/e0*(\d+))"', rq.text):
        ret['episodes'][sn[1]] = sn[0]
    
    return ret

def getRTEpisodeRatings(url):
    rq = get(BASE_URL + url)
    if rq.status_code != 200: return False
    return _getTvRatings(rq.text)

def getRTMovieRatings(url):
    if not url: return False
    rq = get(BASE_URL + url)
    if rq.status_code != 200: return False
    sc = findall('<score-board[^>]*>', rq.text)
    if len(sc) == 0: return False
    res = {'ratings': {}}
    rt = findall('tomatometerscore="(\d+)"', sc[0])
    if len(rt) == 1: res['ratings']['RT'] = {'icon': 'RT-CF' if 'certified-fresh' in sc[0] else 'RT' if int(rt[0]) >= 60 else 'RT-LS', 'value': str(int(rt[0]) / 10).replace('.0', '')}
    res['certifications'] = ['RT-CF'] if 'certified-fresh' in sc[0] else []
    rta = findall('audiencescore="(\d+)"', sc[0])
    if len(rta) == 1: res['ratings']['RTA'] = {'icon': 'RTA' if int(rta[0]) >= 60 else 'RTA-LS', 'value': str(int(rta[0]) / 10).replace('.0', '')} 
    
    return res