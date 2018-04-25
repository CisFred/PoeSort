import os
import sys
import threading
import queue
import json
import pickle
import pprint as pp
import traceback

import req

Leagues = {}
Toons = {}
Tabs = {}

class Toon():
    def __init__(self, data):
        self.__dict__.update(**data['character'])
        self.items = [Item(itm, pos='on ' + self.name)
                      for itm in data['items']]
        self.json = data
            

    def __sub__(self, other):
        print(self.league, self.name)
        for k, v in self.__dict__.items():
            if k in other and other[k] != v:
                print('{}: {} -> {}'.format(k, v, other[v]))

class Item():
    def __init__(self, data, **kwargs):
        self.json = data
        try:
            self.category, (self.subcat,) = data['category'].items()
        except:
            self.category = list(data['category'].keys())[0]
            self.subcat = data['typeLine']
        self.explicit = data['explicitMods'] if 'explicitMods' in data else None
        self.iLvl = data['ilvl']
        self.id = data['id']
        self.name, self.itype = Item.get_name(data)
        self.where = kwargs['pos'] if 'pos' in kwargs else Item.get_pos(data)
        self.league = kwargs['league'] if 'league' in kwargs else data['league']
        if 'socketedItems' in data:
            self.sockets = [Item(gem, pos=self.where, league=self.league)
                            for gem in data['socketedItems']]
        add_league_item(self, self.league)

    @classmethod
    def get_name(cls, data):
        tline = data['typeLine']
        if 'name' in data and data['name']:
            name = data['name']
        else:
            name = data['typeLine']
        return name[name.rindex('>')+1:], tline[tline.rindex('>')+1:]
                
def add_league_item(item, league):
    if league not in Leagues:
        Leagues[league] = {'items': {}, 'byname': {}}
    this_league = Leagues[league]
    this_league['items'][item.id] = item
    if item.name not in this_league['byname']:
        this_league['byname'][item.name] = set()
    this_league['byname'][item.name].add(item.id)
        

    
req_lock = threading.Lock()

def get_cnt(which, dest, **kw):
    while True:
        with req_lock:
            thing, hdr = req.get_page(which, headers=True, **kw)
            if 'Retry-After' in hdr:
                print('Need to wait', hdr['Retry-After'])
            if 'X-Rate-Limit-Account' in hdr:
                limits = hdr['X-Rate-Limit-Account'].split(',')
                states = hdr['X-Rate-Limit-Account-State'].split(',')
                for lm, st in zip(limits, states):
                    lim, evry, wait = lm.split(':')
                    now, upto, when = st.split(':')
                    if int(lim) - int(now) < 2:
                        print('slowing', lm, st)
                        threading.Event().wait(1)
                        break
            if thing:
                result = kw.copy()
                result.update(which=which, result=thing)
                print(kw, 'done')
                if dest:
                    dest.put(result)
                return thing
            threading.Event().wait(30)
            print(which, kw, 'retry')

def get_league(league, ma_acnt, dest):
    try:
        tab = get_cnt('stash_count', dest=None, league=league,
                           accountName=ma_acnt)
        tab_cnt = tab['numTabs']
    except:
        print('oops?', tab)
        return
    print(league, 'has', tab_cnt, 'tabs')
    dest.put({'league': league, 'nb_tabs': tab_cnt})
    thd = {}
    for idx in range(tab_cnt):
        thd[idx] = threading.Thread(target=get_cnt,
                                    name=league+'-tab-'+str(idx),
                                    kwargs=dict(which='stash', dest=dest,
                                                league=league,
                                                accountName=ma_acnt,
                                                tabIndex=idx))
        thd[idx].start()
    for idx in range(tab_cnt):
        print('waiting for', idx, 'in', league)
        thd[idx].join()

def save_tab(ddir, data):
    # Add 'diff' before saving new.
    with open('{}/tab-{}'.format(ddir, data['tabIndex']), 'w') as outf:
        pp.pprint(data['result'], stream=outf)

def diff_toon(ddir, toon, data):
    new_char = parse_char(data['character'])
    new_inven = parse_items(data['items'], toon=True)
    old_toon, old_inven = get_toon(ddir, toon)
    char_diff(old_char, new_char)
    inven_diff(old_inven, new_inven)
    
def get_toon(ddir, toon):
    with open('{}/{}'.format(ddir, toon), 'r') as inf:
        data = eval(inf.read())
    return parse_char(data['character']), parse_items(data['items'], toon=True)

def save_toon(ddir, toon, data):
    # Add 'diff' before saving new.
    # diff_toon(ddir, toon, data)
    with open('{}/{}'.format(ddir, toon), 'w') as outf:
        pp.pprint(data, stream=outf)
    


def one_league(league, toons):
    dest = queue.Queue()
    res = get_cnt('acc_name', dest=None)
    account = res['accountName']
    thd = threading.Thread(target=get_league, name='league '+league,
                           args=(league, account, dest))
    thd.start()
    res = None
    wtab = '/'.join((league, 'Stash'))
    ttab = '/'.join((league, 'Toons'))
    os.makedirs(wtab, exist_ok=True)
    os.makedirs(ttab, exist_ok=True)
    print('Getting league', league)
    while True:
        data = dest.get()
        if 'nb_tabs' in data:
            nb_wait = data['nb_tabs']
            res = [None] * nb_wait
        elif not res:
            print('Tab before nb_tabs?')
            print(nb_wait)
        elif 'tabIndex' not in data:
            print('Unknown result', data)
        else:
            for item in data['result']['items']:
                key = league+'-'+item['inventoryId']
                if key not in Tabs:
                    Tabs[key] = {}
                    this = Item(item, pos=key, league=league)
                Tabs[key][this.id] = this
            save_tab(wtab, data)
            nb_wait -= 1
            if nb_wait == 0:
                print('waiting for get_l')
                break
    thd.join()
    for toon in toons:
        print('Getting', toon)
        res = get_cnt('inv', dest=None, character=toon)
        Toons[toon] = Toon(res)
        save_toon(ttab, toon, res)
    
def get_toons():
    ldict = {}
    res = get_cnt('chars', dest=None)
    for toon in res:
        if toon['league'] not in ldict:
            ldict[toon['league']] = []
        ldict[toon['league']].append(toon['name'])
    return list(ldict.keys()), list(ldict.values())

if __name__ == '__main__':
    req.init()
    leagues, toons = get_toons()
    while True:
        for n, l in enumerate(leagues):
            print(n, '-', l)
        what = input('> ')
        try:
            idx = int(what)
            one_league(leagues[idx], toons[idx])
        except:
            traceback.print_exc()
            break
        else:
            with open(leagues[idx]+'/Toons.pkl', 'wb') as outf:
                pickle.dump(Toons, outf)
            with open('./Leagues.pkl', 'wb') as outf:
                pickle.dump(Leagues, outf)
            with open(leagues[idx]+'/Tabs.pkl', 'wb') as outf:
                pickle.dump(Tabs, outf)
            Toons = {}
            Tabs = {}
            
