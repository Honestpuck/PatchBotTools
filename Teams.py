#!/usr/bin/env python3

# Teams.py v1.0b
# Tony Williams 25/07/2019
#

"""See docstring for Teams class"""

import json
import plistlib
import os.path as path
import datetime
import logging
import logging.handlers
import sys
import requests

__all__ = ["Teams"]

# logging requirements
LOGFILE = "/usr/local/var/log/Teams.log"
LOGLEVEL = logging.INFO


class Teams:
    """When given the location of an output plist from Autopkg parses it
    and sends the details on packages uploaded to Jamf Pro to Teams
    """

    description = __doc__

    def __init__(self):

        # extremely dumb command line processing
        try:
            self.plist = sys.argv[1]
        except IndexError:
            self.plist = "autopkg.plist"

        # URL of Teams webhook
        self.url = "https://outlook.office.com/webhook/"
        # token
        self.url += "-e03688a2ab2d/IncomingWebhook/0ac15911fcfa42deb"
        self.url += "1d07f0672950542/63a48cfb-c3ef-4ee9-be63-fafbe4177f30"
        # URL for a button to open package test policy in Jamf Pro
        self.pol_base = "https://suncorp.jamfcloud.com/policies.html?id="

        # set up logging
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        frmt = "%(levelname)s {} %(message)s".format(now)
        # set up logging
        logging.basicConfig(filename=LOGFILE, level=LOGLEVEL, format=frmt)
        self.logger = logging.getLogger("")
        # set logging formatting
        # ch = logging.StreamHandler()
        ch = logging.handlers.TimedRotatingFileHandler(
            LOGFILE, when="D", interval=1, backupCount=7
        )
        ch.setFormatter(logging.Formatter(frmt))
        self.logger.addHandler(ch)
        self.logger.setLevel(LOGLEVEL)

        # JSON for the message to Teams
        # "sections" will be replaced by our work
        self.template = """
        {
            "@context": "https://schema.org/extensions",
            "@type": "MessageCard",
            "themeColor": "0072C6",
            "title": "Autopkg",
            "text": "Packages uploaded",
            "sections": [
            ]
        }
        """

        # JSON for a section of a message
        # we will have a section for each package uploaded
        # in this Autopkg run
        self.section = """
        {
            "startGoup": "true", "title": "**AppName**", "text": "version",
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Policy",
                    "targets": [
                        {
                            "os": "default",
                            "uri": "https://docs.microsoft.com/outlook/actionable-messages"
                        }
                    ]
                }
            ]
        }
        """

        # JSON template for the error message card.
        self.err_template = """
        {
            "@context": "https://schema.org/extensions",
            "@type": "MessageCard",
            "themeColor": "0072C6",
            "title": "Autopkg",
            "text": "Package errors",
            "sections": [
            ]
        }
        """

        # JSON template for a single error on error card.
        self.err_section = """
        {
            "text": "A long message",
            "startGoup": "true",
            "title": "**Firefox.pkg**"
        }
        """

        # JSON template for the empty run message card.
        self.none_template = """
        {
            "@context": "https://schema.org/extensions",
            "@type": "MessageCard",
            "themeColor": "0072C6",
            "title": "Autopkg",
            "text": "**Empty Run**"
        }
        """

    def Teams(self):
        """Do the packages uploaded!"""
        self.logger.info("Starting Run")
        sections = []
        empty = False
        jsr = "jpc_importer_summary_result"
        try:
            fp = open(self.plist, "rb")
            pl = plistlib.load(fp)
        except IOError:
            self.logger.error("Failed to load %s", self.plist)
            sys.exit()
        item = 0
        if jsr not in pl["summary_results"]:
            self.logger.debug("No JPCImporter results")
            empty = True
        else:
            for p in pl["summary_results"][jsr]["data_rows"]:
                sections.append(json.loads(self.section))
                # get the package name without the '.pkg' at the end
                pkg_name = path.basename(p["pkg_path"])[:-4]
                pol_id = p["policy_id"]
                self.logger.debug("Policy: %s Name: %s", pol_id, pkg_name)
                (app, version) = pkg_name.split("-")
                pol_uri = self.pol_base + pol_id
                sections[item]["title"] = "**%s**" % app
                sections[item]["text"] = version
                sections[item]["potentialAction"][0]["targets"][0][
                    "uri"
                ] = pol_uri
                item = item + 1
            j = json.loads(self.template)
            j["sections"] = sections
            d = json.dumps(j)
            requests.post(self.url, data=d)
        # do the error messages
        fails = pl["failures"]
        if len(fails) == 0:  # no failures
            if empty:  # no failures and no summary so send empty run message
                requests.post(self.url, self.none_template)
            sys.exit()
        sections = []
        item = 0
        for f in fails:
            sections.append(json.loads(self.err_section))
            sections[item]["title"] = "**%s**" % f["recipe"]
            sections[item]["text"] = f["message"].replace("\n", " ")
            item = item + 1
        j = json.loads(self.err_template)
        j["sections"] = sections
        d = json.dumps(j)
        requests.post(self.url, d)


if __name__ == "__main__":
    Teams = Teams()
    Teams.Teams()
