#!/usr/bin/env bash
set -e

pip install -r requirements.txt

python Pizza_bidding_app/manage.py collectstatic --noinput
python Pizza_bidding_app/manage.py migrate
