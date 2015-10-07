activate_this = '/data/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import sys
#import logging
sys.path.append('/data/dev/pillar/pillar/')
from flup.server.fcgi import WSGIServer
from application import app as application

#logging.basicConfig(filename='/tmp/error.log', level=logging.DEBUG)

if __name__ == '__main__':
    WSGIServer(application).run()

