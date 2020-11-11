#!/bin/bash
set -e
trap "" SIGINT

[ -z "$LC_ALL" ] && export LC_ALL=C.UTF-8
[ -z "$LANG" ] && export LANG=C.UTF-8

DOWNLOAD_URL=$(curl -fsSL https://api.github.com/repos/SupersonicAds/spotcli/releases/latest \
        | grep browser_download_url \
        | cut -d '"' -f 4)
WHEEL_FILE="$(mktemp -d)/${DOWNLOAD_URL##*/}"
trap "rm -f $WHEEL_FILE >/dev/null 2>&1 || true && echo \"ERROR: SpotCLI wasn't installed\" && exit 1" ERR

echo -en "Downloading latest wheel from GitHub..."
curl -fsSL -o $WHEEL_FILE "$DOWNLOAD_URL"
echo -en "done\n"

echo -en "Detecting Python..."
if pyenv versions >/dev/null 2>&1 && [[ $(python -V 2>/dev/null) == *"Python 3"* ]]
then
    echo -en "$(python -V | sed 's/Python //g') (pyenv)\n"
    PIP="$(which pip)"
elif HOMEBREW_PIP=$(brew list python3 -q 2>/dev/null | grep "pip3$")
then
    echo -en "$($HOMEBREW_PIP -V | grep -Eo 'python [0-9.]+' | sed 's/python //g') (homebrew)\n"
    PIP=$HOMEBREW_PIP
elif [[ $(python3 -V 2>/dev/null) == *"Python 3"* ]]
then
    echo -en "$(python3 -V | sed 's/Python //g') (system)\n"
    PIP="$(which pip3)"
    if [ $(id -u 2>/dev/null) != "0" ] && which sudo >/dev/null 2>&1
    then
        PIP="$(which sudo) $PIP"
    fi
else
    echo -en "ERROR: Python 3 not found\n"
    exit 1
fi

echo -en "Installing SpotCLI..."
PIP_STDOUT=$(mktemp 2>/dev/null)
$PIP install --upgrade -qq "$WHEEL_FILE"
rm -f $WHEEL_FILE >/dev/null 2>&1 || true
rm -f $PIP_STDOUT >/dev/null 2>&1 || true
mkdir -p $HOME/.spot >/dev/null
touch $HOME/.spot/config.yaml >/dev/null
echo -en "done\n"

echo -en "Verifying installation..."
[[ $(spotcli version 2>/dev/null) == *"SpotCLI version"* ]]
echo -en "ok\n"

trap - EXIT
trap - SIGINT
