from requests import get
import json
from re import findall
from urllib.parse import quote

SEARCH_URL = 'https://www.rottentomatoes.com/api/private/v2.0/search?q='
BASE_URL = 'https://www.rottentomatoes.com'

def searchRT(mt):
    rq = get(SEARCH_URL + mt['title'].lower().replace(' ', '+'))
    if rq.status_code == 403: print('Rotten tomatoes api limit reached!')
    if rq.status_code != 200: return False
    try:
        rs = rq.json()
    except:
        return False  
    dictType = {'movie': 'movies', 'tv': 'tvSeries'}
    dictTitle = {'movie': 'name', 'tv': 'title'}
    dictYear = {'movie': 'year', 'tv': 'startYear'}
    dictUrl = {'movie': 'm', 'tv': 'tv'}

    if dictType[mt['type']] in rs:
        for mv in rs[dictType[mt['type']]]:
            if mt['title'].lower() == mv[dictTitle[mt['type']]].lower() and (not mt['year'] or not mv[dictYear[mt['type']]] or abs(int(mt['year']) - mv[dictYear[mt['type']]]) <= 1):
                rt = findall('\/' + dictUrl[mt['type']] + '\/[^/]+', mv['url'])
                if len(rt) == 1: mt['urls']['RT'] = rt[0]
                return len(rt) == 1
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

def getRTTVRatings(mt):
    rq = get(BASE_URL + mt['urls']['RT'])
    if rq.status_code == 403: print('Rotten tomatoes api limit reached!')
    if rq.status_code != 200: return
    
    ret = {'seasons': {}}
    rt = _getTvRatings(rq.text)
    for rtg in rt['ratings']: mt['ratings'][rtg] = rt['ratings'][rtg]
    
    for ct in rt['certifications']:
        if ct not in mt['certifications']: mt['certifications'].append(ct)
    for sn in findall('(' + mt['urls']['RT'].replace('/', '\/') + '\/s0*(\d+))"', rq.text):
        if sn[1] in mt['seasons']: mt['seasons'][sn[1]]['urls']['RT'] = sn[0]

def getRTSeasonRatings(mt):
    rq = get(BASE_URL + mt['urls']['RT'])
    if rq.status_code == 403: print('Rotten tomatoes api limit reached!')
    if rq.status_code != 200: return False
    
    ret = {'episodes': {}}
    rt = _getTvRatings(rq.text)
    for rtg in rt['ratings']: mt['ratings'][rtg] = rt['ratings'][rtg]
    for cf in rt['certifications']: 
        if cf not in mt['certifications']: mt['certifications'].append(cf)

    for sn in findall('(' + mt['urls']['RT'].replace('/', '\/') + '\/e0*(\d+))"', rq.text):
        if sn[1] in mt['episodes']: mt['episodes'][sn[1]]['urls']['RT'] = sn[0]
 
    return True

def getRTEpisodeRatings(mt):
    rq = get(BASE_URL + mt['urls']['RT'])
    if rq.status_code == 403: print('Rotten tomatoes api limit reached!')
    if rq.status_code != 200: return
    rts = _getTvRatings(rq.text)
    for rt in rts: mt['ratings'][rt] = rts['ratings'][rt]

def getRTMovieRatings(mt):
    rq = get(BASE_URL + mt['urls']['RT'])
    if rq.status_code == 403: print('Rotten tomatoes api limit reached!')
    if rq.status_code != 200: return
    sc = findall('<score-board[^>]*>', rq.text)
    if len(sc) == 0: return
    res = {'ratings': {}}
    rt = findall('tomatometerscore="(\d+)"', sc[0])
    if len(rt) == 1: mt['ratings']['RT'] = {'icon': 'RT-CF' if 'certified-fresh' in sc[0] else 'RT' if int(rt[0]) >= 60 else 'RT-LS', 'value': str(float(rt[0]) / 10).replace('.0', '')}
    res['certifications'] = ['RT-CF'] if 'certified-fresh' in sc[0] else []
    rta = findall('audiencescore="(\d+)"', sc[0])
    if len(rta) == 1: mt['ratings']['RTA'] = {'icon': 'RTA' if int(rta[0]) >= 60 else 'RTA-LS', 'value': str(float(rta[0]) / 10).replace('.0', '')} 