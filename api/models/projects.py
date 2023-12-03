from ..utils.db import db
from .regions import Regions
from .users import Users
from enum import Enum

class ProjectStatus(Enum):
    INITIALIZED = 'initialized'
    CLOSED = 'closed'
    PENDING = 'pending'
    IN_PROGRESS = 'in progress'
    REJECTED = 'rejected'

class ProjectCategory(Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'

class Projects(db.Model):
    __tablename__ = 'projects'

    projectID = db.Column(db.Integer, primary_key=True)
    projectName = db.Column(db.String, nullable=False)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'), nullable=False)
    budgetRequired = db.Column(db.Float, nullable=False)
    budgetAvailable = db.Column(db.Float, nullable=False)
    projectStatus = db.Column(db.Enum(ProjectStatus), nullable=False)
    projectScope = db.Column(db.String, nullable=True)  # You can replace 'String' with an appropriate type based on your needs
    category = db.Column(db.Enum(ProjectCategory), nullable=True)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True)
    startDate = db.Column(db.Date, nullable=True)
    dueDate = db.Column(db.Date, nullable=True)

    # Relationship with Questions
    # questions = db.relationship('Questions', backref='project', lazy=True)
    users = db.relationship('Users', secondary='project_users', backref='projects', lazy='dynamic')
    answers = db.relationship('Answers', backref='project', lazy=True)

    def __repr__(self):
        return f"<Project {self.projectID} {self.projectName}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, projectID):
        return cls.query.get_or_404(projectID)

class Questions(db.Model):
    __tablename__ = 'questions'

    questionID = db.Column(db.Integer, primary_key=True)
    # projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    questionText = db.Column(db.String, nullable=False)
    questionType = db.Column(db.String, nullable=False)  # Text input, multiple choice, etc.
    points = db.Column(db.Integer, nullable=False)

    # If the question is multiple choice, store choices in a separate table
    choices = db.relationship('QuestionChoices', backref='question', lazy=True, uselist=True)

    def __repr__(self):
        return f"<Question {self.questionID} {self.questionText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, questionID):
        return cls.query.get_or_404(questionID)
    

class Answers(db.Model):
    __tablename__ = 'answers'

    answerID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID'), nullable=False)
    answerText = db.Column(db.String, nullable=True)  # Adjust based on the answer format

    def __repr__(self):
        return f"<Answer {self.answerID} {self.answerText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, answerID):
        return cls.query.get_or_404(answerID)

class QuestionChoices(db.Model):
    __tablename__ = 'question_choices'

    choiceID = db.Column(db.Integer, primary_key=True)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID'), nullable=False)
    choiceText = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<Choice {self.choiceID} {self.choiceText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, choiceID):
        return cls.query.get_or_404(choiceID)
    
    

class ProjectUser(db.Model):
    __tablename__ = 'project_users'

    id = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)

    def __repr__(self):
        return f"<ProjectUser {self.id} ProjectID: {self.projectID}, UserID: {self.userID}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()