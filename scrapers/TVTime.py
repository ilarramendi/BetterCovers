from requests import get
from re import findall
import json
BASE_URL = 'https://www.tvtime.com/'
headers = {"Host":"www.tvtime.com", 'User-Agent': 'Chrome/94.0.4606.81'}
# Searches TVTime by title and returns an url
def searchTVTime(title):
    rq = get(BASE_URL + 'search?limit=20&q=' + title.lower().replace(' ', '+'), headers=headers)
    if rq.status_code == 200:
        for show in findall('<a href="([^"]+)">\n.+alt="([^"]+)">', rq.text):
            if show[1].lower() == title.lower():
                return show[0]
    return False

# Gets episodes urls and rating from show url for TVTime
def getTVTimeEpisodes(url):
    # "(\/en\/show\/361565\/episode\/\d+)"[^>]+>\n[^>]+>\n[^\d]+\d+
    rq = get(BASE_URL + url, headers=headers)
    if rq.status_code == 200:
        data = findall(r'(?:"(' + url.replace('/','\/')  + r'\/episode\/\d+)" class="col-sm-1[^>]+>\n[^>\n]+>\n[^\d\n]+(\d+)[^-\d])|(?:season(\d+)-content)', rq.text) # QUALITY REGEX BABY!
        ret = {'seasons': {}}
        season = 0
        if len(data) > 0:
            for ep in data:
                if ep[2] != '': 
                    season = int(ep[2])
                    ret['seasons'][season] = {}
                else: ret['seasons'][season][int(ep[1])] = ep[0]
        rating = findall('"ratingValue">([\d\.]+)<', rq.text)
        
        if len(rating) > 0: ret['rating'] = rating[0]
        
        return ret
    return False

# Gets episode rating from a given url
def getTVTimeEpisodeRating(url):
    rq = get(BASE_URL + url[1:], headers=headers)
    if rq.status_code == 200:
        match = findall('"ratingValue">([\d\.]+)<', rq.text)
        return "%.1f" % (float(match[0]) / 2) if len(match) > 0 else False
    return False