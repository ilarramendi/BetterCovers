from re import findall, match, escape
import json

BASE_URL = 'https://www.tvtime.com/'
headers = {"Host":"www.tvtime.com", 'User-Agent': 'Chrome/94.0.4606.81', 'x-requested-with': 'XMLHttpRequest', 'accept': 'application/json, text/javascript, */*; q=0.01'}

# Searches TVTime by title and returns an url
def searchTVTime(title, year, getJSON):
    rq = getJSON(BASE_URL + 'search?limit=20&q=' + title.lower().replace(' ', '+'), headers=headers)
    if rq:
        for item in rq:
            print(item)
            if match(escape(title.lower()) + ('\ \(?' + str(year) + '\(?') if year else '', item['name'].lower()):
                return {'id': str(item['id']), 'image': {'src': item['big_image'], 'height': 0, 'language': 'en', 'source': 'TVtime'}}
        for item in rq:
            if title.lower() == item['name'].lower():
                return {'id': str(item['id']), 'image': {'src': item['big_image'], 'height': 0, 'language': 'en', 'source': 'TVtime'}}    

    return False

# Gets episodes urls and rating from show url for TVTime
def getTVTimeRatings(id, getJSON):
    ret = getJSON(BASE_URL + 'show/' + id + '/ratings', headers=headers)
    return ret if len(ret) > 0 and len(ret[0]) > 0 else False