from re import findall
from time import sleep
   
def getMetacriticScore(IMDBID, get):
    rq = get('https://www.imdb.com/title/' + IMDBID + '/criticreviews', {"Host":"www.imdb.com", 'User-Agent': 'Chrome/94.0.4606.81'})
    if rq.status_code == 200:
        mc = findall('metascore [^"]*">\n[^"]*"ratingValue">(\d+)<(?:.*\n){4}[^"]+"ratingCount">(\d+)', rq.text)
        if len(mc) > 0: 
            return {'rating': "%.1f" % (int(mc[0][0]) / 10), 'MTC-MS': int(mc[0][0]) > 80 and int(mc[0][1]) > 14}  # TODO check 14 or 15
    
    return False
