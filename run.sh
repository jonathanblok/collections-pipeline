#!/bin/sh

# Harvesting

## Dependencies
echo Setting up Python environment 
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## Harvest
echo Starting OAI-PMH harvester
python src/oai_harvester.py

# Transformation

## Dependencies
echo Downloading ShExML..
wget -O 'lib/shexml.jar' 'https://github.com/herminiogg/ShExML/releases/download/v0.6.1/ShExML-v0.6.1.jar'

## Transform chunk
echo Starting transformation in chunks
find data/export/ -maxdepth 1 -type f | xargs -n 1 ./process_chunks.sh
