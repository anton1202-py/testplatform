FROM python:3.12-slim

ENV TZ=Europe/Moscow
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

COPY pyproject.toml poetry.lock /opt/app/
RUN pip install poetry

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-dev

COPY . /opt/app

RUN chmod +x entrypoint.sh
RUN chmod +x entrypoint_worker.sh
RUN chmod +x entrypoint_scheduler.sh
