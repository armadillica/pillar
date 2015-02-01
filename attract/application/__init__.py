import config
from flask import Flask, Blueprint
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.thumbnails import Thumbnail
from flask.ext.assets import Environment, Bundle

# Initialize the Flask all object
app = Flask(__name__, 
    template_folder='templates',
    static_folder='static')

# Filemanager used by Flask-Admin extension
filemanager = Blueprint('filemanager', __name__, static_folder='static/files')

# Choose the configuration to load
app.config.from_object(config.Development)

# Initialized the available extensions
mail = Mail(app)
db = SQLAlchemy(app)
thumb = Thumbnail(app)
assets = Environment(app)

# Import controllers
#from models import model
from application.modules.main import homepage
from application.modules.shots import shots
from application.modules.projects import projects

# Register blueprints for the imported controllers
app.register_blueprint(filemanager)
app.register_blueprint(shots, url_prefix='/shots')
app.register_blueprint(projects, url_prefix='/projects')
