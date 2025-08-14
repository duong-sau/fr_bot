#!/bin/bash

sudo apt-get install -y dos2unix
sudo apt-get install -y screen


BOT_NAME="fr_bot"

cd /home/ubuntu/$BOT_NAME/code
mkdir _settings
mkdir -p /home/ubuntu/$BOT_NAME/{data,logs}

cp -r /home/ubuntu/$BOT_NAME/code/_settings/* _settings/

dos2unix _settings/*