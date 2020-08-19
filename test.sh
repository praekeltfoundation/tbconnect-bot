#!/bin/bash
set -e

usage="usage: $0 [bot] [language]

positional arguments:
  bot           which bot to test, eg. base
  language      which language of the bot to test, eg. eng"

if (( $# != 2 )); then
    echo "$usage"
    exit 1
fi

black --check .
isort -rc -c .
mypy "$1"
flake8 .
py.test
rasa data validate --data "$1/data" -d "$1/domain-$2.yml"
rasa train --data "$1/data" -d "$1/domain-$2.yml"
rasa test --fail-on-prediction-errors --stories "$1/tests" --nlu "$1/data"
