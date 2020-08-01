#!/bin/bash

cd "$(dirname "$0")"
cp src/resources/config.json src/resources/config.json.backup
git stash
git pull
cp src/resources/config.json.backup src/resources/config.json
if sudo docker ps | grep -q "owen-bot"; then
	sudo docker kill "owen-bot"
fi
sudo docker build -t "owen-bot" .
sudo docker run -d -name "owen-bot" -p 80:80 "owen-bot"
