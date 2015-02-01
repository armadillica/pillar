from application import app
from application import db

from application.modules.nodes.models import Node

class NodeShot(db.Model):
    """docstring for NodeShot"""
    id = db.Column(db.Integer, primary_key = True)
    duration = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    node_id = db.Column(db.Integer, db.ForeignKey(Node.id))
    node = db.relationship(Node, backref='node_shot', uselist=False)
        


# Create Many to Many table
"""
assets_tags_table = db.Table('assets_tags', db.Model.metadata,
                           db.Column('asset_id', db.Integer, db.ForeignKey('asset.id')),
                           db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                           )
"""

# class Asset(db.Model): 
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(120), nullable=False)
#     description = db.Column(db.Text, nullable=False)
#     link = db.Column(db.String(512))
#     picture = db.Column(db.String(80))
#     size = db.Column(db.String(7))
#     format = db.Column(db.String(15))
#     duration = db.Column(db.String(15))

#     nodes = db.relationship('Node', secondary=nodes_assets_table)

#     #tags = db.relationship('Tag', secondary=assets_tags_table)

#     def __str__(self):
#         return self.name

"""

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(64))

    def __str__(self):
        return self.name

"""


