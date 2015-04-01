from application import app
#from application import db
from flask.ext.script import Manager
# from flask.ext.migrate import Migrate
# from flask.ext.migrate import MigrateCommand

# migrate = Migrate(app, db)
manager = Manager(app)
# manager.add_command('db', MigrateCommand)

@manager.command
def create_all_tables():
    pass
    #db.create_all()

@manager.command
def runserver():
    try:
       import config
       PORT = config.Development.PORT
       HOST = config.Development.HOST
       DEBUG = config.Development.DEBUG
    except ImportError:
       PORT = 4000
       HOST = '0.0.0.0'
       DEBUG = True

    app.run(
        port=PORT,
        host=HOST,
        debug=DEBUG)

if __name__ == '__main__':
    manager.run()
