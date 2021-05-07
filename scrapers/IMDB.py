from requests import get
from re import findall
import json

def getRating(id):
    rq = get('https://www.imdb.com/title/' + id)
    res = {'MTC-MS': False}
    if rq.status_code == 200:
        mc = findall('"aggregateRating": {\n[^}]*"ratingValue": "([\d.]+)"', rq.text)
        if len(mc) == 1: res['IMDB'] = mc[0].replace('.0', '')
        mc = findall('metacriticScore[^>]*>\n<span>(\d+)<', rq.text)
        if len(mc) == 1: 
            res['MTC'] = str(int(mc[0]) / 10).replace('.0', '')
            if int(mc[0]) > 80:    
                    rq = get('https://www.imdb.com/title/' + id + '/criticreviews')
                    if rq.status_code == 200:
                        mc = findall('ratingCount">(\d+)<', rq.text)
                        if len(mc) > 0: res['MTC-MS'] = int(mc[0]) > 14
    return res