screen -ls | grep -o '[0-9]*\.' | sed 's/\.//' | xargs -I {} screen -S {} -X quit
