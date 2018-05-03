import sys
import threading
import time

from random import random

base = time.time()

class WaitSem():
    def __init__(self, max, delay):
        self.max = max
        self.delay = delay
        self.current = 0
        self.lock = threading.Lock()
        self.reset = False
        self.next = time.time() + delay

    def acquire(self):
        while True:
            with self.lock:
                # trace(self.current, '<?', self.max, 'reset', self.reset)
                self.current += 1 
                go_on = self.current <= self.max
            if not go_on:
                how_much = self.next - time.time()
                # trace('waiting', how_much)
                if how_much > 0:
                    threading.Event().wait(how_much)
                with self.lock:
                    if time.time() >= self.next:
                        self.current = 0
                        self.next = time.time() + self.delay

            else:
                return

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args, **kwargs):
        trace('exit', args, kwargs)

    def cur(self):
        with self.lock:
            return self.current

    def release(self):
        pass


def trace(*args):
    print(int(time.time() - base), threading.current_thread().name, *args)

def gfun(who, sem):
    counter = 0
    while counter < 100:
        # trace('getting sem', who, counter)
        with sem:
            trace('got sem', who, counter, sem.cur())
            threading.Event().wait(random())
            counter += 1

threads = {}
sem = WaitSem(int(sys.argv[1]), int(sys.argv[2]))
maxt = int(sys.argv[3])
trace('creating', maxt, 'threads')
for t in range(maxt):
    threads[t] = threading.Thread(target=gfun, args=(t, sem))

trace('startting', maxt, 'threads')
for t in range(maxt):
    threads[t].start()

trace('waiting for', maxt, 'threads')
for t in range(maxt):
    threads[t].join()
    

