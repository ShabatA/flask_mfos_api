from ..utils.db import db


class AnswerFormats(db.Model):
    __tablename__ = 'answer_formats'

    formatID = db.Column(db.Integer, primary_key=True)
    formatName = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<AnswerFormat {self.formatID} {self.formatName}>"