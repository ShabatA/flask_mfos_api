from api.config.config import Config
from flask_restx import Resource, Namespace, fields
from flask import request, current_app

from api.models.cases import CaseTask, CaseTaskStatus, CaseUser, CasesData
from ..models.users import Users, Role, UserPermissions, PermissionLevel
from ..models.projects import ProjectUser, ProjectTask, ProjectsData, TaskStatus, Activities, ActivityUsers
from werkzeug.security import generate_password_hash, check_password_hash
from http import HTTPStatus
from flask_jwt_extended import (create_access_token,
                                create_refresh_token, jwt_required, get_jwt_identity)
from werkzeug.exceptions import Conflict, BadRequest
from ..models.regions import Regions  # Import the Region model
from ..utils.db import db
from datetime import timedelta

auth_namespace = Namespace('auth', description="a namespace for authentication")

user_management_namespace = Namespace('User Management', description="A namespace to assign/reassign projects and/or cases to users.")

# Define a Swagger model for the users attribute
users_model = auth_namespace.model('User', {
    'userID': fields.Integer(),
    'username': fields.String()
})

permission_model = auth_namespace.model(
    'userpermission', {
        'permission_level': fields.List(fields.String, required=True, description="List of permission names")
    }
)

signup_model = auth_namespace.model(
    'SignUp', {
        'userID': fields.Integer(),
        'username': fields.String(required=True, description="A username"),
        'firstName': fields.String(required=True, description="A first name"),
        'lastName': fields.String(required=True, description="A last name"),
        'email': fields.String(required=True, description="An email"),
        # mobile
        'mobile': fields.String(description='Mobile phone'),
        # job description
        'jobDescription': fields.String(description='Job title'),
        'password': fields.String(required=True, description="A password"),
        'regionName': fields.String(required=True, description="Region Name"),  # Changed to regionName
        'RoleName': fields.String(required=True, description="Role Name"),  # Added roleName
        'permissionNames': fields.List(fields.String, required=True, description="List of permission names"),
        'imageLink': fields.String(required=True, description='Image link.')
    }
)

user_model = auth_namespace.model(
    'Users', {
        'username': fields.String(required=True, description="A username"),
        'email': fields.String(required=True, description="An email"),
        'password': fields.String(required=True, description="A password"),
        'active': fields.Boolean(description="This shows that User is active", default=True),
        'UserStatus': fields.String(description="This shows of staff status"),
        'regionID': fields.Integer(description="Region ID"),  # Added regionID field
        'regionName': fields.String(description="Region Name"),  # Added regionName field
        'RoleName': fields.String(required=True, description="Role Name"),  # Added roleName
        'permissionNames': fields.List(fields.String, required=True, description="List of permission names"),
        'imageLink': fields.String(required=True, description='Image link.')

    }
)


user2_model = auth_namespace.model(
    'Users', {
        'userID': fields.Integer(),
        'username': fields.String(required=True, description="A username"),
        'email': fields.String(required=True, description="An email"),
        'password': fields.String(required=True, description="A password"),
        'imageLink': fields.String(required=True, description='Image link.')
    }
)

role_model = auth_namespace.model(
    'Role', {
        'RoleID': fields.Integer(),
        'RoleName': fields.String()
    }
)

login_model = auth_namespace.model(
    'Login', {
        'email': fields.String(required=True, description="An email"),
        'password': fields.String(required=True, description="A password")
    }
)


@auth_namespace.route('/roles')
class RoleResource(Resource):
    @auth_namespace.expect(role_model)
    @auth_namespace.marshal_with(role_model)
    @auth_namespace.doc(
        description="Create a new role such as admin, staff, etc",
    )
    def post(self):
        data = request.get_json()

        # Check if the role name is already taken
        existing_role = Role.query.filter_by(RoleName=data.get('roleName')).first()
        if existing_role:
            return {'message': 'Role name already taken'}, HTTPStatus.BAD_REQUEST

        new_role = Role(RoleName=data.get('RoleName'))
        new_role.save()

        return new_role, HTTPStatus.CREATED

@auth_namespace.route('/signup')
@auth_namespace.doc(
    description="Create a new user account",
)
class SignUp(Resource):

    @auth_namespace.expect(signup_model)
    @auth_namespace.marshal_with(user2_model)
    def post(self):
        """
        Create a new user account 
        """

        data = request.get_json()

        try:
            region_name = data.get('regionName')
            region = Regions.query.filter_by(regionName=region_name).first()

            if not region:
                # If the region does not exist, create it
                region = Regions(regionName=region_name)
                region.save()  # Assuming you have a method to save the new region

            existing_user = Users.query.filter_by(email=data.get('email')).first()

            if existing_user:
                raise Conflict(f"User with email {data.get('email')} already exists")
            
            role_name = data.get('RoleName')
            role = Role.query.filter_by(RoleName=role_name).first()
            if not role:
                return {'message': f'Role "{role_name}" not found'}, 400

            # Create UserPermissions entries based on the user's permissions
            permission_names = data.get('permissionNames', [])
            # user_permissions = []

            new_user = Users(
                username=data.get('username'),
                email=data.get('email'),
                firstName=data.get('firstName'),
                lastName=data.get('lastName'),
                jobDescription = data.get('jobDescription'),
                mobile = data.get('mobile'),
                password=generate_password_hash(data.get('password')),
                regionID=region.regionID,
                role=role,  # Set the user's role
                imageLink= data.get('imageLink')
            )
            # new_user.save()

            new_user.assign_role_and_permissions(role_name, permission_names)

            new_user.save()

            cases = data.get('cases', [])
            projects = data.get('projects', [])
            
            if cases:
                for case in cases:
                    case_user = CaseUser(caseID=case, userID=new_user.userID)
                    case_user.save()
            
            if projects:
                for project in projects:
                    project_user = ProjectUser(projectID=project, userID=new_user.userID)
                    project_user.save()
            

            return new_user, HTTPStatus.CREATED

        except Conflict as e:
            raise e  # Re-raise the Conflict exception for specific handling
        except Exception as e:
            raise BadRequest(f"Error creating user: {str(e)}")



@auth_namespace.route('/login')

class Login(Resource):

    @auth_namespace.expect(login_model)
    @auth_namespace.doc(
    description="Generate a JWT and Login"
    )
    def post(self):
        """
            Generate a JWT
        
        """

        data = request.get_json()

        email = data.get('email')
        password_hash = data.get('password')

        user = Users.query.filter_by(email=email).first()

        if (user is not None) and check_password_hash(user.password, password_hash):
            access_token = create_access_token(identity=user.username, expires_delta=timedelta(hours=1))
            refresh_token = create_refresh_token(identity=user.username, expires_delta=timedelta(hours=1))

            response = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'regionID': user.regionID if user.regionID else None  # Retrieve regionID from the associated user
            }

            return response, HTTPStatus.OK

        raise BadRequest("Invalid Username or password")


@auth_namespace.route('/refresh')
class Refresh(Resource):

    @jwt_required(refresh=True)
    @auth_namespace.doc(
        description="Refresh a JWT",
    )
    def post(self):
        username = get_jwt_identity()

        access_token = create_access_token(identity=username, expires_delta=timedelta(hours=1))

        return {'access_token': access_token}, HTTPStatus.OK


@auth_namespace.route('/admin-only')
class AdminOnlyResource(Resource):

    @jwt_required()
    @auth_namespace.doc(
        description="Access only for admins",
    )
    def get(self):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        users = Users.query.all()
        count = 0
        for user in users:
            if user.is_admin():
                count+=1
        return {'message': count}, HTTPStatus.OK  

        

        

@auth_namespace.route('/admin/update-user/<int:user_id>')
class UpdateUserByAdmin(Resource):
    @auth_namespace.expect(user_model)
    @auth_namespace.doc(
        description="Update a user's details",
        params={'user_id': 'Specify the user ID'}
    )

    @jwt_required()
    def put(self, user_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # current_user = Users.query.filter_by(username=get_jwt_identity(), is_admin=True).first()

        if not current_user.is_admin():
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        user_to_update = Users.get_by_id(user_id)
        if not user_to_update:
            return {'message': 'User not found.'}, HTTPStatus.NOT_FOUND

        try:
            data = request.get_json(force=True, silent=True)

            if not data:
                return {'message': 'Invalid JSON data.'}, HTTPStatus.BAD_REQUEST

            # Update user fields using the update method
            user_to_update.update(data)
            
            # Save the updated user
            user_to_update.save()

            # Return the updated user without using marshal_with
            return auth_namespace.marshal(user_to_update, user_model), HTTPStatus.OK

        except Exception as e:
            return {'message': f'Error updating user: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@auth_namespace.route('/user/update-details/<int:user_id>')
class UpdateUserByUser(Resource):
    @auth_namespace.expect(user_model)
    @auth_namespace.doc(
        description="Update a user's details",
        params={'user_id': 'Specify the user ID'}
    )

    @jwt_required()
    def put(self, user_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # current_user = Users.query.filter_by(username=get_jwt_identity(), is_admin=True).first()


        user_to_update = Users.get_by_id(user_id)
        if not user_to_update:
            return {'message': 'User not found.'}, HTTPStatus.NOT_FOUND

        try:
            data = request.get_json(force=True, silent=True)

            if not data:
                return {'message': 'Invalid JSON data.'}, HTTPStatus.BAD_REQUEST
            
            # Exclude 'permission_level' from the data dictionary if it's present
            if 'permission_level' in data:
                del data['permission_level']
            
            if 'projects' in data:
                del data['projects']
            
            if 'cases' in data:
                del data['cases']

            # Update user fields using the update method
            user_to_update.update(data)
            
            # Save the updated user
            user_to_update.save()

            # Return the updated user without using marshal_with
            return auth_namespace.marshal(user_to_update, user_model), HTTPStatus.OK

        except Exception as e:
            return {'message': f'Error updating user: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@auth_namespace.route('/admin/deactivate/<int:user_id>')
class DeactivateUserByAdmin(Resource):

    @jwt_required()
    @auth_namespace.doc(
        description="Deactivate a user",
        params={'user_id': 'Specify the user ID'}
    )
    def put(self, user_id):
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin():
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        user_to_update = Users.get_by_id(user_id)
        if user_to_update:
            
            user_to_update.active = False
            user_to_update.save()
            return {'message': 'User deactivated successfully.'}, HTTPStatus.OK
        else:
            return {'message': 'User not found.'}, HTTPStatus.NOT_FOUND

@auth_namespace.route('/admin/activate/<int:user_id>')
class ActivateUserByAdmin(Resource):

    @jwt_required()
    @auth_namespace.doc(
        description="Activate a user",
        params={'user_id': 'Specify the user ID'}
    )
    def put(self, user_id):
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin():
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        user_to_update = Users.get_by_id(user_id)
        if user_to_update:
            
            user_to_update.active = True
            user_to_update.save()
            return {'message': 'User activated successfully.'}, HTTPStatus.OK
        else:
            return {'message': 'User not found.'}, HTTPStatus.NOT_FOUND

@auth_namespace.route('/admin/update-user-permissions/<int:user_id>')
class UpdateUserPermissionsByAdmin(Resource):
    @auth_namespace.expect(permission_model)
    @jwt_required()
    @auth_namespace.doc(
        description="Update a user's permissions",
        params={'user_id': 'Specify the user ID'}
    )
    def put(self, user_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_user.is_admin():
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        user_to_update = Users.get_by_id(user_id)
        if not user_to_update:
            return {'message': 'User not found.'}, HTTPStatus.NOT_FOUND

        try:
            data = request.get_json(force=True, silent=True)

            if not data:
                return {'message': 'Invalid JSON data.'}, HTTPStatus.BAD_REQUEST

            # Update user permissions using the update_permissions method
            user_to_update.update_permissions(data.get('permission_level', []))

            # Return the updated user without using marshal_with
            return auth_namespace.marshal(user_to_update, user_model), HTTPStatus.OK

        except Exception as e:
            return {'message': f'Error updating user permissions: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@auth_namespace.route('/admin/remove-permission/<int:user_id>/<string:permission_name>')
class RemovePermissionByAdmin(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description="Remove a permission from a user",
        params={'user_id': 'Specify the user ID',
                'permission_name': 'Specify the permission level'}
    )
    def delete(self, user_id, permission_name):
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin():
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        user_to_update = Users.get_by_id(user_id)
        if not user_to_update:
            return {'message': 'User not found.'}, HTTPStatus.NOT_FOUND

        try:
            # Check if the permission name is a valid PermissionLevel enum value
            permission_level = PermissionLevel[permission_name]

            # Remove the specified permission from the user's existing permissions
            user_to_update.remove_permission(permission_level)

            return {'message': f'Permission "{permission_name}" removed successfully.'}, HTTPStatus.OK

        except ValueError as e:
            return {'message': str(e)}, HTTPStatus.BAD_REQUEST
        


@auth_namespace.route('/current-user-permissions')
class CurrentUserPermissions(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description='Returns all permissions for the currently logged in user',
        )
    def get(self):
        try:
            current_user_identity = get_jwt_identity()

            # Assuming Users has a method to get user by username
            current_user = Users.query.filter_by(username=current_user_identity).first()

            if current_user:
                # Extract permissions from the current user
                permissions = [permission.permission_level.value for permission in current_user.permissions]

                return {'permissions': permissions}, HTTPStatus.OK
            else:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error getting current user permissions: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@auth_namespace.route('/user-permissions/<int:user_id>')
class UserPermissions(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description = "Returns all permissions for a specific user",
        params={'user_id': 'The ID of the user whose permissions you want to retrieve'},
    )
    def get(self, user_id):
        try:
            # Ensure the requesting user is an admin or the requested user
            current_user_identity = get_jwt_identity()
            current_user = Users.query.filter_by(username=current_user_identity).first()

            if not current_user.is_admin() and current_user.userID != user_id:
                return {'message': 'Access forbidden. Admins or the user only.'}, HTTPStatus.FORBIDDEN

            # Get the user by user_id
            user = Users.get_by_id(user_id)

            if user:
                # Extract permissions from the user
                permissions = [permission.permission_level.value for permission in user.permissions]

                return {'permissions': permissions}, HTTPStatus.OK
            else:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error getting user permissions: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@auth_namespace.route('/current-user-role')
class CurrentUserRole(Resource):
    @jwt_required()
    @auth_namespace.doc(description="Returns the role of the currently logged in user.")
    def get(self):
        try:
            current_user_identity = get_jwt_identity()

            # Assuming Users has a method to get user by username
            current_user = Users.query.filter_by(username=current_user_identity).first()

            if current_user:
                role_name = current_user.role.RoleName if current_user.role else None

                return {'roleName': role_name}, HTTPStatus.OK
            else:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error getting current user role: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@auth_namespace.route('/user-role/<int:user_id>')
class UserRole(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description = "Returns all permissions for a specific user",
        params={'user_id': 'The ID of the user whose permissions you want to retrieve'}
        )
    def get(self, user_id):
        try:
            # Ensure the requesting user is an admin or the requested user
            current_user_identity = get_jwt_identity()
            current_user = Users.query.filter_by(username=current_user_identity).first()

            if not current_user.is_admin() and current_user.userID != user_id:
                return {'message': 'Access forbidden. Admins or the user only.'}, HTTPStatus.FORBIDDEN

            # Get the user by user_id
            user = Users.get_by_id(user_id)

            if user:
                role_name = user.role.RoleName if user.role else None

                return {'roleName': role_name}, HTTPStatus.OK
            else:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error getting user role: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
@auth_namespace.route('/current-user-id')
class CurrentUserId(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description='Returns the ID of the currently logged in user.',
    )
    def get(self):
        try:
            current_user_identity = get_jwt_identity()

            # Assuming Users has a method to get user by username
            current_user = Users.query.filter_by(username=current_user_identity).first()

            if current_user:
                return {'userID': current_user.userID}, HTTPStatus.OK
            else:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error getting current user ID: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@auth_namespace.route('/all-users')
class AllUsers(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description='Returns information for all users.',
    )
    def get(self):
        try:
            # Fetch all users from the database
            all_users = Users.query.all()

            # Create a list to store user data
            users_data = []

            # Iterate through each user and extract relevant information
            admins = 0
            for user in all_users:
                if user.is_admin():
                    admins += 1
                user_data = self.get_user_data(user)
                users_data.append(user_data)
            print(admins)

            # Return the user data as JSON
            return {'users': users_data}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting all users: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

    @staticmethod
    def get_user_data(user):
        
        
        if user.is_admin():
            all_projects = ProjectsData.query.all()
            all_cases = CasesData.query.all()
            all_activities = Activities.query.all()
        else:
            # Fetch all projects the user has access to
            projects = (
                ProjectsData.query.join(Users, Users.userID == ProjectsData.createdBy)
                .filter(Users.userID == user.userID)
                .all()
            )

            # Fetch all cases the user has access to
            cases = CasesData.query.filter(CasesData.userID == user.userID).all()

            # Fetch all projects associated with the user through ProjectUser
            project_user_projects = (
                ProjectsData.query.join(ProjectUser, ProjectsData.projectID == ProjectUser.projectID)
                .filter(ProjectUser.userID == user.userID)
                .all()
            )

            # Fetch all cases associated with the user through CaseUser
            case_user_cases = (
                CasesData.query.join(CaseUser, CasesData.caseID == CaseUser.caseID)
                .filter(CaseUser.userID == user.userID)
                .all()
            )
            
            created_activities = Activities.query.filter_by(createdBy=user.userID).all()

            # Fetch all activities associated with the user through ActivityUsers
            assigned_activities = (
                Activities.query.join(ActivityUsers, Activities.activityID == ActivityUsers.activityID)
                .filter(ActivityUsers.userID == user.userID)
                .all()
            )

            # Combine the created and assigned activities and remove duplicates
            all_activities = list(set(created_activities + assigned_activities))

            # Combine the projects and remove duplicates
            all_projects = list(set(projects + project_user_projects))

            # Combine the cases and remove duplicates
            all_cases = list(set(cases + case_user_cases))

        if user.userID == 27:
            print(all_cases)

        # Fetch all ProjectTasks the user is assigned to
        project_tasks = ProjectTask.query.join(Users.assigned_tasks).filter(Users.userID == user.userID).all()
        total_p_tasks = len(project_tasks)
        completed_p_tasks = 0
        inprogress_p_tasks = 0
        overdue_p_tasks = 0
        not_started_p_tasks = 0
        if total_p_tasks > 0:

            for task in project_tasks:
                if task.status == TaskStatus.DONE:
                    completed_p_tasks += 1
                if task.status == TaskStatus.OVERDUE:
                    overdue_p_tasks += 1
                if task.status == TaskStatus.INPROGRESS:
                    inprogress_p_tasks += 1
                if task.status == TaskStatus.TODO:
                    not_started_p_tasks += 1

        # Fetch all CaseTasks the user is assigned to
        case_tasks = CaseTask.query.join(Users.case_assigned_tasks).filter(Users.userID == user.userID).all()
        total_c_tasks = len(case_tasks)
        completed_c_tasks = 0
        inprogress_c_tasks = 0
        overdue_c_tasks = 0
        not_started_c_tasks = 0
        if total_c_tasks > 0:

            for task in case_tasks:
                if task.status == CaseTaskStatus.DONE:
                    completed_c_tasks += 1
                if task.status == CaseTaskStatus.OVERDUE:
                    overdue_c_tasks += 1
                if task.status == CaseTaskStatus.INPROGRESS:
                    inprogress_c_tasks += 1
                if task.status == CaseTaskStatus.TODO:
                    not_started_c_tasks += 1
        
        user_data = {
            'userID': user.userID,
            'username': user.username,
            'imageLink': user.imageLink,
            'email': user.email,
            'firstName': user.firstName,
            'lastName': user.lastName,
            'jobDescription': user.jobDescription,
            'mobile': user.mobile,
            'active': user.active,
            'userStatus': user.UserStatus.value,
            'date_created': user.date_created.isoformat(),
            'regionID': user.regionID,
            'role': {
                'roleID': user.role.RoleID,
                'roleName': user.role.RoleName
            },
            'permissions': [permission.permission_level.value for permission in user.permissions],
            'activities': [{'activityID': activity.activityID,
                            'activityName': activity.activityName,
                            'deadline': activity.deadline.isoformat() if activity.deadline else None,
                            'duration': activity.duration}for activity in all_activities] if all_activities else [],
            'projects': [{'projectID': project.projectID,
                          'projectName': project.projectName,
                          'status': project.projectStatus.value,
                          'projectType': project.project_type.value,
                          'dueDate': project.dueDate.isoformat() if project.dueDate else None} for project in all_projects] if all_projects else [],
            'cases': [{'caseID': case.caseID,
                       'caseName': case.caseName,
                       'status': case.caseStatus.value,
                       'dueDate': case.dueDate.isoformat() if case.dueDate else None} for case in all_cases] if all_cases else [],
            'project_tasks': [{'taskID': task.taskID,
                               'title': task.title,
                               'description': task.description,
                               'status': task.status.value,
                               'checklist': task.checklist,
                               'stageName': task.stage.name,
                               'projectName': ProjectsData.query.get(task.projectID).projectName,
                               'completionDate': task.completionDate.isoformat() if task.completionDate else None} for task in project_tasks] if project_tasks else [],
            'project_tasks_summary': {'total_p_tasks': total_p_tasks,'completed_p_tasks': completed_p_tasks, 'overdue_p_tasks': overdue_p_tasks,
                                     'not_started_p_tasks': not_started_p_tasks, 'inprogress_p_tasks': inprogress_p_tasks},
            'case_tasks': [{'taskID': task.taskID,
                            'title': task.title,
                            'description': task.description,
                            'status': task.status.value,
                            'checklist': task.checklist,
                            'stageName': task.stage.name,
                            'caseName': CasesData.query.get(task.caseID).caseName,
                            'completionDate': task.completionDate.isoformat() if task.completionDate else None} for task in case_tasks] if case_tasks else [],
            'case_task_summary': {'total_c_tasks': total_c_tasks,'completed_c_tasks': completed_c_tasks, 'overdue_c_tasks': overdue_c_tasks,
                                     'not_started_c_tasks': not_started_c_tasks, 'inprogress_c_tasks': inprogress_c_tasks},
        }
        return user_data

@auth_namespace.route('/user/<int:user_id>')
class SingleUser(Resource):
    @jwt_required()
    @auth_namespace.doc(
        params={'user_id': 'The ID of the user'},
        description='Returns information for a single user.',
    )
    def get(self, user_id):
        try:
            # Get user by ID
            user = Users.get_by_id(user_id)

            # Check if the user exists
            if not user:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

            # Get user data
            user_data = AllUsers.get_user_data(user)

            # Return the user data as JSON
            return {'user': user_data}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting user by ID: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@auth_namespace.route('/current-user/details')
class CurrentUser(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description='Returns information for a single user.',
    )
    def get(self):
        try:
            # Get user by ID
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Check if the user exists
            if not current_user:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

            # Get user data
            user_data = AllUsers.get_user_data(current_user)

            # Return the user data as JSON
            return {'user': user_data}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting user by ID: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@auth_namespace.route('/get-user-id/<string:username>')
class GetUserId(Resource):
    @jwt_required()
    @auth_namespace.doc(
        description='Returns the ID of the specified user.',
        params={'username': 'The username of the user whose ID you want to retrieve'}
    )
    def get(self, username):
        try:
            # Fetch the user by username from the database
            user = Users.query.filter_by(username=username).first()

            if user:
                return {'userID': user.userID}, HTTPStatus.OK
            else:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error getting user ID: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR



######### User Management ############


@user_management_namespace.route('/assign-user/<int:project_id>/<string:username>')
class AssignUserToProjectResource(Resource):
    @jwt_required()
    @user_management_namespace.doc(
        description= 'When a user is given access/responsibility to an existing project.',
        params={
            'project_id': 'The project to re-assign',
            'username': 'The Username of the User to give the project to.'
            }
    )
    def post(self, project_id, username):
        try:
            # Get the current user from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Check if the current user has the necessary permissions (e.g., project owner or admin)
            # Adjust the condition based on your specific requirements
            if not current_user.is_admin():
                return {'message': 'Unauthorized. You do not have permission to link users to projects.'}, HTTPStatus.FORBIDDEN

            # Get the project by ID
            project = ProjectsData.query.get(project_id)
            if not project:
                return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

            

            # Get the user by username
            user = Users.query.filter_by(username=username).first()
            print(f'user.is_active: {user.is_active()}')
            print(f'Type of user.is_active: {type(user.is_active())}')

            if not user: 
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND
            elif  not user.is_active():
                return {'message': 'User is deactivated'}, HTTPStatus.BAD_REQUEST
            

            # Check if the user is already linked to the project
            if ProjectUser.query.filter_by(projectID=project_id, userID=user.userID).first():
                return {'message': 'User is already linked to the project'}, HTTPStatus.BAD_REQUEST

            # Link the user to the project
            project_user = ProjectUser(projectID=project_id, userID=user.userID)
            project_user.save()

            return {'message': 'User linked to the project successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error linking user to project: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@user_management_namespace.route('/reassign-user/<int:project_id>/from/<string:fromusername>/to/<string:tousername>')
class ReassignUserToProjectResource(Resource):
    @jwt_required()
    @user_management_namespace.doc(
        description= 'If necessary a project needs to be given to another user.',
        params={
            'project_id': 'The project to re-assign',
            'fromusername': 'The Username of the User to take the project from.',
            'tousername': 'The Username of the User to give the project to.'
            }
    )

    def put(self, project_id, fromusername, tousername):
        try:
            # Get the current user from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Check if the current user has the necessary permissions (e.g., project owner or admin)
            # Adjust the condition based on your specific requirements
            if not current_user.is_admin():
                return {'message': 'Unauthorized. You do not have permission to link users to projects.'}, HTTPStatus.FORBIDDEN

            # Get the project by ID
            project = ProjectsData.query.get(project_id)
            if not project:
                return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

            # Get the user by username
            fromuser = Users.query.filter_by(username=fromusername).first()
            touser = Users.query.filter_by(username=tousername).first()
            if not fromuser or not touser:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND
            
            if  not touser.is_active():
                return {'message': 'The user you are trying to assign to has been deactivated'}, HTTPStatus.BAD_REQUEST

            
            # Link the user to the project
            project_user = ProjectUser.query.filter_by(projectID=project_id, userID=fromuser.userID).first()
            project_user.userID = touser.userID
            project_user.save()

            return {'message': 'project has been reassigned successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error linking user to project: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        

@user_management_namespace.route('/takeover-all/from/<string:fromusername>/to/<string:tousername>')
class TakeoverResource(Resource):
    @jwt_required()
    @user_management_namespace.doc(
        description= 'When a user is deactivated, all resources must be given to another user.',
        params={
            'fromusername': 'The Username of the User to take all resources from.',
            'tousername': 'The Username of the User to give all resources to.'
            }
    )
    def put(self, fromusername, tousername):
        try:
            # Get the current user from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Check if the current user has the necessary permissions (e.g., project owner or admin)
            # Adjust the condition based on your specific requirements
            if not current_user.is_admin():
                return {'message': 'Unauthorized. You do not have permission to link users to projects.'}, HTTPStatus.FORBIDDEN
            
            # Get the user by username
            fromuser = Users.query.filter_by(username=fromusername).first()
            touser = Users.query.filter_by(username=tousername).first()
            if not fromuser or not touser:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND
            
            if not touser.is_active():
                return {'message': 'The user you are trying to assign to has been deactivated'}, HTTPStatus.BAD_REQUEST
            
            if fromuser.is_active():
                return {'message': 'The user you are trying to takeover from is active. You need to deactivate this user first.'}, HTTPStatus.BAD_REQUEST

            #find all the projects the deactivated user created,
            #and reassign them to the new user
            projects = ProjectsData.query.filter_by(userID=fromuser.userID).all()
            if projects:
                for project in projects:
                    project.userID = touser.userID
                    project.save()

            
            #find all the projects the deactivated user is responsible for,
            #and reassign them to the new user
            project_users = ProjectUser.query.filter_by( userID=fromuser.userID).all()
            if project_users:
                for project_user in project_users:
                    project_user.userID = touser.userID
                    project_user.save()
            
            cases = CasesData.query.filter_by(userID=fromuser.userID).all()
            if cases:
                for case in cases:
                    case.userID = touser.userID
                    case.save()

            
            #find all the case the deactivated user is responsible for,
            #and reassign them to the new user
            case_users = CaseUser.query.filter_by( userID=fromuser.userID).all()
            if case_users:
                for case_user in case_users:
                    case_user.userID = touser.userID
                    case_user.save()

            return {'message': 'Takeover successfull.'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error in performing takeover: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@user_management_namespace.route('/case-assign-user/<int:case_id>/<string:username>')
class AssignUserToCaseResource(Resource):
    @jwt_required()
    @user_management_namespace.doc(
        description= 'When a user is given access/responsibility to an existing case.',
        params={
            'case_id': 'The case to re-assign',
            'username': 'The Username of the User to give the case to.'
            }
    )
    def post(self, case_id, username):
        try:
            # Get the current user from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Check if the current user has the necessary permissions (e.g., case owner or admin)
            # Adjust the condition based on your specific requirements
            if not current_user.is_admin():
                return {'message': 'Unauthorized. You do not have permission to link users to cases.'}, HTTPStatus.FORBIDDEN

            # Get the case by ID
            case = CasesData.query.get(case_id)
            if not case:
                return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

            

            # Get the user by username
            user = Users.query.filter_by(username=username).first()
            print(f'user.is_active: {user.is_active()}')
            print(f'Type of user.is_active: {type(user.is_active())}')

            if not user: 
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND
            elif  not user.is_active():
                return {'message': 'User is deactivated'}, HTTPStatus.BAD_REQUEST
            

            # Check if the user is already linked to the case
            if CaseUser.query.filter_by(caseID=case_id, userID=user.userID).first():
                return {'message': 'User is already linked to the case'}, HTTPStatus.BAD_REQUEST

            # Link the user to the case
            case_user = CaseUser(caseID=case_id, userID=user.userID)
            case_user.save()

            return {'message': 'User linked to the case successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error linking user to case: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@user_management_namespace.route('/case-reassign-user/<int:case_id>/from/<string:fromusername>/to/<string:tousername>')
class ReassignUserToCaseResource(Resource):
    @jwt_required()
    @user_management_namespace.doc(
        description= 'If necessary a case needs to be given to another user.',
        params={
            'case_id': 'The case to re-assign',
            'fromusername': 'The Username of the User to take the case from.',
            'tousername': 'The Username of the User to give the case to.'
            }
    )

    def put(self, case_id, fromusername, tousername):
        try:
            # Get the current user from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Check if the current user has the necessary permissions (e.g., project owner or admin)
            # Adjust the condition based on your specific requirements
            if not current_user.is_admin():
                return {'message': 'Unauthorized. You do not have permission to link users to cases.'}, HTTPStatus.FORBIDDEN

            # Get the case by ID
            case = CasesData.query.get(case_id)
            if not case:
                return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

            # Get the user by username
            fromuser = Users.query.filter_by(username=fromusername).first()
            touser = Users.query.filter_by(username=tousername).first()
            if not fromuser or not touser:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND
            
            if  not touser.is_active():
                return {'message': 'The user you are trying to assign to has been deactivated'}, HTTPStatus.BAD_REQUEST

            
            # Link the user to the case
            case_user = CaseUser.query.filter_by(caseID=case_id, userID=fromuser.userID).first()
            case_user.userID = touser.userID
            case_user.save()

            return {'message': 'case has been reassigned successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error linking user to case: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        