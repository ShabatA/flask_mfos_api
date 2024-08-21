from api.config.config import Config
from flask_restx import Resource, Namespace
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus
from ..models.users import Users
from sqlalchemy import func

from api.models.cases import *
from api.models.projects import *

summary_ns = Namespace('Summary', description='Summary of cases and projects')

@summary_ns.route('/dashboard/projects_and_cases')
class ProjectsAndCases(Resource):
    @jwt_required()
    @summary_ns.doc('Get projects and cases count')
    def get(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            
            # Query to get the count of projects grouped by their status
            project_status_counts = db.session.query(
                ProjectsData.projectStatus, func.count(ProjectsData.projectID)
            ).group_by(ProjectsData.projectStatus).all()

            # Format the result as a dictionary
            project_result = {status.value: count for status, count in project_status_counts}
            
            # Query to get the total count of projects
            total_projects_count = db.session.query(func.count(ProjectsData.projectID)).scalar()
            
            # Add the total count to the result
            project_result['total'] = total_projects_count
            
            # Query to get the count of cases grouped by their status
            case_status_counts = db.session.query(
                CasesData.caseStatus, func.count(CasesData.caseID)
            ).group_by(CasesData.caseStatus).all()

            # Format the result as a dictionary
            case_result = {status.value: count for status, count in case_status_counts}
            
            # Query to get the total count of cases
            total_cases_count = db.session.query(func.count(ProjectsData.projectID)).scalar()
            
            # Add the total count to the result
            case_result['total'] = total_cases_count

            return {
                'projects': project_result,
                'cases': case_result
            }, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error fetching project and case status breakdown: {str(e)}")
            return {"message": f"Error fetching project and case status breakdown: {str(e)}"}, HTTPStatus.INTERNAL_SERVER_ERROR
        