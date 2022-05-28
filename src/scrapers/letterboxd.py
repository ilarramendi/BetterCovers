from re import findall
from jellyfish import jaro_distance

from src.functions import get

BASE_URL = 'https://letterboxd.com' 

def searchLB(IMDBID, title, year):
    max = 0
    link = ''
    rq = get(BASE_URL + '/search/' + (IMDBID if IMDBID else title.lower().replace(' ', '+')))
    if rq.status_code == 200:
        for movie in findall(r'film-title-wrapper">[^>]*"(\/film\/[^"]+)">([^<]+)<[^<]+<[^<]+>([\d\.]+)', rq.text):
            if IMDBID:
                return movie[0]
            elif not year or abs(year - int(movie[2])) <= 1:
                dist = jaro_distance(movie[1].strip().lower(), title.lower())
                if dist > max:
                    max = dist
                    link = movie[0]

    return link if max > 0.85 else False

def getLBRatings(url):
    rq = get(BASE_URL + '/csi' + url + 'rating-histogram/')
    if rq.status_code == 200:
        rt = findall(r'Weighted average of ([\d\.]+)', rq.text)
        if len(rt) == 1:
            if rt: 
                value = "%.1f" % (float(rt[0]) * 2)
                return {'icon': 'LB', 'value': value if value != '10.0' else '10'}
    
    return False