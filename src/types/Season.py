import json
from time import time
from threading import Thread
from datetime import datetime

from src.types.Movie import Movie
from src.scrapers.TVTime import *
from src.scrapers.Trakt import getTraktRating, getTraktSeasonRatings
from src.scrapers.RottenTomatoes import (getRTEpisodeRatings, getRTSeasonRatings)
from src.functions import timediff, checkDate, getJSON, log, avg, process

minVotes = 3
class Season(Movie):
    def updateMediaInfo(self, defaultAudioLanguage, mediainfoUpdateInterval, ffprobe):
        start = time()
        # TODO Do this with threads
        result = [[], [], []]
        for ep in self.episodes: 
            for i, item in enumerate(ep.media_info.update(ep, defaultAudioLanguage, mediainfoUpdateInterval, ffprobe)):
                result[i].extend(item)
       
        self.getMediainfoFromChilds()
        
        if len(result[0]) > 0: log(f'Successfully updated MediaInfo for: "{self.title}" episodes: {", ".join(result[0])} in {timediff(start)}s', 0, 2)
        if len(result[1]) > 0: log(f'No need to update MediaInfo for: "{self.title}" episodes: {", ".join(result[1])}', 1, 4)
        if len(result[2]) > 0: log(f'Error getting MediaInfo for: "{self.title}" episodes: {", ".join(result[2])}', 2, 3)

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
                    res = getJSON(f"https://api.themoviedb.org/3/tv/{showIDS['TMDB']}/season/{self.number}?api_key={tmdbApi}&language=en&append_to_response=releases,external_ids,videos,production_companies,images")
                    if res:
                        if 'poster_path' in res and res['poster_path'] != 'N/A' and res['poster_path']:
                            imgSrc = f"https://image.tmdb.org/t/p/original{res['poster_path']}"
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
                                        imgSrc = f"https://image.tmdb.org/t/p/original{episode['still_path']}"
                                        for img in episodeMetadata.images['backdrops']:
                                            if img['src'] == imgSrc: break
                                        else: 
                                            episodeMetadata.images['backdrops'].append({'src': imgSrc, 'height': 0, 'language': 'en', 'source': 'TMDB'})
                                    
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
                                    imgSrc =  f"https://image.tmdb.org/t/p/original{image['file_path']}"
                                    
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
                        success.append("TMDB")
                    else: error.append("TMDB")
                else: passed.append("TMDB")
        
        # Get IMDB ratings and ids for episodes
        def _getOMDB():  
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
                        success.append("OMDB")
                    else: error.append("OMDB")
                else: passed.append("OMDB")
        
        # Ger RT ratings and certifications for season and episodes
        def _getRT():
            if 'RT' in self.urls:
                if checkDate(self.updates['RT'], self.release_date):
                    RT = getRTSeasonRatings(self.urls['RT'])
                    if RT['statusCode'] == 200: # Get episodes urls and ratings
                        for ep in RT['episodes']: # Set episodes RT url
                            episode = self.getEpisode(ep[0])
                            if episode: 
                                episode.urls['RT'] = ep[1]
                                if checkDate(episode.updates['RT'], episode.release_date):
                                    start2 = time()
                                    RTE = getRTEpisodeRatings(episode.urls['RT'])
                                    if RTE['statusCode'] == 401:
                                        log('Rotten Tomatoes limit reached!', 3, 1)
                                        break
                                    elif RTE['statusCode'] == 200:
                                        for rt in RTE['ratings']: 
                                            episode.ratings[rt] = RT['ratings'][rt]
                                            episode.updates['RT'] = datetime.now()
                                            
                                            log(f'Found {rt} rating in RottenTomatoes for: {episode.title} in: {timediff(start2)}s', 1, 4)
                                        if len(RTE['ratings']) == 0:
                                            log('No ratings found on RT for: ' + episode.title, 2, 4)
                                    else: log('Error getting episode ratings from RT for: ' + episode.title, 2, 4)
                                else: log('No need to update RT metadata for: ' + episode.title, 1, 4)

                        for rt in RT['ratings']: self.ratings[rt] = RT['ratings'][rt]
                        if 'RT-CF' in RT['certifications']:
                            if 'RT-CF' not in self.certifications: self.certifications.append('RT-CF')
                        elif 'RT-CF' in self.certifications: self.certifications.remove('RT-CF')
                        
                        self.updates['RT'] = datetime.now() 
                        success.append("RT")
                    elif RT['statusCode'] == 403:
                        error.append("RT")
                        return log('RottenTomatoes API limit reached!', 3, 1)
                    else: error.append("RT") 
                else: passed.append("RT")

        # Gets episode and season ratings from TVTime
        def _getTVTime():
            if checkDate(self.updates['TVTime'], self.release_date):
                success = False
                rts = []
                for episode in self.episodes:
                    if 'TVTime' in episode.urls:
                        start2 = time()
                        rating = getTVTimeEpisodeRating(episode.urls['TVTime'])
                        if rating:
                            episode.ratings['TVTime'] = {'icon': 'TVTime', 'value': rating}
                            rts.append(float(rating))
                            success = True
                            log(f'Found rating in TvTime for {episode.title}: {rating} in: {timediff(start2)}s', 0, 4)
                        else: log(f'Error getting rating in TvTime for: {episode.title}', 2, 4)
                if success:
                    success.append("TVTime")
                    self.updates['TVTime'] = datetime.now()
                    self.ratings['TVTime'] = {'icon': 'TVTime', 'value': avg(rts)}
                else: error.append("TVTime")
            else: passed.append("TVTime")
        
        # Gets ratings from Trakt
        def _getTrakt():
            if 'Trakt' in self.urls:
                if checkDate(self.updates['Trakt'], self.release_date):
                    start = time()
                    rt = getTraktSeasonRatings(self.urls['Trakt'])
                    if rt:
                        self.ratings['Trakt'] = {'icon': 'Trakt', 'value': rt['rating']}
                        self.updates['Trakt'] = datetime.now()
                        for episode in rt['episodes']:
                            ep = self.getEpisode(int(episode[1]))
                            if ep:
                                ep.ratings['Trakt'] = {'icon': 'Trakt', 'value':  "%.1f" % (int(episode[2]) / 10)}
                                ep.urls['Trakt'] = episode[0]
                        success.append("Trakt")
                    else: error.append("Trakt")
                else: passed.append("Trakt")
            
        tsks = []
        success = []
        passed = []
        error = []

        # Get TMDB first
        _getTMDB()

        for fn in [_getOMDB, _getRT, _getTrakt]:
            tsks.append(Thread(target=fn, args=()))
            tsks[-1].start()
        for tsk in tsks: tsk.join()

        if len(success) > 0: log(f"Successfully updated metadata for: {self.title} from: {', '.join(success)}", 0, 2)
        if len(passed) > 0: log(f"No need to update metadata for: {self.title} from: {', '.join(passed)}", 1, 3)
        if len(error) > 0: log(f"Error getting metadata for: {self.title} from: {', '.join(error)}", 2, 2)