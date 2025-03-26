FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir aiohttp==3.8.4 && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]
