from requests import get
from re import findall
import json
from bs4 import BeautifulSoup

def searchLB(IMDBID, name, year):
    try:
        rq = get('https://letterboxd.com/search/' + (IMDBID if IMDBID else name))
        if rq.status_code != 200: return False
        soup = BeautifulSoup(rq.text, 'lxml')
        for mv in soup.find_all('span', attrs={'class': 'film-title-wrapper'}):
            mvn = mv.find('a')
            if IMDBID: return 'https://letterboxd.com/csi' + mvn['href'] + 'rating-histogram/'
            else:
                if mvn.contents[0].strip().lower() == name.lower() and abs(year - int(mv.find_all('a')[1].contents[0])) <= 1: return 'https://letterboxd.com/csi' + mvn['href'] + 'rating-histogram/'
    except:
        pass
    return False

def getRatingsLB(url):
    try:
        if not url: return False
        rq = get(url)
        if rq.status_code != 200: return False
        soup = BeautifulSoup(rq.text, 'lxml')
        rt = soup.find('a', attrs={'class': 'display-rating'}).contents[0]
        return {'icon': 'LB', 'value': str(float(rt) * 2).replace('.0', '')}
    except: return False