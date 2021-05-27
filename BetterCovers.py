from glob import glob
from subprocess import call, getstatusoutput
from os import access, W_OK
from os.path import exists, join, abspath
import json
from sys import argv, exit
from datetime import timedelta, datetime
import time
from threading import Thread
import functions
from functions import log
from requests import post
from re import findall
from copy import deepcopy
from hashlib import md5

config = {}
tasks = []
running = True
processing = True
tasksLength = 0
dbVersion = 3
db = {'version': dbVersion}

# region Functions
def generateTasks(metadata, overWrite):
    conf = config[metadata['type']]
    tsks = []
    pts = conf['output'].replace('$NAME', (metadata['path'] if metadata['type'] in ['tv', 'season', 'backdrop'] else metadata['mediaFile'] if 'mediaFile' in metadata else metadata['path'] ).rpartition('.')[0].rpartition('/')[2])
    tsk = {
        'out': [],
        'type': metadata['type'],
        'title': metadata['title'],
        'generateImage': path if metadata['type'] in ['episode', 'backdrop'] and config[metadata['type']]['generateImages'] else False,
        'mediainfo': deepcopy(metadata['mediainfo']),
        'ratings': {},
        'ageRating': '',
        'cover': functions.getCover(metadata, config['covers']),
        'productionCompanies': deepcopy(metadata['productionCompanies']) if conf['productionCompanies'] else [],
        'certifications': []}
    tsk['mediainfo']['languages'] = ''

    if tsk['mediainfo']['color'] == 'HDR' and tsk['mediainfo']['resolution'] == 'UHD' and conf['mediainfo']['color']['UHD-HDR']:
        tsk['mediainfo']['color'] = 'UHD-HDR'
        tsk['mediainfo']['resolution'] = ''

    for pr in tsk['mediainfo']:
        if pr != 'languages':
            vl = tsk['mediainfo'][pr]
            tsk['mediainfo'][pr] = '' if  vl == '' or not conf['mediainfo'][pr][vl] else vl
        else:
            for lg in conf['mediainfo']['audio'].split(','):
                if lg in metadata['mediainfo']['languages']:
                    tsk['mediainfo'][pr] = lg
                    break

    for rt in metadata['ratings']:
        if conf['ratings'][rt]: 
            tsk['ratings'][rt] = deepcopy(metadata['ratings'][rt]) 
            if config['usePecentage']:
                tsk['ratings'][rt]['value'] = str(int(float(metadata['ratings'][rt]['value']) * 10)) + '%'
    
    for cr in metadata['certifications']:
        if conf['certifications'][cr]: tsk['certifications'].append(cr)

    if conf['ageRatings'][metadata['ageRating']]:
        tsk['ageRating'] = metadata['ageRating']
    
    imgNm = 'backdrop' if metadata['type'] == 'backdrop' else 'cover'
    if imgNm in metadata: tsk['image'] = metadata[imgNm]

    for pt in [join(metadata['path'], pt) for pt in pts.split(';')]:
        if overWrite or not exists(pt) or automatic: tsk['out'].append(pt)

    if len(tsk['out']) > 0:
        hs = md5(json.dumps(tsk, sort_keys=True).encode('utf8')).hexdigest()
        if not automatic or any(not exists(pt) or hs != functions.getHash(pt) for pt in tsk['out']): # Overwrites all images
            if 'image' in tsk or tsk['generateImage']: tsks.append(tsk)
            else: log('No ' + ('backdrop' if tsk['type'] == 'backdrop' else 'cover') + ' image found for: ' + tsk['title'], 3, 3)
        else: log('No need to update cover for: ' + tsk['title'], 3, 3)
    else: log('Not overwriting any image for: ' + tsk['title'], 3, 3)

    if metadata['type'] == 'tv':
        for sn in metadata['seasons']:
            tsks += generateTasks(metadata['seasons'][sn], overWrite)
            for ep in metadata['seasons'][sn]['episodes']:
                tsks += generateTasks(metadata['seasons'][sn]['episodes'][ep], overWrite)

    if metadata['type'] in ['movie', 'tv']:
        metadata['type'] = 'backdrop'
        tsks += generateTasks(metadata, overWrite)

    return tsks

def processFolder(folder):
    st = time.time()
    if folder not in db:
        metadata = {'ids': {}, 'path': folder}
        mediaFiles = functions.getMediaFiles(folder)
        metadata['title'], metadata['year'] = functions.getName(folder)
        forceSeasons = functions.updateSeasons(config['season']['output'], config['backdrop']['output'], config['episode']['output'], metadata)
        metadata['type'] = 'tv' if len(metadata['seasons']) > 0 else 'movie'

        nfo = join(folder, 'tvshow.nfo') if metadata['type'] == 'tv' else (mediaFiles[0].rpartition('.')[0] + '.nfo') if len(mediaFiles) > 0 else join(folder, 'FALSE')
        if exists(nfo): metadata['ids'] = functions.readNFO(nfo)
        db[folder] = metadata
    else:
        metadata = db[folder]
        forceSeasons = functions.updateSeasons(config['season']['output'], config['backdrop']['output'], config['episode']['output'], metadata)

    functions.getMetadata(metadata, config['omdbApi'], config['tmdbApi'], config['scraping'], config['defaultAudio'], forceSeasons)

    global tasks, tasksLength
    generatedTasks = generateTasks(deepcopy(metadata), overWrite)
    tasks += generatedTasks
    tasksLength += len(generatedTasks)
    log(str(len(generatedTasks)) + ' tasks generated for: ' + metadata['title'] + ' in ' + str(timedelta(seconds=round(time.time() - st))), 2)

def loadConfig(cfg):
    try:
        with open(cfg, 'r') as js:
            global config 
            config = json.load(js)
            if 'version' not in config or config['version'] != 3:
                log('Wrong version of config file, please update!', 1, 0)
                exit()
            if '-omdb' in argv and argv[argv.index('-omdb') + 1] != '': config['omdbApi'] = argv[argv.index('-omdb') + 1]
            if '-tmdb' in argv and argv[argv.index('-tmdb') + 1] != '': config['tmdbApi'] = argv[argv.index('-tmdb') + 1]
        with open(cfg, 'w') as out: 
            out.write(json.dumps(config, indent = 5))
    except:
        log('Error loading config file from: ' + cfg, 1, 0)
        exit()

def processFolders(folders):
    thrs = [False] * threads
    for folder in folders:
        i = 0
        while True:
            if not (thrs[i] and thrs[i].is_alive()):
                thread = Thread(target=processFolder , args=(folder, ))
                thread.start()
                thrs[i] = thread
                break
            i += 1
            if i == threads: i = 0
        if not running: break

    # Wait for threads to end
    for th in thrs: 
        if th and running: th.join()

def processTasks():
    j = 1
    thrs = [False] * threads
    thrsLength = len(str(threads))

    if not exists(join(workDirectory, 'threads')): call(['mkdir', join(workDirectory, 'threads')])
    while running and (processing or len(tasks) > 0):
        if len(tasks) > 0:
            i = 0
            while True:
                if not (thrs[i] and thrs[i].is_alive()):
                    tsk = tasks.pop()
                    thread = Thread(target=functions.processTask, args=(tsk, str(i).zfill(thrsLength)))
                    thread.start()
                    thrs[i] = thread
                    j += 1
                    break
                i += 1
                if i == threads: i = 0

    for th in thrs: 
        if th and running: th.join()    

def saveDB():
    while processing:
        with open(join(workDirectory, 'db.json'), 'w') as dbf:
            dbf.write(json.dumps(deepcopy(db), indent=7))
        time.sleep(10)
# endregion

# region Params
overWrite = '-o' in argv and argv[argv.index('-o') + 1] == 'true'
automatic = '-a' in argv and argv[argv.index('-a') + 1] == 'true'
threads = 20 if not '-w' in argv else int(argv[argv.index('-w') + 1])
config = {}
pt = argv[1]
workDirectory = abspath('./' if '-wd' not in argv else argv[argv.index('-wd') + 1])
functions.workDirectory = workDirectory
folders = sorted(glob(pt)) if '*' in pt else [pt]
gstart = time.time()
if not exists(pt) and '*' in pt and len(glob(pt)) == 0:
    log('Media path doesnt exist', 1, 0)
    exit()
if '-v' in argv: functions.logLevel = int(argv[argv.index('-v') + 1])
# endregion

# region Files
try: # Move files from executable to workdir
    pt = sys._MEIPASS
    for fl in glob(join(pt, 'files', '**'),  recursive=True):
        out = join(workDirectory, fl.partition('files/')[2])
        if not exists(out): call(['cp', '-r', fl, out])
except:
    pass

if exists(join(workDirectory, 'db.json')):
    with open(join(workDirectory, 'db.json')) as js:
        db = json.load(js)
        if db['version'] != dbVersion:
            log('Removing db file because this is a new version of the script', 3, 3)
            db = {'version': dbVersion}

if not exists(join(workDirectory, 'config.json')):
    log('Missing config file', 1, 0)
    exit()

loadConfig(join(workDirectory, 'config.json'))
if config['tmdbApi'] == '' and config['omdbApi'] == '':
    log('A single api key is needed to work (TMDB recommended)', 1, 0)
    exit() 
# endregion

# region Check Dependencies
dependencies = [
    'wkhtmltox',
    'ffmpeg' if config['episode']['generateImages'] else False]

for dp in [d for d in dependencies if d]:
    cl = getstatusoutput('apt-cache policy ' + dp)[1]
    if 'Installed: (none)' in cl:
        log(dp + ' is not installed', 1, 0)
        exit()
# endregion

try:
    log('PROCESSING ' + str(len(folders)) + ' FOLDERS')

    # Generate tasks for each folder
    PROCESSING = Thread(target=processFolders , args=(folders, ))
    PROCESSING.start()
    # Process generated tasks
    GENERATING = Thread(target=processTasks, args=())
    GENERATING.start()

    # Periodicaly save db file
    Thread(target=saveDB, args=()).start()

    PROCESSING.join()
    processing = False
    time.sleep(1)
    with open(join(workDirectory, 'db.json'), 'w') as js:
        js.write(json.dumps(db, indent=7))
    log('Finished generating tasks', 0, 2)
    GENERATING.join()
except KeyboardInterrupt:
    log('Closing BetterCovers!', 3, 0)
    running = False
    functions.logLevel = 0
    GENERATING.join()
    PROCESSING.join()
call(['rm', '-r', join(workDirectory, 'threads')])

# region Update agent library
if running: 
    if config['agent']['apiKey'] != '':
        url = config['agent']['url'] + ('/Library/refresh?api_key=' + config['agent']['apiKey'] if config['agent']['type'] == 'emby' else '/ScheduledTasks/Running/6330ee8fb4a957f33981f89aa78b030f')
        if post(url, headers={'X-MediaBrowser-Token': config['agent']['apiKey']}).status_code < 300:
            log('Succesfully updated ' + config['agent']['type'] + ' libraries (' + config['agent']['url'] + ')', 2, 2)
        else: log('Error accessing ' + config['agent']['type'] + ' at ' + config['agent']['url'])
    else: log('Not updating ' + config['agent']['type'] + ' library, API key not set.', 3, 3)
# endregion

log('DONE! Finished generating ' + str(tasksLength) + ' images in: ' + str(timedelta(seconds=round(time.time() - gstart))), 0, 0)