import os
import sys
import threading
import queue
import json
import deepdiff

import pprint as pp

import req

conn_semaphore = threading.BoundedSemaphore(value=6)

def trace(*args):
    print(threading.current_thread().name, *args)

def get_cnt(which, dest, **kw):
    while True:
        with conn_semaphore:
            thing = req.get_page(which, **kw)
            threading.Event().wait(3)
        if thing:
            result = kw.copy()
            result.update(which=which, result=thing)
            trace(kw, 'done')
            if dest:
                dest.put(result)
            return thing
        trace(which, kw, 'retry')

def get_league(league, ma_acnt, dest):
    try:
        tab = get_cnt('stash_count', dest=None, league=league,
                          accountName=ma_acnt)
        tab_cnt = tab['numTabs']
    except:
        trace('oops?', tab)
        return
    trace(league, 'has', tab_cnt, 'tabs')
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
        trace('waiting for', idx, 'in', league)
        thd[idx].join()

def save_tab(ddir, data):
    # Add 'diff' before saving new.
    with open('{}/tab-{}'.format(ddir, data['tabIndex']), 'w') as outf:
        pp.pprint(data['result'], stream=outf)

def check_tab(ddir, toon, data):
    with open('{}/tab-{}'.format(ddir, data['tabIndex']), 'r') as inf:
        old_data = eval(inf.read())
    print('='*20, '\n', 'tab', data['tabIndex'], '\n', '='*20)
    gen_diff(old_data, data, 1)

def save_toon(ddir, toon, data):
    # Add 'diff' before saving new.
    with open('{}/{}'.format(ddir, toon), 'w') as outf:
        pp.pprint(data, stream=outf)

def check_toon(ddir, toon, data):
    print("checking toon", toon)
    with open('{}/{}'.format(ddir, toon), 'r') as inf:
        old_data = eval(inf.read())
    # print('='*20, '\n', 'toon', toon, '\n', '='*20)
    print(gen_diff(old_data, data, 1))

def diff_toon(league, toon):
    with open('{}/Toons/{}'.format(league, toon), 'r') as inf:
        new_data = eval(inf.read())
    with open('{}/Toons/{}.old'.format(league, toon), 'r') as inf:
        old_data = eval(inf.read())
    dd = deepdiff.DeepDiff(old_data, new_data)
    return new_data, old_data, dd
    pp.pprint(dd)
    # print(gen_dif2(old_data, new_data, 'Top', 1))
        

def gen_dif2(o1, o2, name, ind):
    def outp(*a):
        return (' '*ind)+' '.join([str(x) for x in a])

    if o1 == o2:
        return outp(name, 'identical')
    if isinstance(o1, dict):
        diffs = []
        for k, v in o1.items():
            if k in o2:
                if v != o2[k]:
                    diffs.append(outp(name, gen_dif2(v, o2[k], k, ind+1)))
            else:
                diffs.append(outp(k, 'missing in new', name))
        for k in o2:
            if k not in o1:
                diffs.append(outp(k, 'missing in old', name))
        return '\n'.join(diffs)
    elif isinstance(o1, list):
        pass
    elif isinstance(o1, (str, int, bool)):
        return(outp(name, '{} -> {}'.format(o1, o2)))
    else:
        return(outp(name, type(o1), 'not handled'))
                


def gen_diff(o1, o2, ind):
    def get_it(obj):
        try:
            return ', '.join(['{}: {}'.format(f, obj[f])
                              for f in ('name', 'typeLine', 'x', 'y')
                              if obj[f]])
        except:
            return str(obj)
        
    def find_same(tgt, lst, **exclude):
        def is_ok(fld):
            return fld not in exclude and fld in tgt and tgt[fld]

        def check_return(fld, what):
            poss = [x for x in lst if fld in x and x[fld] == tgt[fld]]
            if len(poss) > 1:
                exclude[fld] = tgt[fld]
                return find_same(tgt, poss, **exclude)
            elif len(poss) == 1:
                what += '{}: {}'.format(fld, tgt[fld])
                return what, poss[0]
            else:
                what += '{}: {}'.format(fld, tgt[fld])
                return what, None


        what = ", ".join(['{}: {}'.format(k, v) for k, v in exclude.items()])

        if isinstance(tgt, list):
            return 'List!', None
        elif isinstance(tgt, dict):
            for fld in ('name', 'typeLine', 'x', 'y', 'id'): 
                if is_ok(fld):
                    return check_return(fld, what)
        elif isinstance(tgt, (int, bool, str)):
            return type(tgt), tgt if tgt in lst else None
        else:
            print('find_same', type(tgt), 'not handled', tgt, lst)
            return type(tgt), lst[0]

    # print(' '*ind, 'checking {:.15s} vs. {:.15s}'.format(str(o1), str(o2)))
    # input('#')
    if o1 == o2:
        return ''
    if type(o1) != type(o2):
        return ' '*ind + 'Diff. Type --{:.15s}-- --{:.15s}--'.format(o1, o2)
    if isinstance(o1, dict):
        end_res = True
        for k, v in o1.items():
            end_res = []
            if k not in o2:
                end_res.append(' '*ind + 'Missing key {} in new'.format(k))
            else:
                xxx = gen_diff(o1[k], o2[k], ind+1)
                if xxx:
                    end_res.append(' '*ind + '{}: {}'.format(k, xxx))
        for k in o2:
            if k not in o1:
                end_res.append(' '*ind + 'Missing key {} in old'.format(k))
        if end_res:
            print('--', '\n'.join(end_res), '--')
        return ' '*ind+'\n'.join(end_res) if end_res else ''
    if isinstance(o1, (list, tuple)):
        end_res = []
        c1 = list(o1)
        c2 = list(o2)
        while c1:
            old_o = c1.pop()
            what, cand = find_same(old_o, c2)
            if not cand:
                end_res.append(' '*ind + '{}: disappeared'.format(what))
            else:
                c2.pop(c2.index(cand))
                xxx = gen_diff(old_o, cand, ind+1)
                if xxx:
                    end_res.append(' '*ind + '{}: {}'.format(what, xxx))
        while c2:
            new_o = c2.pop()
            end_res.append('  '*ind + '{} is new'.format(get_it(new_o)))
        return ' '*ind+'\n'.join(end_res) if end_res else ''
    if isinstance(o1, (str, int, float, bool)):
        return ' '*ind+'{} -> {}'.format(o1, o2)
    print(' '*ind, type(o1), 'NIY!', o1)
    return ''

def one_league(cmd, league, toons):
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
            if cmd == 'save':
                save_tab(wtab, data)
            elif cmd == 'check':
                check_tab(wtab, data)
            nb_wait -= 1
            if nb_wait == 0:
                print('waiting for get_l')
                break
    thd.join()
    for toon in toons:
        print('Getting', toon)
        res = get_cnt('inv', dest=None, character=toon)
        if cmd == 'save':
            save_toon(ttab, toon, res)
        elif cmd == 'check':
            check_toon(ttab, toon, res)
            
def get_toons():
    ldict = {}
    res = get_cnt('chars', dest=None)
    for toon in res:
        if toon['league'] not in ldict:
            ldict[toon['league']] = []
        ldict[toon['league']].append(toon['name'])
    return list(ldict.keys()), list(ldict.values())

if __name__ == '__main__':
    if len(sys.argv) > 2:
        diff_toon(*sys.argv[1:])
        sys.exit(0)
    req.init()
    os.makedirs('Inven', exist_ok=True)
    leagues, toons = get_toons()
    while True:
        for n, l in enumerate(leagues):
            print(n, '-', l, ':', toons[n])
        what = input('> ')
        cmd, idx = what.split()
        try:
            if cmd.startswith('t'):
                toon = idx
                print('Getting', toon)
                res = get_cnt('inv', dest=None, character=toon)
                #pp.pprint(res)
                league=res['character']['league']
                ttab = '/'.join((league, 'Toons'))
                os.makedirs(ttab, exist_ok=True)
                if cmd == 'tsave':
                    save_toon(ttab, toon, res)
                elif cmd == 'tcheck':
                    check_toon(ttab, toon, res)
            else:
                idx = int(idx)
                one_league(cmd, leagues[idx], toons[idx])
        except:
            print(sys.exc_info()[1])
            break
            
