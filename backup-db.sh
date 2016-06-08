#!/bin/bash

mongodump -h localhost:27018 -d eve --out dump/$(date +'%Y-%m-%d-%H%M') --excludeCollection tokens
