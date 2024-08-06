from api.models.regions import Regions
from ..utils.db import db
from enum import Enum
from flask import jsonify
from http import HTTPStatus
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import func


class ProjectStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ASSESSMENT = 'pending assessment'

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

class Category(Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'

class Status(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ASSESSMENT = 'pending assessment'

    def to_dict(self):
        return {'status': self.value}

class ProType(Enum):
    PROJECT = 'PROJECT'
    PROGRAM = 'PROGRAM'

class ProjectsData(db.Model):
    __tablename__ = 'projects_data'

    projectID = db.Column(db.Integer, primary_key=True)
    createdBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'), nullable=False)
    projectName = db.Column(db.String, nullable=False)
    budgetRequired = db.Column(db.Float, nullable=False)
    budgetApproved = db.Column(db.Float, nullable=True)
    projectStatus = db.Column(db.Enum(Status), nullable=False)
    projectScope = db.Column(db.Integer, nullable=False)
    projectIdea = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    addedValue = db.Column(db.Text, nullable=False)
    projectNature = db.Column(db.Integer, nullable=False)
    beneficiaryCategory = db.Column(db.Integer, nullable=False)
    commitment = db.Column(db.Integer, nullable=False)
    commitmentType = db.Column(db.Integer, nullable=True)
    supportingOrg = db.Column(db.Text, nullable=True)
    documents = db.Column(ARRAY(db.String))
    recommendationLetter = db.Column(db.Integer, nullable=True)  
    category = db.Column(db.Enum(Category), nullable=True)
    startDate = db.Column(db.Date, nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dueDate = db.Column(db.Date, nullable=True)
    totalPoints = db.Column(db.Integer, default=0, nullable=True)
    project_type = db.Column(db.Enum(ProType), default= ProType.PROJECT)
    active = db.Column(db.Boolean, default=True)


    users = db.relationship('Users', secondary='project_user', backref='projects_data', lazy='dynamic')
    tasks = db.relationship('ProjectTask', backref='projects_data', lazy=True)
    status_data = db.relationship('ProjectStatusData', backref='projects_data', uselist=False, lazy=True, overlaps="projects_data,status_data")
    
    def _repr_(self):
        return f"<ProjectsData {self.projectID} {self.projectName} {self.createdAt}>"
    
    def save(self):
        
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    def serialize(self):
        return {
            'projectID': self.projectID,
            'projectName': self.projectName,
            'projectStatus': self.projectStatus.value,
            'createdAt': self.createdAt.isoformat(),
            'category': self.category.value,
            'startDate': self.startDate.isoformat() if self.startDate else None,
            'dueDate': self.dueDate.isoformat() if self.dueDate else None,
            'regionName': Regions.query.get(self.regionID).regionName,
            'project_type': self.project_type.value,
            'active': self.active
        }
    
    @classmethod
    def get_by_id(cls, projectID):
        return cls.query.get_or_404(projectID)
    
    def assign_status_data(self, status_data):
        # Delete Project Status Data
        ProjectStatusData.query.filter_by(projectID=self.projectID).delete()

        new_status_data = ProjectStatusData(projectID=self.projectID, status=self.projectStatus.value, data=status_data)
        
        if len(status_data) > 2:
            # Set the startDate to the current date
            self.startDate = datetime.utcnow().date()

            # Assuming status_data.get('dueDate', self.dueDate) returns a string
            due_date_string = status_data.get('dueDate') or str(self.dueDate)

            # Handle the project when due_date_string is an empty string
            if due_date_string:
                # Convert the string to a date object
                self.dueDate = datetime.strptime(due_date_string, '%Y-%m-%d %H:%M:%S.%f').date()
            else:
                self.dueDate = None  # or set it to an appropriate default value

            # Set the budgetApproved attribute
            self.budgetApproved = status_data.get('approvedFunding')

            # Commit changes to the database
            db.session.commit()

        # Save the new status data
        new_status_data.save()

class ActStatus(Enum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

    def to_dict(self):
        return {'status': self.value}

class Activities(db.Model):
    __tablename__ = 'activities'
    
    activityID = db.Column(db.Integer, primary_key=True)
    activityName = db.Column(db.String, nullable=False)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'), nullable=False)
    programID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID', ondelete='CASCADE'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    costRequired = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String, nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    activityStatus = db.Column(db.Enum(ActStatus), default=ActStatus.PENDING, nullable=False)
    assignedTo = db.relationship('Users', secondary='activity_users', backref='assigned_activities', lazy='dynamic', single_parent=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    createdBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    statusData = db.Column(JSONB, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit() 
    

class ActivityUsers(db.Model):
    __tablename__ = 'activity_users'
    id = db.Column(db.Integer, primary_key=True)
    activityID = db.Column(db.Integer, db.ForeignKey('activities.activityID', ondelete='CASCADE'), nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    
    def __repr__(self):
        return f"<ActivityUser {self.id} userID: {self.userID} activityID: {self.taskID}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()  
    
    



class Questions(db.Model):
    _tablename_ = 'questions'

    questionID = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer)  # New "order" column
    questionText = db.Column(db.String, nullable=False)
    questionType = db.Column(db.String, nullable=False)  # Text input, multiple choice, etc.
    points = db.Column(db.Integer, nullable=False)

    # If the question is multiple choice, store choices in a separate table
    choices = db.relationship('QuestionChoices', backref='question', lazy=True, uselist=True)

    def _repr_(self):
        return f"<Question {self.questionID} {self.questionText}>"
    
    def save(self):
        # Set the order when saving a new question
        if not self.order:
            self.order = Questions.query.count() + 1
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
    


class QuestionChoices(db.Model):
    _tablename_ = 'question_choices'

    choiceID = db.Column(db.Integer, primary_key=True)
    questionID = db.Column(db.Integer, db.ForeignKey('questions.questionID', ondelete='CASCADE'), nullable=False)
    choiceText = db.Column(db.String, nullable=False)
    points = db.Column(db.Integer, nullable=False)

    def _repr_(self):
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
    
    

class ProjectUser(db.Model):
    __tablename__ = 'project_user'

    id = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID', ondelete='CASCADE'), nullable=False)
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

    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID', ondelete='CASCADE'), primary_key=True)
    stageID = db.Column(db.Integer, db.ForeignKey('stage.stageID'), primary_key=True)
    started = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    completionDate = db.Column(db.Date, nullable=True)

    project = db.relationship('ProjectsData', backref='project_stages', lazy=True)
    stage = db.relationship('Stage', backref='project_stages', lazy=True)
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class ProjectTask(db.Model):
    __tablename__ = 'project_task'

    taskID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    assignedTo = db.relationship('Users', secondary='project_task_assigned_to', backref='assigned_tasks', lazy='dynamic', single_parent=True)
    cc = db.relationship('Users', secondary='project_task_cc', backref='cc_tasks', lazy='dynamic', single_parent=True)
    description = db.Column(db.String, nullable=True)
    createdBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    attachedFiles = db.Column(db.String, nullable=True)
    stageID = db.Column(db.Integer, db.ForeignKey('stage.stageID', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum(TaskStatus), nullable=False)
    completionDate = db.Column(db.Date, nullable=True)
    checklist = db.Column(JSONB, nullable=True)
    creationDate = db.Column(db.DateTime, default=func.now(), nullable=False)
    startDate = db.Column(db.Date, default=datetime.now().date())

    stage = db.relationship('Stage', backref='tasks', lazy=True)

    def is_overdue(self):
        return self.deadline < datetime.today().date() if not self.status == TaskStatus.DONE else False

    def __repr__(self):
        return f"<ProjectTask {self.taskID} {self.title}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        # Delete related TaskComments
        TaskComments.query.filter_by(taskID=self.taskID).delete()

        self.assignedTo = []
        self.cc = []
        
        # Delete related entries in ProjectTaskAssignedTo and ProjectTaskCC
        ProjectTaskAssignedTo.query.filter_by(task_id=self.taskID).delete()
        ProjectTaskCC.query.filter_by(task_id=self.taskID).delete()
        db.session.commit()
        
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, taskID):
        return cls.query.get_or_404(taskID)

class TaskComments(db.Model):
    __tablename__ = 'task_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    taskID = db.Column(db.Integer, db.ForeignKey('project_task.taskID', ondelete='CASCADE'), nullable=False)
    comment = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    def __repr__(self):
        return f"<TaskComments {self.id} userID: {self.userID} taskID: {self.taskID} comment: {self.comment}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, commentID):
        return cls.query.get_or_404(commentID)

class ProjectTaskAssignedTo(db.Model):
    __tablename__ = 'project_task_assigned_to'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('project_task.taskID', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    
    def __repr__(self):
        return f"<ProjectAssignedTo {self.id} userID: {self.user_id} taskID: {self.task_id}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class ProjectTaskCC(db.Model):
    __tablename__ = 'project_task_cc'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('project_task.taskID', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    
    def __repr__(self):
        return f"<ProjectTaskCC {self.id} userID: {self.user_id} taskID: {self.task_id}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        

class AssessmentQuestions(db.Model):
    __tablename__ = 'assessment_questions'
    questionID = db.Column(db.Integer, primary_key=True)
    questionText = db.Column(db.String, nullable=True)
    
    def __repr__(self):
        return f"<AssessmentQuestions {self.questionID} {self.questionText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        AssessmentAnswers.query.filter_by(questionID=self.questionID).delete()
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, questionID):
        return cls.query.get_or_404(questionID)

class AssessmentAnswers(db.Model):
    __tablename__ = 'assessment_answers'

    answerID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID', ondelete='CASCADE'), nullable=False)
    questionID = db.Column(db.Integer, db.ForeignKey('assessment_questions.questionID', ondelete='CASCADE'), nullable=False)
    answerText = db.Column(db.String, nullable=True)  # Adjust based on the answer format
    notes = db.Column(db.String, nullable=True)

     # Add a foreign key reference to the choices table
    question = db.relationship('AssessmentQuestions', backref='assessment_answers', lazy=True)
   

    def _repr_(self):
        return f"<AssessmentAnswer {self.answerID} {self.answerText}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, answerID):
        return cls.query.get_or_404(answerID)
    
class RequirementSection(Enum):
    FINANCIAL = 'Financial'
    IMPLEMENTATION = 'Implementation'
    MEDIA = 'Media'

class Requirements(db.Model):
    __tablename__ = 'requirements'
    
    requirementID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    section = db.Column(db.Enum(RequirementSection), nullable=False)
    
    def __repr__(self):
        return f"<Requirement {self.projectID} {self.name} {self.description} {self.section.value}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, projectID):
        return cls.query.get_or_404(projectID)
    

class ProjectStatusData(db.Model):
    _tablename_ = 'project_status_data'

    id = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String, nullable=False)
    data = db.Column(JSONB, nullable=True)  # You can adjust the type based on the data you want to store

    project = db.relationship('ProjectsData', backref='project_status_data', lazy=True, overlaps='projects_data')

    def _repr_(self):
        return f"<ProjectStatusData {self.id} ProjectID: {self.projectID}, Status: {self.status}>"

    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
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