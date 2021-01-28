#!/usr/bin/env zsh

# autopkg.sh
# v2.0 ARW 2020-03-19

# run the package build
/usr/local/bin/autopkg run --recipe-list=packages.txt \
    --report-plist=JPCImporter.plist \
    --post com.honestpuck.PatchBot/JPCImporter \
    -k FAIL_RECIPES_WITHOUT_TRUST_INFO=yes

# messages to MS Teams
./Teams.py JPCImporter.plist

# run the patch management
/usr/local/bin/autopkg run --recipe-list=patch.txt \
    --report-plist=PatchManager.plist \
    -k FAIL_RECIPES_WITHOUT_TRUST_INFO=yes

# messages to MS Teams
./PatchTeams.py PatchManager.plist

# run production shift
/usr/local/bin/autopkg run --recipe-list=Production.txt \
    --report-plist=Production.plist \
    -k FAIL_RECIPES_WITHOUT_TRUST_INFO=yes

# messages to MS Teams
./ProdTeams.py Production.plist
