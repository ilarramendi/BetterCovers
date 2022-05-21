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

# TODO change to tmdb api v4
# TODO update all logs
# TODO add moviechart
# TODO update metadata on delete/add episode
# TODO Update readme
# TODO Make readme specific for cover configuration
# TODO add log on each episode getting metadata
# TODO Add logs on getMetadata
# TODO Rotten Tomatoes api returns covers !
# TODO MovieTweetings -> Interesting
# TODO Create better function for requests with included wait
# TODO delete icon from ratings since it can be calculated
# TODO change h264 icon
# TODO images cache not working
# TODO Get different ratings from metacritics
# TODO pass scrapping enabled/disabled to getSeasons
# TODO fix date in container 
# TODO Fix templates, ratings getting too cramed
# TODO Allow the script to be killed with CTRL + C

# TODO Change ratings to be only values stored
# TODO Trailers missiing url?
# TODO change picke to json
# TODO change srings concatenation to {}
# TODO remove year parameter since releaseDate exists
# TODO container logs some thimes get corrupted in console, this dosnt happend in portainer, wtf.
# TODO Also logs in container update in steps or groups instead of normaly
# TODO change user of docker container from root using GUID

# region parameters
# Check parameters
if len(argv) == 1:
    functions.log('A path is needed to work: BetterCovers "/media/movies/*"', 3, 0)
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
threads = 20 if '-w' not in argv else int(argv[argv.index('-w') + 1])
processing = True
overwrite = '-o' in argv
workDirectory = abspath('./' if '-wd' not in argv else argv[argv.index('-wd') + 1])
functions.workDirectory = workDirectory
functions.logLevel = 2 if '--log-level' not in argv else int(argv[argv.index('--log-level') + 1]) 
dry = '--dry' in argv
functions.showColor = '--no-colors' not in argv
# endregion

dbVersion = 6
configVersion = 6
tasksLock = Lock()

tasks = []
tasksLength = 0
db = {'version': dbVersion, 'items': {}}
config = {}
covers = {}

# region Functions
# Calls processfolder for all folders in multiple threads
def processFolders():
    thrs = [False] * threads
    for folder in folders:
        i = 0
        while True:
            if not (thrs[i] and thrs[i].is_alive()): # If thread was not created or its finish
                thrs[i] = Thread(target=processFolder , args=(folder, ))
                thrs[i].start()
                break
            i += 1
            if i == threads: i = 0
        sleep(0.05)

    # Wait for threads to end
    for th in thrs: 
        if th: th.join()
    global processing
    processing = False

# Calls processTask for all tasks until all tasks are done and it finished generating tasks
def processTasks():
    j = 1
    thrs = [False] * threads
    thrsLength = len(str(threads))

    if not exists(join(workDirectory, 'threads')): call(['mkdir', join(workDirectory, 'threads')])
    while processing or len(tasks) > 0:
        if len(tasks) > 0:
            i = 0
            while True:
                if not (thrs[i] and thrs[i].is_alive()):
                    with tasksLock: 
                        tsk = tasks.pop()
                        thrs[i] = Thread(target=tsk.process, args=(str(i).zfill(thrsLength), workDirectory, config['wkhtmltoimagePath']))
                    thrs[i].start()
                    j += 1
                    break
                i += 1
                if i == threads: i = 0

    for th in thrs:
        if th: th.join()   # Wait for threads to finish
    
    return j

# Updates all information for a given movie or tv show and generates tasks
def processFolder(folder):
    start = time.time()
    if folder in db['items']: metadata = db['items'][folder]
    else:
        title, year = functions.getName(folder)
        mediaFiles = functions.getMediaFiles(folder)
        type = 'tv' if len(mediaFiles) == 0 else 'movie'
        path = mediaFiles[0] if type == 'movie' else folder

        metadata = Movie(title, year, path, folder) if type == 'movie' else TvShow(title, year, path, folder)

    
    functions.log('Processing: ' + metadata.title, 1, 2)
    
    # Refresh metadata
    metadata.refresh(config)
    
    # Generate tasks
    if not dry:
        generatedTasks = metadata.generateTasks(overwrite, covers[metadata.type], config['templates'])        
        with tasksLock:
            global tasks, tasksLength
            tasks.extend(generatedTasks)
            tasksLength += len(generatedTasks)

    functions.log('Finished getting metadata for: ' + metadata.title + ((', and generated ' + str(len(generatedTasks)) + ' tasks in: ' + functions.timediff(start)) if not dry else ''), 0, 2)
    
    db['items'][folder] = metadata # Update metadata in database
# endregion

# region check files and dependencies
# Load stored metadata
if exists(join(workDirectory, 'metadata.pickle')):
    with open(join(workDirectory, 'metadata.pickle'), 'rb') as pk:
        try:
            db = pickle.load(pk)
            if 'version' not in db or db['version'] != dbVersion:
                functions.log('Removing metadata file because this is a new version of the script', 3, 1)
                db = {'version': dbVersion}
        except:
            functions.log('Error loading metadata from: ' + join(workDirectory, 'metadata.pickle'), 3, 1)
            exit()

# Load configuration file
if exists(join(workDirectory, 'config', 'config.json')):
    cfg = join(workDirectory, 'config', 'config.json')
    try:
        with open(cfg, 'r') as js:
            config = json.load(js)
            if 'version' not in config or config['version'] != configVersion:
                functions.log('Wrong version of config file, please delete!', 1, 1)
                exit()
            # Load order for ratings and mediainfo, TODO change this to a setting in each image
            functions.ratingsOrder = config['ratingsOrder']
            functions.mediainfoOrder = config['mediaInfoOrder']
    except:
        functions.log('Error loading config file from: ' + cfg, 3, 0)
        exit()
else:
    functions.log('Missing config/config.json inside work directory', 3, 0)
    exit()

# Loads covers configuration file
if exists(join(workDirectory, 'config', 'covers.json')):
    cvr = join(workDirectory, 'config', 'covers.json')
    try:
        with open(cvr, 'r') as js:
            covers = json.load(js)
            if 'version' not in covers or covers['version'] != configVersion:
                functions.log('Wrong version of covers file, please delete!', 1, 0)
                exit()
    except:
        functions.log('Error loading covers file from: ' + cvr, 1, 0)
        exit()
else:
    functions.log('Missing config/cover.json inside work directory', 1, 0)
    exit()

# Check for TMDB api key
if config['tmdbApi'] == '':
    functions.log('TMDB api key is needed to run. (WHY DID YOU REMOVE IT?!?!)', 1, 0)
    exit() 

# Check Dependencies
for dp in [d for d in ['wkhtmltox','ffmpeg'] if d]:
    cl = getstatusoutput('apt-cache policy ' + dp)[1] # TODO fix this for windows
    if 'Installed: (none)' in cl:
        functions.log(dp + ' is not installed', 1, 0)
        exit()

# Set path to wkhtmltoimage
functions.wkhtmltoimage = config['wkhtmltoimagePath']

# Updates IMDB datasets
# TODO fix
#if config['scraping']['IMDB']: 
# endregion

# Start
functions.log('Starting BetterCovers for directory: ' + pt, 1, 2)
st = time.time()
th1 = Thread(target=processFolders)
th1.start()
if not dry:
    th2 = Thread(target=processTasks)
    th2.start()
else: functions.log('Starting dry run', 1, 2)
th1.join() # Wait for tasks to be generated

# Write metadata to pickle file
with open(join(workDirectory, 'metadata.pickle'), 'wb') as file:
    pickle.dump(db, file, protocol=pickle.HIGHEST_PROTOCOL)
if '--json' in argv: # If parameter --json also write to a json file
    with open(join(workDirectory, 'metadata.json'), 'w') as js:
        json.dump({'version': db['version'], 'items': [db['items'][item].toJSON() for item in db['items']]}, js, indent=7, default=str, sort_keys=True)
if not dry: th2.join() # Wait for tasks to be processed
if exists(join(workDirectory, 'threads')): rmtree(join(workDirectory, 'threads'))

# Update Agent
if config['agent']['apiKey'] != '': # TODO add plex
    url = config['agent']['url'] + ('/Library/refresh?api_key=' + config['agent']['apiKey'] if config['agent']['type'] == 'emby' else '/ScheduledTasks/Running/6330ee8fb4a957f33981f89aa78b030f')
    time.sleep(2)
    if post(url, headers={'X-MediaBrowser-Token': config['agent']['apiKey']}).status_code < 300:
        functions.log('Succesfully updated ' + config['agent']['type'] + ' libraries (' + config['agent']['url'] + ')', 0, 2)
    else: functions.log('Error accessing ' + config['agent']['type'] + ' at ' + config['agent']['url'], 2, 2)
else: functions.log('Not updating ' + config['agent']['type'] + ' library, API key not set.', 1, 3)

functions.log('Done, total time was: ' + functions.timediff(st) + ' and generated: ' + str(tasksLength) + ' images.', 0, 1)

