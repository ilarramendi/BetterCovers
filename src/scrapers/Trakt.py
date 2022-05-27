from re import findall

from src.functions import getJSON, get

BASE_URL = "https://trakt.tv"

# Get Trakt Rating with tmdbid
def getTraktRating(tmdbid):
    rq = get(f'{BASE_URL}/search/tmdb/?query={tmdbid}')
    if rq.status_code == 200:
        rt = findall(r'data-url="([^"]+)"[^%]+>(\d+)%', rq.text)
        value = "%.1f" % (int(rt[0][1]) / 10)
        if value != '0.0':
            if len(rt) > 0: return (value if value != '10.0' else '10', rt[0][0])
    return False

def getTraktSeasonRatings(url):
    rq = get(BASE_URL+ url) 
    if rq.status_code == 200:
        return {'rating': "%.1f" % (int(findall(r'(\d+)%', rq.text)[0]) / 10), 'episodes': findall(r'href="([^"]+episodes\/(\d+))"[^%]+>(\d+)%', rq.text)}
    return False