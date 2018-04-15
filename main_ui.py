import io
import json
import sys
import traceback
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk

from req import *


class ShowThings():
    fld = ('name', 'typeLine', 'category', 'requirements', 'properties',
           'explicitMods', 'id')
    ign = ('icon', 'x', 'y', 'w', 'h', 'inventoryId', 'league',
           'identified', 'verified', 'frameType', 'descrText', 'secDescrText',
           'numTabs', 'currencyLayout', 'essenceLayout', 'quadLayout')
    show_fun = {
        'requirements': lambda val: '\n'.join(['{}: {}'.format(
            x['name'],
            x['values'][0][0]) for x in val]),
        'properties': lambda val: '\n'.join(['({}): {}: {}'.format(
            x['type'],
            x['name'],
            x['values'][0][0]) for x in val if 'type' in x]),
        'name': lambda val: (print(locals()), val.split('>>')[-1])[1],
        
    }
    def show(self, data, dest):
        def to_string(val):
            if isinstance(val, (list, tuple)):
                val = '\n'.join([to_string(sub) for sub in val])
            elif isinstance(val, dict):
                val = '\n'.join(['{}: {}'.format(k,to_string(v))
                                 for k,v in val.items()])
            return str(val)
                
        def show_one(lbl, val, row):
            if val is None:
                return
            if lbl in self.show_fun:
                print(lbl, '-->', val)
                real_val = self.show_fun[lbl](val)
            else:
                real_val = to_string(val)
            l = tk.Label(dest, text=lbl, anchor=tk.NW, relief=tk.RAISED)
            v = tk.Label(dest, text=real_val)
            l.grid(row=row, column=0, sticky=tk.N+tk.EW)
            v.grid(row=row, column=1, sticky=tk.EW)
            
        for w in dest.grid_slaves():
            w.destroy()
        for n, i in enumerate(Item.fld):
            show_one(i, data.pop(i, None), n)
        for i in Item.ign:
            data.pop(i, None)
        for n, i in enumerate(data, len(Item.fld)):
            show_one(i, data[i], n)
    

class Item(tk.Button, ShowThings):
    def __init__(self, master, info, item, scale):
        self.__dict__.update(item)
        self.info = info
        img = get_image(item)
        wdth = int(item['w']*42*scale)
        hght = int(item['h']*42*scale)
        img = img.resize((wdth, hght), Image.NEAREST)
        self.image = ImageTk.PhotoImage(img)
        self.item = item
        print(item)
        show_this = lambda d=self.info, i=self.item: self.show(i.copy(), d)
        super().__init__(master, image=self.image, bg='red',
                         command=show_this,
                         width=wdth, height=hght)
                
class InventoryTab(tk.Frame, ShowThings):
    def __init__(self, master, league, index, items):
        super().__init__(width=512, height=512)

        self.inside = items.copy()
        content = items.pop('items', [])
        self.league = league
        self.master = master
        self.idx_name = 'Content/{}/stash-{}'.format(league, index)
        title = 'Tab {}: {} --- {} items'.format(
            index,
            content[0]['inventoryId'] if content else 'void',
            len(content))
        print(title)
        self.index = index
        frame = self
        pb_style = ttk.Style()
        pb_style.configure('.', relief=tk.RAISED)
        var = tk.IntVar()
        self.dsp = tk.Frame(frame)
        self.title = tk.Label(frame, text=title)
        self.pbar = ttk.Progressbar(frame, mode='determinate', variable=var,
                                    orient=tk.HORIZONTAL, maximum=len(content),
                                    # style=pb_style
        )
        self.info = tk.Frame(frame)
        self.title.grid(row=0, column=0, columnspan=2, sticky=tk.EW)
        self.pbar.grid(row=1, column=0, columnspan=2, sticky=tk.EW)
        self.dsp.grid(row=2, column=0, sticky=tk.EW)
        self.info.grid(row=2, column=1, sticky=tk.EW)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        self.info.columnconfigure(0, weight=1)
        self.info.columnconfigure(1, weight=1)
        self.content = {}
        self.show(items, self.info)
        self.show_items(content)
        self.save()

    def save(self):
        try:
            os.mkdir('Content/'+self.league)
        except:
            pass
        with open(self.idx_name, 'w') as outf:
            print(json.dumps(self.inside), file=outf)

    def load(self):
        try:
            with open(self.idx_name, 'r') as inf:
                data = inf.read()
            return json.loads(data)
        except:
            return {}

    def diff(self):
        def rdiff(x, y):
            if isinstance(x, dict):
                for k in x:
                    if k in y:
                        rdiff(x[k], y[k])

        old_tab = self.load(self)
        

    def show_items(self, content):
        def get_layout(item, content):
            if 'essenceLayout' in self.inside:
                print('Essence')
                layout = self.inside['essenceLayout']['essences']
                scale = self.inside['essenceLayout']['scale']
                pos = layout[item['x']]
                return pos['x'], pos['y'], pos['h'], pos['w'], scale, True
            if 'divinationLayout' in self.inside:
                print('cards')
                return item['x'] % 12, item['x'] // 12, 1, 1, 1, False
            if 'fragmentLayout' in self.inside:
                print('Fragments')
                layout = self.inside['fragmentLayout']
                pos = layout[item['x']]
                return pos['x'], pos['y'], pos['h'], pos['w'], 1, True
            if 'quadLayout' in self.inside:
                print('Quad')
                return item['x'], item['y'], item['h'], item['w'], 0.25, False
            if 'currencyLayout' in self.inside:
                print('Currency')
                layout = self.inside['currencyLayout']
                pos = layout[str(item['x'])]
                return pos['x'], pos['y'], pos['h'], pos['w'], 1, True
            print('Normal')
            return item['x'], item['y'], item['h'], item['w'], 1, False

        for item in content:
            x, y, h, w, scale, place_it = get_layout(item, content)
            wdgt = Item(self.dsp, self.info, item, scale)
            print(x, y, h, w, scale)
            if place_it:
                x /= 512
                y /= 512
                wdgt.place(rely=y, relx=x, anchor=tk.NE)
                print('place', x, y)
            else:
                print('grid', x, y)
                wdgt.grid(row=y, column=x, rowspan=h, columnspan=w)
            self.pbar.step(1)
            self.master.root.update()
            
        self.pbar.destroy()

class ToonButtons(tk.Frame):
    def __init__(self, master, toons):
        super().__init__(master)
        leagues = {}
        self.master=master
        self.root = master.master
        for toon in toons:
            if 'league' not in toon:
                toon['league'] = 'Void'
            if toon['league'] not in leagues:
                leagues[toon['league']] = []
            leagues[toon['league']].append(toon)
        for nl, l in enumerate(sorted(leagues)):
            lbf = tk.LabelFrame(self, text=l)
            for nt, t in enumerate(leagues[l]):
                b = tk.Button(lbf, text=t['name'],
                              command=lambda l=l,t=t: self.show_toon(l,t))
                b.grid(row=0, column=nt, sticky=tk.EW)
                lbf.columnconfigure(nt, weight=1)
            lbf.grid(row=0, column=nl, sticky=tk.EW)
            self.columnconfigure(nl, weight=1)
        self.leagues = list(leagues.keys())
    def show_toon(self, league, toon):
        pass

class LeagueButtons(tk.Frame):
    def __init__(self, master, leagues):
        super().__init__(master)
        self.master=master
        self.root = master.master
        for nl, l in enumerate(sorted(leagues)):
            b = tk.Button(self, text=l,
                          command=lambda l=l: self.show_league(l))
            b.grid(row=0, column=nl, sticky=tk.EW)
        self.tabs = {l: {} for l in leagues}
        self.ctab = None
    def show_league(self, league):
        tab_cnt = get_page('stash_count', league=league,
                           accountName=self.master.account)['numTabs']
        print(league, tab_cnt)
        for i in range(tab_cnt):
            frame = self.master.oframe
            b = tk.Button(frame, text=str(i),
                          command=lambda l=league,n=i: self.show_tab(l,n))
            b.grid(row=0, column=i, sticky=tk.EW)
            frame.columnconfigure(i, weight=1)
    def show_tab(self, league, index):
        if self.ctab:
            self.ctab.grid_remove()
        if index not in self.tabs:
            print('New tab', league, index)
            items = get_page('stash', league=league,
                             accountName=self.master.account,
                             tabIndex=index)
            tab = InventoryTab(self, league, index, items)

            tab.grid(row=1, column=0, columnspan=50, sticky=tk.NSEW)
            self.tabs[league][index] = tab
        else:
            print('Old tab', league, index)
            self.tabs[league][index].grid()
        self.ctab = self.tabs[league][index]

class BaseUI(tk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.master = root
        self.account = get_page('acc_name')['accountName']
        print('account', self.account)
        self.oframe = tk.Frame(self)
        self.toons = ToonButtons(self, get_page('chars'))
        self.leagues = LeagueButtons(self, self.toons.leagues)
        self.toons.grid(sticky=tk.EW)
        self.leagues.grid(sticky=tk.EW)
        self.oframe.grid(sticky=tk.NSEW)
        self.grid()

if __name__ == '__main__':
    root = tk.Tk()
    BaseUI(root)
    root.mainloop()
