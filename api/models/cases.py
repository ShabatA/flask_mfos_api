from ..utils.db import db
from enum import Enum
from werkzeug.exceptions import NotFound
from datetime import datetime

class CaseStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Cases(db.Model):
    """
    Represents a case in the application.

    Attributes:
        caseID (int): The unique identifier for the case.
        caseName (str): The name of the case.
        budgetRequired (Decimal): The budget required for the case.
        budgetAvailable (Decimal): The budget available for the case.
        caseStatus (CaseStatus): The status of the case.
        caseCategory (str): The category of the case.
        userID (int): The user ID associated with the case.
        regionID (int): The region ID associated with the case.
        user (Users): The user associated with the case.
        region (Regions): The region associated with the case.
        createdAt (datetime): The date and time when the case was created.
    """

    __tablename__ = 'cases'

    caseID = db.Column(db.Integer, primary_key=True)
    caseName = db.Column(db.String, nullable=False)
    budgetRequired = db.Column(db.Numeric(precision=10, scale=2))
    budgetAvailable = db.Column(db.Numeric(precision=10, scale=2))
    caseStatus = db.Column(db.Enum(CaseStatus))
    caseCategory = db.Column(db.String, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'))
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    region = db.relationship('Regions', backref='cases', foreign_keys=[regionID])

    def __init__(self, caseName, budgetRequired, budgetAvailable, caseStatus, caseCategory, userID, regionID, createdAt=None):
        self.caseName = caseName
        self.budgetRequired = budgetRequired
        self.budgetAvailable = budgetAvailable
        self.caseStatus = caseStatus
        self.caseCategory = caseCategory
        self.userID = userID
        self.regionID = regionID
        self.createdAt = createdAt or datetime.utcnow()

    def __repr__(self):
        return f"<Case {self.caseID} {self.caseName}>"

    def save(self):
        """
        Save the case to the database.
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        Delete the case from the database.
        """
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, caseID: int) -> 'Cases':
        """
        Get a case by its ID.

        Args:
            caseID (int): The ID of the case to retrieve.

        Returns:
            Cases: The case with the specified ID.

        Raises:
            NotFound: If no case with the specified ID is found.
        """
        case = cls.query.get(caseID)
        if case is None:
            raise NotFound(f"Case with ID {caseID} not found.")
        return case
