from requests import get
from re import findall
from time import sleep

def getMetacriticScore(IMDBID):
    try:
        sleep(3)
        rq = get('https://www.imdb.com/title/' + IMDBID + '/criticreviews', headers={"Host":"www.imdb.com", 'User-Agent': 'Chrome/94.0.4606.81'})
        if rq.status_code == 200:
            mc = findall('metascore score_favorable">\n[^"]*"ratingValue">(\d+)<(?:.*\n){4}[^"]+"ratingCount">(\d+)', rq.text)
            if len(mc) > 0: 
                return {'rating': "%.1f" % (int(mc[0][0]) / 10), 'MTC-MS': int(mc[0][0]) > 80 and int(mc[0][1]) > 14}  # TODO check 14 or 15
    except: print('Error getting MetaCritic Ratings (Too many requests?)')
    
    return False
