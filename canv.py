from queue import Queue
import random
import sys
import threading
import time
import tkinter as tk

__TICKS__ = []

global running

def mean_x(where, size, vlist):
    lmax = len(vlist) - 1
    if size > where:
        size = where
    if where + size > lmax:
        size = lmax - where
    rmin = where - size
    rmax = where + size + 1
    nval = sum(vlist[rmin:rmax])/(rmax-rmin)
    print(where, ':', vlist[rmin:rmax], '-->', nval)
    return nval

def draw_p(px, py, nx, ny, canv, colr='black'):
    if px and py:
        canv.create_line(px*5, py, nx*5, ny, fill=colr)
        canv.create_oval((nx*5)-1, ny-1, (nx*5)+1, ny+1, fill='red')
        print('dp to', nx, ny)

def g_value(vmin, vmax, max_d, outq):
    def gen_one():
        if not max_d:
            cur_spread = (vmax - vmin) / 2
        else:
            cur_spread = max_d * 2
        pre_v = vmin + int(random.random() * (vmax - vmin))
        while True:
            r_val = (random.random() - 0.5)
            p_spr = r_val * cur_spread
            p_v = pre_v + p_spr
            if p_v >= vmin and p_v <= vmax:
                pre_v = p_v
                yield pre_v

    gen = gen_one()
    while running:
        outq.put(next(gen))
        threading.Event().wait(0.1)


def main():
    global running

    running = True
    counter = 0
    prev_p = (None, None)
    root = tk.Tk()
    outq = Queue()
    argl = list(map(int,sys.argv[1:])) + [outq,]
    maxh = argl[1] * 1.3
    canv = tk.Canvas(root, width=100, height=maxh,
                     scrollregion=(0, 0, 1200, maxh))
    scrb = tk.Scrollbar(root, orient=tk.HORIZONTAL)
    canv['xscrollcommand'] = scrb.set
    scrb['command'] = canv.xview
    
    def end_one():
        global running
        running = False
        thrd.join()
        prev_p = (None, None)
        nval = []
        for nm, vl in enumerate(__TICKS__):
            cur_p = (nm, int(mean_x(nm, 2, __TICKS__)))
            draw_p(*prev_p, *cur_p, canv, 'green')
            prev_p = cur_p
        print('redraw done')
        strt['command'] = root.destroy

    def getpt():
        try:
            nval = outq.get_nowait()
        except:
            pass
        else:
            nonlocal counter, prev_p
            cur_p = (counter, int(nval))
            __TICKS__.append(nval)
            draw_p(*prev_p, *cur_p, canv, 'yellow')
            prev_p = cur_p
            counter += 1
        root.after(5, getpt)
        

    strt = tk.Button(root, text='Exit', command=end_one)
    canv.grid(sticky=tk.EW)
    scrb.grid(sticky=tk.EW)
    strt.grid(sticky=tk.EW)
    root.columnconfigure(0, weight=1)
    thrd = threading.Thread(target=g_value, args=argl)
    thrd.start()
    root.after(5, getpt)
    tk.mainloop()

main()
