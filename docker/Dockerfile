FROM node:24-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        supervisor && \
    rm -rf /var/lib/apt/lists/*

COPY requirements requirements/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements/prod.txt

COPY ./app /app
COPY ./scripts /scripts
COPY --from=frontend-builder /frontend/dist /app/frontend

EXPOSE 8000
EXPOSE 50051

RUN chmod +x /scripts/*

ENTRYPOINT ["/scripts/entrypoint.sh"]
