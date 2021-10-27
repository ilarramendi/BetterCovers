from requests import get
from re import findall
import json

BASE_URL = 'https://letterboxd.com' 

def searchLB(IMDBID, title, year):
    rq = get(BASE_URL + '/search/' + (IMDBID if IMDBID else title.lower().replace(' ', '+')))
    if rq.status_code == 200:
        for movie in findall('film-title-wrapper">[^>]*"(\/film\/[^"]+)">([^<]+)<[^<]+<[^<]+>([\d\.]+)', rq.text):
            if IMDBID: return movie[0]
            elif movie[1].strip().lower() == title.lower() and (not year or abs(year - int(movie[2])) <= 1):
                return movie[0]
        

    return False

def getLBRatings(url):
    rq = get(BASE_URL + '/csi' + url + 'rating-histogram/')
    if rq.status_code == 200:
        rt = findall('Weighted average of ([\d\.]+)', rq.text)
        if len(rt) == 1:
            if rt: return {'icon': 'LB', 'value': ("%.1f" % (float(rt[0]) * 2)).replace('.0', '')}
    
    return False