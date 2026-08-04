# A generic pipeline for transforming Axiell Collections to Linked Data 
Harvest Axiell Collections data and tranform it to Linked Data using ShExML. Currently, only connections to Axiell Collections via the OAI-PMH API are supported.

## How to Run
```
./run.sh
```

## Configuration


### Endpoint
The endpoint configuration for both the source and target of the data is located in ``` config/config.yml ```. The ```SRC_API_LIMIT``` defines the amount of records harvested per call from the endpoint, and also the size of the chunks being processed by ShExML. If you find your system running out of memory, lower that value. 

### Mapping
There is currently one mapping in development, which maps from the AdlibXML provided by the OAI-PMH endpoint of Axiell Collections to the [NDE Schema.org Application Profile](https://docs.nde.nl/schema-profile/), located in ``` config/collections_schema.shexml ```.
