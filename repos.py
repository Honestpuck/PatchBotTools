#!/usr/bin/env python3

# repos.py
# print the list of AutoPkg repos in search order
# NOTE: Totally lacking in any error checking or handling

import plistlib
from os import path

plist = path.expanduser('~/Library/Preferences/com.github.autopkg.plist')
fp = open(plist, 'rb')
prefs = plistlib.load(fp)
search = prefs['RECIPE_SEARCH_DIRS']
repos = prefs['RECIPE_REPOS']

# start at 3 to skip the built in ones.
for i in range(3, len(search)):
    print(repos[search[i]]['URL'])
