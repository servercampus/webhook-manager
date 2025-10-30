FROM python:3.11-slim

WORKDIR /app
COPY app /app

RUN pip install --no-cache-dir flask requests werkzeug

EXPOSE 8080
CMD ["python", "main.py"]
