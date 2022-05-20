from datetime import datetime, timedelta
from json import dumps
from os.path import join, exists
from time import time
from threading import Thread
from re import findall
from urllib.parse import quote


import scrapers.IMDB
from scrapers.letterboxd import getLBRatings, searchLB
from scrapers.MetaCritic import getMetacriticScore
from scrapers.RottenTomatoes import (getRTMovieRatings, getRTTVRatings, searchRT)
from scrapers.TVTime import *
from scrapers.Trakt import getTraktRating



from functions import log, checkDate, getJSON, get, timediff, getName, getMediaFiles, readNFO, avg, frequent
scrapers.IMDB.updateIMDBDataset('.', 10, 10, get)


from MediaInfo import MediaInfo

from Task import Task

class Movie:
    def __init__(self, title, year, path, folder): # TODO add more params to constructor
        self.title = title
        self.year = year
        self.urls = {}
        self.trailers = []
        self.release_date = datetime.now()
        self.production_companies = []
        self.path = path
        self.folder = folder
        self.ids = {}
        self.certifications = []
        self.ageRating = 'NR'
        self.ratings = {}
        self.media_info = MediaInfo()
        self.updates = {
            "TMDB": datetime.utcfromtimestamp(1),
            "OMDB": datetime.utcfromtimestamp(1),
            "RT": datetime.utcfromtimestamp(1),
            "LB": datetime.utcfromtimestamp(1),
            "IMDB": datetime.utcfromtimestamp(1),
            "TVTime": datetime.utcfromtimestamp(1),
            "MC": datetime.utcfromtimestamp(1),
            "Trakt": datetime.utcfromtimestamp(1),
            "mediaInfo": datetime.utcfromtimestamp(1)
        }
        self.type = ''
        self.images = {
            "backdrops": [],
            "covers": [],
            "logos": []
        }

        
        # Movie
        if str(type(self)) == "<class 'Movie.Movie'>": 
            self.type = 'movie'

        # TV
        if str(type(self)) == "<class 'TvShow.TvShow'>": 
            self.seasons = []
            self.type = 'tv'

        # Season
        if str(type(self)) == "<class 'Season.Season'>": 
            self.episodes = []
            self.type = 'season'
            self.number = -1

        # Episode
        if str(type(self)) == "<class 'Episode.Episode'>": 
            self.type = 'episode'
            self.number = -1
        
        if self.path != False:
            # TV / Movie
            if self.type in ['tv', 'movie']:
                # Get info from NFO
                nfo = join(self.path, 'tvshow.nfo') if self.type == 'tv' else (self.path.rpartition('.')[0] + '.nfo')
                if exists(nfo): self.ids = readNFO(nfo)
                
                imdbid = findall('imdbid=(tt\d+)', self.path)
                if len(imdbid) == 1: 
                    self.ids['IMDB'] = imdbid[0]
                
                tmdbid = findall('tmdbid=(\d+)', self.path)
                if len(tmdbid) == 1: 
                    self.ids['TMDB'] = tmdbid[0]

    def refresh(self, config):
        # Update metadata if needed
        getMetadata = Thread(target=self.updateMetadata , args=(config['omdbApi'], config['tmdbApi'], config['scraping'], config['preferedImageLanguage']))
        getMetadata.start()
        
        # Update mediainfo for movies sync
        self.media_info.update(self, config['defaultAudioLanguage'], config['mediaInfoUpdateInterval']) 

        getMetadata.join() 

    def toJSON(self):
        ret = {}
        for property, value in vars(self).items():
            if property == 'media_info':
                ret[property] = value.toJSON()
            elif property in ['episodes', 'seasons']:
                ret[property] = [p.toJSON() for p in value]
            else:
                ret[property] = value
        return ret 

    def __str__(self):
        return dumps(self.toJSON(), indent=5, default=str, sort_keys=True)

    def generateTasks(self, overwrite, config, templates): 
        ret = Task.generateTask(self.type, self, overwrite, config, templates)

        if self.type in ['movie', 'tv', 'season']:
            ret.extend(Task.generateTask('backdrop', self, overwrite, config['backdrop'], templates)) # Seasons have backdrops?     
        if self.type == 'tv':
            for season in self.seasons: 
                ret.extend(season.generateTasks(overwrite, config['season'], templates))
        if self.type == 'season': 
            for episode in self.episodes:
                ret.extend(episode.generateTasks(overwrite, config['episode'], templates))
        
        return ret
            
    def getTemplate(self, templates, backdrop):
        def _ratingsOk(ratings):
            for rt in ratings:
                if rt not in self.ratings: return False
                value = float(ratings[rt][1:])
                rating = float(self.ratings[rt]['value'])
                if ratings[rt][0] == '>':
                    if rating <= value: return False
                elif rating >= value: return False
            return True
        
        def _companiesOk(companies):
            pc = [pc['id'] for pc in self.production_companies]
            for pr in companies:
                if pr not in pc: return False
            return True

        def _mediainfoOk(mediainfo):
            for pr in mediainfo:
                if pr == 'languages':
                    if not arrayOk(mediainfo['languages'], self.mediainfo.languages):
                        return False
                elif mediainfo[pr] != getattr(self.mediainfo, pr): return False
            return True
        
        def _ageRatingOk(rating):
            order = ['G', 'PG', 'PG-13', 'R', 'NC-17', 'NR']
            if order.indexOf(rating) < order.indexof(self.ageRating): return False

        # TODO add type_backdrop to readme
        type = (self.type + '_backdrop') if backdrop else self.type # type if its a backdrop
        for template in templates: # Returns the first matching template
            if 'type' not in template or type in template['type'].split(';'):
                if 'ratings' not in template or _ratingsOk(template['ratings']): 
                    if 'mediainfo' not in template or _mediainfoOk(template['mediainfo']):
                        if 'ageRating' not in template or _ageRatingOk(template['ageRating']):
                            if 'productionCompanies' not in template or _companiesOk(template['productionCompanies']):
                                return template['cover']
        
        return 'backdrop' if backdrop or self.type == 'episode' else 'cover'  # default templates if no custom match found

    def updateMetadata(self, omdbApi, tmdbApi, scraping, preferedImageLanguage):
        # Gets metadata from TMDB api
        def _getTMDB():
            if checkDate(self.updates['TMDB'], self.release_date):
                start = time()
                
                if 'TMDB' not in self.ids and 'IMDB' in self.ids: # If missing TMDB id search by IMDBID
                    res = getJSON('https://api.themoviedb.org/3/find/' + self.ids['IMDB'] + '?api_key=' + tmdbApi + '&language=' + preferedImageLanguage + '&external_source=imdb_id')
                    if res and len(res[self.type + '_results']) == 1:  
                        self.ids['TMDB'] = str(res[self.type + '_results'][0]['id'])
                    else: log("No results found searching by IMDB id in TMDB: " + self.ids['IMDB'], 2, 5)
                
                if 'TMDB' not in self.ids: # If still missing TMDB id search by title
                    res = getJSON('https://api.themoviedb.org/3/search/' + self.type + '?api_key=' + tmdbApi + '&language=en&page=1&include_adult=false&append_to_response=releases,external_ids&query=' + quote(self.title) + ('&year=' + str(self.year) if self.year else ''))
                    if res and 'results' in res:
                        if len(res['results']) == 1:
                            self.ids['TMDB'] = str(res['results'][0]['id'])
                        else:
                            for result in res['results']:
                                if result['name'].lower() == self.title.lower():
                                    self.ids['TMDB'] = str(result['id'])
                                    break
                            else: log("No results found searching by title in TMDB: " + self.title, 3, 4)
                    else: log("No results found searching by title in TMDB: " + self.title, 3, 4)

                if 'TMDB' in self.ids: # If TMDB id is found get results
                    result = getJSON('https://api.themoviedb.org/3/' + self.type + '/' + self.ids['TMDB'] + '?api_key=' + tmdbApi + '&language=en&append_to_response=releases,external_ids,videos,production_companies,images')
                    if result:
                        # TMDB Rating
                        if 'vote_average' in result and result['vote_average'] != 0:
                            self.ratings['TMDB'] = {'icon': 'TMDB', 'value': str(result['vote_average'])}
                        
                        # IMDB ID
                        if 'imdb_id' in result['external_ids'] and result['external_ids']['imdb_id'] and 'IMDB' not in self.ids:
                            self.ids['IMDB'] = result['external_ids']['imdb_id']
                        
                        #if 'last_air_date' in result and result['last_air_date']:
                        #    metadata['releaseDate'] = datetime.strptime(result['last_air_date'], '%Y-%m-%d').strftime("%d/%m/%Y") # TODO change this on new episodes
                        
                        # Release Date
                        if 'release_date' in result and result['release_date']:
                            self.release_date = datetime.strptime(result['release_date'], '%Y-%m-%d')
                        
                        # Age ratings
                        if 'releases' in result and 'countries' in result['releases']:
                            for rl in result['releases']['countries']:
                                if rl['iso_3166_1'] == 'US':
                                    if rl['certification'] != '': self.age_rating = rl['certification']
                                    break
                        
                        # Trailers
                        if 'results' in result['videos']:
                            for vd in result['videos']['results']:
                                if vd['site'] == 'YouTube' and vd['type'] == 'Trailer':
                                    for tr in self.trailers:
                                        if tr['id'] == vd['key']: break
                                    else: self.trailers.append({'id': vd['key'], 'name': vd['name'], 'language': vd['iso_639_1'].upper(), 'resolution': vd['size']})

                        # Seasons
                        if 'seasons' in result:
                            for sn in result['seasons']:
                                season = self.getSeason(sn['season_number'])
                                if season: season.ids['TMDB'] = str(sn['id'])

                        # Title
                        self.title = result['title'] if 'title' in result else result['name'] if 'name' in result else self.title
                        
                        # Production Companies
                        if 'production_companies' in result:
                            for pc in result['production_companies']:
                                if pc['logo_path']: 
                                    for prc in self.production_companies: 
                                        if prc['id'] == pc['id']: break
                                    else:
                                        self.production_companies.append({'id': pc['id'], 'name': pc['name'], 'logo': 'https://image.tmdb.org/t/p/original' + pc['logo_path']})
                        
                        # Images
                        for prop in result['images']:
                            mtProp = prop if prop != 'posters' else 'covers'
                            for image in result['images'][prop]:
                                imgSrc = 'https://image.tmdb.org/t/p/original' + image['file_path']
                                
                                for img in self.images[mtProp]:
                                    if img['src'] == imgSrc: break
                                else: 
                                    self.images[mtProp].append({
                                        'src': imgSrc,
                                        'height': image['height'],
                                        'language': image['iso_639_1'],
                                        'source': 'TMDB'}
                                    )

                        self.updates['TMDB'] = datetime.now()
                        log('Finished getting TMDB metadata for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                    else: log('TMDB id found but no results found for: ' + self.title, 3, 4)
                else: log("TMDB id not found for: " + self.title, 3, 4)
            else: log('No need to update TMDB metadata for: ' + self.title, 1, 3)
        
        # Gets suplemetary metadata from OMDB api
        def _getOMDB():   
            if len(omdbApi) > 0 and ('IMDB' in self.ids or self.title):
                if checkDate(self.updates['OMDB'], self.release_date):
                    start = time()
                    url = 'http://www.omdbapi.com/?apikey=' + omdbApi + '&tomatoes=true'
                    url += '&i=' + self.ids['IMDB'] if 'IMDBID' in self.ids else '&t=' + quote(self.title.replace(' ', '+')) + ('&y=' + str(self.year) if self.year else '')
                    res = getJSON(url)
                    if res:
                        # Images
                        if 'Poster' in res and res['Poster'] != 'N/A':
                            for img in self.images['covers']:
                                if img['src'] == res['Poster']: break
                            else: self.images['covers'].append({
                                    'src': res['Poster'],
                                    'height': 0,
                                    'language': 'en',
                                    'source': 'OMDB'})
                        
                        # Metacritic Score
                        if 'Metascore' in res and res['Metascore'] != 'N/A':
                            self.ratings['MTC'] = {'icon': 'MTC', 'value': "%.1f" % (int(res['Metascore']) / 10)}
                        
                        # IMDB Score
                        if 'imdbRating' in res and res['imdbRating'] != 'N/A':
                            self.ratings['IMDB'] = {'icon': 'IMDB', 'value': "%.1f" % float(res['imdbRating'])}
                        
                        # RT Score
                        if 'Ratings' in res:
                            for rt in res['Ratings']:
                                if rt['Source'] == 'Rotten Tomatoes' and rt['Value'] != 'N/A':
                                    self.ratings['RT'] = {'icon': 'RT' if int(rt['Value'][:-1]) >= 60 else 'RT-LS', 'value': str(int(rt['Value'][:-1]) / 10).rstrip('0').rstrip('.')}
                                    break
                        
                        # IMDB ID
                        if 'imdbID' in res and 'IMDB' not in self.ids and res['imdbID'] != 'N/A':
                            self.ids['IMDB'] = res['imdbID'] 

                        self.updates['OMDB'] = datetime.now()
                        log('Finished getting OMDB metadata for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                    else: log('No results found on OMDB for: ' + self.title, 2, 4)
                else: log('No need to update OMDB metadata for: ' + self.title, 1, 3)
        
        # Get RT ratings, certifications and url for media and seasons if needed
        def _getRT():
            if scraping['RT']: 
                if checkDate(self.updates['RT'], self.release_date):
                    start = time()
                    url = self.urls['RT'] if 'RT' in self.urls else searchRT(self.type, self.title, self.year, getJSON)
                    if url:
                        # RT URL
                        self.urls['RT'] = url
                        rt = getRTMovieRatings(url, get) if self.type == 'movie' else getRTTVRatings(url, get)
                        if rt['statusCode'] == 403: return log('Rotten tomatoes api limit reached!', 3, 1)
                        
                        # RT and RTA Score
                        for rating in rt['ratings']: self.ratings[rating] = rt['ratings'][rating]
                        
                        # RT Certified Fresh Certification
                        if 'RT-CF' in rt['certifications']:
                            if 'RT-CF' not in self.certifications: self.certifications.append('RT-CF')
                        elif 'RT-CF' in self.certifications:
                            self.certifications.remove('RT-CF')
                        
                        # TODO FIX
                        '''
                        if 'seasons' in rt:
                            for sn in rt['seasons']:
                                if sn in metadata['seasons']: metadata['seasons'][sn]['URLS']['RT'] = rt['seasons'][sn]
                        '''

                        if len(rt['ratings']) > 0 or ('seasons' in rt and len(rt['seasons']) > 0):
                            self.updates['RT'] = datetime.now()
                            log('Finished getting RT metadata for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                        else: log('No ratings found on RottenTomatoes for: ' + self.title, 2, 4)
                    else: log('No results found on RottenTomatoes for: ' + self.title, 2, 4)
                else: log('No need to update RottenTomatoes metadata for: ' + self.title, 1, 3)
        
        # Gets IMBD and MTC scores and certifications from IMBD
        def _getIMDB():
            if scraping['IMDB'] and 'IMDB' in self.ids:
                if checkDate(self.updates['IMDB'], self.release_date): 
                    start = time()
                    imdb = scrapers.IMDB.getIMDBRating(self.ids['IMDB'])
                    if imdb:
                        self.ratings['IMDB'] = {'icon': 'IMDB', 'value': imdb[0]}
                        self.updates['IMDB'] = datetime.now()
                        log('Found IMDB rating in dataset for: ' + self.title + ': ' + str(imdb[0]) + ', in: ' + timediff(start), 1, 3)
                    else: log('No result found in IMDB DATASET for: ' + self.title, 2, 4)
                    
                    # TODO Fix
                    if self.type == 'tv': # TODO run this again when episodes are added
                        eps = scrapers.IMDB.getEpisodesIMDBID(self.ids['IMDB'])
                        for ep in eps: # Get episodes ids
                            if int(ep[1]) in self.seasons and int(ep[2]) in self.seasons[int(ep[1])]['episodes']:
                                self.seasons.getSeason(int(ep[1])).getEpisode(int(ep[2])).ids['IMDB'] = str(ep[0])
                else: log('No need to update IMDB metadata for: ' + self.title, 1, 3)
        
        # Gets movie ratings from letterboxd
        def _getLB():
            if self.type == 'movie' and scraping['LB'] and 'IMDB' in self.ids:
                if checkDate(self.updates['LB'], self.release_date):
                    start = time()
                    LB = self.urls['LB'] if 'LB' in self.urls else searchLB(self.ids['IMDB'], self.title, self.year, get)
                    if LB: 
                        self.urls['LB'] = LB
                        LB = getLBRatings(LB, get)
                        if LB: 
                            self.ratings['LB'] = LB
                            self.updates['LB'] = datetime.now()
                            log('Found LetterBox rating for: ' + self.title + ': ' + LB['value'] + ', in: ' + timediff(start), 1, 3)
                    else: log('No results found in LetterBox for: ' + self.title, 2, 4)
                else: log('No need to update Letterbox metadata for: ' + self.title, 1, 3)
    
        #TODO fix
        # Get episode and season ratings from TVTime (all in only one request)
        def _getTVTime():
            if self.type == 'tv' and scraping['TVTime']:
                if checkDate(self.updates['TVTime'], self.release_date):
                    start = time()
                    tvTime = searchTVTime(self.title, self.year, getJSON) # TODO search by id
                    if tvTime:
                        self.ids['TvTime'] = tvTime['id']

                        for image in self.images['covers']:
                            if image['src'] == tvTime['image']: break
                        else:
                            self.images['covers'].append(tvTime['image'])
                        
                        ratings = getTVTimeRatings(self.ids['TvTime'], getJSON)
                        if ratings:
                            for season in ratings:
                                for episode in season:
                                    sn = self.getSeason(int(episode['season_number']))
                                    ep = sn.getEpisode(int(episode['number'])) if sn else False
                                    if ep: ep.ratings['TVTime'] = {'icon': 'TVTime', 'value': "%.1f" % episode['ratings']}      
                                
                            rtsTotal = [] # Get ratings average for show and seasons from episodes
                            for season in self.seasons:
                                rts = []
                                for episode in season.episodes:
                                    if 'TVTime' in episode.ratings:
                                        rts.append(episode.ratings['TVTime']['value'])
                                        rtsTotal.append(episode.ratings['TVTime']['value'])
                                if len(rts): season.ratings['TVTime'] = {'icon': 'TVTime', 'value': avg(rts)}
                            if len(rtsTotal): self.ratings['TVTime'] = {'icon': 'TVTime', 'value': avg(rtsTotal)}
                            
                            log('Finished getting TVTime metadata for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                            self.updates['TVTime'] = datetime.now()
                        else: log('No episode ratings found in TVTime for: ' + self.title, 2, 4)
                    else: log('No result found in TVTime for: ' + self.title, 2, 4)
                else: log('No need to update TVTime metadata for: ' + self.title, 1, 3)
        
        # TODO do this for seasons and episodes?
        # Gets ratings from metaCritic
        def _getMetaCritic():
            if scraping['MetaCritic'] and 'IMDB' in self.ids:
                if checkDate(self.updates['MC'], self.release_date):
                    start = time()
                    sc = getMetacriticScore(self.ids['IMDB'], get)
                    if sc:
                        self.ratings['MTC'] = {'icon': 'MTC-MS' if sc['MTC-MS'] else 'MTC', 'value': sc['rating']}
                        if sc['MTC-MS']:
                            if 'MTC-MS' not in self.certifications: self.certifications.append('MTC-MS')
                        elif 'MTC-MS' in self.certifications:
                            self.certifications.remove('MTC-MS')
                        
                        self.updates['MC'] = datetime.now()
                        log('Finished getting MetaCritic ratings for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                    else: log('Error getting MetaCritic ratings for: ' + self.title, 2, 4)
                else: log('No need to update MetaCritic metadata for: ' + self.title, 1, 3)
        
        # Gets ratings from Trakt
        def _getTrakt():
            if scraping['Trakt'] and 'TMDB' in self.ids:
                if checkDate(self.updates['Trakt'], self.release_date):
                    start = time()
                    rt = getTraktRating(self.ids['TMDB'], get)
                    if rt:
                        self.ratings['Trakt'] = {'icon': 'Trakt', 'value': rt}
                        self.updates['Trakt'] = datetime.now()
                        log('Finished getting Trakt ratings for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                    else: log('Error getting Trakt ratings for: ' + self.title, 2, 4)
                else: log('No need to update Trakt metadata for: ' + self.title, 1, 3)
        
        tsks = []

        _getTMDB() # Get general information first

        for fn in [_getOMDB, _getRT, _getIMDB, _getLB, _getTVTime, _getMetaCritic, _getTrakt]: # Starts rest of the tasks
            tsks.append(Thread(target=fn, args=()))
            tsks[-1].start()
        for tsk in tsks: tsk.join() # Wait for tasks to finish

        if self.type == 'tv': # TODO get specific production companies for eachg epiosode
            for sn in self.seasons:
                sn.production_companies = self.production_companies
    
    # Returns the mediainfo as an averag of all children (seasons or episodes)
    def getMediainfoFromChilds(self):
        res = {'source': [], 'languages': [], 'color': [], 'codec': [], 'resolution': []}
        for ch in self.seasons if self.type == 'tv' else self.episodes:
            for property, value in vars(ch.media_info).items():
                res[property].append(value)
        
        for pr in res:
            if pr != 'languagea' and len(res[pr]) > 0: setattr(self.media_info, pr, frequent(res[pr]))
        
        if len(res['languages']) > 0:
            self.languages = res['languages'][0]
            for language in res['languages'][0]:
                for languages in res['languages']:
                    if language not in languages: 
                        self.media_info.languages.remove(language)
                        break