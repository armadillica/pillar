FROM ubuntu:14.04
MAINTAINER Francesco Siddi <francesco@blender.org>

RUN apt-get update && apt-get install -y \
python \
python-dev \
python-pip \
git \
vim \
nano \
zlib1g-dev \
libjpeg-dev \
python-crypto \
python-openssl \
libssl-dev \
libffi-dev \
software-properties-common \
apache2-mpm-event \
libapache2-mod-wsgi \
libapache2-mod-xsendfile

RUN add-apt-repository ppa:mc3man/trusty-media \
&& apt-get update && apt-get install -y \
ffmpeg

RUN mkdir /data \
&& mkdir /data/www \
&& mkdir /data/www/pillar \
&& mkdir /data/dev \
&& mkdir /data/dev/pillar \
&& mkdir /storage \
&& mkdir /storage/shared \
&& mkdir /storage/pillar \
&& mkdir /data/config \
&& mkdir /storage/logs

ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2
ENV APACHE_PID_FILE /var/run/apache2.pid
ENV APACHE_RUN_DIR /var/run/apache2
ENV APACHE_LOCK_DIR /var/lock/apache2

RUN mkdir -p $APACHE_RUN_DIR $APACHE_LOCK_DIR $APACHE_LOG_DIR

RUN git clone https://github.com/armadillica/pillar.git /data/www/pillar

RUN pip install virtualenv \
&& virtualenv /data/venv

RUN . /data/venv/bin/activate \
&& pip install -r /data/www/pillar/requirements.txt

VOLUME /data/dev/pillar
VOLUME /data/config
VOLUME /storage/shared
VOLUME /storage/pillar

ENV MONGO_HOST mongo_pillar

EXPOSE 80

ADD 000-default.conf /etc/apache2/sites-available/000-default.conf

CMD ["/usr/sbin/apache2", "-D", "FOREGROUND"]
