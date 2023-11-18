from ..utils.db import db
from .cases import Cases
from .questions import Questions



class CaseQuestionsMappings(db.Model):
    __tablename__ = 'case_questions_mappings'

    mappingID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID'), nullable=False)

    case = db.relationship('Cases', backref='case_questions_mapping', foreign_keys=[caseID])
    question = db.relationship('Questions', backref='case_questions_mapping', foreign_keys=[questionID])

    def __repr__(self):
        return f"<CaseQuestionsMapping {self.mappingID} Case: {self.caseID} Question: {self.questionID}>"