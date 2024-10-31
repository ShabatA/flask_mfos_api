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
            total_cases_count = db.session.query(func.count(CasesData.caseID)).scalar()
            
            # Add the total count to the result
            case_result['total'] = total_cases_count

            # Query to get the count of activities grouped by their status
            activity_status_counts = db.session.query(
                Activities.activityStatus, func.count(Activities.activityID)
            ).group_by(Activities.activityStatus).all()

            # Format the result as a dictionary
            activity_result = {status.value: count for status, count in activity_status_counts}
            
            
            # Query to get the count of programs grouped by active status
            program_status_counts = db.session.query(
                ProjectsData.active, func.count(ProjectsData.projectID)
            ).filter(ProjectsData.project_type == ProType.PROGRAM).group_by(ProjectsData.active).all()

            # Format the result for active/inactive programs
            program_result = {
                "active": sum(count for active, count in program_status_counts if active),
                "inactive": sum(count for active, count in program_status_counts if not active)
            }
            return {
                'projects': project_result,
                'cases': case_result,
                'total_activities': activity_result,
                'total_programs': program_result
            }, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error fetching project and case status breakdown: {str(e)}")
            return {"message": f"Error fetching project and case status breakdown: {str(e)}"}, HTTPStatus.INTERNAL_SERVER_ERROR

@summary_ns.route("/get_all_tasks/current_user", methods=["GET"])
class GetAllAssignedTasksResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Get the current user from the JWT token
            user = Users.query.filter_by(username=get_jwt_identity()).first()
            
            # Fetch all ProjectTasks and CaseTasks assigned to the user
            project_tasks = (
                ProjectTask.query.join(Users.assigned_tasks)
                .filter(Users.userID == user.userID)
                .all()
            )
            case_tasks = (
                CaseTask.query.join(Users.case_assigned_tasks)
                .filter(Users.userID == user.userID)
                .all()
            )

            # Project Tasks summary counts
            total_p_tasks = len(project_tasks)
            completed_p_tasks = sum(1 for task in project_tasks if task.status == TaskStatus.DONE)
            overdue_p_tasks = sum(1 for task in project_tasks if task.status == TaskStatus.OVERDUE)
            inprogress_p_tasks = sum(1 for task in project_tasks if task.status == TaskStatus.INPROGRESS)
            not_started_p_tasks = sum(1 for task in project_tasks if task.status == TaskStatus.TODO)

            # Case Tasks summary counts
            total_c_tasks = len(case_tasks)
            completed_c_tasks = sum(1 for task in case_tasks if task.status == CaseTaskStatus.DONE)
            overdue_c_tasks = sum(1 for task in case_tasks if task.status == CaseTaskStatus.OVERDUE)
            inprogress_c_tasks = sum(1 for task in case_tasks if task.status == CaseTaskStatus.INPROGRESS)
            not_started_c_tasks = sum(1 for task in case_tasks if task.status == CaseTaskStatus.TODO)

            # Format project and case tasks details
            all_tasks = {
                "project_tasks": [
                    {
                        "taskID": task.taskID,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status.value,
                        "checklist": task.checklist,
                        "stageName": task.stage.name if task.stage else None,
                        "projectName": ProjectsData.query.get(task.projectID).projectName,
                        "startDate": task.startDate.strftime("%Y-%m-%d") if task.startDate else None,
                        "deadline": task.deadline.strftime("%Y-%m-%d") if task.deadline else None,
                        "completionDate": task.completionDate.isoformat() if task.completionDate else None,
                    }
                    for task in project_tasks
                ],
                "case_tasks": [
                    {
                        "taskID": task.taskID,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status.value,
                        "checklist": task.checklist,
                        "stageName": task.stage.name if task.stage else None,
                        "caseName": CasesData.query.get(task.caseID).caseName,
                        "completionDate": task.completionDate.isoformat() if task.completionDate else None,
                    }
                    for task in case_tasks
                ],
                "summary": {
                    "project_tasks_summary": {
                        "total_p_tasks": total_p_tasks,
                        "completed_p_tasks": completed_p_tasks,
                        "overdue_p_tasks": overdue_p_tasks,
                        "not_started_p_tasks": not_started_p_tasks,
                        "inprogress_p_tasks": inprogress_p_tasks,
                    },
                    "case_task_summary": {
                        "total_c_tasks": total_c_tasks,
                        "completed_c_tasks": completed_c_tasks,
                        "overdue_c_tasks": overdue_c_tasks,
                        "not_started_c_tasks": not_started_c_tasks,
                        "inprogress_c_tasks": inprogress_c_tasks,
                    },
                },
            }

            return all_tasks, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting all assigned tasks: {str(e)}")
            return {"message": "Internal Server Error"}, HTTPStatus.INTERNAL_SERVER_ERROR
