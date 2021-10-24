from requests import get
from re import findall
import json

# Gets certifications, IMDB rating and METACRITIC rating from IMDB
def getIMDBRating(id):
    ret = {'ratings': {}, 'certifications': []}
    rq = get('https://www.imdb.com/title/' + id)
    if rq.status_code != 200: return ret
    # "aggregateRating": {\n[^}]*"ratingValue": "([\d.]+)"
    sc = findall('AggregateRatingButton__RatingScore[^>]*>([\d\.]{1,4})<', rq.text) # Get IMDB score
    if len(sc) > 0: ret['ratings']['IMDB'] = {'icon': 'IMDB', 'value': sc[0].replace('.0', '')}
    # Metacritic score is only shown for movies for some reason
    sc = findall('metacriticScore[^>]*>\n<span>(\d+)<', rq.text) # Get METACRITIC score
    if len(sc) == 1: 
        if int(sc[0]) > 80:    
                rq = get('https://www.imdb.com/title/' + id + '/criticreviews')
                if rq.status_code == 200:
                    mc = findall('ratingCount">(\d+)<', rq.text)
                    if len(mc) > 0 and int(mc[0]) > 14: # MTC must watch if ammount of ratings > 14 and rating > 80
                        ret['certifications'] = ['MTC-MS']
        ret['ratings']['MTC'] = {'icon': 'MTC-MS' if 'MTC-MS' in ret['certifications'] else 'MTC', 'value': str(int(mc[0]) / 10).replace('.0', '')} # Set MTC icon depending on score
    return ret  