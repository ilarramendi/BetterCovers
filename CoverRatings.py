from glob import glob
from re import findall
from subprocess import call, getstatusoutput
from requests import get
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from os import path, access, W_OK
import json
import sys

brHeight = 40
imHeight = 30
txHeight = 25
space = 5 if not '-s' in sys.argv else int(sys.argv[sys.argv.index('-s') + 1])
padding = 15
rectangleColor = '#191919af' if not '-b' in sys.argv else sys.argv[sys.argv.index('-b') + 1]
textColor = '#ffffffb4' if not '-t' in sys.argv else sys.argv[sys.argv.index('-t') + 1]
hAlign = 'l' if '-hl' in sys.argv else 'r' if '-hr' in sys.argv else 'c'
vAlign = 't' if '-vt' in sys.argv else 'b'
mediaInfo = '-i' in sys.argv
overWrite = '-o' in sys.argv

if '-a' in sys.argv:
    apiKey = sys.argv[sys.argv.index('-a') + 1]
    with open('./config.json', 'w') as js: json.dump({'apiKey': apiKey}, js)
elif path.exists('./config.json'):
    with open('./config.json', 'r') as js: apiKey = json.load(js)['apiKey']
else: 
    print('Please supply an api key with: -a apiKey')
    sys.exit()

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = path.abspath(".")
    return path.join(base_path, relative_path)

def downloadImage(url, path, retry):
    response = get(url)
    i = 0 
    while response.status_code != 200 and i < retry:
        sleep(1)
        response = get(url)
        i += 1

    if response.status_code == 200:
        file = open(path, 'wb')
        file.write(response.content)
        file.close()
        return True
    else: 
        logText('Failed to download: ' + url, error = True)
        return False

i = 1
files = sorted(glob([pt for pt in sys.argv[1:] if '/' in pt][0]))
lenFiles = str(len(files))
for file in files:
    print('[' + str(i).zfill(len(lenFiles)) + '/' + lenFiles +'] ', end='')
    i += 1
    if path.exists(file + '/poster.jpg') and not overWrite: # Skip if cover exists
        print('Cover already exists and overwrite is disabled')
        continue 
    if not access(file, W_OK) or (path.exists(file + '/poster.jpg') and not access(file + '/poster.jpg', W_OK)):
        print('\033[91mCant write poster (acces denied) on:', file, '\033[0m')
        continue
    # region Parse name from file
    inf = findall("\/([^\/]+) \(?(\d{4})\)?$", file)
    if len(inf) == 0: inf = findall("\/([^\/]+)$", file)
    else: inf = inf[0]
    if len(inf) == 0:
        print('\033[93mCant parse name from:', file, '\033[0m')
        continue
    # endregion

    name = inf[0]
    year = inf[1] if len(inf) == 2 else False
    info = {}
    
    # region Search file on omdbapi
    response = get('http://www.omdbapi.com/?apikey=' + apiKey + '&tomatoes=true&t=' + name.replace(' ', '+') + ('&y=' + year if year else ''))
    if response.status_code == 401:
        print('\033[91mDaily Api Limit Reached!!!!!\033[0m')
        break
    if response.status_code != 200 or'application/json' not in response.headers.get('content-type'): 
        print('\033[91mError connecting to omdbapi, code:', response.status_code, name, '\033[0m')
        continue
    res = response.json()
    if 'Error' in res: 
        print('\033[93mNo info found for:', name, year, '\033[0m')
        if res['Error'] != 'Movie not found!':
            print('\033[91', res['Error'], '\033[0m')
        continue
    if year and abs(int(year) - int(findall('\d{4}' ,res['Year'])[0])) > 1: 
        print('\033[93mWrong info found: ' + name + ' (' + year + ') | ' + res['Title'] + ' (' + res['Year'] + ')\033[0m')
        continue
    # endregion
    
    # region Parse ratings
    if 'Metascore' in res: info['mts'] = res['Metascore']
    if 'imdbRating' in res: info['imdb'] = res['imdbRating']
    rts = [rt for rt in res['Ratings'] if rt['Source'] == 'Rotten Tomatoes']
    if len(rts) > 0 and rts[0]['Value'] != 'N/A': info['rt'] = str(int(rts[0]['Value'][:-1]) / 10)
    infoIndex = list(filter(lambda inf: info[inf] != 'N/A', info)) # Filter ratings
    if 'mts' in infoIndex: info['mts'] = str(int(info['mts']) / 10)
    if len(infoIndex) == 0 and not mediaInfo:
        print('\033[93mNo ratings found and mediaInfo not set for:', res['Title'], '\033[0m')
        continue
    infoIndex.sort()
    # endregion

    # region Download image
    if not ('Poster' in res and res['Poster'] != 'N/A' and downloadImage(res['Poster'], 'cover.jpg', 3)):
        print('\033[93mPoster missing or failed to download for:', res['Title'], '\033[0m')
        continue
    # endregion

    # region Add ratings to images
    if len(infoIndex) > 0:
        img = Image.open("./cover.jpg").convert("RGBA").resize((300,450))
        overlay = Image.new('RGBA', img.size, (0,0,0,0))
        recsize = ((0, img.size[1] - brHeight if vAlign == 'b' else 0), (img.size[0], img.size[1] if vAlign == 'b' else brHeight)) 
        ImageDraw.Draw(overlay).rectangle(recsize, fill=rectangleColor)
        img = Image.alpha_composite(img, overlay).convert("RGB")
        font = ImageFont.truetype(resource_path("media/font.ttf"), txHeight)
        draw = ImageDraw.Draw(img)

        le = (300 - padding) // len(infoIndex) 
        x = padding if hAlign == 'c' else 300 if hAlign == 'r' else 0
        space = 3
        for rt in infoIndex if hAlign != 'r' else reversed(infoIndex):
            im = Image.open(resource_path('media/' + rt + ".png")) 
            tsize = draw.textsize(info[rt], font)[0]
            sp = (le - im.size[0] - tsize - space) // 2
            imgPos = (x + sp if hAlign == 'c' else (x + space) if hAlign == 'l' else x - tsize - space * 2 - im.size[0], (img.size[1] - imHeight - (brHeight - imHeight) // 2) if vAlign == 'b' else (brHeight - imHeight) // 2)
            img.paste(im, imgPos, im)
            txtPos = (x + sp + im.size[0] + space if hAlign == 'c' else x + space * 2 + im.size[0] if hAlign == 'l' else imgPos[0] + im.size[0] + space, img.size[1] - txHeight - (brHeight - txHeight) // 2 - 1 if vAlign == 'b' else (brHeight - txHeight) // 2 - 1)
            draw.text(txtPos, info[rt], textColor, font=font)
            x = x + le if hAlign == 'c' else txtPos[0] + tsize if hAlign == 'l' else imgPos[0]
    else: img = Image.open("./cover.jpg").resize((300,450))
    # endregion
    
    # region Add mediaInfo to images
    if mediaInfo:
        mediaFiles = []
        for ex in ['mkv', 'mp4']: mediaFiles += glob(file + '/*.' + ex)
        if len(mediaFiles) == 1:
            out = getstatusoutput('mediainfo "' + mediaFiles[0] + '" --Inform="Video;%colour_primaries%,%Height%,%Width%,%Format%"')
            if out[0] == 0:
                x = img.size[0] - space
                y = brHeight + 2 if vAlign == 't' and len(infoIndex) > 0 else 5
                if '2160' in out[1] or '3840' in out[1]:
                    im = Image.open(resource_path('media/4k.png'))
                    img.paste(im, (x - im.size[0], y), im)
                    x -= im.size[0] + space
                if 'HEVC' in out[1]:
                    im = Image.open(resource_path('media/hevc.png'))
                    img.paste(im, (x - im.size[0], y), im)
                    x -= im.size[0] + space
                if 'BT.2020' in out[1]:
                    im = Image.open(resource_path('media/hdr.png'))
                    img.paste(im, (x - im.size[0], y), im)
            else: print('Error getting media info, Is mediainfo installed?', out[1])
        else: print('No media files found, skipping MediaInfo for:', res['Title'])
    # endregion
    
    print('\033[92m' + 'Cover image ' + ('overwriten' if path.exists(file + '/poster.jpg') else'saved') + ' for: ' + res['Title'] + '\033[0m')
    img.save(file + '/poster.jpg')
    img.close()
    call(['rm', './cover.jpg'])
    