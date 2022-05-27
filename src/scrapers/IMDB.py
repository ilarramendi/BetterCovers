from re import findall
from os.path import exists, join
from glob import glob
import urllib.request
from datetime import datetime
import gzip
from subprocess import call

minRatings = 5
ratingsFile = ''
episodesFile = ''

from src.functions import get, log

# TODO caca
# Downloads if necesary new dataset and sets its path for functions below
def updateIMDBDataset(wd, updateInterval):
    if not exists(join(wd, 'cache')): call(['mkdir', join(wd, 'cache')])

    global ratingsFile, episodesFile
    rtsFile = glob(join(wd, 'cache/IMDBRatings*.tvs'))
    if len(rtsFile) == 0 or (datetime.now() - datetime.strptime(rtsFile[0].rpartition('_')[2].rpartition('.')[0], '%Y-%m-%d')).days > updateInterval:
        tz = urllib.request.urlopen('https://datasets.imdbws.com/title.ratings.tsv.gz')
        if tz.getcode() == 200:
            out = join(wd, 'cache/IMDBRatings_' + datetime.now().strftime('%Y-%m-%d') + '.tvs')
            with open(out, 'wb') as outfile: # Extract gz in memory and save output to file
                outfile.write(gzip.decompress(tz.read()))
                ratingsFile = out
            log('Succesfully updated IMDB Ratings Dataset', 0, 2)
        else: log('Error downloading Ratings Dataset from IMDB', 3, 1)
    else: 
        log('No need to update IMDB Ratings Dataset', 1, 4)
        ratingsFile = rtsFile[0]

    epsFile = glob(join(wd, 'cache/IMDBEpisodes*.tvs'))
    if len(epsFile) == 0 or (datetime.now() - datetime.strptime(epsFile[0].rpartition('_')[2].rpartition('.')[0], '%Y-%m-%d')).days > updateInterval:
        tz = urllib.request.urlopen('https://datasets.imdbws.com/title.episode.tsv.gz')
        if tz.getcode() == 200:
            out = join(wd, './cache/IMDBEpisodes_' + datetime.now().strftime('%Y-%m-%d') + '.tvs')
            with open(out, 'wb') as outfile: # Extract gz in memory and save output to file
                outfile.write(gzip.decompress(tz.read()))
                episodesFile = out
            log('Succesfully updated IMDB Episodes Dataset', 0, 2)
        else: log('Error downloading Episodes Dataset from IMDB', 3, 1)
    else: 
        log('No need to update IMDB Episodes Dataset', 1, 4)   
        episodesFile = epsFile[0]

def getIMDBRating(id):
    with open(ratingsFile, 'r') as f:
        rt = findall(id + r'[^\S]([\d\.]+)[^\S](\d+)', f.read()) # \s dosnt work for some reason so \s = [^\S]
        if len(rt) > 0 and int(rt[0][1]) > minRatings: return ("%.1f" % float(rt[0][0]), rt[0][1])
        else: return False

def getEpisodesIMDBID(showID):
    with open(episodesFile, 'r') as f:
        return findall(r'(tt\d+)[^\S]' + showID + r'[^\S](\d+)[^\S](\d+)', f.read()) # ID, SeasonNumber, EpisodeNumber
