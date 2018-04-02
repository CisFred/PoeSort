import os
import os.path
import sys
import sqlite3

def db_check(item, league, toon_or_tab):
    if not db_get(item, 'Items'):
        db_add(item, 'Items')
        db_link(item, toon=toon_or_tab, league=league, tab=toon_or_tab)
