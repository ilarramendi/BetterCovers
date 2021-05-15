from requests import get
from re import findall
import json

def getIMDBRating(mt):
    rq = get('https://www.imdb.com/title/' + mt['ids']['IMDBID'])
    if rq.status_code == 200:
        mc = findall('"aggregateRating": {\n[^}]*"ratingValue": "([\d.]+)"', rq.text)
        if len(mc) == 1:
            mt['ratings']['IMDB'] = {'icon': 'IMDB', 'value': mc[0].replace('.0', '')}
        mc = findall('metacriticScore[^>]*>\n<span>(\d+)<', rq.text)
        if len(mc) == 1: 
            if int(mc[0]) > 80:    
                    rq = get('https://www.imdb.com/title/' + id + '/criticreviews')
                    if rq.status_code == 200:
                        mc2 = findall('ratingCount">(\d+)<', rq.text)
                        if len(mc2) > 0 and int(mc2[0]) > 14:
                            mt['certifications'].append('MTC-MS')
            
            mt['ratings']['MTC'] = {'icon': 'MTC-MS' if 'MTC-MS' in mt['certifications'] else 'MTC', 'value': str(int(mc[0]) / 10).replace('.0', '')}