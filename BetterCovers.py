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

config = {}
tasks = []
running = True
processing = True
tasksLength = 0
dbVersion = 1
db = {'version': dbVersion}

# region Functions
def generateTasks(metadata, overWrite):
    conf = config[metadata['type']]
    tsks = []
    tsk = {
        'out': join(metadata['path'], conf['output']) if metadata['type'] != 'episode' else metadata['path'].rpartition('.')[0] + '.jpg',
        'type': metadata['type'],
        'title': metadata['title'],
        'overwrite': overWrite,
        'generateImage': path if metadata['type'] in ['episode', 'backdrop'] and config[metadata['type']]['generateImages'] else False,
        'mediainfo': deepcopy(metadata['mediainfo']),
        'ratings': {},
        'ageRating': '',
        'overlay': ''}
    tsk['mediainfo']['languages'] = ''
    
    for ol in config['overlays']:
        if (metadata['type'] in ol['type'].split(',') or ol['type'] == '*') and (ol['path'] in metadata['path'] or ol['path'] == '*'):
            tsk['overlay'] = ol['name']
    if tsk['mediainfo']['color'] == 'HDR' and tsk['mediainfo']['resolution'] == 'UHD' and conf['mediainfo']['config']['color']['UHD-HDR']:
        tsk['mediainfo']['color'] = 'UHD-HDR'
        tsk['mediainfo']['resolution'] = ''

    for pr in tsk['mediainfo']:
        if pr != 'languages':
            vl = tsk['mediainfo'][pr]
            tsk['mediainfo'][pr] = '' if  vl == '' or not conf['mediainfo']['config'][pr][vl] else vl
        else:
            for lg in conf['mediainfo']['audio'].split(','):
                if lg in metadata['mediainfo']['languages']:
                    tsk['mediainfo'][pr] = lg
                    break

    if 'ratings' in metadata:
        for rt in metadata['ratings']:
            if conf['ratings']['config'][rt]: tsk['ratings'][rt] = metadata['ratings'][rt] 

    if 'ageRating' in metadata and conf['ageRatings']['config'][metadata['ageRating']]:  tsk['ageRating'] = metadata['ageRating']

    imgNm = 'backdrop' if metadata['type'] == 'backdrop' else 'cover'
    if imgNm in metadata: tsk['image'] = metadata[imgNm]

    if overWrite or not exists(tsk['out']):
        if ('image' in tsk or tsk['generateImage']) and ('mediainfo' in tsk or 'ratings' in tsk): tsks.append(tsk)
    else: log('Existing cover image found for: ' + title + (' S' + str(season) if season else '') + ('E' + str(episode) if episode else ''), 3, 3)

    if metadata['type'] == 'tv':
        for sn in metadata['seasons']:
            tsks += generateTasks(metadata['seasons'][sn], overWrite)
            for ep in metadata['seasons'][sn]['episodes']:
                tsks += generateTasks(metadata['seasons'][sn]['episodes'][ep], overWrite)

    if metadata['type'] in ['movie', 'tv', 'season']:
        metadata['type'] = 'backdrop'
        tsks += generateTasks(metadata, overWrite)

    return tsks

def getName(folder):
    inf = findall("\/([^\/]+)[ \.]\(?(\d{4})\)?", folder)
    if len(inf) == 0: 
        inf = findall("\/([^\/]+)$", folder)
        if len(inf) == 0:
            log('Cant parse name from: ' + folder, 3, 1)
            return [False, False]
        else: return [inf[0], False]
    else: return [inf[0][0].translate({'.': ' ', '_': ' '}), inf[0][1]]

def processFolder(folder):
    st = time.time()
    if folder in db:
        functions.updateMetadata(db[folder], config['metadataUpdateInterval'], config['omdbApi'], config['tmdbApi'], config['scraping'])
        metadata = deepcopy(db[folder])
    else:
        metadata = {'ids': {}, 'path': folder}
        mediaFiles = functions.getMediaFiles(folder)
        metadata['title'], metadata['year'] = getName(folder)
        metadata['seasons'] = functions.getSeasons(folder, config['season']['output'], config['backdrop']['output'], metadata['title'])
        metadata['type'] ='tv' if len(metadata['seasons']) > 0 else 'movie'

        if metadata['type'] == 'tv': # Get IDS from NFO
            nfo = join(folder, 'tvshow.nfo')
            if exists(nfo): metadata['ids'] = functions.readNFO(nfo)
        elif len(mediaFiles) == 1:
            nfo = mediaFiles[0].rpartition('.')[0] + '.nfo'
            if exists(nfo): metadata['ids'] = functions.readNFO(nfo)

        if metadata['type'] == 'movie': # Get mediainfo
            if len(mediaFiles) == 1:
                if functions.getConfigEnabled(config['movie']['mediainfo']['config']):
                    metadata['mediainfoDate'] = datetime.now().strftime("%d/%m/%Y")
                    metadata['mediainfo'] = functions.getMediaInfo(mediaFiles[0], config['defaultAudio'])
        else: log('Error finding media file on: ' + folder, 3, 3)

        functions.getMetadata(metadata, config['omdbApi'], config['tmdbApi'], config['scraping'])
        if len(metadata['ids']) == 0 and not metadata['title']: return log('No id or name can be found for: ' + folder, 1, 1)  

        if metadata['type'] == 'tv':
            metadata = functions.getSeasonsMetadata(metadata,
                config['omdbApi'],
                config['tmdbApi'],
                #functions.getConfigEnabled(config['tv']['mediainfo']['config']) or functions.getConfigEnabled(config['season']['mediainfo']['config']),
                not exists(folder + '/' + config['tv']['output']) or not exists(folder + '/' + config['backdrop']['output']),
                overWrite,
                config['defaultAudio'])
        db[folder] = deepcopy(metadata)

    #if not overWrite and metadata['type'] == 'movie' and exists(folder + '/' + config['movie']['output']) and exists(folder + '/' + config['backdrop']['output']):
    #    return log('Existing cover image found for: ' + metadata['title'], 3, 3) 
    global tasks, tasksLength
    generatedTasks = generateTasks(metadata, overWrite)
    tasks += generatedTasks
    tasksLength += len(generatedTasks)
    log('Succesfully generated ' + str(len(generatedTasks)) + ' tasks for: ' + metadata['title'] + ' in ' + str(timedelta(seconds=round(time.time() - st))), 2)

def processTask(task, thread, taskPos):
    st = time.time()
    img = functions.generateImage(
        config[task['type']],
        task['ratings'],
        task['ageRating'] if 'ageRating' in task else False,
        task['language'] if 'language' in task else False,
        task['mediainfo'] if 'mediainfo' in task else False,
        task['image'] if not task['generateImage'] else False,
        thread,
        coverHTML,
        task['out'],
        task['generateImage'])
    
    log(('[' + taskPos + '/' + str(tasksLength) + '][' + thread + '] ' if functions.logLevel > 2 else '') +
        ('Succesfully generated ' if img else 'Error generating ') + ('backdrop' if task['type'] == 'backdrop' else 'cover') +
        ' image for ' +
        task['title'] +
        (' S' + str(task['season']) if task['season'] else '') +
        ('E' + str(task['episode']) if task['episode'] else '') +
        ' in ' +
        str(round(time.time() - st)) + 's',
        2 if img else 1)

def loadConfig(cfg):
    try:
        with open(cfg, 'r') as js:
            global config 
            config = json.load(js)
            if 'version' not in config or config['version'] != 1:
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
                    thread = Thread(target=functions.generateIMage2, args=(tsk, config[tsk['type']], str(i).zfill(thrsLength)))
                    thread.start()
                    thrs[i] = thread
                    j += 1
                    break
                i += 1
                if i == threads: i = 0

    for th in thrs: 
        if th and running: th.join()    
# endregion

# region Params
overWrite = '-o' in argv and argv[argv.index('-o') + 1] == 'true'
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
    log('A single api key is needed to work', 1, 0)
    exit() 

if exists(join(workDirectory, 'cover.html')):
    with open(join(workDirectory, 'cover.html'), 'r') as fl: functions.coverHTML = fl.read()
else:
    log('Missing cover.html', 1, 0)
    exit()
if not exists(join(workDirectory, 'cover.css')):
    log('Missing cover.css', 1, 0)
    exit()
# endregion

# region Check Dependencies
dependencies = [
    'mediainfo' if functions.getConfigEnabled(config['tv']['mediainfo']['config']) or functions.getConfigEnabled(config['season']['mediainfo']['config']) or functions.getConfigEnabled(config['episode']['mediainfo']['config']) or functions.getConfigEnabled(config['movie']['mediainfo']['config']) else False,
    'wkhtmltopdf',
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

    PROCESSING.join()
    processing = False
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
    else: log('Not updating ' + config['agent']['type'] + ' library, Are api and url set?', 3, 3)
# endregion

log('DONE! Finished generating ' + str(tasksLength) + ' images in: ' + str(timedelta(seconds=round(time.time() - gstart))), 0, 0)