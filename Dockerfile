FROM python:3.10.16-bullseye

ENV PYTHONUNBUFFERED 1

COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN ls

EXPOSE 8000