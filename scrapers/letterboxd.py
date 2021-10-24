from requests import get
from re import findall
import json
from bs4 import BeautifulSoup

BASE_URL = 'https://letterboxd.com/csi' 

def searchLB(IMDBID, name, year):
    rq = get('https://letterboxd.com/search/' + (IMDBID if IMDBID else name))
    if rq.status_code == 200:
        soup = BeautifulSoup(rq.text, 'lxml')
        if soup:
            for mv in soup.find_all('span', attrs={'class': 'film-title-wrapper'}):
                media = mv.find('a')
                if media:
                    if IMDBID: return media['href'] + 'rating-histogram/'
                    else:
                        # If search by name check if year is almost the same
                        if media.contents[0].strip().lower() == name.lower() and (not year or abs(year - int(mv.find_all('a')[1].contents[0])) <= 1):
                            return  media['href'] + 'rating-histogram/'

    return False

def getLBRatings(url):
    rq = get(BASE_URL + url)
    if rq.status_code == 200:
        soup = BeautifulSoup(rq.text, 'lxml')
        if soup:
            rt = soup.find('a', attrs={'class': 'display-rating'}).contents[0]
            if rt: return {'icon': 'LB', 'value': str(float(rt) * 2).replace('.0', '')}
    return False