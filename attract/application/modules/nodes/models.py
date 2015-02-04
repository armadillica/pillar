from application import app
from application import db

import os
import os.path as op
import datetime

import hashlib
import time

from werkzeug import secure_filename


def prefix_name(obj, file_data):
    # Collect name and extension
    parts = op.splitext(file_data.filename)
    # Get current time (for unique hash)
    timestamp = str(round(time.time()))
    # Has filename only (not extension)
    file_name = secure_filename(timestamp + '%s' % parts[0])
    # Put them together
    full_name = hashlib.md5(file_name).hexdigest() + parts[1]
    return full_name


# Create directory for file fields to use
file_path = op.join(op.dirname(__file__), 'static/files',)
try:
    os.mkdir(file_path)
except OSError:
    pass


class NodeType(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(120), nullable=False)

    custom_fields = db.relationship('CustomFields', backref='NodeType',
        cascade="all, delete, delete-orphan")

    def __str__(self):
        return self.name


class Node(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(120), nullable=False)
    url = db.Column(db.String(120))
    description = db.Column(db.Text)
    main_picture = db.Column(db.String(80))
    order = db.Column(db.Integer)
    creation_date = db.Column(db.DateTime(), default=datetime.datetime.now)
    edit_date = db.Column(db.DateTime())
    
    parent_id = db.Column(db.Integer, db.ForeignKey('node.id'))
    parent = db.relationship('Node', remote_side=[id]) 

    node_type_id = db.Column(db.Integer(), db.ForeignKey(NodeType.id))
    node_type = db.relationship(NodeType, backref='Node')

    properties = db.relationship('NodeProperties', backref='Node',
        cascade="all, delete, delete-orphan")

    def get_property(self, name):
        for p in self.properties:
            if p.custom_field.name_url == name:
                return p
        print 'p'
        return None

    def __str__(self):
        return self.name


class CustomFields(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    node_type_id = db.Column(db.Integer(), db.ForeignKey(NodeType.id))

    field_type = db.Column(db.String(128))
    order = db.Column(db.Integer())
    name = db.Column(db.String(128))
    name_url = db.Column(db.String(128))
    description = db.Column(db.Text())


class NodeProperties(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    node_id = db.Column(db.Integer(), db.ForeignKey(Node.id)) 

    custom_field_id = db.Column(db.Integer(), db.ForeignKey(CustomFields.id))
    custom_field = db.relationship(CustomFields, backref='NodeProperties')

    value = db.Column(db.Text())
