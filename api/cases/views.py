from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from http import HTTPStatus
from ..models.cases import Cases, CaseStatus
from ..models.users import Users
from ..utils.db import db
from datetime import datetime
from flask import jsonify
from flask import request


case_namespace = Namespace("Cases", description="Namespace for cases")

case_model = case_namespace.model(
    'Case', {
        'caseID': fields.Integer(),
        'caseName': fields.String(required=True, description="A case name"),
        'budgetRequired': fields.Float(required=True, description="Budget required"),
        'budgetAvailable': fields.Float(required=True, description="Budget available"),
        'caseCategory': fields.String(description="Case category"),
        'caseStatus': fields.String(enum=[status.value for status in CaseStatus], description="Case status"),
        'regionID': fields.Integer(required=True, description="Region ID"),
        'userID': fields.Integer(required=True, description="User ID"),
        'createdAt': fields.DateTime(description="Date and time of creation"),
    }
)

case_model_2 = case_namespace.model(
    'Case2', {
        'caseName': fields.String(required=True, description="A case name"),
        'budgetRequired': fields.Float(required=True, description="Budget required"),
        'budgetAvailable': fields.Float(required=True, description="Budget available"),
        'caseCategory': fields.String(description="Case category"),
        'caseStatus': fields.String(enum=[status.value for status in CaseStatus], description="Case status"),
    })

@case_namespace.route('/users/cases')
class GetCasesByCurrentUser(Resource):
    @case_namespace.marshal_list_with(case_model)
    @jwt_required()
    def get(self):
        """
        Get cases based on the current user's role and region
        """
        all_cases = Cases.query.all()
        return all_cases, HTTPStatus.OK


    @case_namespace.expect(case_model)
    @case_namespace.marshal_with(case_model_2)
    # @case_namespace.doc(description="Create a new case")
    @jwt_required()
    def post(self):
        """
        Create a new case
        """
        username = get_jwt_identity()
        current_user = Users.query.filter_by(username=username).first()
        data = request.get_json()

        # Check if the regionID is provided in the case data; use staff member's region if not
        region_id = data.get('regionID', current_user.regionID)

        new_case = Cases(
            caseName=data.get('caseName'),
            budgetRequired=float(data.get('budgetRequired', 0.0)),
            budgetAvailable=float(data.get('budgetAvailable', 0.0)),
            caseCategory=data.get('caseCategory'),
            caseStatus=CaseStatus(data.get('caseStatus')),
            # user=current_user,
            userID=current_user.userID,
            regionID=region_id,
            createdAt=datetime.utcnow(),  # Set the creation time
        )
        # new_case.users = current_user

        new_case.save()

        return new_case, HTTPStatus.CREATED
