FROM debian
MAINTAINER Francesco Siddi <francesco@blender.org>

RUN apt-get update && apt-get install -y \
python \
python-dev \
python-pip \
git \
nano \
zlib1g-dev \
libjpeg-dev \


RUN mkdir /data
RUN mkdir /data/www
RUN mkdir /data/www/pillar
RUN mkdir /data/dev
RUN mkdir /data/dev/pillar

RUN git clone https://github.com/armadillica/pillar.git /data/www/pillar

RUN pip install virtualenv
RUN virtualenv /data/venv
RUN . /data/venv/bin/activate && pip install -r /data/www/pillar/requirements.txt

VOLUME /data/dev/pillar

ENV MONGO_HOST mongo_pillar

EXPOSE 5000

ADD runserver.sh /runserver.sh

ENTRYPOINT ["bash", "/runserver.sh"]
