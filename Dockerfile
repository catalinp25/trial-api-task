FROM python:3.10.12

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -m pip install --upgrade bittensor



COPY . .

EXPOSE 8000

# Start the FastAPI app
RUN sed -i 's/\r$//g' /app/start_app.sh
RUN chmod +x /app/start_app.sh
ENTRYPOINT  ["/app/start_app.sh"]