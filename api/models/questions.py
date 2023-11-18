from ..utils.db import db

class Questions(db.Model):
    __tablename__ = 'questions'

    questionID = db.Column(db.Integer, primary_key=True)
    questionText = db.Column(db.String, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    formatID = db.Column(db.Integer, db.ForeignKey('answer_formats.formatID'), nullable=False)
    questionType = db.Column(db.String, nullable=False)

    format = db.relationship('AnswerFormat', backref='questions', foreign_keys=[formatID])

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




