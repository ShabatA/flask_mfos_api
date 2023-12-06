from ..utils.db import db
from .regions import Regions
from .users import Users
from enum import Enum
from flask import jsonify
from http import HTTPStatus

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
    
    def delete(self):
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
        answers = Answers.query.filter_by(projectID=self.projectID).all()

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
            question = Questions.get_by_id(question_id)

            if question.questionType == 'single choice':
                # For single-choice questions, associate the choice with the answer
                choice = QuestionChoices.get_by_id(choice_id)
                new_answer = Answers(
                    projectID=self.projectID,
                    questionID=question_id,
                    choiceID=choice_id,
                    answerText=None  # Set answerText to None for single-choice questions
                )
            else:
                # For text-based questions, associate the answer text with the answer
                new_answer = Answers(
                    projectID=self.projectID,
                    questionID=question_id,
                    answerText=answer_text,
                    choiceID=None  # Set choiceID to None for text-based questions
                )

            # Save the answer to the database
            new_answer.save()

    @classmethod
    def get_by_id(cls, projectID):
        return cls.query.get_or_404(projectID)
    
    def edit_answers(self, edited_answers):
        for edited_answer_data in edited_answers:
            answer_id = edited_answer_data['answer_id']
            new_answer_text = edited_answer_data.get('new_answer_text')
            new_choice_id = edited_answer_data.get('new_choice_id')

            # Get the existing answer by ID
            existing_answer = Answers.query.get_or_404(answer_id)

            # Check if the answer belongs to the current project
            if existing_answer.projectID != self.projectID:
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
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, questionID):
        return cls.query.get_or_404(questionID)
    
    def assign_choices(self, choices_with_points):
        # Assuming choices_with_points is a list of tuples, each containing (choice_text, points)
        for choice_text, points in choices_with_points:
            new_choice = QuestionChoices(questionID=self.questionID, choiceText=choice_text, points=points)
            new_choice.save()
    

class Answers(db.Model):
    __tablename__ = 'answers'

    answerID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID'), nullable=False)
    answerText = db.Column(db.String, nullable=True)  # Adjust based on the answer format

     # Add a foreign key reference to the choices table
    question = db.relationship('Questions', backref='answers', lazy=True)
    choiceID = db.Column(db.Integer, db.ForeignKey('question_choices.choiceID'), nullable=True)

    # Define a relationship with the choices table
    choice = db.relationship('QuestionChoices', foreign_keys=[choiceID], backref='answer', lazy=True)

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
    points = db.Column(db.Integer, nullable=False)

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

