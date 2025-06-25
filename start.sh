#!/bin/bash

screen -ls | grep -o '[0-9]*\.' | sed 's/\.//' | xargs -I {} screen -S {} -X quit

BOT_NAME="fr_bot"

cd /home/ubuntu/$BOT_NAME/code
dos2unix ini/*
mkdir -p /home/ubuntu/$BOT_NAME/{data,logs}
# sudo mount -t tmpfs -o size=32M tmpfs /home/ubuntu/$BOT_NAME/data

screen -dmS main_screen
screen -S main_screen -X stuff "source linux_env/bin/activate\n"
screen -S main_screen -X stuff "python AssetControl/Asset_Process.py\n"

screen -dmS discord_screen
screen -S discord_screen -X stuff "source linux_env/bin/activate\n"
screen -S discord_screen -X stuff "python Discord.py /home/ubuntu/fr_bot/logs/asset/syslog.log\n"
