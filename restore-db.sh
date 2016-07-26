#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 dump/{timestamp, like 2016-07-26-1150}" >&2
    exit 1
fi

mongorestore -h localhost:27017 -d eve --maintainInsertionOrder --stopOnError "$1/eve"
