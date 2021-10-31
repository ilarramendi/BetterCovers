from re import findall

# Get Trakt Rating with tmdbid
def getTraktRating(tmdbid, get):
    rq = get('https://trakt.tv/search/tmdb/?query=' + tmdbid)
    if rq.status_code == 200:
        rt = findall('fa-heart rating-\d"><\/div>(\d+)%', rq.text)
        if len(rt) > 0: return "%.1f" % (int(rt[0]) / 10)
    return False