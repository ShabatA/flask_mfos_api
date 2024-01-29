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
    
    projectsFunds = db.relationship('ProjectFunds', backref='projects_data', lazy=True)
    casesFunds = db.relationship('CaseFunds', backref='cases', lazy=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()



class ProjectFunds(db.Model):
    __tablename__ = 'project_funds'
    
    fundID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    fundsAllocated = db.Column(db.Float, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class CaseFunds(db.Model):
    __tablename__ = 'case_funds'
    
    fundID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    fundsAllocated = db.Column(db.Float, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Donors(db.Model):
    __tablename__ = 'donors'
    
    donorID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    
    donations = db.relationship('Donations', backref='donors', lazy=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Donations(db.Model):
    __tablename__ = 'donations'
    
    id = db.Column(db.Integer, primary_key=True)
    donorID = db.Column(db.Integer, db.ForeignKey('donors.donorID'), nullable=False)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    
    