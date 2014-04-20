from flask import (abort,
                   Blueprint,
                   jsonify,
                   render_template,
                   redirect,
                   request)

from flask.ext.thumbnails import Thumbnail
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.orm import aliased

from application.models.model import (
    Node,
    NodeType)

# Name of the Blueprint
projects = Blueprint('projects', __name__)

@projects.route("/")
def index():
    projects = {}
    for project in Node.query.\
        join(NodeType).\
        filter(NodeType.url == 'project'):
        status = None
        if project.status:
            status = project.status.name
        projects[project.id] = dict(
            name=project.name,
            status=status)
    return jsonify(projects=projects)
