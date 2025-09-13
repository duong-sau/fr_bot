#!/bin/bash
screen -ls | grep -o '[0-9]*\.' | sed 's/\.//' | xargs -I {} screen -S {} -X quit

BOT_NAME="fr_bot"

cd /home/ubuntu/$BOT_NAME/code

screen -dmS server_screen
screen -S server_screen -X stuff "source .linux_env/bin/activate\n"
screen -S server_screen -X stuff "export PYTHONPATH=/home/ubuntu/fr_bot/code\n"
screen -S server_screen -X stuff "python MainProcess/BotController.py\n"




