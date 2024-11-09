from ..utils.db import db
from enum import Enum
from datetime import datetime, timedelta
from .regions import Regions
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import JSONB
import random


# class UserRole(Enum):
#     ADMIN = "admin"
#     REGIONLEADER = "regionleader"
#     STAFF = "staff"
#     ORGANIZATION = "organization"


class UserStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PermissionLevel(Enum):
    DASHBOARD = "dashboard"
    NOTIFICATIONS = "notifications"
    MESSAGES = "messages"
    SUGCASES = "sugcases"
    SUBCASES = "subcases"
    REPORTS = "reports"
    USERS = "users"
    SUGPROJECTS = "sugprojects"
    SUBPROJECTS = "subprojects"
    CUSER = "cuser"
    FINANCE = "finance"
    ALL = "all"
    ADDUSER = "adduser"
    MANAGEUSER = "manageuser"


class Users(db.Model):
    __tablename__ = "users"

    userID = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), index=True, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    firstName = db.Column(db.String)
    lastName = db.Column(db.String)
    jobDescription = db.Column(db.String)
    mobile = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    UserStatus = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    regionID = db.Column(db.Integer, db.ForeignKey("regions.regionID"))
    imageLink = db.Column(db.String(255))

    # Relationship with Role
    role_id = db.Column(db.Integer, db.ForeignKey("roles.RoleID"))
    role = db.relationship("Role", back_populates="users")

    permissions = db.relationship(
        "UserPermissions", back_populates="user", cascade="all, delete-orphan"
    )

    # cases = db.relationship('Cases', backref='user', lazy=True)
    region = db.relationship("Regions", backref="users")

    def __repr__(self):
        return f"<Users {self.userID} {self.username}>"
    
    # Password handling methods
    def set_password(self, password):
        """Hash and set the password."""
        self.password = generate_password_hash(password)
        db.session.commit()
    
    def check_password(self, password):
        """Check if the provided password matches the hashed password."""
        return check_password_hash(self.password, password)

    def assign_role_and_permissions(self, role_name, permission_names):
        role = Role.query.filter_by(RoleName=role_name).first()
        if not role:
            raise ValueError(f'Role "{role_name}" not found')

        self.role = role

        if role_name == "admin":
            permission_level = PermissionLevel.ALL
            user_permission = UserPermissions(
                user=self, permission_level=permission_level
            )
            self.permissions.append(user_permission)
        else:
            for permission_name in permission_names:
                permission_level = PermissionLevel[permission_name]
                user_permission = UserPermissions(
                    user=self, permission_level=permission_level
                )
                self.permissions.append(user_permission)

    def update_permissions(self, permission_names):
        # Remove existing permissions
        self.permissions = []

        # Add new permissions
        for permission_name in permission_names:
            permission_level = PermissionLevel[permission_name]
            user_permission = UserPermissions(
                user=self, permission_level=permission_level
            )
            self.permissions.append(user_permission)

        db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def is_active(self):
        return self.active

    @classmethod
    def get_by_id(cls, userID):
        return cls.query.get_or_404(userID)

    def is_admin(self):
        """
        Check if the user has the 'admin' role.
        :return: True if the user has the 'admin' role, False otherwise.
        """
        return True if self.role.RoleID == 1 else False

    def update(self, data):
        for key, value in data.items():
            if key == "password":
                # Check if the new password is different from the existing one
                if not check_password_hash(self.password, value):
                    value = generate_password_hash(value)
                    setattr(self, key, value)
                else:
                    # Skip updating the password if it's the same
                    continue
            elif key == "regionName":
                # Handle 'regionName' separately
                region = Regions.query.filter_by(regionName=value).first()
                if region is not None:
                    setattr(self, "region", region)
                else:
                    # Handle the case where the region is not found
                    raise ValueError("Region not found.")
            elif key == "permission_level":
                self.update_permissions(value)
            elif key == "projects":
                self.update_projects(value)
            elif key == "cases":
                self.update_cases(value)
            else:
                # For other fields, simply update them
                setattr(self, key, value)

        # Assuming db is an instance of SQLAlchemy
        db.session.commit()

    def update_cases(self, case_list):
        from api.models.cases import CaseUser
        # Delete linked cases
        CaseUser.query.filter_by(userID=self.userID).delete()
        for case in case_list:
            case_user = CaseUser(caseID=case, userID=self.userID)
            case_user.save()

    def update_projects(self, project_list):
        from api.models.projects import ProjectUser
        # Delete linked cases
        ProjectUser.query.filter_by(userID=self.userID).delete()
        for project in project_list:
            pro_user = ProjectUser(projectID=project, userID=self.userID)
            pro_user.save()

    def remove_permission(self, permission):
        """
        Remove a specific permission from the user's existing permissions.
        :param permission: The permission to be removed from the user.
        """
        permission_to_remove = next(
            (p for p in self.permissions if p.permission_level == permission), None
        )

        if permission_to_remove:
            self.permissions.remove(permission_to_remove)
            db.session.commit()
        else:
            raise ValueError(f"Permission '{permission}' not found for the user.")

    def mini_user_details(self):
        return {
            "userID": self.userID,
            "fullName": f"{self.firstName} {self.lastName}",
            "username": self.username,
            "email": self.email,
        }


# Role Model
class Role(db.Model):
    __tablename__ = "roles"
    RoleID = db.Column(db.Integer, primary_key=True)
    RoleName = db.Column(db.String(50), nullable=False, default="staff")
    users = db.relationship("Users", back_populates="role")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, RoleID):
        return cls.query.get_or_404(RoleID)


# RolePermissions Model
class UserPermissions(db.Model):
    __tablename__ = "user_permissions"
    UserID = db.Column(db.Integer, db.ForeignKey("users.userID"), primary_key=True)
    permission_level = db.Column(
        db.Enum(PermissionLevel), primary_key=True, default=PermissionLevel.DASHBOARD
    )
    user = db.relationship("Users", back_populates="permissions")

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_ids(cls, user_id, permission_id):
        return cls.query.get_or_404((user_id, permission_id))


class UserTaskStatus(Enum):
    TODO = "To Do"
    INPROGRESS = "In Progress"
    DONE = "Done"
    OVERDUE = "Overdue"

class UserTask(db.Model):
    __tablename__ = "user_task"

    taskID = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer, db.ForeignKey("users.userID"), nullable=False)  # Direct link to the user
    user = db.relationship("Users", backref="personal_tasks", lazy=True)  # Relationship to user
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(UserTaskStatus), default=UserTaskStatus.TODO, nullable=False)
    completionDate = db.Column(db.Date, nullable=True)
    checklist = db.Column(JSONB, nullable=True)
    creationDate = db.Column(db.DateTime, default=datetime.utcnow)
    startDate = db.Column(db.Date, default=datetime.now().date())

    def is_overdue(self):
        return self.deadline < datetime.today().date() if self.status != UserTaskStatus.DONE else False

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, taskID):
        return cls.query.get_or_404(taskID)

    def serialize(self):
        return {
            "taskID": self.taskID,
            "title": self.title,
            "deadline": str(self.deadline),
            "description": self.description,
            "status": self.status.value,
            "completionDate": str(self.completionDate) if self.completionDate else None,
            "checklist": self.checklist,
            "creationDate": self.creationDate.isoformat(),
            "startDate": self.startDate.strftime("%Y-%m-%d") if self.startDate else None,
        }


class OTPRequest(db.Model):
    __tablename__ = 'otp_requests'

    id = db.Column(db.Integer, primary_key=True, index=True)
    email = db.Column(db.String, nullable=False)
    otp = db.Column(db.String, nullable=False)
    expiration_time = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    def mark_as_used(self):
        """Mark this OTP entry as used."""
        self.is_used = True
        db.session.commit()

    @classmethod
    def generate_otp(cls, email, expiration_minutes=5):
        """Generate a 6-digit OTP, save it, and set an expiration time."""
        otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP
        expiration_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)

        otp_entry = cls(email=email, otp=otp, expiration_time=expiration_time)
        db.session.add(otp_entry)
        db.session.commit()
        return otp  # Return the OTP to send it to the user
    
    @staticmethod
    def verify_and_delete_otp(email, otp):
        """Verify if an OTP is valid for a given email, then delete it if valid or expired."""
        otp_entry = OTPRequest.query.filter_by(email=email, otp=otp, is_used=False).first()
        
        # Check if the OTP exists and is not expired
        if otp_entry:
            if otp_entry.expiration_time >= datetime.utcnow():
                otp_entry.mark_as_used()
                db.session.delete(otp_entry)
                db.session.commit()
                return otp_entry  # Valid OTP
            else:
                # Delete if expired
                db.session.delete(otp_entry)
                db.session.commit()
        return None  # Return None if verification fails
    
    @staticmethod
    def verify_otp(email, otp):
        """Verify if an OTP is valid for a given email."""
        otp_entry = OTPRequest.query.filter_by(email=email, otp=otp, is_used=False).first()
        
        # Check if the OTP exists and is not expired
        if otp_entry and otp_entry.expiration_time >= datetime.utcnow():
            return otp_entry  # Return the OTP entry instead of True
        return None  # Return None if verification fails
    
    

    @classmethod
    def cleanup_expired_otps(cls):
        """Delete expired OTP entries from the database."""
        expired_otps = cls.query.filter(cls.expiration_time < datetime.utcnow(), cls.is_used == False).all()
        for otp in expired_otps:
            db.session.delete(otp)
        db.session.commit()
