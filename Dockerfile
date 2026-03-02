FROM python:3.11-slim

# CAPTURA A VERSÃO INJETADA PELO GITHUB ACTIONS
ARG APP_VERSION=dev-local
ENV APP_VERSION=${APP_VERSION}

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]