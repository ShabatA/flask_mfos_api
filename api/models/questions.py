from ..utils.db import db
# from .answerformat import AnswerFormats
from .cases import Cases


class Questions(db.Model):
    __tablename__ = 'questions'

    questionID = db.Column(db.Integer, primary_key=True)
    questionText = db.Column(db.String, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    formatID = db.Column(db.Integer, db.ForeignKey('answer_formats.formatID'), nullable=False)
    questionType = db.Column(db.String, nullable=False)

    format = db.relationship('AnswerFormats', backref='questions', foreign_keys=[formatID])

    def __repr__(self):
        return f"<Question {self.questionID} {self.questionText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def get_by_id(cls, questionID):
        return cls.query.get_or_404(questionID)
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseQuestionsMappings(db.Model):
    __tablename__ = 'case_questions_mappings'

    mappingID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID'), nullable=False)

    case = db.relationship('Cases', backref='case_questions_mapping', foreign_keys=[caseID])
    question = db.relationship('Questions', backref='case_questions_mapping', foreign_keys=[questionID])

    def __repr__(self):
        return f"<CaseQuestionsMapping {self.mappingID} Case: {self.caseID} Question: {self.questionID}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def get_by_id(cls, mappingID):
        return cls.query.get_or_404(mappingID)
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class AnswerFormats(db.Model):
    __tablename__ = 'answer_formats'

    formatID = db.Column(db.Integer, primary_key=True)
    formatName = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<AnswerFormat {self.formatID} {self.formatName}>"
