import time
import pickle
import json
from time import sleep
from threading import Lock, Thread
from sys import argv
from subprocess import call, getstatusoutput
from shutil import rmtree
from requests import post
from os.path import abspath, exists, join
from glob import glob
from datetime import timedelta, datetime

import src.functions
from src.functions import log, timediff, getName, getMediaFiles
from src.types.TvShow import TvShow
from src.types.Movie import Movie

from src.scrapers.IMDB import updateIMDBDataset

# region parameters
# Check parameters
if len(argv) == 1:
    log('A path is needed to work: "/media/movies/*"', 3, 0)
    exit()
if '-wd' in argv and len(argv) == argv.index('-wd') + 1:
    log('-wd parameter requieres a correct directory: -wd ./BetterCovers', 3, 0)
    exit()
if '-w' in argv and (len(argv) == argv.index('-w') + 1 or not argv[argv.index('-w') + 1].isnumeric()):
    log('-w parameter requieres a number: -w 20', 3, 0)
    exit()
if '--log-level' in argv and (len(argv) == argv.index('--log-level') + 1 or not argv[argv.index('--log-level') + 1].isnumeric()):
    log('--log-level parameter requieres a number: --log-level 2', 3, 0)
    exit()

pt = argv[1]
folders = sorted(glob(pt + ('/' if pt[-1] != '/' else ''))) if '*' in pt else [f"{pt}/"] # if its a single folder dont use glob
threads = 30 if '-w' not in argv else int(argv[argv.index('-w') + 1])
overwrite = '-o' in argv
workDirectory = abspath('./config' if '-wd' not in argv else argv[argv.index('-wd') + 1])
src.functions.logFile = join(workDirectory, 'logs', datetime.now().strftime("%Y-%m-%d %H:%M") + '.log')
logLevel = 2 if '--log-level' not in argv else int(argv[argv.index('--log-level') + 1]) 
src.functions.logLevel = logLevel
dry = '--dry' in argv
showColor = '--no-colors' not in argv
# endregion

dbVersion = 8
configVersion = 8

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
        title, year = getName(folder)
        mediaFiles = getMediaFiles(folder, config['extensions'])
        type = 'tv' if len(mediaFiles) == 0 else 'movie'
        path = mediaFiles[0] if type == 'movie' else folder
        metadata = Movie(title, year, path, folder) if type == 'movie' else TvShow(title, year, path, folder)
        db['items'][folder] = metadata
    
    # Refresh metadata
    metadata.refresh(config)
    if metadata.type == 'tv' and len(metadata.seasons) == 0: return log(f'Empty folder: "{folder}"', 1, 2)
    
    # Generate images
    if not dry: 
        global tasks, tasksLock
        tsks = metadata.process(overwrite, config, str(thread), workDirectory)
        with tasksLock: tasks += tsks

# endregion

# region check files
# Load stored metadata
if exists(join(workDirectory, 'metadata.pickle')):
    with open(join(workDirectory, 'metadata.pickle'), 'rb') as pk:
        try:
            db = pickle.load(pk)
            if 'version' not in db or db['version'] != dbVersion:
                log('Removing metadata file because this is a new version of the script', 3, 1)
                db = {'version': dbVersion, 'items': {}}
        except:
            log(f'Error loading metadata from: "{join(workDirectory, "metadata.pickle")}"', 3, 1)
            exit()

# Load configuration file
if exists(join(workDirectory, 'config.json')):
    cfg = join(workDirectory, 'config.json')
    try:
        with open(cfg, 'r') as js:
            config = json.load(js)
            if 'version' not in config or config['version'] != configVersion:
                log('Wrong version of config file, please delete!', 1, 1)
                exit()
    except:
        log(f'Error loading config file from: "{cfg}"', 3, 0)
        exit()
else:
    log('Missing config/config.json inside work directory', 3, 0)
    exit()

if not exists(join(workDirectory, 'threads')): call(['mkdir', join(workDirectory, 'threads')])
if not exists(join(workDirectory, 'logs')): call(['mkdir', join(workDirectory, 'logs')])
# endregion

# Check for TMDB api key
if config['tmdbApi'] == '':
    log('TMDB api key is needed to run. (WHY DID YOU REMOVE IT?!?!)', 1, 0)
    exit() 

# Updates IMDB datasets
if config['scraping']['IMDB']: updateIMDBDataset(workDirectory, config['IMDBDatasetUpdateInterval'])

# Start
log('Starting BetterCovers for directory: ' + pt, 1, 2)
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
        log(f"Succesfully updated {config['agent']['type']} libraries ({config['agent']['url']})", 0, 2)
    else: log(f"Error accessing  {config['agent']['type']} at {config['agent']['url']}", 2, 2)
else: log(f"Not updating {config['agent']['type']} library, API key not set.", 1, 3)

log(f"Done, total time was: {timediff(st, False)} and generated {tasks} images.", 0, 1)

