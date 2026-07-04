FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY duty_bot/ duty_bot/

ENTRYPOINT ["python", "-m", "duty_bot"]
