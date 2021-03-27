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

def processFolder(folder, thread):
    st = time.time()
    seasons = getSeasons(folder)
    type = 'tv' if len(seasons) > 0 else 'movie'
    name, year = getMediaName(folder)

    if not overWrite and type == 'movie' and exists(join(folder, 'poster.jpg')):
        return print('Poster exists')

    metadata = getMetadata(name, type, year, config['omdbApi'], config['tmdbApi'])  
    if type == 'movie' and getConfigEnabled(config['movie']['mediainfo']['config']):
        mediaFiles = []
            
        for ex in extensions: 
            mediaFiles += glob(join(folder.translate({91: '[[]', 93: '[]]'}), '*.' + ex))
        if len(mediaFiles) > 0:
            minfo = getMediaInfo(mediaFiles[0])
            if minfo:
                metadata['mediainfo'] = minfo
            else: print('Error getting media info!')
        else: print('Error getting media info no video files found on:', folder)
    elif type == 'tv' and 'tmdbid' in metadata:
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
        generateSeasonsImages(name, sns['seasons'], config['season'], thread, coverHTML)
    
    if 'cover' not in metadata: 
        return print('\033[93mCover image not found for:', name, '\033[0m')
    if exists(join(folder, 'poster.jpg')) and not access(join(folder, 'poster.jpg'), W_OK):
        return print('\033[91mCant write to:', join(folder, 'poster.jpg'), '\033[0m')
    img = generateImage(
        config['movie'],
        metadata['ratings'] if 'ratings' in metadata else [],
        metadata['mediainfo'] if 'mediainfo' in metadata else [],
        metadata['cover'],
        thread,
        coverHTML)
    if img: 
        call(['mv', '-f', img, join(folder, 'poster.jpg')])
        print('\033[92m[' + str(thread) + '] Succesfully generated cover for', name, 'in', timedelta(seconds=round(time.time() - st)), '\033[0m')
    else: print('\033[91mError generating image\033[0m')

print('STARTING')
overWrite = '-o' in argv
threads = 10 if not '-w' in argv else int(argv[argv.index('-w') + 1])
config = {}
minVotes = 5
extensions = ['mkv', 'mp4']
path = [pt for pt in argv[1:] if '/' in pt][0]
files = sorted(glob(path)) if '*' in path else [path]
lenThread = len(files) // threads
filesSplit = 5

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
while i < len(files): 
    thrsFiles.append(files[i: i + filesSplit])
    i += filesSplit

# Generate threads
thrs = [False] * threads
for fls in thrsFiles:
    i = 0
    while True:
        if not (thrs[i] and thrs[i].is_alive()):
            fn = lambda i: [processFolder(fl, i) for fl in fls]
            thread = Thread(target=fn, args=(i, ))
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
        
