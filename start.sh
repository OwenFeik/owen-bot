if screen -ls | grep -q "owen-bot"; then
	screen -X -S owen-bot kill
fi
screen -S owen-bot -dm bash -c "cd ~/owen-bot; touch resources/.log; python3.6 bot.py > resources/.log"
