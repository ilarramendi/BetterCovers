from requests import get
from re import findall
import json
from bs4 import BeautifulSoup

def searchLB(mt):
    try:
        rq = get('https://letterboxd.com/search/' + (mt['ids']['IMDBID'] if 'IMDBID' in mt['ids'] else name))
        if rq.status_code != 200: return False
        soup = BeautifulSoup(rq.text, 'lxml')
        for mv in soup.find_all('span', attrs={'class': 'film-title-wrapper'}):
            mvn = mv.find('a')
            print(mvn)
            if 'IMDBID' in mt['ids']: 
                mt['urls']['LB'] = 'https://letterboxd.com/csi' + mvn['href'] + 'rating-histogram/'
                return True
            else:
                if mvn.contents[0].strip().lower() == name.lower() and abs(year - int(mv.find_all('a')[1].contents[0])) <= 1: 
                    mt['urls']['LB'] =  'https://letterboxd.com/csi' + mvn['href'] + 'rating-histogram/'
                    return True
    except:
        pass
    return False

def getLBRatings(mt):
    try:
        rq = get(mt['urls']['LB'])
        if rq.status_code != 200: return
        soup = BeautifulSoup(rq.text, 'lxml')
        rt = soup.find('a', attrs={'class': 'display-rating'}).contents[0]
        mt['ratings']['LB'] = {'icon': 'LB', 'value': str(float(rt) * 2).replace('.0', '')}
    except: return