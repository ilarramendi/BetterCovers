import json
import pickle
import time
from glob import glob
from os.path import abspath, exists, join
from shutil import rmtree
from subprocess import call, getstatusoutput
from sys import argv
from threading import Lock, Thread
from time import sleep
from datetime import timedelta

from requests import post

from Movie import Movie
from TvShow import TvShow

import functions

import scrapers.IMDB

# TODO change to tmdb api v4
# TODO add moviechart
# TODO update metadata on delete/add episode
# TODO add log on each episode getting metadata
# TODO Rotten Tomatoes api returns covers !
# TODO MovieTweetings -> Interesting
# TODO delete icon from ratings since it can be calculated on the fly
# TODO images cache not working
# TODO Get different ratings from metacritics
# TODO pass scrapping enabled/disabled to getSeasons
# TODO fix date in container 
# TODO Allow the script to be killed with CTRL + C

# TODO Change ratings to be only values stored
# TODO Trailers missiing url?
# TODO remove year point since releaseDate exists
# TODO container logs some thimes get corrupted in console, this dosnt happend in portainer, wtf.
# TODO Also logs in container update in steps or groups instead of normaly
# TODO change user of docker container from root using GUID
# TODO make a function to check the configuration file
# TODO make readme more detail and easier to understand
# TODO Change time.time to the code timing function but is not realy relevant since all timers take more than 3 seconds so i guess is good enought this comment went a bit long but yea
# TODO make css noob-friendly (add css variables)
# TODO dont update metadata each run if last time didnt give results
# TODO rethink log levels
# TODO add options removed from covers.json like 4k-hdr
# TODO try system links as a way to make images load faster in emby
# TODO make MTC and Trakt scrapper work better
# TODO what is cover art archive?
# TODO get fanart from somewhere to generate images
# TODO fix hash for automatic image overwrite
# TODO add matched to log
# TODO fix tv show performance
# TODO add again number of images generated at the end
# TODO make a method to check the similarity in 2 strings to match on search
# TODO NYTIMES Critic's Pick as certifications
# TODO change places where i pass get as a parameter to scrapper
# TODO REDO ALL SCRAPPERS LIKE RE
# TODO Add directors to filters!

# region parameters
# Check parameters
if len(argv) == 1:
    functions.log('A path is needed to work: "/media/movies/*"', 3, 0)
    exit()
if '-wd' in argv and len(argv) == argv.index('-wd') + 1:
    functions.log('-wd parameter requieres a correct directory: -wd ./BetterCovers', 3, 0)
    exit()
if '-w' in argv and (len(argv) == argv.index('-w') + 1 or not argv[argv.index('-w') + 1].isnumeric()):
    functions.log('-w parameter requieres a number: -w 20', 3, 0)
    exit()
if '--log-level' in argv and (len(argv) == argv.index('--log-level') + 1 or not argv[argv.index('--log-level') + 1].isnumeric()):
    functions.log('--log-level parameter requieres a number: --log-level 2', 3, 0)
    exit()

pt = argv[1]
folders = sorted(glob(pt + ('/' if pt[-1] != '/' else ''))) if '*' in pt else [pt] # if its a single folder dont use glob
threads = 30 if '-w' not in argv else int(argv[argv.index('-w') + 1])
overwrite = '-o' in argv
workDirectory = abspath('./config' if '-wd' not in argv else argv[argv.index('-wd') + 1])
functions.workDirectory = workDirectory
functions.logLevel = 2 if '--log-level' not in argv else int(argv[argv.index('--log-level') + 1]) 
dry = '--dry' in argv
functions.showColor = '--no-colors' not in argv
# endregion

dbVersion = 7
configVersion = 7

tasks = 0
tasksLock = Lock()

db = {'version': dbVersion, 'items': {}}
config = {}

# region Functions
# Calls processfolder for all folders in multiple threads
def processFolders():
    thrs = [False] * threads
    for folder in folders:
        i = 0
        while True:
            if not (thrs[i] and thrs[i].is_alive()): # If thread was not created or its finish
                thrs[i] = Thread(target=processFolder , args=(folder, i))
                thrs[i].start()
                break
            i += 1
            if i == threads: i = 0
        sleep(0.05)

    # Wait for threads to end
    for th in thrs: 
        if th: th.join()

# Updates all information for a given movie or tv show and generates tasks
def processFolder(folder, thread):
    start = time.time()
    if folder in db['items']: metadata = db['items'][folder]
    else:
        title, year = functions.getName(folder)
        mediaFiles = functions.getMediaFiles(folder, config['extensions'])
        type = 'tv' if len(mediaFiles) == 0 else 'movie'
        path = mediaFiles[0] if type == 'movie' else folder

        metadata = Movie(title, year, path, folder) if type == 'movie' else TvShow(title, year, path, folder)
        db['items'][folder] = metadata
    
    # Refresh metadata
    metadata.refresh(config)
    if metadata.type == 'tv' and len(metadata.seasons) == 0: return functions.log(f'Empty folder: "{folder}"', 1, 2)
    
    # Generate images
    if not dry: 
        global tasks, tasksLock
        tsks = metadata.process(overwrite, config, str(thread), workDirectory)
        with tasksLock: tasks += tsks

# endregion

# region check files and dependencies
# Load stored metadata
if exists(join(workDirectory, 'metadata.pickle')):
    with open(join(workDirectory, 'metadata.pickle'), 'rb') as pk:
        try:
            db = pickle.load(pk)
            if 'version' not in db or db['version'] != dbVersion:
                functions.log('Removing metadata file because this is a new version of the script', 3, 1)
                db = {'version': dbVersion, 'items': {}}
        except:
            functions.log(f'Error loading metadata from: "{join(workDirectory, "metadata.pickle")}"', 3, 1)
            exit()

# Load configuration file
if exists(join(workDirectory, 'config.json')):
    cfg = join(workDirectory, 'config.json')
    try:
        with open(cfg, 'r') as js:
            config = json.load(js)
            if 'version' not in config or config['version'] != configVersion:
                functions.log('Wrong version of config file, please delete!', 1, 1)
                exit()
    except:
        functions.log('Error loading config file from: "{cfg}"', 3, 0)
        exit()
else:
    functions.log('Missing config/config.json inside work directory', 3, 0)
    exit()

if not exists(join(workDirectory, 'threads')): call(['mkdir', join(workDirectory, 'threads')])

# Check for TMDB api key
if config['tmdbApi'] == '':
    functions.log('TMDB api key is needed to run. (WHY DID YOU REMOVE IT?!?!)', 1, 0)
    exit() 

# Updates IMDB datasets
if config['scraping']['IMDB']: scrapers.IMDB.updateIMDBDataset(workDirectory, config['IMDBDatasetUpdateInterval'])

# Start
functions.log('Starting BetterCovers for directory: ' + pt, 1, 2)
st = time.time()
processFolders()

# Write metadata to pickle file
with open(join(workDirectory, 'metadata.pickle'), 'wb') as file:
    pickle.dump(db, file)
if '--json' in argv: # If parameter --json also write to a json file
    with open(join(workDirectory, 'metadata.json'), 'w') as js:
        json.dump({'version': db['version'], 'items': [db['items'][item].toJSON() for item in db['items']]}, js, indent=7, default=str, sort_keys=True)

# if exists(join(workDirectory, 'threads')): rmtree(join(workDirectory, 'threads'))

# Update Agent
if config['agent']['apiKey'] != '':
    url = f"{config['agent']['url']}{'/Library/refresh?api_key=' + config['agent']['apiKey'] if config['agent']['type'] == 'emby' else '/ScheduledTasks/Running/6330ee8fb4a957f33981f89aa78b030f'}"
    if post(url, headers={'X-MediaBrowser-Token': config['agent']['apiKey']}).status_code < 300:
        functions.log(f"Succesfully updated {config['agent']['type']} libraries ({config['agent']['url']})", 0, 2)
    else: functions.log(f"Error accessing  {config['agent']['type']} at {config['agent']['url']}", 2, 2)
else: functions.log(f"Not updating {config['agent']['type']} library, API key not set.", 1, 3)

functions.log(f"Done, total time was: {functions.timediff(st, False)} and generated {tasks} images.", 0, 1)

