
from ..utils.db import db
from enum import Enum
from datetime import datetime
from flask import jsonify
from http import HTTPStatus
from sqlalchemy.dialects.postgresql import JSONB

class CaseStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    INPROGRESS = "in progress"
    REJECTED = "rejected"
    COMPLETED = "completed"
    ASSESSMENT = "pending assessment"

class CaseCategory(Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'

class CaseTaskStatus(Enum):
    TODO = 'To Do'
    INPROGRESS = 'In Progress'
    DONE = 'Done'
    OVERDUE = 'Overdue'

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
    budgetRequired = db.Column(db.Float, nullable=False)
    budgetAvailable = db.Column(db.Float, nullable=False)
    caseStatus = db.Column(db.Enum(CaseStatus))
    category = db.Column(db.Enum(CaseCategory), nullable=True)
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
    tasks = db.relationship('CaseTask', backref='cases', lazy=True)
    status_data = db.relationship('CaseStatusData', backref='cases', uselist=False, lazy=True)

    

    def __repr__(self):
        return f"<Case {self.caseID} {self.caseName}>"

    def delete(self):
        """
        Delete the case from the database.
        """
        db.session.delete(self)
        db.session.commit()

    def save(self, answers=None, status_data=None):
        db.session.add(self)
        db.session.commit()

        # If answers are provided, create and assign them to the case
        if answers:
            self.assign_answers(answers)

        # If status_data is provided, create and assign it to the case
        if status_data:
            self.assign_status_data(status_data)

        # If answers are provided, create and assign them to the case
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
    
    def assign_status_data(self, status_data):
            
        new_status_data = CaseStatusData(caseID=self.caseID, status=self.caseStatus.value, data=status_data)
        self.startDate = status_data.get('startDate', self.startDate)
        self.dueDate = status_data.get('dueDate', self.dueDate)
        db.sesion.commit()
        new_status_data.save()


    def assign_answers(self, answers):
        for answer_data in answers:
            questionID = answer_data['questionID']
            answerText = answer_data.get('answerText')
            extras = answer_data.get('extras')  # Retrieve the 'extras' key if it exists

            # Assuming you have a method to get a Question by ID
            question = CQuestions.get_by_id(questionID)

            if question.questionType == 'single choice':
                choiceID = answer_data.get('choiceID')
                # For single-choice questions, associate the choice with the answer
                new_answer = CAnswers(
                    caseID=self.caseID,
                    questionID=questionID,
                    choiceID=choiceID,
                    answerText=None, # Set answerText to None for multiple-choice questions
                    extras=extras
                )
                new_answer.save()
            elif question.questionType == 'multi choice':
                choiceIDs = answer_data.get('choiceID', [])
                # For multiple-choice questions, associate the choices with the answer
                for choiceID in choiceIDs:
                    choice = CQuestionChoices.get_by_id(choiceID)
                    new_answer = CAnswers(
                        caseID=self.caseID,
                        questionID=questionID,
                        choiceID=choiceID,
                        answerText=None, # Set answerText to None for multiple-choice questions
                        extras=extras
                    )
                    new_answer.save()
            else:
                # For text-based questions, associate the answer text with the answer
                new_answer = CAnswers(
                    caseID=self.caseID,
                    questionID=questionID,
                    answerText=answerText,
                    choiceID=None,  # Set choiceID to None for text-based questions
                    extras=extras
                )
                new_answer.save()

    @classmethod
    def get_by_id(cls, caseID):
        return cls.query.get_or_404(caseID)
    
    def edit_answers(self, caseID,edited_answers):
        for edited_answer_data in edited_answers:
            questionID = edited_answer_data['questionID']
            new_answer_text = edited_answer_data.get('answerText')
            new_choice_id = edited_answer_data.get('choiceID')

            # Assuming you have a method to get a Question by ID
            question = CQuestions.get_by_id(questionID)

            if not question:
                response = jsonify({'message': 'Question not found'})
                response.status_code = HTTPStatus.NOT_FOUND
                return response

            # Delete existing answers for the given question ID
            CAnswers.query.filter_by(questionID=questionID,caseID=caseID).delete()

            if question.questionType == 'multi choice' and isinstance(new_choice_id, list):
                # For multiple-choice questions, add new rows for each choice
                for choice_id in new_choice_id:
                    new_answer = CAnswers(
                        caseID=self.caseID,
                        questionID=questionID,
                        choiceID=choice_id,
                        answerText=None
                    )
                    db.session.add(new_answer)
            else:
                # For single-choice or text-based questions, update the existing row
                new_answer = CAnswers(
                    caseID=self.caseID,
                    questionID=questionID,
                    choiceID=new_choice_id if question.questionType == 'single choice' else None,
                    answerText=new_answer_text if question.questionType == 'text' else None
                )
                db.session.add(new_answer)

        # Commit the changes to the database
        db.session.commit()

        return jsonify({'message': 'Answers updated successfully'})

class CaseStage(db.Model):
    _tablename_ = 'case_stages'

    stageID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    # status = db.Column(db.String, nullable=False)  # You can use this field to indicate if the stage is 'started', 'completed', etc.

    def _repr_(self):
        return f"<CaseStage {self.stageID} {self.name}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseToStage(db.Model):
    _tablename_ = 'case_to_stage'

    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), primary_key=True)
    stageID = db.Column(db.Integer, db.ForeignKey('case_stage.stageID'), primary_key=True)
    started = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    completionDate = db.Column(db.Date, nullable=True)

    case = db.relationship('Cases', backref='case_to_stage', lazy=True)
    stage = db.relationship('CaseStage', backref='case_to_stage', lazy=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    

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
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CQuestions(db.Model):
    __tablename__ = 'cquestions'

    questionID = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer)  # New "order" column
    questionText = db.Column(db.String, nullable=False)
    questionType = db.Column(db.String, nullable=False)  # Text input, multiple choice, etc.
    points = db.Column(db.Integer, nullable=False)

    # If the question is multiple choice, store choices in a separate table
    choices = db.relationship('CQuestionChoices', backref='cquestions', lazy=True, uselist=True)

    def __repr__(self):
        return f"<Question {self.questionID} {self.questionText}>"
    
    def save(self):
        # Set the order when saving a new question
        if not self.order:
            self.order = CQuestions.query.count() + 1
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
    
    def add_choice(self, choice_text, points):
        new_choice = CQuestionChoices(questionID=self.questionID, choiceText=choice_text, points=points)
        new_choice.save()
    

class CAnswers(db.Model):
    __tablename__ = 'canswers'

    answerID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('cquestions.questionID'), nullable=False)
    answerText = db.Column(db.String, nullable=True)  # Adjust based on the answer format
    extras = db.Column(JSONB, nullable=True)

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
    
    def delete(self):
        db.session.delete(self)
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
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, choiceID):
        return cls.query.get_or_404(choiceID)

class CaseTask(db.Model):
    _tablename_ = 'case_tasks'

    taskID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    title = db.Column(db.String, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    assignedTo = db.relationship('Users', secondary='c_task_assigned_to', backref='c_assigned_tasks', lazy='dynamic')
    cc = db.relationship('Users', secondary='c_task_cc', backref='c_cc_tasks', lazy='dynamic')
    description = db.Column(db.String, nullable=True)
    createdBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    attachedFiles = db.Column(db.String, nullable=True)
    stageID = db.Column(db.Integer, db.ForeignKey('case_stage.stageID'), nullable=False)
    status = db.Column(db.Enum(CaseTaskStatus), nullable=False)
    completionDate = db.Column(db.Date, nullable=True)

    stage = db.relationship('CaseStage', backref='tasks', lazy=True)

    def is_overdue(self):
        return self.deadline < datetime.today().date() if not self.status.DONE else False

    def _repr_(self):
        return f"<CaseTask {self.taskID} {self.title}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        # Delete related TaskComments
        CaseTaskComments.query.filter_by(taskID=self.taskID).delete()

        self.assignedTo = []
        self.cc = []
        
        db.session.delete(self)
        db.session.commit()
        
        
    
    @classmethod
    def get_by_id(cls, taskID):
        return cls.query.get_or_404(taskID)

class CaseTaskComments(db.Model):
    _tablename_ = 'ctask_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    taskID = db.Column(db.Integer, db.ForeignKey('case_task.taskID'), nullable=False)
    comment = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    def __repr__(self) -> str:
        return f"<TaskComments {self.id} userID: {self.userID} taskID: {self.taskID} comment: {self.comment}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class CaseTaskAssignedTo(db.Model):
    __tablename__ = 'c_task_assigned_to'
    task_id = db.Column(db.Integer, db.ForeignKey('case_task.taskID'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.userID'), primary_key=True)


class CaseTaskCC(db.Model):
    __tablename__ = 'c_task_cc'
    task_id = db.Column(db.Integer, db.ForeignKey('case_task.taskID'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.userID'), primary_key=True)

class CaseStatusData(db.Model):
    _tablename_ = 'case_status_data'

    id = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    status = db.Column(db.String, nullable=False)
    data = db.Column(JSONB, nullable=True)  # You can adjust the type based on the data you want to store

    project = db.relationship('Cases', backref='case_status_data', lazy=True)

    def _repr_(self):
        return f"<CaseStatusData {self.id} caseID: {self.caseID}, Status: {self.status}>"

    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def get_status_data_by_case_id(case_id):
        try:
            # Retrieve the case status data based on the case ID
            status_data = CaseStatusData.query.filter_by(caseID=case_id).first()

            if status_data:
                return status_data.data
            else:
                return None  # or an appropriate value indicating no data found

        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            print(f'Error retrieving case status data: {str(e)}')
            return None  # or raise an exception, depending on your error handling strategy

class CaseAssessmentQuestions(db.Model):
    __tablename__ = 'case_assessment_questions'
    questionID = db.Column(db.Integer, primary_key=True)
    questionText = db.Column(db.String, nullable=True)
    
    def __repr__(self):
        return f"<CaseAssessmentQuestions {self.questionID} {self.questionText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        CaseAssessmentAnswers.query.filter_by(questionID=self.questionID).delete()
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, questionID):
        return cls.query.get_or_404(questionID)

class CaseAssessmentAnswers(db.Model):
    __tablename__ = 'case_assessment_answers'

    answerID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases.caseID'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('case_assessment_questions.questionID'), nullable=False)
    answerText = db.Column(db.String, nullable=True)
    extras = db.Column(JSONB, nullable=True)
    
    # Add a foreign key reference to the choices table
    question = db.relationship('CaseAssessmentQuestions', backref='case_assessment_answers', lazy=True)
   

    def _repr_(self):
        return f"<CaseAssessmentAnswer {self.answerID} {self.answerText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, answerID):
        return cls.query.get_or_404(answerID)

