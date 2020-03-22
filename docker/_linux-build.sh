#!/bin/bash

cd /project/
python3 -m pip install pycairo
# python3 -m pip install --pre beeware
python3 -m pip install -r requirements.txt

cd /project/blackholeguiclient
rm -rfv linux
briefcase create
briefcase build
chown -hR 1000:1000 linux
