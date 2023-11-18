from ..utils.db import db
from enum import Enum
from datetime import datetime
from .regions import Regions


class UserRole(Enum):
    ADMIN = "admin"
    REGIONLEADER = "regionleader"
    STAFF = "staff"
    ORGANIZATION = "organization"

class UserStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Users(db.Model):
    __tablename__ = 'users'

    userID = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), index=True, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    firstName = db.Column(db.String)
    lastName = db.Column(db.String)
    jobDescription = db.Column(db.String)
    userRole = db.Column(db.Enum(UserRole))
    mobile = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=False)
    UserStatus = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'))


    def __repr__(self):
        return f"<Users {self.UserID} {self.Username}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, userID):
        return cls.query.get_or_404(userID)