# A generic pipeline for transforming Axiell Collections to Linked Data 
Harvest Axiell Collections data and tranform it to Linked Data using ShExML. Currently, only connections to Axiell Collections via the OAI-PMH API are supported.

## How to Run
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=config/
wget -O 'lib/shexml.jar' 'https://github.com/herminiogg/ShExML/releases/download/v0.6>'
python src/oai_harvester.py
java -jar lib/shexml.jar -m config/collections_schema.shexml -f jsonld -o data/output/data.jsonld 
```

## Configuration
### Endpoint
The endpoint configuration for both the source and target of the data is located in ``` config/endpoint.py ```.

### Mapping
There is currently one mapping in development, which maps from the AdlibXML provided by the OAI-PMH endpoint of Axiell Collections to the [NDE Schema.org Application Profile](https://docs.nde.nl/schema-profile/), located in ``` config/collections_schema.shexml ```.
