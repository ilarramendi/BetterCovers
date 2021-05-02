from requests import get
import json
from re import findall

SEARCH_URL = 'https://www.rottentomatoes.com/api/private/v2.0/search?q='

def searchMovie(title, year = False):
    rq = get(SEARCH_URL + title.lower().replace(' ', '+'))
    if rq.status_code == 200:
        try:
            rs = rq.json()
        except:
            return False
        if 'movies' in rs:
            for mv in rs['movies']:
                if title.lower() == mv['name'].lower():
                    if not year or int(year) == mv['year']:
                        return getMovieRatings('https://www.rottentomatoes.com' + mv['url'])
    return False

def getMovieRatings(url):
    rq = get(url)
    if rq.status_code == 200:
        sc = findall('<score-board[^>]*>', rq.text)
        if len(sc) > 0:
            res = {}
            rt = findall('tomatometerscore="(\d+)"', sc[0])
            if len(rt) == 1: res['RT'] = rt[0]
            res['CF'] = 'certified-fresh' in sc[0]
            rta = findall('audiencescore="(\d+)"', sc[0])
            if len(rta) == 1: res['RTA'] = rta[0]
            return res            
    return False