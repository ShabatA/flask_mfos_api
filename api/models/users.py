from api.models.cases import CaseUser
from api.models.projects import ProjectUser
from ..utils.db import db
from enum import Enum
from datetime import datetime
from .regions import Regions


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
    DASHBOARD = 'dashboard'
    NOTIFICATIONS = 'notifications'
    MESSAGES = 'messages'
    SUGCASES = 'sugcases'
    SUBCASES = 'subcases'
    REPORTS = 'reports'
    USERS = 'users'
    SUGPROJECTS = 'sugprojects'
    SUBPROJECTS = 'subprojects'
    CUSER = 'cuser'
    FINANCE = 'finance'
    ALL = 'all'
    ADDUSER = 'adduser'
    MANAGEUSER = 'manageuser'

class Users(db.Model):
    __tablename__ = 'users'

    userID = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), index=True, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    firstName = db.Column(db.String)
    lastName = db.Column(db.String)
    jobDescription = db.Column(db.String)
    mobile = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    UserStatus = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'))

    # Relationship with Role
    role_id = db.Column(db.Integer, db.ForeignKey('roles.RoleID'))
    role = db.relationship('Role', back_populates='users')

    permissions = db.relationship('UserPermissions', back_populates='user', cascade='all, delete-orphan')


    # cases = db.relationship('Cases', backref='user', lazy=True)
    region = db.relationship('Regions', backref='users')

    def __repr__(self):
        return f"<Users {self.userID} {self.username}>"
    
    def assign_role_and_permissions(self, role_name, permission_names):
        role = Role.query.filter_by(RoleName=role_name).first()
        if not role:
            raise ValueError(f'Role "{role_name}" not found')

        self.role = role

        if role_name == 'admin':
            permission_level = PermissionLevel.ALL
            user_permission = UserPermissions(user=self, permission_level=permission_level)
            self.permissions.append(user_permission)
        else:
            for permission_name in permission_names:
                permission_level = PermissionLevel[permission_name]
                user_permission = UserPermissions(user=self, permission_level=permission_level)
                self.permissions.append(user_permission)
    
    def update_permissions(self, permission_names):
        # Remove existing permissions
        self.permissions = []

        # Add new permissions
        for permission_name in permission_names:
            permission_level = PermissionLevel[permission_name]
            user_permission = UserPermissions(user=self, permission_level=permission_level)
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
        return self.role and self.role.RoleID == 1
    
    def update(self, data):
        for key, value in data.items():
            if key == 'regionName':
                # Handle 'regionName' separately
                region = Regions.query.filter_by(regionName=value).first()
                if region is not None:
                    setattr(self, 'region', region)
                else:
                    # Handle the case where the region is not found
                    raise ValueError('Region not found.')
            elif key == 'permission_level':
                self.update_permissions(value)
            elif key == 'projects':
                self.update_projects(value)
            elif key == 'cases':
                self.update_cases(value)

            else:
                # For other fields, simply update them
                setattr(self, key, value)

        # Assuming db is an instance of SQLAlchemy
        db.session.commit()
    
    def update_cases(self, case_list):
        # Delete linked cases
        CaseUser.query.filter_by(userID=self.userID).delete()
        for case in case_list:
            case_user = CaseUser(caseID=case, userID=self.userID)
            case_user.save()
    
    def update_projects(self, project_list):
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
            (p for p in self.permissions if p.permission_level == permission),
            None
        )

        if permission_to_remove:
            self.permissions.remove(permission_to_remove)
            db.session.commit()
        else:
            raise ValueError(f"Permission '{permission}' not found for the user.")

# Role Model
class Role(db.Model):
    __tablename__ = 'roles'
    RoleID = db.Column(db.Integer, primary_key=True)
    RoleName = db.Column(db.String(50), nullable=False, default = "staff")
    users = db.relationship('Users', back_populates='role')

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
    __tablename__ = 'user_permissions'
    UserID = db.Column(db.Integer, db.ForeignKey('users.userID'), primary_key=True)
    permission_level = db.Column(db.Enum(PermissionLevel), primary_key=True, default=PermissionLevel.DASHBOARD)
    user = db.relationship('Users', back_populates='permissions')
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    @classmethod
    def get_by_ids(cls, user_id, permission_id):
        return cls.query.get_or_404((user_id, permission_id))