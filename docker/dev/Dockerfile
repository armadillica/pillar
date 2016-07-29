FROM ubuntu:14.04
MAINTAINER Francesco Siddi <francesco@blender.org>

RUN apt-get update && apt-get install -y \
python \
python-dev \
python-pip \
vim \
nano \
zlib1g-dev \
libjpeg-dev \
python-crypto \
python-openssl \
libssl-dev \
libffi-dev \
software-properties-common \
git

RUN add-apt-repository ppa:mc3man/trusty-media \
&& apt-get update && apt-get install -y \
ffmpeg

RUN mkdir -p /data/git/pillar \
&& mkdir -p /data/storage/shared \
&& mkdir -p /data/storage/pillar \
&& mkdir -p /data/config \
&& mkdir -p /data/storage/logs

RUN pip install virtualenv \
&& virtualenv /data/venv

ENV PIP_PACKAGES_VERSION = 2
ADD requirements.txt /requirements.txt

RUN . /data/venv/bin/activate && pip install -r /requirements.txt

VOLUME /data/git/pillar
VOLUME /data/config
VOLUME /data/storage/shared
VOLUME /data/storage/pillar

ENV MONGO_HOST mongo_pillar

EXPOSE 5000

ADD runserver.sh /runserver.sh

ENTRYPOINT ["bash", "/runserver.sh"]
