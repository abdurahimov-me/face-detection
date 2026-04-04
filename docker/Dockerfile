FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        postgresql-client \
        curl \
        supervisor && \
    rm -rf /var/lib/apt/lists/*

COPY requirements requirements/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements/prod.txt

COPY ./app /app

EXPOSE 8000
EXPOSE 50051

COPY ./scripts /scripts
RUN chmod +x /scripts/*

ENTRYPOINT ["/scripts/entrypoint.sh"]