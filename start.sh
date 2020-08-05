#!/bin/bash

cd "$(dirname "$0")"

if [ "$1" == "-u" ]; then
	cp resources/config.json resources/config.json.backup
	git stash
	git pull
	cp resources/config.json.backup resources/config.json
fi

touch .log
sudo docker logs owen-bot >> .log

if sudo docker ps | grep -q "owen-bot"; then
	sudo docker kill "owen-bot"
fi
yes | sudo docker system prune
sudo docker build -t "owen-bot" .
sudo docker run -d --name "owen-bot" -e TZ=Australia/Melbourne \
	-v $(pwd)/resources:/owen-bot/resources "owen-bot"
