#!/bin/bash
set -e

usage="usage: $0 [bot] [language]

positional arguments:
  bot           which bot to run, eg. base
  language      which language of the bot to run, eg. eng"

if (( $# != 2 )); then
    echo "$usage"
    exit 1
fi


rasa run actions --actions "$1.actions.actions" &
child=$!
trap 'kill -TERM "$child"' SIGTERM EXIT

rasa train --data "$1/data" -d "$1/domain-$2.yml"
rasa shell
