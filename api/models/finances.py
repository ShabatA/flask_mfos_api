from ..utils.db import db
from enum import Enum
from datetime import datetime
from flask import jsonify
from http import HTTPStatus
from sqlalchemy.dialects.postgresql import JSONB

class RegionAccount(db.Model):
    __tablename__ = 'region_account'
    
    accountID = db.Column(db.Integer, primary_key=True)
    accountName = db.Column(db.String, nullable=False)
    totalFund = db.Column(db.Float, nullable=False)
    availableFund = db.Column(db.Float, nullable=False)
    
    answers = db.relationship('ProjectFunds', backref='projects', lazy=True)


class ProjectFunds(db.Model):
    __tablename__ = 'project_funds'
    
    fundID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    fundsAllocated = db.Column(db.Float, nullable=True)
    
    
    