FROM python:3.11-slim

WORKDIR /app
COPY app /app

RUN pip install --no-cache-dir flask requests werkzeug gunicorn

EXPOSE 8080
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "main:app"]
