FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
COPY manage.py /app/manage.py

WORKDIR /app/src/api

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
