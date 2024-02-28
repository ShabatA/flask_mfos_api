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
    usedFund = db.Column(db.Float, nullable=False, default= 0)
    accountType = db.Column(db.String)
    notes = db.Column(db.Text)
    lastTransation = db.Column(db.Date, nullable=True)
    health_funds = db.Column(db.Float, nullable=True, default= 0)
    education_funds = db.Column(db.Float, nullable=True, default= 0)
    general_funds = db.Column(db.Float, nullable=True, default= 0)
    shelter_funds = db.Column(db.Float, nullable=True, default= 0)
    sponsorship_funds = db.Column(db.Float, nullable=True, default= 0)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'))
    currency = db.Column(db.String, default = 'USD')
    
    
    projectsFunds = db.relationship('ProjectFunds', backref='projects_data', lazy=True)
    casesFunds = db.relationship('CaseFunds', backref='cases_data', lazy=True)
    donations = db.relationship('Donations', backref='region_account', lazy=True)

    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class FinancialFund(db.Model):
    __tablename__ = 'financial_fund'
    
    fundID = db.Column(db.Integer, primary_key=True)
    fundName = db.Column(db.String, nullable=False)
    totalFund = db.Column(db.Float, nullable=False)
    usedFund = db.Column(db.Float, nullable=True)
    accountType = db.Column(db.String)
    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    currency = db.Column(db.String, default = 'USD')
    
    donations = db.relationship('Donations', backref='financial_fund', lazy=True)
    payments = db.relationship('Payments', backref='financial_fund',lazy=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


# Hold amounts after Project Approval, all payments must spend from this amount
class ProjectFunds(db.Model):
    __tablename__ = 'project_funds'
    
    fundID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=False)
    fundsAllocated = db.Column(db.Float, nullable=True)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

# Hold amounts after Case Approval, all payments must spend from this amount
class CaseFunds(db.Model):
    __tablename__ = 'case_funds'
    
    fundID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=False)
    fundsAllocated = db.Column(db.Float, nullable=True)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    
    
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
    donorType = db.Column(db.String)
    country = db.Column(db.String)
    email = db.Column(db.String)
    phoneNumber = db.Column(db.String)
    
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
    fundID = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    details = db.Column(db.Text, nullable=True)
    currency = db.Column(db.String, default = 'USD')
    field = db.Column(db.String)
    donationType = db.Column(db.String)
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class ProjectFundReleaseRequests(db.Model):
    __tablename__ = 'project_fund_release_requests'
    
    requestID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=False)
    fundsRequested = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    requestedBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approvedAt = db.Column(db.DateTime, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class CaseFundReleaseRequests(db.Model):
    __tablename__ = 'case_fund_release_requests'
    
    requestID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=False)
    fundsRequested = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    requestedBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approvedAt = db.Column(db.DateTime, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        
class TransferStage(Enum):
    ASSESSMENT = 'Pending Assessment'
    ONGOING = 'On Going'
    APPROVED = 'Approved'
    

class FundTransferRequests(db.Model):
    __tablename__ = 'fund_transfer_requests'
    
    requestID = db.Column(db.Integer, primary_key=True)
    from_fund = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'))
    to_fund = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'))
    transferAmount = db.Column(db.Float, nullable=False)
    requestedBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    stage = db.Column(db.Enum(TransferStage), default=TransferStage.ASSESSMENT)
    notes = db.Column(db.Text)
    attachedFiles = db.Column(db.String, nullable=True)
    approvedAt = db.Column(db.DateTime, nullable=True)
    currencyFrom = db.Column(db.String)
    currencyTo = db.Column(db.String)
    exchangeRate = db.Column(db.Float)
    
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class PaymentFor(Enum):
    CASE = 'Case'
    PROJECT = 'Case'
    OTHER = 'Other'

class Payments(db.Model):
    __tablename__ = 'payments'
    
    paymentID = db.Column(db.Integer, primary_key=True)
    from_fund = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'))
    paymentFor = db.Column(db.Enum(PaymentFor), nullable=False, default=PaymentFor.OTHER)
    paymentName = db.Column(db.String)
    paymentMethod = db.Column(db.String)
    amount = db.Column(db.Float)
    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    currency = db.Column(db.String)
    transferExpenses = db.Column(db.Float)
    exchangeRate = db.Column(db.Float)
    supportingFiles = db.Column(db.String, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
     
    
    
    