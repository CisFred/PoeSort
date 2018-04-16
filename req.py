import json
import os
import os.path
import requests
import traceback
try:
    from PIL import Image, ImageDraw, ImageFont
except:
    pass

cookies=dict(POESESSID='')

link_base = 'https://www.pathofexile.com/character-window/'
links=dict(acc_name='get-account-name',
           chars='get-characters',
           inv = 'get-items?character={character}',
           char_jewel = 'get-passive-skills?eqData=false&character={character}',
           stash_count = 'get-stash-items?league={league}&accountName={accountName}',
           stash = 'get-stash-items?league={league}&accountName={accountName}&tabIndex={tabIndex}',
           )

def get_page(link, **kwargs):
    url = link_base + links[link].format(**kwargs)
    
    r = requests.get(url, cookies=cookies)
    if r.text == 'error':
        print(r.content)
        return None
    try:
        # print(r.text)
        res = json.loads(r.text)
        if 'error' in res:
            print(res['error'])
            return None
        return res
    except:
        print(r.text)
        traceback.print_exc()
        return None

def get_image(item):
    base_url = 'https://web.poecdn.com/image/Art/'
    base_img = 'https://web.poecdn.com/gen/image/'
    try:
        url = item['icon']
        if url.startswith(base_url):
            base = base_url
            icon_file = url[len(base_url):url.index('?')]
        elif url.startswith(base_img):
            base = base_img
            icon_file = url[len(base_img):]
        else:
            print('Bad start', url)
            base = None
    except:
        base = None
    if base:
        if not os.path.exists(icon_file):
            print('getting', base + '/' + icon_file)
            r = requests.get(base + '/' + icon_file)
            os.makedirs(os.path.dirname(icon_file), exist_ok=True)
            with open(icon_file, "wb") as out:
                out.write(r.content)
        return Image.open(icon_file)

    try:
        print("Can't get icon from", item['icon'])
    except:
        print("No icon in", item)
    img = Image.new('RGBA', (156,156), (255,255,255,0))
    fnt = ImageFont.truetype('Arial.ttf', 40)
    d = ImageDraw.Draw(img)
    d.text((10, 10), item['typeLine'] if 'typeLine' in item else '???',
           font=fnt, fill=(255, 255, 255, 150))
    return img

def init():
    with open('.poecfg', 'r') as inf:
        for line in inf.readlines():
            if line.startswith('POESESSID='):
                cookies['POESESSID'] = line[10:].rstrip()
                break
        else:
            print('Not found')
            raise KeyError('POESESSID=')
