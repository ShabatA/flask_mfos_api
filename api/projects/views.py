from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.projects import Projects
from http import HTTPStatus
from ..utils.db import db

project_namespace = Namespace('project', description="a namespace for project")

project_model = project_namespace.model(
    'Project', {
        'projectID': fields.Integer(),
        'projectName': fields.String(required=True, description="Project Name"),
        'regionID': fields.Integer(required=True, description="Region ID"),
        'budgetRequired': fields.Float(required=True, description="Budget Required"),
        'fieldName': fields.String(required=True, description="Field Name"),
    }
)

@project_namespace.route('/project')

class Project(Resource):
    pass
