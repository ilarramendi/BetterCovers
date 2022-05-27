
from jellyfish import jaro_distance

from re import findall


SEARCH_URL = "https://www.rogerebert.com/reviews?utf8=%E2%9C%93&sort%5Border%5D=newest&filters%5Byears%5D%5B%5D=1000&filters%5Byears%5D%5B%5D=3000&filters%5Bstar_rating%5D%5B%5D=0.0&filters%5Bstar_rating%5D%5B%5D=4.0&filters%5Bno_stars%5D=1&page=1&filters%5Btitle%5D="

from src.functions import get

# TODO add year to search
def getRERatings(title):
    req = get(f"{SEARCH_URL}{title}",  {"Host":"www.rogerebert.com", 'User-Agent': 'Chrome/94.0.4606.81'})
    max = 0
    maxValue = 0
    gm = False
    name = ''
    
    if req.status_code == 200:
        for item in findall(r'review-stack--title">\n[^>]*>([^<]+)<\/a>\n(<img .*\n)?(?:.*\n){6}<span (.*)', req.text):
            val = (item[2].count('"star-full"') + item[1].count('"star-half"')) * 2
            dist = jaro_distance(item[0].lower(), title.lower())
            if max < dist:
                max = dist
                maxValue = val
                gm = "Great Movie" in item[1]
                name = item[0]
    if maxValue == int(maxValue) and maxValue < 10: maxValue = f"{maxValue}.0"
    # if max > 0.85: print(f"Matched '{title}' to '{name}'")
    
    return (str(maxValue), gm) if max > 0.85 else False