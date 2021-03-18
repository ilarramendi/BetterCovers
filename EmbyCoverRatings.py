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
txHeight = 25

extensions = ['mp4', 'mkv']

with open('./config.json', 'r') as json_file:
    apiKey = json.load(json_file)['apiKey']

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

files = []
for ex in extensions:
    files += glob(sys.argv[1] + '.' + ex)

i = 1
for file in files: 
    if not path.exists(file.rpartition('/')[0] + '/cover.jpg'):
        name, year = re.findall('\/([^\/]+)\((\d+)\)', file)[0]
        info = {}
        if name[-1] == ' ': name = name[:-1]
        
        response = requests.get('http://www.omdbapi.com/?apikey=' + apiKey + '&t=' + name.replace(' ', '+'))
        res = response.json()
        if response.status_code != 200 or 'Error' in res: print('No movies found')
        else:
            yr = int(re.findall('\d{4}' ,res['Year'])[0])
            if yr > int(year) + 1 or yr < int(year) - 1: print('Wrong movie found', name, res['Title'], year, yr)
            else:  
                if 'Metascore' in res: info['mts'] = res['Metascore']
                if 'imdbRating' in res: info['imdb'] = res['imdbRating']
                for rt in res['Ratings']:
                    if rt['Source'] == 'Rotten Tomatoes':
                        info['rt'] = rt['Value']
                        break

                info2 = {}
                for inf in info:
                    if info[inf] != 'N/A': info2[inf] = info[inf]

                if len(info2) > 0 and 'Poster' in res and downloadImage(res['Poster'], 'cover.jpg', 3):
                    img = Image.open("cover.jpg")
                    draw = ImageDraw.Draw(img)
                    draw.line((0, img.size[1]) + img.size, fill='#505059', width=brHeight * 2)
                    font = ImageFont.truetype("Roboto-Medium.ttf", txHeight)
                    le = 300 // len(info2)
                    x = 0
                    spc = 10 // len(info2)
                    for rt in info2:
                        print((brHeight - txHeight) // 2)
                        im = Image.open(rt + ".png")
                        tsize = draw.textsize(info2[rt], font)[0]
                        sp  = (le - im.size[0] - tsize - spc) // 2
                        img.paste(im, (x + sp, img.size[1] - imHeight - (brHeight - imHeight) // 2), im)
                        draw.text((x + sp + im.size[0] + spc, img.size[1] - txHeight - (brHeight - txHeight) // 2), info2[rt],(0,0,0),font=font)
                        x += le

                    img.save(file.rpartition('/')[0] + '/cover.jpg')
    