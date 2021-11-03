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

from requests import post

import functions

# TODO change to tmdb api v4
# TODO update all logs
# TODO add trakt and moviechart
# TODO update metadata on delete/add episode
# TODO Update readme
# TODO Make readme specific for cover configuration
# TODO add log on each episode getting metadata
# TODO Add logs on getMetadata
# TODO Rotten Tomatoes api returns covers
# TODO MovieTweetings -> Interesting
# TODO Create better function for requests with included wait
# TODO delete icon from ratings since it can be calculated
# TODO change h264 icon
# TODO images cache not working
# TODO Get different ratings from metacritics
# TODO pass scrapping enabled/disabled to getSeasons
# TODO fix all scraperDate update
# TODO instead of having scraperDate change to next update day
# TODO fix date in container
# TODO Fix templates, ratings getting too cramed
# TODO Allow the script to be killed with CTRL + C

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
# endregion


dbVersion = 5
configVersion = 5
tasksLock = Lock()

tasks = []
tasksLength = 0
db = {'version': dbVersion}
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
                    with tasksLock: tsk = tasks.pop()# Use lock to prevent corruption
                    thrs[i] = Thread(target=functions.processTask, args=(tsk, str(i).zfill(thrsLength)))
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
    metadata = db[folder] if folder in db else functions.scannFolder(folder)  # Get existing metadata or get metadata from folder
    functions.log('Processing: ' + metadata['title'], 0, 2)
    if metadata['type'] == 'tv': # Update seasons and episodes from disk
        if not functions.updateSeasons(metadata):
            functions.log('No seasons found for: ' + metadata['title'] + ', is this a TV show?', 3, 1)
            return
    
    # Update metadata if needed
    getMetadata = Thread(target=functions.getMetadata , args=(metadata, config['omdbApi'], config['tmdbApi'], config['scraping'], config['preferedImageLanguage']))
    getMetadata.start()
    
    if metadata['type'] == 'movie': functions.getMediaInfo(metadata, config['defaultAudioLanguage'], config['mediainfoUpdateInterval']) # Update mediainfo for movies
    
    getMetadata.join() # Wait for metadata
    if metadata['type'] == 'tv': # Update mediainfo and metadata for seasons
        tsks = [] # Does all seasons in parallel, this can be improved for efficiency (generaly slow for anime with lots of chapters in each season)
        for sn in metadata['seasons']: 
            tsks.append(Thread(target=functions.getSeasonMetadata , args=(sn, metadata['seasons'][sn], metadata['ids'], config['omdbApi'], config['tmdbApi'])))
            tsks.append(Thread(target=functions.getSeasonMediainfo , args=(metadata['seasons'][sn], config['defaultAudioLanguage'], config['mediainfoUpdateInterval'])))
            tsks[-1].start()
            tsks[-2].start()
        for tsk in tsks: tsk.join()
        metadata['mediainfo'] = functions.getParentMediainfo(metadata['seasons'])

    # Generate tasks
    if not dry:
        generatedTasks = functions.generateTasks(metadata['type'], metadata, overwrite, covers[metadata['type']], config['templates'])
        if metadata['type'] == 'tv':
            for sn in metadata['seasons']: # Generate tasks for each season/episode
                generatedTasks += functions.generateTasks('season', metadata['seasons'][sn], overwrite, covers['season'], config['templates'])
                for ep in metadata['seasons'][sn]['episodes']:
                    generatedTasks += functions.generateTasks('episode', metadata['seasons'][sn]['episodes'][ep], overwrite, covers['episode'], config['templates'])
        
        # Added lock to prevent problems with accessing the same variable from different threads, this was never a problem tho
        with tasksLock: 
            global tasks, tasksLength
            tasks.extend(generatedTasks) # Extend SHOULD be thread safe anyway
            tasksLength += len(generatedTasks)

    functions.log('Finished getting metadata for: ' + metadata['title'] + ((', and generated ' + str(len(generatedTasks)) + ' tasks in: ' + functions.timediff(start)) if not dry else ''), 0, 2)
    
    db[folder] = metadata # Update metadata in database
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
if exists(join(workDirectory, 'config.json')):
    cfg = join(workDirectory, 'config.json')
    try:
        with open(cfg, 'r') as js:
            config = json.load(js)
            if 'version' not in config or config['version'] != configVersion:
                functions.log('Wrong version of config file, please update!', 1, 1)
                exit()
            # Load order for ratings and mediainfo, TODO change this to a setting in each image
            functions.ratingsOrder = config['ratingsOrder']
            functions.mediainfoOrder = config['mediainfoOrder']
    except:
        functions.log('Error loading config file from: ' + cfg, 3, 0)
        exit()
else:
    functions.log('Missing config.json inside work directory', 3, 0)
    exit()

# Loads covers configuration file
if exists(join(workDirectory, 'covers.json')):
    cvr = join(workDirectory, 'covers.json')
    try:
        with open(cvr, 'r') as js:
            covers = json.load(js)
            if 'version' not in covers or covers['version'] != configVersion:
                functions.log('Wrong version of covers file, please update!', 1, 0)
                exit()
    except:
        functions.log('Error loading covers file from: ' + cvr, 1, 0)
        exit()
else:
    functions.log('Missing cover.json inside work directory', 1, 0)
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
if config['scraping']['IMDB']: functions.scrapers.IMDB.updateIMDBDataset(workDirectory, 10, 10, functions.get)
# endregion


# Start
functions.log('Starting BetterCovers for directory: ' + pt, 1, 2)
st = time.time()
th1 = Thread(target=processFolders)
th1.start()
if not dry:
    th2 = Thread(target=processTasks)
    th2.start()
else: log('Starting dry run', 1, 2)
th1.join() # Wait for tasks to be generated

# Write metadata to pickle file
with open(join(workDirectory, 'metadata.pickle'), 'wb') as file:
    pickle.dump(db, file, protocol=pickle.HIGHEST_PROTOCOL)
if '--json' in argv: # If parameter --json also write to a json file
    with open(join(workDirectory, 'metadata.json'), 'w') as js:
        js.write(json.dumps(db, indent=7))
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

functions.log('FINISH, total time was: ' + functions.timediff(st), 0, 1)

