FROM python:3.6
WORKDIR /owen-bot
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
CMD [ "python", "-u", "bot.py", "&>>", "resources/.log" ]
