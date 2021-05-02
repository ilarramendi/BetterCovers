from requests import get
from re import findall
import json
from urllib.parse import quote


def getUrl(type, title, year = False):
    rq = get('https://www.moviemania.io/phone/search?q=' + quote(title))
    if rq.status_code != 200: return False
    for sp in rq.text.split('section-title'):
        if '>' + type + '<' in sp:
            for it in sp.split('item'): 
                tl = findall('"title">([^<]+)', it)
                yr = findall('"year">(\d+)', it)
                url = findall('href="([^"]*)"', it)
                if len(tl) == 1 and len(url) == 1 and title.lower() == tl[0].lower() and (not year or len(yr) != 1 or year == yr[0]):
                    return 'https://www.moviemania.io' + url[0]
    return False

def getTextlessPosters(url):
    rq = get(url)
    if rq.status_code != 200 or len(rq.history) != 1 or rq.history[0].status_code != 301: return False
    res = []
    for ps in findall('"(\/wallpaper\/[^"]*)"', rq.text):
        res.append('https://www.moviemania.io/download/' + ps.partition('-')[0].rpartition('/')[2] + '/720x1280' )
    return res

def getTextlessPostersByName(type, name, year = False):
    url = getUrl(type, name, year)
    return url and getPosters(url) 
