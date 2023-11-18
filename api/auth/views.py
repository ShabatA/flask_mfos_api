from api.config.config import Config
from flask_restx import Resource, Namespace, fields
from flask import request
from ..models.users import Users, UserRole, UserStatus
from werkzeug.security import generate_password_hash, check_password_hash
from http import HTTPStatus
from flask_jwt_extended import (create_access_token,
                                create_refresh_token, jwt_required, get_jwt_identity)
from werkzeug.exceptions import Conflict, BadRequest
from ..models.regions import Regions  # Import the Region model

auth_namespace = Namespace('auth', description="a namespace for authentication")

signup_model = auth_namespace.model(
    'SignUp', {
        'userID': fields.Integer(),
        'username': fields.String(required=True, description="A username"),
        'firstName': fields.String(required=True, description="A first name"),
        'lastName': fields.String(required=True, description="A last name"),
        'email': fields.String(required=True, description="An email"),
        'password': fields.String(required=True, description="A password"),
        'regionName': fields.String(required=True, description="Region Name"),  # Changed to regionName
        'userRole': fields.String(enum=[role.value for role in UserRole] ,required=True, description="User Role"),
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
        'userRole': fields.String(enum=[role.value for role in UserRole], required=True, description="User Role"),
    }
)

login_model = auth_namespace.model(
    'Login', {
        'email': fields.String(required=True, description="An email"),
        'password': fields.String(required=True, description="A password")
    }
)


@auth_namespace.route('/signup')
class SignUp(Resource):

    @auth_namespace.expect(signup_model)
    @auth_namespace.marshal_with(user_model)
    def post(self):
        """
            Create a new user account 
        """

        data = request.get_json()

        try:
            region_name = data.get('regionName')
            region = Regions.query.filter_by(regionName=region_name).first()

            if not region:
                raise BadRequest(f"Region with name {region_name} not found")

            new_user = Users(
                username=data.get('username'),
                email=data.get('email'),
                password=generate_password_hash(data.get('password')),
                regionID=region.regionID,
                userRole=UserRole(data.get('userRole'))
            )

            new_user.save()

            return new_user, HTTPStatus.CREATED

        except Exception as e:
            raise Conflict(f"User with email {data.get('email')} exists")


@auth_namespace.route('/login')
class Login(Resource):

    @auth_namespace.expect(login_model)
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
    def post(self):
        username = get_jwt_identity()

        access_token = create_access_token(identity=username)

        return {'access_token': access_token}, HTTPStatus.OK


@auth_namespace.route('/admin-only')
class AdminOnlyResource(Resource):

    @jwt_required()
    def get(self):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        if current_user.userRole != UserRole.ADMIN:
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        return {'message': 'Welcome, Admin!'}, HTTPStatus.OK

@auth_namespace.route('/admin/update-user/<int:user_id>')
class UpdateUserByAdmin(Resource):
    @auth_namespace.expect(user_model)
    @auth_namespace.marshal_with(user_model)
    @jwt_required()
    def put(self, user_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        if current_user.userRole != UserRole.ADMIN:
            return {'message': 'Access forbidden. Admins only.'}, HTTPStatus.FORBIDDEN

        user_to_update = Users.get_by_id(user_id)
        if user_to_update:
            # Update user fields here
            data = request.get_json()
            # Update only the fields that are present in the request
            if 'username' in data:
                user_to_update.username = data['username']
            if 'email' in data:
                user_to_update.email = data['email']
            if 'password' in data:
                user_to_update.password = generate_password_hash(data['password'])
            if 'active' in data:
                user_to_update.active = data['active']
            if 'UserStatus' in data:
                user_to_update.UserStatus = UserStatus(data['UserStatus'])
            if 'regionID' in data:
                user_to_update.regionID = data['regionID']
            if 'userRole' in data:
                user_to_update.userRole = UserRole(data['userRole'])


            user_to_update.save()
            return user_to_update, HTTPStatus.OK
        else:
            return {'message': 'User not found.'}, HTTPStatus.NOT_FOUND

@auth_namespace.route('/admin/remove-user/<int:user_id>')
class RemoveUserByAdmin(Resource):

    @jwt_required()
    def delete(self, user_id):
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if current_admin.userRole != UserRole.ADMIN:
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