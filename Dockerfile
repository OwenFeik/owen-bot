FROM python:3.6
WORKDIR /owen-bot
COPY requirements.txt .
EXPOSE 80
RUN pip install -r requirements.txt
COPY src/ .
CMD [ "python", "bot.py" ]
