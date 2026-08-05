#!/bin/bash

if [ $# -eq 0 ]
  then
    echo "No arguments supplied"
    exit 1
fi
mv $@ data/chunk/             # Take all arguments and move them to the target directory
sleep 1
timestamp=$(date +%s)
echo "processing $@ ===> chunk_$timestamp.jsonld"
java -jar lib/shexml.jar -m config/basic_schema.shexml -f jsonld -o data/output/chunk_$timestamp.jsonld && rm data/chunk/*
