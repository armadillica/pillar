FROM ubuntu:14.04
MAINTAINER Eibriel <eibriel@eibriel.com>

RUN mkdir attract

RUN apt-get update && apt-get install -y \
git

RUN git clone https://github.com/fsiddi/attract.git /attract/

RUN apt-get update && apt-get install -y \
python-pip

RUN pip install -r /attract/requirements.txt

EXPOSE 5000

CMD ["python", "/attract/attract/manage.py", "runserver"]
