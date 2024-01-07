from ..utils.db import db
from .regions import Regions
from .users import Users
from enum import Enum
from flask import jsonify
from http import HTTPStatus
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB


class ProjectStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    def to_dict(self):
        return {'status': self.value}

class TaskStatus(Enum):
    TODO = 'To Do'
    INPROGRESS = 'In Progress'
    DONE = 'Done'
    OVERDUE = 'Overdue'

class ProjectCategory(Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'

class Projects(db.Model):
    _tablename_ = 'projects'

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
    users = db.relationship('Users', secondary='project_user', backref='projects', lazy='dynamic')
    answers = db.relationship('Answers', backref='projects', lazy=True)
    tasks = db.relationship('ProjectTask', backref='projects', lazy=True)
    status_data = db.relationship('ProjectStatusData', backref='projects', uselist=False, lazy=True)

    def _repr_(self):
        return f"<Project {self.projectID} {self.projectName}>"
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def save(self, answers=None, status_data=None):
        db.session.add(self)
        db.session.commit()

        # If answers are provided, create and assign them to the project
        if answers:
            self.assign_answers(answers)

        # If status_data is provided, create and assign it to the project
        if status_data:
            self.assign_status_data(status_data)
    
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
    
    def assign_status_data(self, status_data):
        new_status_data = ProjectStatusData(projectID=self.projectID, status=self.projectStatus.value, data=status_data)
        new_status_data.save()


    def assign_answers(self, answers):
        for answer_data in answers:
            questionID = answer_data['questionID']
            answerText = answer_data.get('answerText')
            

            # Assuming you have a method to get a Question by ID
            question = Questions.get_by_id(questionID)

            if question.questionType == 'single choice':
                choiceID = answer_data.get('choiceID')
                # For single-choice questions, associate the choice with the answer
                new_answer = Answers(
                    projectID=self.projectID,
                    questionID=questionID,
                    choiceID=choiceID,
                    answerText=None  # Set answerText to None for multiple-choice questions
                )
                new_answer.save()
            elif question.questionType == 'multi choice':
                choiceIDs = answer_data.get('choiceID', [])
                # For multiple-choice questions, associate the choices with the answer
                for choiceID in choiceIDs:
                    choice = QuestionChoices.get_by_id(choiceID)
                    new_answer = Answers(
                        projectID=self.projectID,
                        questionID=questionID,
                        choiceID=choiceID,
                        answerText=None  # Set answerText to None for multiple-choice questions
                    )
                    new_answer.save()
            else:
                # For text-based questions, associate the answer text with the answer
                new_answer = Answers(
                    projectID=self.projectID,
                    questionID=questionID,
                    answerText=answerText,
                    choiceID=None  # Set choiceID to None for text-based questions
                )
                new_answer.save()

            # Save the answer to the database
            # new_answer.save()

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
            if not existing_answer:
                response = jsonify({'message': 'Answer not found'})
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
    _tablename_ = 'questions'

    questionID = db.Column(db.Integer, primary_key=True)
    # projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    questionText = db.Column(db.String, nullable=False)
    questionType = db.Column(db.String, nullable=False)  # Text input, multiple choice, etc.
    points = db.Column(db.Integer, nullable=False)

    # If the question is multiple choice, store choices in a separate table
    choices = db.relationship('QuestionChoices', backref='question', lazy=True, uselist=True)

    def _repr_(self):
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
    
    def add_choice(self, choice_text, points):
        new_choice = QuestionChoices(questionID=self.questionID, choiceText=choice_text, points=points)
        new_choice.save()
    

class Answers(db.Model):
    _tablename_ = 'answers'

    answerID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID'), nullable=False)
    answerText = db.Column(db.String, nullable=True)  # Adjust based on the answer format

     # Add a foreign key reference to the choices table
    question = db.relationship('Questions', backref='answers', lazy=True)
    choiceID = db.Column(db.Integer, db.ForeignKey('question_choices.choiceID'), nullable=True)

    # Define a relationship with the choices table
    choice = db.relationship('QuestionChoices', foreign_keys=[choiceID], backref='answer', lazy=True)

    def _repr_(self):
        return f"<Answer {self.answerID} {self.answerText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, answerID):
        return cls.query.get_or_404(answerID)

class QuestionChoices(db.Model):
    _tablename_ = 'question_choices'

    choiceID = db.Column(db.Integer, primary_key=True)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID'), nullable=False)
    choiceText = db.Column(db.String, nullable=False)
    points = db.Column(db.Integer, nullable=False)

    def _repr_(self):
        return f"<Choice {self.choiceID} {self.choiceText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, choiceID):
        return cls.query.get_or_404(choiceID)
    
    

class ProjectUser(db.Model):
    _tablename_ = 'project_user'

    id = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)

    def _repr_(self):
        return f"<ProjectUser {self.id} ProjectID: {self.projectID}, UserID: {self.userID}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    


class Stage(db.Model):
    _tablename_ = 'stages'

    stageID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    # status = db.Column(db.String, nullable=False)  # You can use this field to indicate if the stage is 'started', 'completed', etc.

    def _repr_(self):
        return f"<Stage {self.stageID} {self.name}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class ProjectStage(db.Model):
    _tablename_ = 'project_stages'

    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), primary_key=True)
    stageID = db.Column(db.Integer, db.ForeignKey('stage.stageID'), primary_key=True)
    started = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    completionDate = db.Column(db.Date, nullable=True)

    project = db.relationship('Projects', backref='project_stages', lazy=True)
    stage = db.relationship('Stage', backref='project_stages', lazy=True)


class ProjectTask(db.Model):
    _tablename_ = 'project_tasks'

    taskID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    title = db.Column(db.String, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    assignedTo = db.relationship('Users', secondary='task_assigned_to', backref='assigned_tasks', lazy='dynamic')
    cc = db.relationship('Users', secondary='task_cc', backref='cc_tasks', lazy='dynamic')
    description = db.Column(db.String, nullable=True)
    createdBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    attachedFiles = db.Column(db.String, nullable=True)
    stageID = db.Column(db.Integer, db.ForeignKey('stage.stageID'), nullable=False)
    status = db.Column(db.Enum(TaskStatus), nullable=False)
    completionDate = db.Column(db.Date, nullable=True)

    stage = db.relationship('Stage', backref='tasks', lazy=True)

    def is_overdue(self):
        return self.deadline < datetime.today().date() if not self.status.DONE else False

    def _repr_(self):
        return f"<ProjectTask {self.taskID} {self.title}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, taskID):
        return cls.query.get_or_404(taskID)

class TaskComments(db.Model):
    _tablename_ = 'task_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    taskID = db.Column(db.Integer, db.ForeignKey('project_task.taskID'), nullable=False)
    comment = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    def __repr__(self) -> str:
        return f"<TaskComments {self.id} userID: {self.userID} taskID: {self.taskID} comment: {self.comment}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        

# Association tables for many-to-many relationships
task_assigned_to = db.Table('task_assigned_to',
                           db.Column('task_id', db.Integer, db.ForeignKey('project_task.taskID')),
                           db.Column('user_id', db.Integer, db.ForeignKey('users.userID'))
                           )

task_cc = db.Table('task_cc',
                   db.Column('task_id', db.Integer, db.ForeignKey('project_task.taskID')),
                   db.Column('user_id', db.Integer, db.ForeignKey('users.userID'))
                   )

class ProjectStatusData(db.Model):
    _tablename_ = 'project_status_data'

    id = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects.projectID'), nullable=False)
    status = db.Column(db.String, nullable=False)
    data = db.Column(JSONB, nullable=True)  # You can adjust the type based on the data you want to store

    project = db.relationship('Projects', backref='project_status_data', lazy=True)

    def _repr_(self):
        return f"<ProjectStatusData {self.id} ProjectID: {self.projectID}, Status: {self.status}>"

    def save(self):
        db.session.add(self)
        db.session.commit()
    
    @staticmethod
    def get_status_data_by_project_id(project_id):
        try:
            # Retrieve the project status data based on the project ID
            status_data = ProjectStatusData.query.filter_by(projectID=project_id).first()

            if status_data:
                return status_data.data
            else:
                return None  # or an appropriate value indicating no data found

        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            print(f'Error retrieving project status data: {str(e)}')
            return None  # or raise an exception, depending on your error handling strategy