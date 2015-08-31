FROM debian
MAINTAINER Francesco Siddi <francesco@blender.org>

RUN apt-get update && apt-get install -y \
python \
python-dev \
python-pip \
git \
nano

RUN mkdir /data
RUN mkdir /data/www
RUN mkdir /data/www/attract_server_dev
#RUN git clone https://github.com/armadillica/attract.git /data/www/attract

RUN pip install virtualenv
RUN virtualenv /data/venv
#RUN . /data/venv/bin/activate
#RUN pip install -r requirements.txt

VOLUME /data/www/attract_server_dev

EXPOSE 5000

ENTRYPOINT . /data/venv/bin/activate; \
cd /data/www/attract_server_dev; \
