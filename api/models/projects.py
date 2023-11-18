from ..utils.db import db
from .regions import Regions
from .accountfields import AccountFields

class Projects(db.Model):
    __tablename__ = 'projects'

    projectID = db.Column(db.Integer, primary_key=True)
    projectName = db.Column(db.String, nullable=False)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'), nullable=False)
    budgetRequired = db.Column(db.Float, nullable=False)  # Assuming money is represented as Numeric
    budgetAvailable = db.Column(db.Float, nullable=False)  # Assuming money is represented as Numeric
    projectStatus = db.Column(db.String, nullable=False)
    fieldID = db.Column(db.Integer, db.ForeignKey('accountfields.fieldID'))  # Adjust based on your Field table name and primary key column

    def __repr__(self):
        return f"<Project {self.projectID} {self.projectName}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        
    @classmethod
    def get_by_id(cls, projectID):
        return cls.query.get_or_404(projectID)