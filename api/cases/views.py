from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required,get_jwt_identity
from ..models.cases import Cases
from ..models.users import Users
from http import HTTPStatus
from ..utils.db import db

case_namespace = Namespace("Cases", description="Namespace for cases")

case_model = case_namespace.model(
    'Case',{
        'id':fields.Integer(),
        'name':fields.String(required=True,description="A case name"),
        'budget_required':fields.Float(required=True,description="Budget required"),
        'category':fields.String(required=True, enum=['A','B','C','D'],description="Case category"),
        'status':fields.String(required=True,enum=['pending','approved','rejected'],description="Case status"),
    }
)

case_status_model = case_namespace.model(
    'CaseStatus',{
        'status':fields.String(required=True,description="Case status",
        enum=['pending','approved','rejected'])

    }
)

@case_namespace.route('/users/cases')
class GetCasesByCurrentUser(Resource):
    @case_namespace.marshal_list_with(case_model)
    @jwt_required()
    def get(self):
        """
        Get cases based on the current user's role and region
        """
        current_user_id = get_jwt_identity()

        # Get the current user from the database
        current_user = Users.query.get(current_user_id)

        if current_user.userRole == 'admin':
            # If the user is an admin, retrieve all cases
            all_cases = Cases.query.all()
        elif current_user.userRole == 'staff':
            # If the user is a staff member, retrieve cases only from their region
            all_cases = Cases.query.filter_by(regionID=current_user.regionID).all()
        else:
            return {'message': 'Invalid user role.'}, HTTPStatus.FORBIDDEN

        return all_cases, HTTPStatus.OK
    
    @case_namespace.expect(case_model)
    @case_namespace.marshal_with(case_model)
    @case_namespace.doc(description="Create a new case")
    @jwt_required()
    def post(self):
        """
        Create a new case
        """
        username = get_jwt_identity()
        current_user = Users.query.filter_by(username=username).first()
        data = case_namespace.payload

        # Check if the regionID is provided in the case data; use staff member's region if not
        region_id = data.get('regionID', current_user.regionID) if current_user.userRole == 'staff' else data.get('regionID', None)

        new_case = Cases(
            caseName=data['name'],
            budgetRequired=data['budget_required'],
            caseCategory=data['category'],
            caseStatus=data['status'],
            userID=current_user.userID,
            regionID=region_id  # Use the determined region ID
        )

        new_case.user = current_user
        new_case.save()

        return new_case, HTTPStatus.CREATED