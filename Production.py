#!/usr/bin/env python3
#
# Production v1.0
# Tony Williams 25/07/2019
#

"""See docstring for Production class"""

from os import path
import plistlib
import xml.etree.ElementTree as ET
import datetime
import logging
import logging.handlers
import requests

from autopkglib import Processor, ProcessorError  # pylint: disable=import-error

__all__ = ["Production"]


class Package:
    """A package. This exists merely to carry the variables"""

    title = ""  # the application title matching the test policy
    patch = ""  # name of the patch definition
    name = ""  # full name of the package '<title>-<version>.pkg'
    version = ""  # the version of our package
    idn = ""  # id of the package in our JP server


class Production(Processor):
    """Moves a package from testing to production by disabling the test
    policy, changing the production policy to use the new package, and
    creating a patch policy
    """

    description = __doc__

    # logging requirements
    LOGFILE = "/usr/local/var/log/%s.log" % "Production"
    LOGLEVEL = logging.DEBUG

    input_variables = {
        "package": {"required": True, "description": "Package name"},
        "patch": {"required": False, "description": "Patch name"},
    }

    output_variables = {
        "Production_summary_result": {"description": "Summary of action"}
    }

    """Build our class"""
    prefs = plistlib.readPlist(
        path.expanduser("~/Library/Preferences/JPCImporter.plist")
    )
    base = prefs["url"] + "/JSSResource"
    auth = (prefs["user"], prefs["password"])

    # a package
    pkg = Package()
    # logging
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    frmt = "%(levelname)s {} {} %(message)s".format("Production", now)
    logger = logging.getLogger("")
    # set logging formatting
    # ch = logging.StreamHandler()
    ch = logging.handlers.TimedRotatingFileHandler(
        LOGFILE, when="D", interval=1, backupCount=7
    )
    ch.setFormatter(logging.Formatter(frmt))
    logger.addHandler(ch)
    logger.setLevel(LOGLEVEL)

    def lookup(self):
        """look up test policy to find package name, id and version """
        self.logger.debug("Starting")
        url = self.base + "/policies/name/Test-" + self.pkg.title
        pack_base = "package_configuration/packages/package"
        self.logger.debug("About to request %s", url)
        ret = requests.get(url, auth=self.auth)
        if ret.status_code != 200:
            raise ProcessorError(
                "Test policy download failed: {} : {}".format(ret.status_code, url)
            )
        root = ET.fromstring(ret.text)
        test_id = root.findtext("general/id")
        self.logger.debug("Got test policy id %s", test_id)
        self.pkg.idn = root.findtext(pack_base + "/id")
        self.pkg.name = root.findtext(pack_base + "/name")
        self.pkg.version = self.pkg.name.split("-")[1][:-4]

    def production(self):
        # change the package in the production policy
        url = self.base + "/policies/name/Install " + self.pkg.title
        pack_base = "package_configuration/packages/package"
        self.logger.debug("About to request %s", url)
        ret = requests.get(url, auth=self.auth)
        if ret.status_code != 200:
            raise ProcessorError(
                "Prod policy download failed: {} : {}".format(ret.status_code, url)
            )
        prod = ET.fromstring(ret.text)
        prod.find(pack_base + "/id").text = self.pkg.idn
        prod.find(pack_base + "/name").text = self.pkg.name
        data = ET.tostring(prod)
        self.logger.debug("About to put install policy %s", url)
        ret = requests.put(url, auth=self.auth, data=data)
        if ret.status_code != 201:
            raise ProcessorError(
                "Prod policy upload failed: {} : {}".format(ret.status_code, url)
            )

    def patch(self):
        # now we start on the patch definition
        # download the list of titles
        url = self.base + "/patchsoftwaretitles"
        ret = requests.get(url, auth=self.auth)
        self.logger.debug("About to request PST list %s", url)
        if ret.status_code != 200:
            raise ProcessorError(
                "Patch list download failed: {} : {}".format(ret.status_code, url)
            )
        root = ET.fromstring(ret.text)
        # find out title to get ID
        root.findall("patch_software_title")
        ident = 0
        for ps_title in root.findall("patch_software_title"):
            if ps_title.findtext("name") == self.pkg.patch:
                ident = ps_title.findtext("id")
                break
        if ident == 0:
            raise ProcessorError(
                "Patch list did not contain title: {}".format(self.pkg.title)
            )
        # get patch list for our title
        url = self.base + "/patchsoftwaretitles/id/" + str(ident)
        self.logger.debug("About to request PST by ID: %s", url)
        ret = requests.get(url, auth=self.auth)
        if ret.status_code != 200:
            raise ProcessorError(
                "Patch software download failed: {} : {}".format(
                    str(ident), self.pkg.name
                )
            )
        root = ET.fromstring(ret.text)
        # find the patch version that matches our version
        done = False
        for record in root.findall("versions/version"):
            if record.findtext("software_version") == self.pkg.version:
                package = record.find("package")
                add = ET.SubElement(package, "id")
                add.text = self.pkg.idn
                add = ET.SubElement(package, "name")
                add.text = self.pkg.name
                done = True
                break
        if not done:
            raise ProcessorError(
                "Patch definition version not found: {} : {} : {}".format(
                    str(ident), self.pkg.name, self.pkg.version
                )
            )
        # update the patch def
        data = ET.tostring(root)
        self.logger.debug("About to put PST: %s", url)
        ret = requests.put(url, auth=self.auth, data=data)
        if ret.status_code != 201:
            raise ProcessorError(
                "Patch definition update failed with code: %s" % ret.status_code
            )
        # now the patch policy - this will be a journey as well
        # first get the list of patch policies for our software title
        url = self.base + "/patchpolicies/softwaretitleconfig/id/" + str(ident)
        self.logger.debug("About to request patch list: %s", url)
        ret = requests.get(url, auth=self.auth)
        if ret.status_code != 200:
            raise ProcessorError(
                "Patch policy list download failed: {} : {}".format(
                    str(ident), self.pkg.name
                )
            )
        root = ET.fromstring(ret.text)
        pol_list = root.findall("patch_policy")
        pol_id = 0
        for pol in pol_list:
            if "Stable" in pol.findtext("name"):
                pol_id = pol.findtext("id")
                # now grab that policy
                url = self.base + "/patchpolicies/id/" + str(pol_id)
                self.logger.debug("About to request PP by ID: %s", url)
                ret = requests.get(url, auth=self.auth)
                if ret.status_code != 200:
                    raise ProcessorError(
                        "Patch policy download failed: {} : {}".format(
                            str(pol_id), self.pkg.name
                        )
                    )
                # now edit the patch policy
                root = ET.fromstring(ret.text)
                root.find("general/target_version").text = self.pkg.version
                root.find("general/release_date").text = ""
                # create a description with date
                now = datetime.datetime.now().strftime(" (%Y-%m-%d)")
                desc = "Update " + self.pkg.title + now
                root.find("user_interaction/self_service_description").text = desc
                data = ET.tostring(root)
                self.logger.debug("About to update Stable PP: %s", url)
                ret = requests.put(url, auth=self.auth, data=data)
                if ret.status_code != 201:
                    raise ProcessorError(
                        "Stable patch update failed with code: %s" % ret.status_code
                    )
                pol_id = ET.fromstring(ret.text).findtext("id")
            if "Test" in pol.findtext("name"):
                pol_id = pol.findtext("id")
                # now grab that policy
                url = self.base + "/patchpolicies/id/" + str(pol_id)
                self.logger.debug("About to request PP by ID: %s", url)
                ret = requests.get(url, auth=self.auth)
                if ret.status_code != 200:
                    raise ProcessorError(
                        "Patch policy download failed: {} : {}".format(
                            str(pol_id), self.pkg.name
                        )
                    )
                # now edit the patch policy
                root = ET.fromstring(ret.text)
                root.find("general/enabled").text = "false"
                data = ET.tostring(root)
                self.logger.debug("About to update Test PP: %s", url)
                ret = requests.put(url, auth=self.auth, data=data)
                if ret.status_code != 201:
                    raise ProcessorError(
                        "Test patch update failed with code: %s" % ret.status_code
                    )
        return pol_id

    def main(self):
        """Do it!"""
        # clear any pre-exising summary result
        if "Production_summary_result" in self.env:
            del self.env["production_summary_result"]
        self.pkg.title = self.env.get("package")
        if self.env.get("patch"):
            self.pkg.patch = self.env.get("patch")
        else:
            self.pkg.patch = self.pkg.title
        self.logger.debug("About to call lookup for %s", self.pkg.title)
        self.lookup()
        self.production()
        if self.pkg.patch == "None":
            pol = "00"
        else:
            pol = self.patch()
        if pol != "":
            self.env["production_summary_result"] = {
                "summary_text": "The following updates were productionized:",
                "report_fields": ["title", "version"],
                "data": {"title": self.pkg.title, "version": self.pkg.version},
            }


if __name__ == "__main__":
    PROCESSOR = Production()
    PROCESSOR.execute_shell()
