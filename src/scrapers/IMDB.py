from re import findall
import json
from os.path import exists, realpath, join
from glob import glob
import urllib.request
from datetime import datetime
import gzip
from subprocess import call

minRatings = 5
ratingsFile = ''
episodesFile = ''

# TODO caca
# Downloads if necesary new dataset and sets its path for functions below
def updateIMDBDataset(wd, ratingsUpdateInterval, episodesUpdateInterval, get):
    if not exists(join(wd, 'cache')): call(['mkdir', join(wd, 'cache')])

    global ratingsFile, episodesFile
    rtsFile = glob(join(wd, 'cache/IMDBRatings*.tvs')) # WD is always an absolute path
    if len(rtsFile) == 0 or (datetime.now() - datetime.strptime(rtsFile[0].rpartition('_')[2].rpartition('.')[0], '%m-%d-%Y')).days > ratingsUpdateInterval:
        tz = urllib.request.urlopen('https://datasets.imdbws.com/title.ratings.tsv.gz')
        if tz.getcode() == 200:
            out = join(wd, 'cache/IMDBRatings_' + datetime.now().strftime('%m-%d-%Y') + '.tvs')
            with open(out, 'wb') as outfile: # Extract gz in memory and save output to file
                outfile.write(gzip.decompress(tz.read()))
                ratingsFile = out
            print('Succesfully updated IMDB Ratings Dataset')
        else: print('Error downloading Ratings Dataset from IMDB')
    else: 
        print('No need to update IMDB Ratings Dataset')
        ratingsFile = rtsFile[0]

    epsFile = glob(join(wd, 'cache/IMDBEpisodes*.tvs'))
    if len(epsFile) == 0 or (datetime.now() - datetime.strptime(epsFile[0].rpartition('_')[2].rpartition('.')[0], '%m-%d-%Y')).days > episodesUpdateInterval:
        tz = urllib.request.urlopen('https://datasets.imdbws.com/title.episode.tsv.gz')
        if tz.getcode() == 200:
            out = join(wd, './cache/IMDBEpisodes_' + datetime.now().strftime('%m-%d-%Y') + '.tvs')
            with open(out, 'wb') as outfile: # Extract gz in memory and save output to file
                outfile.write(gzip.decompress(tz.read()))
                episodesFile = out
            print('Succesfully updated IMDB Episodes Dataset')
        else: print('Error downloading Episodes Dataset from IMDB')
    else: 
        print('No need to update IMDB Episodes Dataset')   
        episodesFile = epsFile[0]

def getIMDBRating(id):
    with open(ratingsFile, 'r') as f:
        rt = findall(id + r'[^\S]([\d\.]+)[^\S](\d+)', f.read()) # \s dosnt work for some reason so \s = [^\S]
        if len(rt) > 0 and int(rt[0][1]) > minRatings: return ("%.1f" % float(rt[0][0]), rt[0][1])
        else: return False

def getEpisodesIMDBID(showID):
    with open(episodesFile, 'r') as f:
        return findall(r'(tt\d+)[^\S]' + showID + r'[^\S](\d+)[^\S](\d+)', f.read()) # ID, SeasonNumber, EpisodeNumber
