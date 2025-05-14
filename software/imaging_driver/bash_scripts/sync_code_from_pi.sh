#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
rsync -avz --progress --exclude={'*.egg-info','.git','bash_scripts'} -e 'ssh -p 22' pi@imaging.local:/home/pi/src/imaging_driver "$SCRIPT_DIR/../../"