#!/bin/sh

echo Setting up Python environment 
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=config/
echo Downloading ShExML
wget -O 'lib/shexml.jar' 'https://github.com/herminiogg/ShExML/releases/download/v0.6.1/ShExML-v0.6.1.jar'
rm data/export/*.xml
echo Starting OAI-PMH harvester
python src/oai_harvester.py
rm data/output/*.jsonld
echo Starting transformation
java -jar lib/shexml.jar -m config/collections_schema.shexml -f jsonld -o data/output/kc.jsonld
