#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 dump/{timestamp, like 2016-07-26-1150}" >&2
    exit 1
fi

echo "THIS WILL DROP EXISTING CONNECTIONS"
echo "Press [ENTER] to continue, [CTRL]+[C] to abort."
read dummy

mongorestore -h localhost:27017 -d eve --drop --maintainInsertionOrder --stopOnError "$1/cloud"
