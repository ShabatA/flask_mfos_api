from ..utils.db import db
from enum import Enum
from werkzeug.exceptions import NotFound
from datetime import datetime
from flask import jsonify
from http import HTTPStatus

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
    caseCategory = db.Column(db.String)
    serviceRequired = db.Column(db.String)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'))
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    region = db.relationship('Regions', backref='cases', foreign_keys=[regionID])
    startDate = db.Column(db.Date, nullable=True)
    dueDate = db.Column(db.Date, nullable=True)
    # Relationship with Questions
    # questions = db.relationship('Questions', backref='project', lazy=True)
    users = db.relationship('Users', secondary='case_users', backref='cases', lazy='dynamic')
    answers = db.relationship('CAnswers', backref='cases', lazy=True)

    # def __init__(self, caseName, budgetRequired, budgetAvailable, caseStatus, caseCategory, userID, regionID, createdAt=None):
    #     self.caseName = caseName
    #     self.budgetRequired = budgetRequired
    #     self.budgetAvailable = budgetAvailable
    #     self.caseStatus = caseStatus
    #     self.caseCategory = caseCategory
    #     self.userID = userID
    #     self.regionID = regionID
    #     self.createdAt = createdAt or datetime.utcnow()

    def __repr__(self):
        return f"<Case {self.caseID} {self.caseName}>"

    def delete(self):
        """
        Delete the case from the database.
        """
        db.session.delete(self)
        db.session.commit()

    def save(self, answers=None):
        db.session.add(self)
        db.session.commit()

        # If answers are provided, create and assign them to the project
        if answers:
            self.assign_answers(answers)
    
    def calculate_total_points(self):
        total_points = 0

        # Fetch answers associated with the project
        answers = CAnswers.query.filter_by(caseID=self.caseID).all()

        for answer in answers:
            # If the answer is for a text-based question, add its points
            if answer.choice is None:
                total_points += answer.question.points
            else:
                # If the answer is for a single-choice question, add the points of the selected choice
                total_points += answer.choice.points

        return total_points


    def assign_answers(self, answers):
        for answer_data in answers:
            question_id = answer_data['question_id']
            answer_text = answer_data.get('answer_text')
            choice_id = answer_data.get('choice_id')

            # Assuming you have a method to get a Question by ID
            question = CQuestions.get_by_id(question_id)

            if question.questionType == 'single choice':
                # For single-choice questions, associate the choice with the answer
                choice = CQuestionChoices.get_by_id(choice_id)
                new_answer = CAnswers(
                    caseID=self.caseID,
                    questionID=question_id,
                    choiceID=choice_id,
                    answerText=None  # Set answerText to None for single-choice questions
                )
            else:
                # For text-based questions, associate the answer text with the answer
                new_answer = CAnswers(
                    caseID=self.caseID,
                    questionID=question_id,
                    answerText=answer_text,
                    choiceID=None  # Set choiceID to None for text-based questions
                )

            # Save the answer to the database
            new_answer.save()

    @classmethod
    def get_by_id(cls, caseID):
        return cls.query.get_or_404(caseID)
    
    def edit_answers(self, edited_answers):
        for edited_answer_data in edited_answers:
            answer_id = edited_answer_data['answer_id']
            new_answer_text = edited_answer_data.get('new_answer_text')
            new_choice_id = edited_answer_data.get('new_choice_id')

            # Get the existing answer by ID
            existing_answer = CAnswers.query.get_or_404(answer_id)

            # Check if the answer belongs to the current project
            if existing_answer.caseID != self.caseID:
                response = jsonify({'message': 'Answer not found for the specified project'})
                response.status_code = HTTPStatus.NOT_FOUND
                return response

            if existing_answer.choice is not None:
                # If the existing answer is for a single-choice question, update the choice
                existing_answer.choiceID = new_choice_id
            else:
                # If the existing answer is for a text-based question, update the answer text
                existing_answer.answerText = new_answer_text

        # Commit the changes to the database
        db.session.commit()

        return jsonify({'message': 'Answers updated successfully'})
    

class CaseUser(db.Model):
    __tablename__ = 'case_users'

    id = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)

    def __repr__(self):
        return f"<CaseUser {self.id} CaseID: {self.caseID}, UserID: {self.userID}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()


class CQuestions(db.Model):
    __tablename__ = 'cquestions'

    questionID = db.Column(db.Integer, primary_key=True)
    # projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    questionText = db.Column(db.String, nullable=False)
    questionType = db.Column(db.String, nullable=False)  # Text input, multiple choice, etc.
    points = db.Column(db.Integer, nullable=False)

    # If the question is multiple choice, store choices in a separate table
    choices = db.relationship('CQuestionChoices', backref='cquestions', lazy=True, uselist=True)

    def __repr__(self):
        return f"<Question {self.questionID} {self.questionText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, questionID):
        return cls.query.get_or_404(questionID)
    
    def assign_choices(self, choices_with_points):
        # Assuming choices_with_points is a list of tuples, each containing (choice_text, points)
        for choice_text, points in choices_with_points:
            new_choice = CQuestionChoices(questionID=self.questionID, choiceText=choice_text, points=points)
            new_choice.save()
    

class CAnswers(db.Model):
    __tablename__ = 'canswers'

    answerID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('cquestions.questionID'), nullable=False)
    answerText = db.Column(db.String, nullable=True)  # Adjust based on the answer format

     # Add a foreign key reference to the choices table
    question = db.relationship('CQuestions', backref='canswers', lazy=True)
    choiceID = db.Column(db.Integer, db.ForeignKey('cquestion_choices.choiceID'), nullable=True)

    # Define a relationship with the choices table
    choice = db.relationship('CQuestionChoices', foreign_keys=[choiceID], backref='answer', lazy=True)

    def __repr__(self):
        return f"<Answer {self.answerID} {self.answerText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, answerID):
        return cls.query.get_or_404(answerID)

class CQuestionChoices(db.Model):
    __tablename__ = 'cquestion_choices'

    choiceID = db.Column(db.Integer, primary_key=True)
    questionID = db.Column(db.Integer, db.ForeignKey('cquestions.questionID'), nullable=False)
    choiceText = db.Column(db.String, nullable=False)
    points = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Choice {self.choiceID} {self.choiceText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, choiceID):
        return cls.query.get_or_404(choiceID)

