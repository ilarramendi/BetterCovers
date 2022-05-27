from threading import Thread, Lock
from re import findall
from os.path import join
from glob import glob

from src.types.Season import Season
from src.types.Movie import Movie
from src.types.Episode import Episode

from functions import log
class TvShow(Movie):
    def refresh(self, config):
        self.updateFiles(config['extensions'])

        if len(self.seasons) == 0: return log(f"No seasons found for: {self.title}", 2, 3)
        
        # Update metadata if needed
        self.updateMetadata(config['omdbApi'], config['tmdbApi'], config['scraping'], config['preferedImageLanguage'])

        # Does all seasons in parallel, this can be improved for efficiency (generaly slow for anime with lots of chapters in each season)
        tsks = [] 
        lock = Lock()
        results = [[], [], []]
        for sn in self.seasons: 
            tsks.append(Thread(target=sn.updateMetadata, args=(self.ids, config['omdbApi'], config['tmdbApi'])))
            tsks.append(Thread(target=sn.updateMediaInfo, args=(config['defaultAudioLanguage'], config['mediaInfoUpdateInterval'], config['ffprobe'])))
            tsks[-1].start()
            tsks[-2].start()
        for tsk in tsks: tsk.join()
        
        self.getMediainfoFromChilds()      

    def getSeason(self, number):
        for season in self.seasons:
            if season.number == number: return season
        return False
    
    def deleteSeason(self, number):
        i = 0
        for season in self.seasons:
            if season.number == number: break
            i += 1
        else: i = -1
        
        if i > -1: del self.seasons[i]

    # Update season and episodes
    def updateFiles(self, mediaExtensions):
        item = TvShow(False, False, False, False)
        for folder in glob(join(self.path.translate({91: '[[]', 93: '[]]'}), '*')):
            sn = findall('.*\/[Ss]eason[ ._-](\d{1,3})$', folder)
            if len(sn) == 1: # If its a season
                season = Season(self.title + ' (S:' + str(int(sn[0])) + ')', self.year, folder, folder)
                season.number = int(sn[0])
                item.seasons.append(season)

                files = []
                # Finds all media files inside season
                for ex in mediaExtensions: 
                    files += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex)) 
                for file in files: 
                    epn = findall('S0*' + str(season.number) + 'E0*(\d+)', file) 
                    if len(epn) == 1: # If its an episode
                        episode = Episode(self.title + ' (S:' + str(season.number) + ' E:' + str(int(epn[0])).zfill(len(str(len(season.episodes)))) + ')', self.year, file, folder)
                        episode.number = int(epn[0])
                        season.episodes.append(episode)

        # Deletes all season from metadata that are missing from disk
        seasonsDel = []
        for sn in self.seasons:
            if not item.getSeason(sn): seasonsDel.append(sn) 
            else:
                episodesDel = []
                # Deletes all episodes from season that are missing from disk
                for ep in sn.episodes:
                    if not item.getEpisode(ep): episodesDel.append(ep)      
                for ep in episodesDel: self.getSeason(sn).deleteEpisode(ep)
        for sn in seasonsDel: self.deleteSeason(sn)
        
        # Add new seasons
        for sn in item.seasons:
            season = self.getSeason(sn.number)
            if not season or sn.path != season.path:
                self.deleteSeason(sn.number)
                self.seasons.append(sn)
            else:
                for ep in sn.episodes:
                    if not season.getEpisode(ep.number) or ep.path != season.getEpisode(ep.number).path: # if its a new episode or path changed add episode
                        season.deleteEpisode(ep.number)
                        season.episodes.append(ep)
                            