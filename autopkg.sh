#!/usr/bin/env zsh

# autopkg.sh
# v2.0 ARW 2020-03-19

# run the package build
/usr/local/bin/autopkg run --recipe-list=/Users/"$(whoami)"/Documents/PatchBotTools/packages.txt \
    --post com.honestpuck.PatchBot/JPCImporter \
    --report-plist=/Users/"$(whoami)"/Documents/JPCImporter.plist \
    -k FAIL_RECIPES_WITHOUT_TRUST_INFO=yes

# messages to MS Teams
/Users/"$(whoami)"/Documents/PatchBotTools/Teams.py \
    /Users/"$(whoami)"/Documents/JPCImporter.plist

# run the patch management
/usr/local/bin/autopkg run --recipe-list=/Users/"$(whoami)"/Documents/PatchBotTools/patch.txt \
    --report-plist=/Users/"$(whoami)"/Documents/PatchManager.plist \
    -k FAIL_RECIPES_WITHOUT_TRUST_INFO=yes

# messages to MS Teams
/Users/"$(whoami)"/Documents/PatchBotTools/PatchTeams.py \
    /Users/"$(whoami)"/Documents/PatchManager.plist
