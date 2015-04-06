FROM ubuntu:14.04
MAINTAINER Eibriel <eibriel@eibriel.com>

RUN apt-get update && apt-get install -y \
mongodb

#RUN mkdir /data && mkdir /data/db

RUN mkdir /data

VOLUME /data/db 

CMD ["mongod", "--smallfiles"]

EXPOSE 27017

#CMD ["python", "/attract/attract/manage.py", "runserver", "-DFOREGROUND"]
