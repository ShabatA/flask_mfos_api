from ..utils.db import db
from enum import Enum

class CaseStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class CaseCategory(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"



class Cases(db.Model):
    __tablename__ = 'cases'

    caseID = db.Column(db.Integer, primary_key=True)
    caseName = db.Column(db.String, nullable=False)
    budgetRequired = db.Column(db.Numeric(precision=10, scale=2), nullable=False)  # Assuming money is represented as Numeric
    budgetAvailable = db.Column(db.Numeric(precision=10, scale=2), nullable=False)  # Assuming money is represented as Numeric
    caseStatus = db.Column(db.String, nullable=False)
    caseCategory = db.Column(db.String)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    fieldID = db.Column(db.Integer, db.ForeignKey('accountfields.fieldID'))  # Adjust based on your Field table name and primary key column
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'))  # Adjust based on your Region table name and primary key column

    user = db.relationship('Users', backref='cases', foreign_keys=[userID])
    field = db.relationship('AccountFields', backref='cases', foreign_keys=[fieldID])
    region = db.relationship('Regions', backref='cases', foreign_keys=[regionID])

    def __repr__(self):
        return f"<Case {self.caseID} {self.caseName}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def get_by_id(self, caseID):
        return self.query.get_or_404(caseID)
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, caseID):
        return cls.query.get_or_404(caseID)
