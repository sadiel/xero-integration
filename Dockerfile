FROM python:3.7-slim-buster
MAINTAINER Sadiel Orama "sadiel.o@gmail.com"
COPY src /src
COPY . /
WORKDIR src
RUN pip install pyxero
CMD python runserver.py