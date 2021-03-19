from glob import glob
from re import findall
from subprocess import call
from requests import get
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from os import path
import json
import sys

brHeight = 40
imHeight = 30
txHeight = 25
space = 3
padding = 15
rectangleColor = '#191919af' if not '-b' in sys.argv else sys.argv[sys.argv.index('-b') + 1]
textColor = '#ffffffb4' if not '-t' in sys.argv else sys.argv[sys.argv.index('-t') + 1]
hAlign = 'l' if '-hl' in sys.argv else 'r' if '-hr' in sys.argv else 'c'
vAlign = 't' if '-vt' in sys.argv else 'b'


if '-a' in sys.argv:
    apiKey = sys.argv[sys.argv.index('-a') + 1]
    with open('./config.json', 'w') as js: json.dump({'apiKey': apiKey}, js)
else: 
    with open('./config.json', 'r') as js: apiKey = json.load(js)['apiKey']

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
for file in glob([pt for pt in sys.argv if '/' in pt][0]): 
    if path.exists(file + '/poster.jpg'): continue # Skip if cover exists
    
    # Parse name from file
    inf = findall("\/([^\/]+) \(?(\d{4})\)?$", file)
    if len(inf) == 0: inf = findall("\/([^\/]+)$", file)
    else: inf = inf[0]

    if len(inf) == 0:
        print('\033[93mCant parse name from: ' + file + '\033[0m')
        continue
    
    name = inf[0]
    year = inf[1] if len(inf) == 2 else False
    info = {}
    
    # Search file on omdbapi
    response = get('http://www.omdbapi.com/?apikey=' + apiKey + '&tomatoes=true&t=' + name.replace(' ', '+') + ('&y=' + year if year else ''))
    res = response.json()
    if response.status_code != 200 or 'Error' in res: 
        print('No info found for:', name, year)
        continue
    if year and abs(int(year) - int(findall('\d{4}' ,res['Year'])[0])) > 1: 
        print('Wrong info found: ' + name + ' (' + year + ') | ' + res['Title'] + ' (' + res['Year'] + ')')
        continue
    
    # Parse ratings
    if 'Metascore' in res: info['mts'] = res['Metascore']
    if 'imdbRating' in res: info['imdb'] = res['imdbRating']
    rts = [rt for rt in res['Ratings'] if rt['Source'] == 'Rotten Tomatoes']
    if len(rts) > 0 and rts[0]['Value'] != 'N/A': info['rt'] = str(int(rts[0]['Value'][:-1]) / 10)
    infoIndex = list(filter(lambda inf: info[inf] != 'N/A', info)) # Filter ratings
    if 'mts' in infoIndex: info['mts'] = str(int(info['mts']) / 10)
    if len(infoIndex) == 0:
        print('No ratings found for:', res['Title'])
        continue
    infoIndex.sort()

    # Download image
    if not ('Poster' in res and res['Poster'] != 'N/A' and downloadImage(res['Poster'], 'cover.jpg', 3)):
        print('Poster missing or failed to download for: ' + res['Title'])
        continue

    # Add ratings to images
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

    img.save(file + '/poster.jpg')
    call(['rm', './cover.jpg'])
    print('\033[92m' + 'Cover image saved for: ' + res['Title'] + '\033[0m')