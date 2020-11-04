#!/bin/bash
set -eu
trap "" SIGINT

DOWNLOAD_URL=$(curl -fsSL https://api.github.com/repos/SupersonicAds/spotcli/releases/latest \
        | grep browser_download_url \
        | cut -d '"' -f 4)
WHEEL_FILE="$(mktemp -d)/${DOWNLOAD_URL##*/}"
trap "rm -f $WHEEL_FILE || true && echo 'ERROR: SpotCLI wasn\\'t installed' && exit 1" ERR

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
    echo -en "You may need to enter sudo password"
    PIP="sudo $(which pip3)"
else
    echo -en "ERROR: Python 3 not found\n"
    exit 1
fi

echo -en "Installing SpotCLI..."
PIP_STDOUT=$(mktemp)
$PIP install "$WHEEL_FILE" >/dev/null
rm -f $WHEEL_FILE
rm -f $PIP_STDOUT
mkdir -p $HOME/.spot
touch $HOME/.spot/config.yaml
echo -en "done\n"

echo -en "Verifying installation..."
[[ $(spotcli version) == *"SpotCLI version"* ]]
echo -en "ok\n"

trap - EXIT
trap - SIGINT
