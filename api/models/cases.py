from api.models.regions import Regions
from api.models.users import Users
from ..utils.db import db
from enum import Enum
from datetime import datetime
from flask import jsonify
from http import HTTPStatus
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func


class CaseStat(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    INPROGRESS = "in progress"
    REJECTED = "rejected"
    COMPLETED = "completed"
    ASSESSMENT = "pending assessment"


class CaseCat(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class CaseTaskStatus(Enum):
    TODO = "To Do"
    INPROGRESS = "In Progress"
    DONE = "Done"
    OVERDUE = "Overdue"


class CasesData(db.Model):

    __tablename__ = "cases_data"

    caseID = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    regionID = db.Column(db.Integer, db.ForeignKey("regions.regionID"))
    caseName = db.Column(db.String, nullable=False)
    sponsorAvailable = db.Column(db.String, nullable=True)
    budgetApproved = db.Column(db.Float, nullable=True)
    question1 = db.Column(JSONB, nullable=False)
    question2 = db.Column(JSONB, nullable=False)
    question3 = db.Column(JSONB, nullable=False)
    question4 = db.Column(JSONB, nullable=False)
    question5 = db.Column(JSONB, nullable=False)
    question6 = db.Column(JSONB, nullable=False)
    question7 = db.Column(JSONB, nullable=False)
    question8 = db.Column(JSONB, nullable=False)
    question9 = db.Column(JSONB, nullable=False)
    question10 = db.Column(JSONB, nullable=False)
    question11 = db.Column(db.Float, nullable=False)
    question12 = db.Column(db.Integer, nullable=False)
    caseStatus = db.Column(db.Enum(CaseStat), nullable=False)
    category = db.Column(db.Enum(CaseCat), nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    startDate = db.Column(db.Date, nullable=True)
    dueDate = db.Column(db.Date, nullable=True)
    total_points = db.Column(db.Integer, nullable=True)
    approvedPayments = db.Column(db.Float, nullable=True, default=0)

    region = db.relationship("Regions", backref="cases_data", foreign_keys=[regionID])
    users = db.relationship(
        "Users", secondary="case_users", backref="cases_data", lazy="dynamic"
    )
    beneficaries = db.relationship("CaseBeneficiary", backref="cases_data", uselist=False,lazy=True)
    tasks = db.relationship("CaseTask", backref="cases_data", lazy=True)
    status_data = db.relationship(
        "CaseStatusData", backref="cases_data", uselist=False, lazy=True
    )
    
    beneficiary_form = db.relationship(
        "BeneficiaryForm", backref="case", uselist=False, lazy=True
    )

    def __repr__(self):
        return f"<Case {self.caseID} {self.caseName}>"

    def delete(self):
        """
        Delete the case from the database.
        """
        db.session.delete(self)
        db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def assign_status_data(self, status_data):
        # Delete Case Status Data
        CaseStatusData.query.filter_by(caseID=self.caseID).delete()

        new_status_data = CaseStatusData(
            caseID=self.caseID, status=self.caseStatus.value, data=status_data
        )

        if len(status_data) > 2:
            # Set the startDate to the current date
            self.startDate = datetime.utcnow().date()

            # Assuming status_data.get('dueDate', self.dueDate) returns a string
            due_date_string = status_data.get("dueDate") or str(self.dueDate)

            # Handle the case when due_date_string is an empty string
            if due_date_string:
                # Convert the string to a date object
                self.dueDate = datetime.strptime(
                    due_date_string, "%Y-%m-%d %H:%M:%S.%f"
                ).date()
            else:
                self.dueDate = None  # or set it to an appropriate default value

            # Set the budgetApproved attribute
            self.budgetApproved = status_data.get("approvedFunding")

        # Commit changes to the database
        db.session.commit()

        # Save the new status data
        new_status_data.save()

    @classmethod
    def get_by_id(cls, caseID):
        return cls.query.get_or_404(caseID)

    def delete_associated_data(self):

        CaseAssessmentAnswers.query.filter_by(caseID=self.caseID).delete()

        # Delete linked projects
        CaseUser.query.filter_by(caseID=self.caseID).delete()

        # Delete linked stages
        CaseToStage.query.filter_by(caseID=self.caseID).delete()

        # Delete Tasks
        task_ids = [
            task.taskID for task in CaseTask.query.filter_by(caseID=self.caseID).all()
        ]

        # Delete associated TaskComments rows
        CaseTaskComments.query.filter(CaseTaskComments.taskID.in_(task_ids)).delete()

        # Delete Tasks
        CaseTask.query.filter_by(caseID=self.caseID).delete()

        # Delete Project Status Data
        CaseStatusData.filter_by(caseID=self.caseID).delete()

    def serialize(self):
        user = Users.query.get(self.userID)
        return {
            "caseID": self.caseID,
            "caseName": f"Waiting Case {self.caseID}" if "New" in self.caseName else self.caseName,
            "caseStatus": self.caseStatus.value,
            "createdAt": self.createdAt.isoformat(),
            "category": self.category.value,
            "startDate": self.startDate.isoformat() if self.startDate else None,
            "dueDate": self.dueDate.isoformat() if self.dueDate else None,
            "regionName": Regions.query.get(self.regionID).regionName,
            "serviceRequired": self.question3['questionChoice'],
            "serviceDate": self.beneficaries.serviceDate if self.beneficaries else None,
            "cost": self.question11,
            "referringPerson": f"{user.firstName} {user.lastName}"
        }

    def full_serialize(self):
        beneficiaries = CaseBeneficiary.query.filter_by(caseID=self.caseID).all()
        users_assigned_to_case = (
            Users.query.join(CaseUser, Users.userID == CaseUser.userID)
            .filter(CaseUser.caseID == self.caseID)
            .all()
        )
        region_details = {
            "regionID": self.regionID,
            "regionName": Regions.query.get(self.regionID).regionName,
        }
        user = Users.query.get(self.userID)
        user_details = {
            "userID": user.userID,
            "userFullName": f"{user.firstName} {user.lastName}",
            "username": user.username,
        }

        stages = CaseToStage.query.filter_by(caseID=self.caseID).all()
        completed_stages = [stage for stage in stages if stage.completed]

        if completed_stages:
            latest_completed_stage = max(
                completed_stages, key=lambda stage: stage.stageID
            )
        else:
            latest_completed_stage = (
                min(stages, key=lambda stage: stage.stageID) if stages else None
            )
        return {
            "caseID": self.caseID,
            "caseName": f"Waiting Case {self.caseID}" if "New" in self.caseName else self.caseName,
            "region": region_details,
            "stageName": (
                latest_completed_stage.stage.name if latest_completed_stage else "N/A"
            ),
            "user": user_details,
            "budgetApproved": self.budgetApproved,
            "sponsorAvailable": self.sponsorAvailable,
            "question1": self.question1,
            "question2": self.question2,
            "question3": self.question3,
            "question4": self.question4,
            "question5": self.question5,
            "question6": self.question6,
            "question7": self.question7,
            "question8": self.question8,
            "question9": self.question9,
            "question10": self.question10,
            "question11": self.question11,
            "question12": self.question12,
            "caseStatus": (
                "Assessment"
                if self.caseStatus == CaseStat.ASSESSMENT
                else self.caseStatus.value
            ),
            "category": self.category.value if self.category else None,
            "createdAt": self.createdAt.isoformat(),
            "dueDate": self.dueDate.isoformat() if self.dueDate else None,
            "startDate": self.startDate.isoformat() if self.startDate else None,
            "totalPoints": self.total_points,
            "beneficiaries": (
                [beneficiary.serialize() for beneficiary in beneficiaries]
                if beneficiaries
                else []
            ),
            "assignedUsers": (
                [user.userID for user in users_assigned_to_case]
                if users_assigned_to_case
                else []
            ),
        }

    def approved_serialize(self):
        beneficiaries = CaseBeneficiary.query.filter_by(caseID=self.caseID).all()
        users_assigned_to_case = (
            Users.query.join(CaseUser, Users.userID == CaseUser.userID)
            .filter(CaseUser.caseID == self.caseID)
            .all()
        )
        region_details = {
            "regionID": self.regionID,
            "regionName": Regions.query.get(self.regionID).regionName,
        }
        user = Users.query.get(self.userID)
        user_details = {
            "userID": user.userID,
            "userFullName": f"{user.firstName} {user.lastName}",
            "username": user.username,
        }

        stages = CaseToStage.query.filter_by(caseID=self.caseID).all()
        completed_stages = [stage for stage in stages if stage.completed]

        if completed_stages:
            latest_completed_stage = max(
                completed_stages, key=lambda stage: stage.stageID
            )
        else:
            latest_completed_stage = (
                min(stages, key=lambda stage: stage.stageID) if stages else None
            )
        stages_data = []
        for stage in stages:
            # Fetch all tasks for the linked stage
            tasks = CaseTask.query.filter_by(
                caseID=self.caseID, stageID=stage.stageID
            ).all()
            total_tasks = len(tasks)
            completed_tasks = 0
            inprogress_tasks = 0
            overdue_tasks = 0
            not_started_tasks = 0
            completionPercent = 0
            if total_tasks > 0:

                for task in tasks:
                    if task.status == CaseTaskStatus.DONE:
                        completed_tasks += 1
                    if task.status == CaseTaskStatus.OVERDUE:
                        overdue_tasks += 1
                    if task.status == CaseTaskStatus.INPROGRESS:
                        inprogress_tasks += 1
                    if task.status == CaseTaskStatus.TODO:
                        not_started_tasks += 1
                completionPercent = (completed_tasks / total_tasks) * 100
            stage_details = {
                "stageID": stage.stage.stageID,
                "name": stage.stage.name,
                "started": stage.started,
                "completed": stage.completed,
                "completionDate": (
                    stage.completionDate.isoformat() if stage.completionDate else None
                ),
                "totalTasks": total_tasks,
                "completedTasks": completed_tasks,
                "completionPercent": completionPercent,
                "notStartedTasks": not_started_tasks,
                "overdueTasks": overdue_tasks,
                "inprogressTasks": inprogress_tasks,
            }
            stages_data.append(stage_details)

        return {
            "caseID": self.caseID,
            "caseName": self.caseName,
            "region": region_details,
            "stageName": (
                latest_completed_stage.stage.name if latest_completed_stage else "N/A"
            ),
            "user": user_details,
            "budgetApproved": self.budgetApproved,
            "sponsorAvailable": self.sponsorAvailable,
            "question1": self.question1,
            "question2": self.question2,
            "question3": self.question3,
            "question4": self.question4,
            "question5": self.question5,
            "question6": self.question6,
            "question7": self.question7,
            "question8": self.question8,
            "question9": self.question9,
            "question10": self.question10,
            "question11": self.question11,
            "question12": self.question12,
            "caseStatus": (
                "Assessment"
                if self.caseStatus == CaseStat.ASSESSMENT
                else self.caseStatus.value
            ),
            "category": self.category.value if self.category else None,
            "createdAt": self.createdAt.isoformat(),
            "dueDate": self.dueDate.isoformat() if self.dueDate else None,
            "startDate": self.startDate.isoformat() if self.startDate else None,
            "totalPoints": self.total_points,
            "beneficiaries": (
                [beneficiary.serialize() for beneficiary in beneficiaries]
                if beneficiaries
                else []
            ),
            "assignedUsers": (
                [user.userID for user in users_assigned_to_case]
                if users_assigned_to_case
                else []
            ),
            "stages_data": stages_data,
        }


class CaseBeneficiary(db.Model):
    __tablename__ = "case_beneficiary"

    beneficiaryID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer, db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        unique=True
    )
    # Personal Information
    firstName = db.Column(db.String, nullable=False)
    surName = db.Column(db.String, nullable=False)
    gender = db.Column(db.String, nullable=False)
    birthDate = db.Column(db.String, nullable=False)
    birthPlace = db.Column(db.String, nullable=False)
    nationality = db.Column(db.String, nullable=False)
    idType = db.Column(db.String, nullable=False)
    idNumber = db.Column(db.String, nullable=False)

    # Address and Contact Information
    regionId = db.Column(
        db.Integer, db.ForeignKey("regions.regionID", ondelete="CASCADE"), nullable=True
    )  # New field added to match 'regionId'
    otherRegion = db.Column(
        db.String, nullable=True
    )  # New field added to match 'otherRegion'
    address = db.Column(
        db.String, nullable=True
    )  # Marked as non-nullable to match the Dart model
    phoneNumber = db.Column(db.String, nullable=False)
    altPhoneNumber = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=False)

    # Service Information
    serviceRequired = db.Column(db.String, nullable=False)
    otherServiceRequired = db.Column(db.String, nullable=True)
    problemDescription = db.Column(db.Text, nullable=True)
    serviceDescription = db.Column(db.Text, nullable=True)

    # Financial Information
    totalSupportCost = db.Column(db.Float, nullable=True)
    receiveFundDate = db.Column(db.Date, nullable=True)
    paymentMethod = db.Column(db.String, nullable=True)
    paymentsType = db.Column(db.String, nullable=True)
    otherPaymentType = db.Column(db.String, nullable=True)
    incomeType = db.Column(db.String, nullable=True)
    otherIncomeType = db.Column(db.String, nullable=True)

    # Housing Information
    housing = db.Column(db.String, nullable=True)
    otherHousing = db.Column(db.String, nullable=True)
    housingType = db.Column(db.String, nullable=True)
    otherHousingType = db.Column(db.String, nullable=True)

    # Family Information
    totalFamilyMembers = db.Column(db.Integer, nullable=True)
    childrenUnder15 = db.Column(db.String, nullable=True)
    isOldPeople = db.Column(db.Boolean, nullable=True)
    isDisabledPeople = db.Column(db.Boolean, nullable=True)
    isStudentsPeople = db.Column(db.Boolean, nullable=True)

    # Other Information
    serviceDate = db.Column(
        db.String, nullable=True
    )  # Marked as String to match the Dart model
    numberOfPayments = db.Column(db.String, nullable=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def serialize(self):
        return {
            "beneficiaryID": self.beneficiaryID,
            "caseID": self.caseID,
            "firstName": self.firstName,
            "surName": self.surName,
            "gender": self.gender,
            "birthDate": self.birthDate,
            "birthPlace": self.birthPlace,
            "nationality": self.nationality,
            "idType": self.idType,
            "idNumber": self.idNumber,
            "regionId": self.regionId,  # New field added
            "otherRegion": self.otherRegion,  # New field added
            "address": self.address,
            "phoneNumber": self.phoneNumber,
            "altPhoneNumber": self.altPhoneNumber,
            "email": self.email,
            "serviceRequired": self.serviceRequired,
            "otherServiceRequired": self.otherServiceRequired,
            "problemDescription": self.problemDescription,
            "serviceDescription": self.serviceDescription,
            "totalSupportCost": self.totalSupportCost,
            "receiveFundDate": (
                self.receiveFundDate.isoformat() if self.receiveFundDate else None
            ),
            "paymentMethod": self.paymentMethod,
            "paymentsType": self.paymentsType,
            "otherPaymentType": self.otherPaymentType,
            "incomeType": self.incomeType,
            "otherIncomeType": self.otherIncomeType,
            "housing": self.housing,
            "otherHousing": self.otherHousing,
            "housingType": self.housingType,
            "otherHousingType": self.otherHousingType,
            "totalFamilyMembers": self.totalFamilyMembers,
            "childrenUnder15": self.childrenUnder15,
            "isOldPeople": self.isOldPeople,
            "isDisabledPeople": self.isDisabledPeople,
            "isStudentsPeople": self.isStudentsPeople,
            "serviceDate": self.serviceDate,
            "numberOfPayments": self.numberOfPayments,
        }


class BeneficiaryForm(db.Model):
    __tablename__ = "beneficiary_form"

    formID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    url = db.Column(db.String, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseStage(db.Model):
    __tablename__ = "case_stage"

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
    __tablename__ = "case_to_stage"

    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        primary_key=True,
    )
    stageID = db.Column(
        db.Integer,
        db.ForeignKey("case_stage.stageID", ondelete="CASCADE"),
        primary_key=True,
    )
    started = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    completionDate = db.Column(db.Date, nullable=True)

    case = db.relationship("CasesData", backref="case_to_stage", lazy=True)
    stage = db.relationship("CaseStage", backref="case_to_stage", lazy=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseUser(db.Model):
    __tablename__ = "case_users"

    id = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=False,
    )
    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)

    def __repr__(self):
        return f"<CaseUser {self.id} CaseID: {self.caseID}, UserID: {self.userID}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseTask(db.Model):
    __tablename__ = "case_task"

    taskID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=False,
    )
    title = db.Column(db.String, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    assignedTo = db.relationship(
        "Users",
        secondary="case_task_assigned_to",
        backref="case_assigned_tasks",
        lazy="dynamic",
        single_parent=True,
    )
    cc = db.relationship(
        "Users",
        secondary="case_task_cc",
        backref="case_cc_tasks",
        lazy="dynamic",
        single_parent=True,
    )
    description = db.Column(db.String, nullable=True)
    createdBy = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    attachedFiles = db.Column(db.String, nullable=True)
    stageID = db.Column(db.Integer, db.ForeignKey("case_stage.stageID"), nullable=False)
    status = db.Column(db.Enum(CaseTaskStatus), nullable=False)
    completionDate = db.Column(db.Date, nullable=True)
    checklist = db.Column(JSONB, nullable=True)
    creationDate = db.Column(db.DateTime, default=func.now(), nullable=False)
    startDate = db.Column(db.Date, default=datetime.now().date())

    stage = db.relationship("CaseStage", backref="tasks", lazy=True)

    def is_overdue(self):
        return (
            self.deadline < datetime.today().date()
            if not self.status == CaseTaskStatus.DONE
            else False
        )

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

        # Delete related entries in CaseTaskAssignedTo and CaseTaskCC
        CaseTaskAssignedTo.query.filter_by(task_id=self.taskID).delete()
        CaseTaskCC.query.filter_by(task_id=self.taskID).delete()
        db.session.commit()

        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, taskID):
        return cls.query.get_or_404(taskID)

    def serialize(self):
        comments = (
            CaseTaskComments.query.filter_by(taskID=self.taskID)
            .order_by(CaseTaskComments.date.desc())
            .limit(5)
            .all()
        )
        return {
            "taskID": self.taskID,
            "title": self.title,
            "deadline": str(self.deadline),
            "description": self.description,
            "assignedTo": [user.username for user in self.assignedTo],
            "assignedTo_ids": [user.userID for user in self.assignedTo],
            "cc": [user.username for user in self.cc],
            "cc_ids": [user.userID for user in self.cc],
            "createdBy": self.createdBy,
            "attachedFiles": self.attachedFiles,
            "status": self.status.value,
            "completionDate": str(self.completionDate) if self.completionDate else None,
            "comments": [comment.serialize() for comment in comments],
            "checklist": self.checklist,
            "creationDate": self.creationDate.isoformat(),
            "startDate": (
                self.startDate.strftime("%Y-%m-%d") if self.startDate else None
            ),
        }


class CaseTaskComments(db.Model):
    __tablename__ = "case_task_comments"

    id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)
    taskID = db.Column(
        db.Integer,
        db.ForeignKey("case_task.taskID", ondelete="CASCADE"),
        nullable=False,
    )
    comment = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, nullable=False)

    def __repr__(self) -> str:
        return f"<CaseTaskComments {self.id} userID: {self.userID} taskID: {self.taskID} comment: {self.comment}>"

    def serialize(self):
        return {
            "user": (
                Users.query.get(self.userID).username
                if Users.query.get(self.userID)
                else "Unknown User"
            ),
            "comment": self.comment,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, commentID):
        return cls.query.get_or_404(commentID)


class CaseTaskAssignedTo(db.Model):
    __tablename__ = "case_task_assigned_to"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("case_task.taskID", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)

    def __repr__(self):
        return f"<CaseTaskAssignedTo {self.id} userID: {self.user_id} taskID: {self.task_id}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseTaskCC(db.Model):
    __tablename__ = "case_task_cc"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("case_task.taskID", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)

    def __repr__(self):
        return f"<CaseTaskCC {self.id} userID: {self.user_id} taskID: {self.task_id}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseStatusData(db.Model):
    __tablename__ = "case_status_data"

    id = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(db.String, nullable=False)
    data = db.Column(
        JSONB, nullable=True
    )  # You can adjust the type based on the data you want to store

    case_data = db.relationship("CasesData", backref="case_status_data", lazy=True)

    def __repr__(self):
        return (
            f"<CaseStatusData {self.id} caseID: {self.caseID}, Status: {self.status}>"
        )

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
            print(f"Error retrieving case status data: {str(e)}")
            return (
                None  # or raise an exception, depending on your error handling strategy
            )


class CaseAssessmentQuestions(db.Model):
    __tablename__ = "case_assessment_questions"
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
    __tablename__ = "case_assessment_answers"

    answerID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=False,
    )
    questionID = db.Column(
        db.Integer,
        db.ForeignKey("case_assessment_questions.questionID"),
        nullable=False,
    )
    answerText = db.Column(db.String, nullable=True)
    extras = db.Column(JSONB, nullable=True)

    # Add a foreign key reference to the choices table
    question = db.relationship(
        "CaseAssessmentQuestions", backref="case_assessment_answers", lazy=True
    )

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
