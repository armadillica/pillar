import sys
from flup.server.fcgi import WSGIServer
from application import app

activate_this = '/data/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
sys.path.append('/data/dev/pillar/pillar/')

if __name__ == '__main__':
    WSGIServer(app).run()
