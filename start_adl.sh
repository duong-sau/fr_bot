#!/bin/bash

screen -ls | grep -o '[0-9]*\.' | sed 's/\.//' | xargs -I {} screen -S {} -X quit

BOT_NAME="fr_bot"

cd /home/ubuntu/$BOT_NAME/code

screen -dmS adl_screen
screen -S adl_screen -X stuff "source .linux_env/bin/activate\n"
screen -S adl_screen -X stuff "python MainProcess/ADLControl/Main.py\n"

screen -r adl_screen



