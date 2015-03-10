from eve import Eve

# import config
# from flask import Flask, Blueprint
# from flask.ext.mail import Mail
# from flask.ext.sqlalchemy import SQLAlchemy
# from flask.ext.thumbnails import Thumbnail
# from flask.ext.assets import Environment, Bundle

# Initialize the Flask all object

from eve.io.mongo import Validator

class ValidateCustomFields(Validator):
    def _validate_validcf(self, validcf, field, value):
        if validcf:
            print self.document['node_type']
            if value == 'hi':
                return True
            else:
                self._error(field, "Must be hi")


app = Eve(validator=ValidateCustomFields)


# Filemanager used by Flask-Admin extension
# filemanager = Blueprint('filemanager', __name__, static_folder='static/files')

# # Choose the configuration to load
# app.config.from_object(config.Development)

# # Initialized the available extensions
# mail = Mail(app)
# db = SQLAlchemy(app)
# thumb = Thumbnail(app)
# assets = Environment(app)

# # Import controllers
# from application.modules.nodes import node_types
# from application.modules.nodes import nodes
# from application.modules.main import homepage
# from application.modules.shots import shots
# from application.modules.projects import projects

# # Register blueprints for the imported controllers
# app.register_blueprint(filemanager)
# app.register_blueprint(shots, url_prefix='/shots')
# app.register_blueprint(projects, url_prefix='/projects')
# app.register_blueprint(node_types, url_prefix='/node-types')
# app.register_blueprint(nodes, url_prefix='/nodes')
