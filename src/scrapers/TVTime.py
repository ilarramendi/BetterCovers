from src.functions import getJSON

BASE_URL = 'https://www.tvtime.com'
headers = {
    "Host":"www.tvtime.com", 
    'User-Agent': 'Chrome/94.0.4606.81', 
    'x-requested-with': 'XMLHttpRequest', 
    'accept': 'application/json, text/javascript, */*; q=0.01'
}

# Searches TVTime by title and returns an url
def searchTVTime(title, year):
    rq = getJSON(f"{BASE_URL}/search?limit=20&q={title.lower().replace(' ', '+')}", headers)
    if rq:
        for item in rq:
            print(item) # TODO fix

    return False

# Gets episodes urls and rating from show url for TVTime
def getTVTimeRatings(id):
    ret = getJSON(f"{BASE_URL}/show/{id}/ratings", headers)
    return ret if len(ret) > 0 and len(ret[0]) > 0 else False