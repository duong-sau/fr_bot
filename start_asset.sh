#!/bin/bash

screen -ls | grep -o '[0-9]*\.' | sed 's/\.//' | xargs -I {} screen -S {} -X quit

BOT_NAME="fr_bot"

cd /home/ubuntu/$BOT_NAME/code
dos2unix _settings/*
mkdir -p /home/ubuntu/$BOT_NAME/{data,logs}
# sudo mount -t tmpfs -o size=32M tmpfs /home/ubuntu/$BOT_NAME/data

screen -dmS main_screen
screen -S main_screen -X stuff "source .linux_env/bin/activate\n"
screen -S main_screen -X stuff "python MainProcess/AssetControl/Main.py\n"

screen -r main_screen
