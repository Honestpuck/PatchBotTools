#!/usr/bin/env python3

# Move.py v1.0
# Tony Williams (ARW) 2020-02-20
#
# Move a package into production at the appropriate time

import datetime

import logging.handlers
from logging import Logger
import plistlib
import subprocess
import sys
from os import path
import requests


class Move:
    """Move a package into production at the appropriate time"""

    LOGFILE = "/usr/local/var/log/%s.log" % "PatchManager"
    LOGLEVEL = logging.DEBUG

    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    frmt = "%(levelname)s {} %(message)s".format(now)
    logger = logging.getLogger("")
    ch = logging.handlers.TimedRotatingFileHandler(
        LOGFILE, when="D", interval=1, backupCount=7
    )
    ch.setFormatter(logging.Formatter(frmt))
    logger.addHandler(ch)
    logger.setLevel(LOGLEVEL)
    logger.propagate = False

    # Which pref format to use, autopkg or jss_importer
    autopkg = False
    if autopkg:
        plist = path.expanduser("~/Library/Preferences/com.github.autopkg..plist")
        fp = open(plist, "rb")
        prefs = plistlib.load(fp)
        base = prefs["JSS_URL"] + "/JSSResource/"
        auth = (prefs["API_USERNAME"], prefs["API_PASSWORD"])
    else:
        plist = path.expanduser("~/Library/Preferences/JPCImporter.plist")
        fp = open(plist, "rb")
        prefs = plistlib.load(fp)
        base = prefs["url"] + "/JSSResource/"
        auth = (prefs["user"], prefs["password"])
    hdrs = {"accept": "application/json"}

    def Error(self, line):
        """ print a line to stdout and log before exiting. """
        print(line)
        self.logger.error(line)
        sys.exit(1)

    def policy_list(self):
        """ get the list of patch policies from JP and turn it into a dictionary """
        url = self.base + "patchpolicies"
        ret = requests.get(url, auth=self.auth, headers=self.hdrs)
        self.logger.debug("GET policy list url: %s status: %s" % (url, ret.status_code))
        if ret.status_code != 200:
            raise self.Error("GET failed URL: %s Err: %s" % (url, ret.status_code))
        # turn the list into a dictionary keyed on the policy name
        d = {}
        for p in ret.json()["patch_policies"]:
            d[p["name"]] = p["id"]
        return d

    def policy(self, idn):
        """ get a single patch policy """
        url = self.base + "patchpolicies/id/" + idn
        ret = requests.get(url, auth=self.auth, headers=self.hdrs)
        self.logger.debug("GET policy url: %s status: %s" % (url, ret.status_code))
        if ret.status_code != 200:
            raise self.Error("GET failed URL: %s Err: %s" % (url, ret.status_code))
        return ret.json()["patch_policy"]

    def move(self, recipes):
        """ run autopkg with a list of packages to move """
        report = path.expanduser("~/Documents/move.plist")
        plist = "--report-plist=" + report
        command = ["autopkg", "run"] + recipes
        command += [plist, "-k", "FAIL_RECIPES_WITHOUT_TRUST_INFO=yes"]
        self.logger.debug("command: " + " ".join(command))
        subprocess.run(command)

    def loop(self):
        now = datetime.datetime.now()
        recipes = []
        policies = self.policy_list()
        for key in policies:
            if "Test" in key:
                self.logger.warning("Found Test patch policy: " + key)
                policy = self.policy(str(policies[key]))
                if not policy["general"]["enabled"]:
                    self.logger.debug("Policy not enabled")
                    continue
                description = policy["user_interaction"][
                    "self_service_description"
                ].split()
                # we may have found a patch policy with no proper description yet
                if len(description) != 3:
                    continue
                title, datestr = description[1:]
                date = datetime.datetime.strptime(datestr, "(%Y-%m-%d)")
                delta = now - date
                self.logger.debug(
                    "Found delta to check: %s in %s" % (delta.days, title)
                )
                if delta.days > 6:
                    recipes.append(title + ".prod")
                    self.logger.debug("Found one to move: %s" % title)
        if recipes:
            self.logger.debug("We have found moves to make")
            self.move(recipes)
            report = path.expanduser("~/Documents/move.plist")
            command = ["./ProdTeams.py", report]
            self.logger.debug("command: " + " ".join(command))
            subprocess.run(command, shell=True)


if __name__ == "__main__":
    Move = Move()
    Move.loop()
