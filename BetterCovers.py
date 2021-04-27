from glob import glob
from subprocess import call
from os import access, W_OK
from os.path import exists, realpath, join
import json
from sys import argv, exit
from datetime import timedelta
import time
from threading import Thread
from functions import *

tasks = []

def generateTasks(metadata, path, type, title, overWrite, season = False, episode = False):
    conf = config[type]
    tsk = {
        'out': join(path, 'folder.jpg') if type != 'episode' else path.rpartition('.')[0] + '.jpg',
        'type': type,
        'title': title,
        'season': season,
        'episode': episode,
        'overwrite': overWrite,
        'generateImage': path if type == 'episode' and config['episode']['generateImages'] else False}
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
    
    if 'cover' in metadata: tsk['image'] = metadata['cover']
    if ('cover' in metadata or tsk['generateImage']) and ('mediainfo' in tsk or 'ratings' in tsk): tasks.append(tsk)

    tsk2 = tsk.copy()
    if 'backdrop' in metadata: tsk2['image'] = metadata['backdrop']
    tsk2['type'] = 'backdrop'
    tsk2['out'] = tsk2['out'].rpartition('/')[0] + '/backdrop.jpg'
    if ('backdrop' in metadata or tsk2['generateImage']) and ('mediainfo' in tsk2 or 'ratings' in tsk2): tasks.append(tsk2)
    if type == 'tv' and 'seasons' in metadata:
        for season in metadata['seasons']:
            generateTasks(metadata['seasons'][season], metadata['seasons'][season]['path'], 'season', title, overWrite, season)
    
    if type == 'season' and 'episodes' in metadata:
        for episode in metadata['episodes']:
            generateTasks(metadata['episodes'][episode], metadata['episodes'][episode]['path'], 'episode', title, overWrite, season, episode)

def processFolder(folder):
    seasons = getSeasons(folder)
    type = 'tv' if len(seasons) > 0 else 'movie'
    name, year = getMediaName(folder)
    st = time.time()

    metadata = getMetadata(name, type, year, config['omdbApi'], config['tmdbApi'])

    if type == 'tv':
        sns = getSeasonsMetadata(
            metadata['imdbid'] if 'imdbid' in metadata else False,
            metadata['tmdbid'] if 'tmdbid' in metadata else False,
            seasons,
            config['omdbApi'],
            config['tmdbApi'],
            getConfigEnabled(config['tv']['mediainfo']['config']) or getConfigEnabled(config['season']['mediainfo']['config']),
            minVotes,
            name)
        metadata['seasons'] = sns['seasons']
        if 'mediainfo' in sns: metadata['mediainfo'] = sns['mediainfo']
        else: print('\033[91mError getting mediainfo for:', name, '\033[0m')
    elif type == 'movie' and getConfigEnabled(config['movie']['mediainfo']['config']):
        mediaFiles = []
        for ex in extensions: 
            mediaFiles += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex))
        if len(mediaFiles) > 0:
            minfo = getMediaInfo(mediaFiles[0])
            if minfo: metadata['mediainfo'] = minfo
            else: print('\033[91mError getting mediainfo for:', name, '\033[0m')
        else: print('\033[91mError getting mediainfo no video files found on:', folder, '\033[0m')
       
    generateTasks(metadata, folder, type, name, overWrite)
    print('\033[92mMetadata and mediainfo found for:', name, 'in', timedelta(seconds=round(time.time() - st)), '\033[0m')

def processTask(task, thread):
    if task['overwrite'] or not exists(task['out']):
        st = time.time()
        img = generateImage(
            config[task['type']],
            task['ratings'] if 'ratings' in task else False,
            task['mediainfo'] if 'mediainfo' in task else False,
            task['image'] if not task['generateImage'] else False,
            thread,
            coverHTML,
            task['out'],
            task['generateImage'])
        print(
            '\033[92m[' + str(thread) + ']Succesfully generated image for:' if img else '\033[91m[' + str(thread) + ']Error generating image for:',
            task['title'],
            '(' + task['type'] + ')',
            'S' + str(task['season']) if task['season'] else '',
            'E' + str(task['episode']) if task['episode'] else '',
            'in',
            timedelta(seconds=round(time.time() - st)),
            '\033[0m')
    else: 
        print(
            '\033[93m[' + str(thread) + ']Existing cover found for:',
            task['title'],
            'S' + str(task['season']) if task['season'] else '',
            'E' + str(task['episode']) if task['episode'] else '',
            '\033[0m')

# region Params
overWrite = '-o' in argv and argv[argv.index('-o') + 1] == 'true'
threads = 20 if not '-w' in argv else int(argv[argv.index('-w') + 1])
config = {}
pt = argv[1]
cfg = './config.json' if '-c' not in argv else argv[argv.index('-c') + 1]
files = sorted(glob(pt)) if '*' in pt else [pt]
threadSplit = 5
gstart = time.time()
if not exists(pt) and '*' in pt and len(glob(pt)) == 0:
    print('Path dosnt exist')
    exit()
# endregion

# region Files
if not exists(cfg):
    print('Missing config.json, downloading default config.')
    if call(['wget', 'https://raw.githubusercontent.com/ilarramendi/Cover-Ratings/main/config.json', '-q']) == 0:
        print('Succesfully downloaded default config.')
    else: 
        print('\033[91mError downloading default config\033[0m')
        exit()

try:
    with open(cfg, 'r') as js: 
        config = json.load(js)
except:
    print('\033[91mError loading ./config.json\033[0m')
    exit()

if '-omdb' in argv and argv[argv.index('-omdb') + 1] != '': config['omdbApi'] = argv[argv.index('-omdb') + 1]
if '-tmdb' in argv and argv[argv.index('-omdb') + 1] != '': config['tmdbApi'] = argv[argv.index('-tmdb') + 1] 
if config['tmdbApi'] == '' and config['omdbApi'] == '':
    print('\033[91mA single api key is needed to work\033[0m')
    exit()
with open(cfg, 'w') as out: 
    out.write(json.dumps(config, indent = 5))    

if exists(resource_path('cover.html')): 
    with open(resource_path('cover.html'), 'r') as fl: coverHTML = fl.read()
else:
    print('\033[91mMissing cover.html\033[0m')
    exit()
if not exists(resource_path('cover.css')):
    print('\033[91mMissing cover.css\033[0m')
    exit()

try:
    pt = sys._MEIPASS
except Exception: 
    pt = realpath(__file__).rpartition('/')[0]
# endregion

# region Check Dependencies
dependencies = [
    'mediainfo' if getConfigEnabled(config['tv']['mediainfo']['config']) or getConfigEnabled(config['season']['mediainfo']['config']) or getConfigEnabled(config['episode']['mediainfo']['config']) or getConfigEnabled(config['movie']['mediainfo']['config']) else False,
    'cutycapt',
    'ffmpeg' if config['episode']['generateImages'] else False]

for dp in [d for d in dependencies if d]:
    cl = getstatusoutput('apt-cache policy ' + dp)[1]
    if 'Installed: (none)' in cl:
        print(dp, 'is not installed')
        exit()
# endregion

print('DOWNLOADING METADATA AND GETTING MEDIAINFO FOR', len(files), 'FOLDERS')

# region Download Metadata
thrs = [False] * threads
for file in files:
    i = 0
    while True:
        if not (thrs[i] and thrs[i].is_alive()):
            thread = Thread(target=processFolder , args=(file, ))
            thread.start()
            thrs[i] = thread
            break
        i += 1
        if i == threads: i = 0

# Wait for threads to end
for th in thrs: 
    if th: th.join()
# endregion

print('GENERATING IMAGES FOR', len(tasks), 'ITEMS')

# region Start Threads
# Generating nedded files for threads
if not exists(join(pt, 'threads')): call(['mkdir', join(pt, 'threads')])
for i in range(threads):
    pth = join(pt, 'threads', str(i))
    if not exists(pth): call(['mkdir', pth])

thrs = [False] * threads
for tsk in tasks:
    i = 0
    while True:
        if not (thrs[i] and thrs[i].is_alive()):
            thread = Thread(target=processTask, args=(tsk, i, ))
            thread.start()
            thrs[i] = thread
            break
        i += 1
        if i == threads: i = 0

# Wait for threads to end
for th in thrs: 
    if th: th.join()
# endregion

call(['rm', '-r', join(pt, 'threads')])
print('DONE, total time was:', timedelta(seconds=round(time.time() - gstart)))
        
