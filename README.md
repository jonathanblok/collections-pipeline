# A generic pipeline for Axiell Collections to Linked Data 
Harvest Axiell Collections data and tranform it to Linked Data using ShExML.

## How to Run

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=config/
wget -O 'lib/shexml.jar' 'https://github.com/herminiogg/ShExML/releases/download/v0.6>
python src/oai_harvester.py
java -jar lib/shexml.jar -m config/collections_schema.shexml -f jsonld -o data/output>

```

## Configuration
### Endpoint
``` config/endpoint.py ```
### Mapping
``` config/collections_schema.shexml ```