from Movie import Movie
from threading import Thread
from datetime import datetime
from time import time

import json

from scrapers.Trakt import getTraktRating
from functions import timediff, checkDate, getJSON, log, avg
from scrapers.RottenTomatoes import (getRTEpisodeRatings, getRTSeasonRatings)
from scrapers.TVTime import *

from functions import get

minVotes = 3


class Season(Movie):
    def updateMediaInfo(self, defaultAudioLanguage, mediainfoUpdateInterval):
        start = time()
        # TODO Do this with threads
        for ep in self.episodes: 
            ep.media_info.update(ep, defaultAudioLanguage, mediainfoUpdateInterval)
        self.getMediainfoFromChilds()

    def deleteEpisode(self, number):
        i = -1
        for episode in self.episodes:
            if episode.number == number: break
            i += 1
        if i > -1: del self.episodes[i]

    def getEpisode(self, number):
        for episode in self.episodes:
            if episode.number == number: return episode
        return False

    def updateMetadata(self, showIDS, omdbApi, tmdbApi):
        for ep in self.episodes: ep.production_companies = self.production_companies
        
        # Get season and episode poster, episodes ratings and TMDBID from TMDB
        def _getTMDB():
            if 'TMDB' in showIDS:
                if checkDate(self.updates['TMDB'], self.release_date):
                    start = time()
                    # Can search by id here but its the same (?
                    res = getJSON('https://api.themoviedb.org/3/tv/' + showIDS['TMDB'] + '/season/' + str(self.number) + '?api_key=' + tmdbApi + '&language=en&append_to_response=releases,external_ids,videos,production_companies,images')
                    if res:
                        if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']:
                            imgSrc = 'https://image.tmdb.org/t/p/original' + res['poster_path']
                            for img in self.images['covers']:
                                if img['src'] == imgSrc: break
                            else: 
                                self.images['covers'].append(
                                    {
                                        'src': imgSrc,
                                        'height': 0,
                                        'language': 'en',
                                        'source': 'TMDB'
                                    }
                                )

                        # Episodes metadata
                        if 'episodes' in res:
                            rts = []

                            for episode in res['episodes']:
                                if 'episode_number' not in episode or episode['episode_number'] == 'N/A': 
                                    continue # Continue if missing episode number
                                episodeNumber = int(episode['episode_number'])
                                if not self.getEpisode(episodeNumber): 
                                    continue # Continue if episode is not in season
                                
                                episodeMetadata = self.getEpisode(episodeNumber)
                                if episodeMetadata:
                                    # Cover Images
                                    if 'still_path' in episode and episode['still_path'] != 'N/A' and episode['still_path']: 
                                        imgSrc = 'https://image.tmdb.org/t/p/original' + episode['still_path']
                                        for img in episodeMetadata.images['covers']:
                                            if img['src'] == imgSrc: break
                                        else: 
                                            episodeMetadata.images['covers'].append({'src': imgSrc, 'height': 0, 'language': 'en', 'source': 'TMDB'})
                                    
                                    # Ratings
                                    if 'vote_average' in episode and episode['vote_average'] != 'N/A' and 'vote_count' in episode and episode['vote_count'] > minVotes:
                                        episodeMetadata.ratings['TMDB'] = {'icon': 'TMDB', 'value': "%.1f" % float(episode['vote_average'])}
                                        rts.append(float(episode['vote_average']))
                                    
                                    # ID
                                    if 'id' in episode: episodeMetadata.ids['TMDB'] = str(episode['id'])
                                    
                                    # Release Date
                                    if 'air_date' in episode and episode['air_date'] != '':
                                        episodeMetadata.release_date = datetime.strptime(episode['air_date'], '%Y-%m-%d')
                            
                            # Set season rating as avergage of all episodes ratings
                            if len(rts) > 0:
                                self.ratings['TMDB'] = {'icon': 'TMDB', 'value': avg(rts)}
                        
                        # Season Release date
                        if 'air_date' in res and len(res['air_date']) > 0: self.release_date = datetime.strptime(res['air_date'], '%Y-%m-%d') 
                        
                        
                        # Images
                        if 'images' in res:
                            for prop in res['images']:
                                mtProp = prop if prop != 'posters' else 'covers'
                                for image in res['images'][prop]:
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
                    else: log('Error getting info on TMDB for: ' + self.title, 3, 4)
                else: log('No need to update TMDB metadata for: ' + self.title, 1, 3)
        
        # Get IMDB ratings and ids for episodes
        def _getOMDB():  
            start = time()
            if len(omdbApi) > 0 and 'IMDBID' in showIDS:
                if checkDate(self.updates['OMDB'], self.release_date):
                    res = getJSON('http://www.omdbapi.com/?i=' + showIDS['IMDBID'] + '&Season=' + str(number) + '&apikey=' + omdbApi)
                    if res and 'Episodes' in res and len(res['Episodes']) > 0: # TODO get more data here
                        rts = []
                        for ep in res['Episodes']:
                            if self.getEpisode(int(ep['Episode'])):
                                if 'imdbRating' in ep and ep['imdbRating'] != 'N/A' and float(ep['imdbRating']) > 0: 
                                    self.getEpisode(int(ep['Episode'])).ratings['IMDB'] = {'icon': 'IMDB', 'value': "%.1f" % float(ep['imdbRating'])}
                                    rts.append(float(ep['imdbRating']))
                                
                                if 'imdbID' in ep and ep['imdbID'] != 'N/A':
                                    self.getEpisode(int(ep['Episode'])).ids['IMDB'] = ep['imdbID']
                            
                        self.updates['OMDB'] = datetime.now()
                        if len(rts) > 0: self.ratings['IMDB'] = {'icon': 'IMDB', 'value': avg(rts)}
                        log('Finished getting OMDB metadata for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                    else: log('Error getting info on OMDB for: ' + self.title, 3, 4)
                else: log('No need to update OMDB metadata for: ' + self.title, 1, 3)
        
        # Ger RT ratings and certifications for season and episodes
        def _getRT():
            start = time()
            if 'RT' in self.urls:
                if checkDate(self.updates['RT'], self.release_date):
                    RT = getRTSeasonRatings(self.urls['RT'], get)
                    if RT['statusCode'] == 200: # Get episodes urls and ratings
                        for ep in RT['episodes']: # Set episodes RT url
                            episode = self.getEpisode(ep[0])
                            if episode: 
                                episode.urls['RT'] = ep[1]
                                if checkDate(episode.updates['RT'], episode.release_date):
                                    start2 = time()
                                    RTE = getRTEpisodeRatings(episode.urls['RT'], get)
                                    if RTE['statusCode'] == 401:
                                        log('Rotten Tomatoes limit reached!', 3, 1)
                                        break
                                    elif RTE['statusCode'] == 200:
                                        for rt in RTE['ratings']: 
                                            episode.ratings[rt] = RT['ratings'][rt]
                                            episode.updates['RT'] = datetime.now()
                                            
                                            log('Found ' + rt + ' rating in RottenTomatoes for: ' + episode.title + ' in: ' + timediff(start2), 1, 4)
                                        if len(RTE['ratings']) == 0:
                                            log('No ratings found on RT for: ' + episode.title, 2, 4)
                                    else: log('Error getting episode ratings from RT for: ' + episode.title, 2, 4)
                                else: log('No need to update RT metadata for: ' + episode.title, 1, 4)

                        for rt in RT['ratings']: self.ratings[rt] = RT['ratings'][rt]
                        if 'RT-CF' in RT['certifications']:
                            if 'RT-CF' not in self.certifications: self.certifications.append('RT-CF')
                        elif 'RT-CF' in self.certifications: self.certifications.remove('RT-CF')
                        
                        self.updates['RT'] = datetime.now() 
                        log('Finished getting RT metadata for: ' + self.title + ' in: ' + timediff(start), 1, 3)
                    elif RT['statusCode'] == 403: return log('RottenTomatoes API limit reached!', 3, 1)
                    else: log('Error geting metadata from RottenTomatoes: ' + str(RT['statusCode']), 2, 4)            
                else: log('No need to update TMDB metadata for: ' + self.title, 1, 3)

        # Gets episode and season ratings from TVTime
        def _getTVTime():
            if checkDate(self.updates['TvTime'], self.release_date):
                start = time()
                success = False
                rts = []
                for episode in self.episodes:
                    if 'TVTime' in episode.urls:
                        start2 = time()
                        rating = getTVTimeEpisodeRating(episode.urls['TVTime'], get)
                        if rating:
                            episode.ratings['TVTime'] = {'icon': 'TVTime', 'value': rating}
                            rts.append(float(rating))
                            success = True
                            log('Found rating in TvTime for ' + episode.title + ': ' + rating + ' in: ' + timediff(start2), 0, 4)
                        else: log('Error getting rating in TvTime for: ' + episode.title, 2, 4)
                if success:
                    log('Finished getting TVTime metadata for: ' + self.title + ' in: ' + timediff(start), 1, 5)
                    self.updates['TvTime'] = datetime.now()
                    self.ratings['TVTime'] = {'icon': 'TVTime', 'value': avg(rts)}
                else: log('Error getting TVTime metadata for: ' + self.title, 2, 3)
            else: log('No need to update TVTime metadata for: ' + self.title, 1, 4)
        
        # Gets ratings from Trakt
        def _getTrakt():
            if 'TMDB' in self.ids:
                if checkDate(self.updates['Trakt'], self.release_date):
                    start = time()
                    rt = getTraktRating(self.ids['TMDB'], get)
                    if rt:
                        self.ratings['Trakt'] = {'icon': 'Trakt', 'value': rt}
                        self.updates['Trakt'] = datetime.now()
                        log('Found rating in Trakt for ' + self.title + ': ' + rt + ' in: ' + timediff(start), 1, 3)
                    else: log('Error getting Trakt ratings for: ' + self.title, 2, 4)
                else: log('No need to update Trakt metadata for: ' + self.title, 1, 3)
            
            for eps in self.episodes:
                if 'TMDB' in eps.ids:
                    if checkDate(eps.updates['Trakt'], eps.release_date):
                        start = time()
                        rt = getTraktRating(eps.ids['TMDB'], get)
                        if rt:
                            eps.ratings['Trakt'] = {'icon': 'Trakt', 'value': rt}
                            eps.updates['Trakt'] = datetime.now()
                            log('Found rating in Trakt for ' + eps.title + ': ' + rt + ' in: ' + timediff(start), 1, 3)
                        else: log('Error getting Trakt ratings for:' + eps.title, 2, 4)
                    else: log('No need to update Trakt metadata for: ' + eps.title, 1, 3)
            
        # Get TMDB first
        _getTMDB()

        tsks = []
        for fn in [_getOMDB, _getRT, _getTrakt]:
            tsks.append(Thread(target=fn, args=()))
            tsks[-1].start()
        for tsk in tsks: tsk.join()