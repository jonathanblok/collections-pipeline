#!/bin/bash

mv $@ data/chunk/             # Take all arguments and move them to the target directory
sleep 1
timestamp=$(date +%s)
java -jar lib/shexml.jar -m config/collections_schema.shexml -f jsonld -o data/output/$timestamp.jsonld && rm data/chunk/*