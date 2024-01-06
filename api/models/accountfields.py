from ..utils.db import db
from enum import Enum


class FieldName(Enum):
    Health = 'Health',
    Education = 'Education',
    General = 'General',
    Shelter = 'Shelter',
    Sponsorship = 'Sponsorship'



class AccountFields(db.Model):
    __tablename__ = 'accountfields'

    fieldID = db.Column(db.Integer, primary_key=True)
    fieldName = db.Column(db.Enum(FieldName), nullable=False)
    percentage = db.Column(db.Float, nullable=False)  # Assuming money is represented as Numeric

    def __repr__(self):
        return f"<Field {self.fieldID} {self.fieldName}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, fieldID):
        return cls.query.get_or_404(fieldID)