from sys import argv
import json
from os.path import exists, join, abspath
import time
from subprocess import call, getstatusoutput
import functions
from datetime import timedelta, datetime
from threading import Thread, Lock
from time import sleep
from glob import glob 
import pickle 

# TODO Daemon in thread to terminate when core program ends
# TODO check scrapers
# TODO generate tasks for backdrops (llamar la misma funcion cambiandole el param de config por el bakdrop dentro)
# TODO edit production companies based on episode/season
# TODO production companies not loading for tv
# TODO change to tmdb api v4
# TODO metadata update
# TODO add thread lock to getseasonmetadata and getseasonmedainfo
# TODO update tv mediainfo
# TODO change config file to YAML
# TODO update all logs
# TODO ratings icons are not sorted anymore
# TODO add log to view time for each provider (_getRT)
# TODO get season TVTime score as average
# TODO add trakt and moviechart



# region parameters
if len(argv) == 1:
    functions.log('A path is needed to work: BetterCovers "/media/movies/*"', 3, 0)
    exit()
pt = argv[1]
folders = sorted(glob(pt)) if '*' in pt else [pt] # if its a single folder dont use glob
if '-wd' in argv and len(argv) == argv.index('-wd') + 1:
    functions.log('-wd parameter requieres a correct directory: -wd ./BetterCovers', 3, 0)
    exit()
workDirectory = abspath('./' if '-wd' not in argv else argv[argv.index('-wd') + 1])
functions.workDirectory = workDirectory
overwrite = '-o' in argv
automaticOverwrite = '-a' in argv
if '-w' in argv and (len(argv) == argv.index('-w') + 1 or not argv[argv.index('-w') + 1].isnumeric()):
    functions.log('-w parameter requieres a number: -w 20', 3, 0)
    exit()
threads = 20 if '-w' not in argv else int(argv[argv.index('-w') + 1])
processing = True
# endregion


dbVersion = 3
configVersion = 3
tasksLock = Lock()

tasks = []
tasksLength = 0
db = {'version': dbVersion}

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
    print('asd')
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

# Loads configuration file and sets omdb and tmdb keys if found in parameters
def loadConfig(cfg):
    try:
        with open(cfg, 'r') as js:
            global config 
            config = json.load(js)
            if 'version' not in config or config['version'] != configVersion:
                log('Wrong version of config file, please update!', 1, 0)
                exit()
            if '-omdb' in argv and len(argv) > (argv.index('-omdb') + 1) and argv[argv.index('-omdb') + 1] != '': config['omdbApi'] = argv[argv.index('-omdb') + 1]
            if '-tmdb' in argv and len(argv) > (argv.index('-tmdb') + 1) and argv[argv.index('-tmdb') + 1] != '': config['tmdbApi'] = argv[argv.index('-tmdb') + 1]
        with open(cfg, 'w') as out: 
            out.write(json.dumps(config, indent = 5))
    except:
        log('Error loading config file from: ' + cfg, 1, 0)
        exit()

# Updates all information for a given movie or tv show and generates tasks
def processFolder(folder):
    start = time.time()
    if folder not in db: # New entry
        metadata = {'path': folder}
        mediaFiles = functions.getMediaFiles(folder) # finds media files inside folder
        metadata['title'], metadata['year'] = functions.getName(folder) # Parse title and year from folder
        if len(mediaFiles) == 0: 
            metadata['type'] = 'tv'
        else: metadata['type'] = 'movie' # Movie

        # TODO get IMDBID from name
        nfo = join(folder, 'tvshow.nfo') if metadata['type'] == 'tv' else (mediaFiles[0].rpartition('.')[0] + '.nfo') if len(mediaFiles) > 0 else join(folder, 'FALSE')
        if exists(nfo): metadata['ids'] = functions.readNFO(nfo) # Gets ids from NFO file if exists
    else: # Existing folder
        metadata = db[folder] # Get metadata from database
    
    if metadata['type'] == 'tv': 
        if not functions.updateSeasons(metadata):
            log('No seasons found for: ' + metadata['title'], 3, 1)
            return
    
    
    # Update metadata if needed
    getMetadata = Thread(target=functions.getMetadata , args=(metadata, config['omdbApi'], config['tmdbApi'], config['scraping'], config['preferedImageLanguage']))
    getMetadata.start()
    
    # Update mediainfo for movies
    if metadata['type'] == 'movie':
        if 'mediainfoDate' not in metadata or (datetime.now() - datetime.strptime(metadata['mediainfoDate'], '%d/%m/%Y')) >= timedelta(days=config['mediainfoUpdateInterval']):
            mediainfo = functions.getMediaInfo(functions.getMediaFiles(folder)[0], config['defaultAudioLanguage'])
            if mediainfo: 
                metadata['mediainfo'] = mediainfo
                metadata['mediainfoDate'] = datetime.now().strftime("%d/%m/%Y")
            elif 'mediainfo' not in metadata: metadata['mediainfo'] = {}
        else: log('No need to update mediainfo for: ' + metadata['title'], 3, 3)
    
    getMetadata.join()
    if metadata['type'] == 'tv':
        tsks = []
        for sn in metadata['seasons']: 
            tsks.append(Thread(target=functions.getSeasonMetadata , args=(sn, metadata['seasons'][sn], metadata['ids'], config['omdbApi'], config['tmdbApi'])))
            tsks.append(Thread(target=functions.getSeasonMediainfo , args=(metadata['seasons'][sn], config['defaultAudioLanguage'], config['mediainfoUpdateInterval'])))
            tsks[-1].start()
            tsks[-2].start()
        for tsk in tsks: tsk.join()
        metadata['mediainfo'] = functions.getParentMediainfo(metadata['seasons'])

    # Generate tasks
    functions.log('Finished getting metadata for: ' + metadata['title'] + ' in:' + functions.timediff(start), 0, 2)
    start2 = time.time()
    generatedTasks = functions.generateTasks(metadata['type'], metadata, overwrite, automaticOverwrite, config[metadata['type']], config['templates'])
    if metadata['type'] == 'tv':
        for sn in metadata['seasons']:
            generatedTasks += functions.generateTasks('season', metadata['seasons'][sn], overwrite, automaticOverwrite, config['season'], config['templates'])
            for ep in metadata['seasons'][sn]['episodes']:
                generatedTasks += functions.generateTasks('episode', metadata['seasons'][sn]['episodes'][ep], overwrite, automaticOverwrite, config['episode'], config['templates'])
    
    # Added lock to prevent problems with accessing the same variable from different threads, this was never a problem tho
    with tasksLock: 
        global tasks, tasksLength
        tasks.extend(generatedTasks) # Extend SHOULD be thread safe anyway
        tasksLength += len(generatedTasks)
    
    functions.log(str(len(generatedTasks)) + ' tasks generated for: ' + metadata['title'] + ' in ' + functions.timediff(start2), 0, 2)
    
    db[folder] = metadata # Update metadata in database

# endregion


# Load "database"
if exists(join(workDirectory, 'db.pickle')):
    with open(join(workDirectory, 'db.pickle'), 'rb') as pk:
        try:
            db = pickle.load(pk)
            if 'version' not in db or db['version'] != dbVersion:
                functions.log('Removing database file because this is a new version of the script', 3, 3)
                db = {'version': dbVersion}
        except:
            functions.log('Error loading database from: ' + join(workDirectory, 'db.pickle'), 2, 2)

# Check for configuration file
if not exists(join(workDirectory, 'config.json')):
    log('Missing config.json inside work directory', 1, 0)
    exit()
else: loadConfig(join(workDirectory, 'config.json'))

# Check for TMDB api key
if config['tmdbApi'] == '':
    log('TMDB api key is needed to run. (WHY DID YOU REMOVE IT?!?!)', 1, 0)
    exit() 

# region Check Dependencies
dependencies = [
    'wkhtmltox',
    'ffmpeg' if config['episode']['extractImage'] else False]

for dp in [d for d in dependencies if d]:
    cl = getstatusoutput('apt-cache policy ' + dp)[1]
    if 'Installed: (none)' in cl:
        log(dp + ' is not installed', 1, 0)
        exit()
# endregion

# Start

st = time.time()
functions.log('Starting BetterCovers for directory: ' + pt, 1, 1)


th1 = Thread(target=processFolders)
th1.start()
th2 = Thread(target=processTasks)
th2.start()
th1.join()
# Write database to file
with open(join(workDirectory, 'db.pickle'), 'wb') as file:
    pickle.dump(db, file, protocol=pickle.HIGHEST_PROTOCOL)
if '--json' in argv:
    with open(join(workDirectory, 'db.json'), 'w') as js:
        js.write(json.dumps(db, indent=7))
th2.join()
functions.log('FINISH, total time was: ' + functions.timediff(st), 0, 1)

