import os
import sys
import threading
import queue
import json

import pprint as pp

import req

def get_cnt(which, dest, **kw):
    while True:
        thing = req.get_page(which, **kw)
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

def save_toon(ddir, toon, data):
    # Add 'diff' before saving new.
    with open('{}/{}'.format(ddir, toon), 'w') as outf:
        pp.pprint(data, stream=outf)


def one_league(league, toons):
    dest = queue.Queue()
    account = get_cnt('acc_name', dest=None)['accountName']
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
            save_tab(wtab, data)
            nb_wait -= 1
            if nb_wait == 0:
                print('waiting for get_l')
                break
    thd.join()
    for toon in toons:
        print('Getting', toon)
        res = get_cnt('inv', dest=None, character=toon)
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
            print(sys.exc_info()[1])
            break
            
