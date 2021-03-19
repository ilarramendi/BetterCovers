from glob import glob
import re
import requests
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from os import path
import json
import sys

brHeight = 40
imHeight = 30
txHeight = 26
rectangleColor = (25, 25, 25, int(255 * 0.8))
textColor = '#fcfcfc'

if len(sys.argv) == 3:
    apiKey = sys.argv[2]
    with open('./config.json', 'w') as js: json.dump({'apiKey': apiKey}, js)
else: 
    with open('./config.json', 'r') as js: apiKey = json.load(js)['apiKey']


def downloadImage(url, path, retry):
    response = requests.get(url)
    i = 0
    while response.status_code != 200 and i < retry:
        sleep(1)
        response = requests.get(url)
        i += 1

    if response.status_code == 200:
        file = open(path, 'wb')
        file.write(response.content)
        file.close()
        return True
    else: 
        logText('Failed to download: ' + url, error = True)
        return False


for file in glob(sys.argv[1]): 
    if path.exists(file + '/cover.jpg'): continue # Skip if cover exists
    
    # Parse name from file
    inf = re.findall("\/([^\/]+) \(?(\d{4})\)?$", file)
    if len(inf) == 0: inf = re.findall("\/([^\/]+)$", file)
    else: inf = inf[0]

    if len(inf) == 0:
        print('\033[93mCant parse name from: ' + file + '\033[0m')
        continue
    
    name = inf[0]
    year = inf[1] if len(inf) == 2 else False
    info = {}
    
    # Search file on omdbapi
    response = requests.get('http://www.omdbapi.com/?apikey=' + apiKey + '&t=' + name.replace(' ', '+') + ('&y=' + year if year else ''))
    res = response.json()
    if response.status_code != 200 or 'Error' in res: 
        print('No info found for:', name, year)
        continue
    if year and abs(int(year) - int(re.findall('\d{4}' ,res['Year'])[0])) > 1: 
        print('Wrong info found: ' + name + ' (' + year + ') | ' + res['Title'] + ' (' + res['Year'] + ')')
        continue
    
    # Parse ratings
    if 'Metascore' in res: info['mts'] = res['Metascore']
    if 'imdbRating' in res: info['imdb'] = res['imdbRating']
    for rt in res['Ratings']:
        if rt['Source'] == 'Rotten Tomatoes':
            info['rt'] = rt['Value']
            break
    infoIndex = list(filter(lambda inf: info[inf] != 'N/A', info)) # Filter ratings
    if len(infoIndex) == 0:
        print('No ratings found for:', res['Title'])
        continue

    # Download image
    if 'Poster' not in res or not downloadImage(res['Poster'], 'cover.jpg', 3):
        print('Poster missing or failed to download for: ' + res['Title'])
        continue

    # Add ratings to images
    img = Image.open("cover.jpg").convert("RGBA")
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    ImageDraw.Draw(overlay).rectangle(((0, img.size[1] - brHeight), (img.size[0], img.size[1])), fill=rectangleColor) # Rectangle
    img = Image.alpha_composite(img, overlay).convert("RGB")
    font = ImageFont.truetype("Roboto-Medium.ttf", txHeight) # Font can be customized here
    draw = ImageDraw.Draw(img)

    le = 300 // len(infoIndex)
    x = 0
    space = 15 // len(infoIndex)
    for rt in infoIndex:
        im = Image.open(rt + ".png")
        tsize = draw.textsize(info[rt], font)[0]
        sp  = (le - im.size[0] - tsize - space) // 2
        img.paste(im, (x + sp, img.size[1] - imHeight - (brHeight - imHeight) // 2), im)
        draw.text((x + sp + im.size[0] + space, img.size[1] - txHeight - (brHeight - txHeight) // 2 - 1) , info[rt], textColor, font=font)
        x += le

    img.save(file + '/cover.jpg')
    print('\033[92m' + 'Cover image saved for: ' + res['Title'] + '\033[0m')
