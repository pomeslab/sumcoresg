#! /usr/bin/env python

import util
from app_config import db

class Usage(db.Model):
    __tablename__ = "usage"

    id = db.Column(db.Integer, primary_key=True)
    clustername = db.Column(db.String(128))
    username = db.Column(db.String(128))
    runningcores = db.Column(db.Integer)
    notrunningcores = db.Column(db.Integer)
    created = db.Column(db.DateTime)

    def __init__(self, clustername, username, runningcores, notrunningcores, created):
        self.clustername = clustername
        self.username = username
        self.runningcores = runningcores
        self.notrunningcores = notrunningcores
        self.created = created

    def __repr__(self):
        return "<{0:20s} on {1:10s} at {2} - running_cores: {3:8d}; not_running_cores: {4:8d}".format(
            self.username, self.clustername, 
            util.format_datetime(self.created),
            self.runningcores, self.notrunningcores)

class Account(db.Model):
    __tablename__ = "account"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128))
    password = db.Column(db.String(128))
    created = db.Column(db.DateTime)

    def __init__(self, email, password, created):
        self.email = email
        self.password = password
        self.created = created

    def __repr__(self):
        return "<{0} joined at {1})>".format(
            self.email, 
            util.format_datetime(self.created))

class Figure(db.Model):
    __tablename__ = 'figure'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    # db.BINARY doesn't work, haven't tried db.BLOB 
    content = db.Column(db.LargeBinary)
    created = db.Column(db.DateTime)

    def __init__(self, name, content, created):
        self.name = name
        self.content = content
        self.created = created

    def __repr(self):
        return "<{0} created on {1}>".format(self.name, self.created)
