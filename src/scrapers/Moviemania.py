from re import findall
import json
from urllib.parse import quote

# TODO rework or discard, page is kinda ok

def getUrl(type, title, year = False):
    rq = get('https://www.moviemania.io/phone/search?q=' + quote(title))
    if rq.status_code != 200: return False
    for sp in rq.text.split('section-title'):
        if '>' + type + '<' in sp:
            for it in sp.split('item'): 
                tl = findall(r'"title">([^<]+)', it)
                yr = findall(r'"year">(\d+)', it)
                url = findall(r'href="([^"]*)"', it)
                if len(tl) == 1 and len(url) == 1 and title.lower() == tl[0].lower() and (not year or len(yr) != 1 or abs(year - yr[0]) <= 1):
                    return 'https://www.moviemania.io' + url[0]
    return False

def getTextlessPosters(url):
    rq = get(url)
    if rq.status_code != 200 or len(rq.history) != 1 or rq.history[0].status_code != 301: return False
    res = []
    for ps in findall(r'"(\/wallpaper\/[^"]*)"', rq.text):
        res.append('https://www.moviemania.io/download/' + ps.partition('-')[0].rpartition('/')[2] + '/720x1280' )
    return res

def getTextlessPostersByName(type, name, year = False):
    url = getUrl(type, name, year)
    return url and getPosters(url) 
