#!/bin/bash

cd "$(dirname "$0")"

touch resources/.log

if sudo docker ps | grep -q "owen-bot"; then
	sudo docker logs owen-bot &>> resources/.log
	sudo docker kill "owen-bot"
fi

MODE=$1

if [ "$MODE" == "-u" ]; then
	cp resources/config.json resources/config.json.backup
	git stash
	git pull
	cp resources/config.json.backup resources/config.json

	MODE="-b"
fi

if [ "$MODE" == "-b" ]; then
	sudo docker rm owen-bot
	sudo docker build -t "owen-bot" .
fi

sudo docker run -d --name "owen-bot" -e TZ=Australia/Melbourne \
	-v $(pwd)/resources:/owen-bot/resources "owen-bot"
