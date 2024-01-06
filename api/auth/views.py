from api.config.config import Config
from flask_restx import Resource, Namespace, fields
from flask import request, current_app
from ..models.users import Users, Role, UserPermissions, PermissionLevel
from werkzeug.security import generate_password_hash, check_password_hash
from http import HTTPStatus
from flask_jwt_extended import (create_access_token,
                                create_refresh_token, jwt_required, get_jwt_identity)
from werkzeug.exceptions import Conflict, BadRequest
from ..models.regions import Regions  # Import the Region model
from ..utils.db import db

auth_namespace = Namespace('auth', description="a namespace for authentication")

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
    }
)

user_model = auth_namespace.model(
    'Users', {
        'userID': fields.Integer(),
        'username': fields.String(required=True, description="A username"),
        'email': fields.String(required=True, description="An email"),
        'password': fields.String(required=True, description="A password"),
        'active': fields.Boolean(description="This shows that User is active", default=True),
        'UserStatus': fields.String(description="This shows of staff status"),
        'regionID': fields.Integer(description="Region ID"),  # Added regionID field
        'regionName': fields.String(description="Region Name"),  # Added regionName field
        'RoleName': fields.String(required=True, description="Role Name"),  # Added roleName
        'permissionNames': fields.List(fields.String, required=True, description="List of permission names"),

    }
)


user2_model = auth_namespace.model(
    'Users', {
        'userID': fields.Integer(),
        'username': fields.String(required=True, description="A username"),
        'email': fields.String(required=True, description="An email"),
        'password': fields.String(required=True, description="A password"),
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
                role=role  # Set the user's role
            )
            # new_user.save()

            new_user.assign_role_and_permissions(role_name, permission_names)

            new_user.save()

            # Save all UserPermissions entries
            # for user_permission in user_permissions:
            #     user_permission.save()

            # db.session.add(new_user)
            # db.session.commit()

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
            access_token = create_access_token(identity=user.username)
            refresh_token = create_refresh_token(identity=user.username)

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

        access_token = create_access_token(identity=username)

        return {'access_token': access_token}, HTTPStatus.OK


@auth_namespace.route('/admin-only')
class AdminOnlyResource(Resource):

    @jwt_required()
    @auth_namespace.doc(
        description="Access only for admins",
    )
    def get(self):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        if current_user.is_admin():
            return {'message': 'Welcome, Admin!'}, HTTPStatus.FORBIDDEN

        return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.OK

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


@auth_namespace.route('/admin/remove-user/<int:user_id>')
class RemoveUserByAdmin(Resource):

    @jwt_required()
    @auth_namespace.doc(
        description="Remove a user",
        params={'user_id': 'Specify the user ID'}
    )
    def delete(self, user_id):
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin():
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        user_to_remove = Users.get_by_id(user_id)
        if user_to_remove:
            # Check if the current admin is trying to remove their own account
            if current_admin.userID == user_to_remove.userID:
                return {'message': 'Admin cannot remove their own account.'}, HTTPStatus.FORBIDDEN

            # Remove the user
            user_to_remove.delete()
            return {'message': 'User removed successfully.'}, HTTPStatus.OK
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
            for user in all_users:
                user_data = {
                    'userID': user.userID,
                    'username': user.username,
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
                    'permissions': [permission.permission_level.value for permission in user.permissions]
                }
                users_data.append(user_data)

            # Return the user data as JSON
            return {'users': users_data}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting all users: {str(e)}")
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


# function to return users
        # username
        # email
        # password
        #

# function current user info
        # username
        # email
        # password
        # region
        # role
        # permissions

        