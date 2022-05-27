from re import findall

from src.functions import getJSON, get

# Get Trakt Rating with tmdbid
def getTraktRating(tmdbid):
    rq = get(f'https://trakt.tv/search/tmdb/?query={tmdbid}')
    if rq.status_code == 200:
        rt = findall(r'(\d+)%', rq.text)
        value = "%.1f" % (int(rt[0]) / 10)
        if len(rt) > 0: return value if value != '10.0' else '10'
    return False