# Een generieke pipeline voor het transformeren van Axiell Collections data naar Linked Data 

Deze repository biedt een pipeline die het ophalen, transformeren en pushen ondersteunt door middel van Github Actions, ShExML en Python. Op dit moment wordt alleen nog het ophalen van het OAI-PMH endpoint van Axiell Collections ondersteund. 

## Hoe uit te voeren
```
chmod +x run.sh
./run.sh
```

## Configureren


### Endpoint
The endpoint configuration for both the source and target of the data is located in ``` config/config.yml ```. The ```SRC_API_LIMIT``` defines the amount of records harvested per call from the endpoint, and also the size of the chunks being processed by ShExML. If you find your system running out of memory, lower that value. 

### Mapping
There is currently one mapping in development, which maps from the AdlibXML provided by the OAI-PMH endpoint of Axiell Collections to the [NDE Schema.org Application Profile](https://docs.nde.nl/schema-profile/), located in ``` config/collections_schema.shexml ```.
