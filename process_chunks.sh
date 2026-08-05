#!/bin/bash

if [ $# -eq 0 ]
  then
    echo "No arguments supplied"
    exit 1
fi
mv $@ data/chunk/             # Take file and move them to the target directory
sleep 1
filename=chunk_$(date +%s).jsonld
echo "processing $@ ===> data/output/$filename"
java -jar lib/shexml.jar -m config/basic_schema.shexml -f jsonld -o data/output/$filename && rm data/chunk/*.xml