from glob import glob
from subprocess import call
from os import access, W_OK
from os.path import exists, realpath, join
import json
from sys import argv
from datetime import timedelta
import time
from threading import Thread
from functions import *

tasks = []

def generateTasks(metadata, path, type):
    conf = config[type]
    tsk = {'path': join(path, 'poster.jpg') if type != 'episode' else path.rpartition('.')[0] + '.jpg', 'type': type}
    if 'mediainfo' in metadata:
        cfg = []
        if 'HDR' in metadata['mediainfo'] and 'UHD' in metadata['mediainfo'] and conf['mediainfo']['config']['UHD-HDR']:
            metadata['mediainfo'].remove('HDR')
            metadata['mediainfo'].remove('UHD')
            cfg.append('UHD-HDR')
        for mi in metadata['mediainfo']:
            if conf['mediainfo']['config'][mi]: cfg.append(mi)
        if len(cfg) > 0:
            tsk['mediainfo'] = cfg
    
    if 'ratings' in metadata:
        cfg = {}
        for rt in metadata['ratings']:
            if conf['ratings']['config'][rt]: cfg[rt] = metadata['ratings'][rt]
        if len(cfg) > 0:
            tsk['ratings'] = cfg
    
    if 'cover' in metadata and ('mediainfo' in tsk or 'ratings' in tsk): 
        tsk['image'] = metadata['cover']
        tasks.append(tsk)

    if type == 'tv' and 'seasons' in metadata:
        for season in metadata['seasons']:
            generateTasks(metadata['seasons'][season], metadata['seasons'][season]['path'], 'season')
    
    if type == 'season' and 'episodes' in metadata:
        for episode in metadata['episodes']:
            generateTasks(metadata['episodes'][episode], metadata['episodes'][episode]['path'], 'episode')

def processFolder(folder):
    seasons = getSeasons(folder)
    type = 'tv' if len(seasons) > 0 else 'movie'
    name, year = getMediaName(folder)

    if not overWrite and type == 'movie' and exists(join(folder, 'poster.jpg')):
        return print('Poster exists')

    metadata = getMetadata(name, type, year, config['omdbApi'], config['tmdbApi'])
    if 'cover' not in metadata:
        return print('Cover image not found')

    if type == 'tv' and 'tmdbid' in metadata:
        print('Getting seasons metadata and mediainfo for:', name)
        sns = getSeasonsMetadata(
            metadata['imdbid'] if 'imdbid' in metadata else False,
            metadata['tmdbid'],
            seasons,
            config['omdbApi'],
            config['tmdbApi'],
            getConfigEnabled(config['tv']['mediainfo']['config']) or getConfigEnabled(config['season']['mediainfo']['config']),
            minVotes)
        metadata['seasons'] = sns['seasons']
        if 'mediainfo' in sns: metadata['mediainfo'] = sns['mediainfo']
        else: print('Error getting mediainfo for tv show!')
    elif type == 'movie' and getConfigEnabled(config['movie']['mediainfo']['config']):
        mediaFiles = []
        for ex in extensions: 
            mediaFiles += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex))
        if len(mediaFiles) > 0:
            minfo = getMediaInfo(mediaFiles[0])
            if minfo: metadata['mediainfo'] = minfo
            else: print('Error getting media info!')
        else: print('Error getting media info no video files found on:', folder)
    
    generateTasks(metadata, folder, type)
    #print(json.dumps(metadata, indent = 5))

def processTask(tasks, thread):
    for task in tasks:
        st = time.time()
        if generateImage(
            config[task['type']],
                task['ratings'] if 'ratings' in task else False,
                task['mediainfo'] if 'mediainfo' in task else False,
                task['image'],
                thread,
                coverHTML,
                task['path']):
            print('Succesfully generated image in', timedelta(seconds=round(time.time() - st)))
            #print(task)

def downloadAllMetadata(folders):
    for folder in folders:
        processFolder(folder)

print('STARTING')

# region Params
overWrite = '-o' in argv
threads = 10 if not '-w' in argv else int(argv[argv.index('-w') + 1])
config = {}
path = [pt for pt in argv[1:] if '/' in pt][0]
files = sorted(glob(path)) if '*' in path else [path]
threadSplit = 5
metadataDownloaded = False
# endregion

# region Files
if exists('./config.json'):
    with open('./config.json', 'r') as js: 
        config = json.load(js)
    if '-omdb' in argv: config['omdbApi'] = argv[argv.index('-omdb') + 1]
    if '-tmdb' in argv: config['tmdbApi'] = argv[argv.index('-tmdb') + 1]    
    with open('./config.json', 'w') as out: 
        out.write(json.dumps(config, indent = 5))
else: 
    print('Missing config.json')
    call(['pkill', '-f', 'BetterCovers'])

if exists(resource_path('cover.html')): 
    with open(resource_path('cover.html'), 'r') as fl: coverHTML = fl.read()
else:
    print('Missing cover.html')
    call(['pkill', '-f', 'BetterCovers'])
if not exists(resource_path('cover.css')):
    print('Missing cover.scss')
    call(['pkill', '-f', 'BetterCovers'])
# endregion

print('DOWNLOADING METADATA FOR', len(files), 'FOLDERS')

i = 0
thrs = [False] * threads
while i < len(files):
    j = 0
    while True:
        if not (thrs[j] and thrs[j].is_alive()):
            thread = Thread(target=downloadAllMetadata, args=(files[i: i + 2], ))
            thread.start()
            thrs[j] = thread
            j += 1
            if j == threads: j = 0
            i += 2
            break
        j += 1
        if j == threads: j = 0

# Wait for threads to end
for th in thrs: 
    if th: th.join()

print('GENERATING IMAGES FOR', len(tasks), 'ITEMS')
# Get temp folder or path next to script
try:
    pt = sys._MEIPASS
except Exception: 
    pt = realpath(__file__).rpartition('/')[0]

# Create temp files for threads
if not exists(join(pt, 'threads')): call(['mkdir', join(pt, 'threads')])
for i in range(threads):
    pth = join(pt, 'threads', str(i))
    if not exists(pth): call(['mkdir', pth])

# Split files for threads
thrsFiles = []
i = 0
while i < len(tasks): 
    thrsFiles.append(tasks[i: i + threadSplit])
    i += threadSplit

# Generate threads
thrs = [False] * threads
for fls in thrsFiles:
    i = 0
    while True:
        if not (thrs[i] and thrs[i].is_alive()):
            thread = Thread(target=processTask, args=(fls, i, ))
            thread.start()
            thrs[i] = thread
            i += 1
            if i == threads: i = 0
            break
        i += 1
        if i == threads: i = 0

# Wait for threads to end
for th in thrs: 
    if th: th.join()

call(['rm', '-r', join(pt, 'threads')])
print('DONE')
        
