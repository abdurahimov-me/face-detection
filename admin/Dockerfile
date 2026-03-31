# Python image versiyasini belgilash
FROM python:3.12-slim

# shell
SHELL ["/bin/bash", "-c"]

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Katalogni o'rnatish
WORKDIR /app

# Requirements faylini konteynerga nusxalash
COPY requirements.txt requirements.txt

# Python kutubxonalarini o'rnatish
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


RUN mkdir -p /opt/run

# Barcha loyihani konteynerga nusxalash
COPY  . .


