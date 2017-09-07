#!/bin/bash -ex

mongodump -h localhost:27018 -d cloud --out dump/$(date +'%Y-%m-%d-%H%M') --excludeCollection tokens --excludeCollection flamenco_task_logs
