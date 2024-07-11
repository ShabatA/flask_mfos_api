from flask import request, current_app
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus

from sqlalchemy import desc
from api.models.accountfields import AccountFields
from api.models.finances import ProjectFunds, RegionAccount
from api.models.regions import Regions
from api.utils.project_category_calculator import ProjectCategoryCalculator

from api.utils.project_requirement_processor import ProjectRequirementProcessor
from ..models.projects import *
from ..utils.db import db
from ..models.users import Users
from flask import jsonify
from datetime import datetime, date



project_namespace = Namespace('Projects', description="A namespace for Projects")
stage_namespace = Namespace('Project Stages', description="A namespace for Project Stages")
task_namespace = Namespace('Project Tasks', description="A namespace for Project Tasks")
assessment_namespace = Namespace('Project Assessment', description="A namespace for Project Assessment")

requirements_namespace = Namespace('Requirements', description="A namespace for requirements. These will be universal for both Case and Project Approval")

activity_namespace = Namespace('Activities', description='A namespace for stand-alone activities and activities linked to programs')

stage_model = stage_namespace.model(
    'Stage', {
        'name': fields.String(required=True, description='Name of the stage'),
    }
)

requirements_model = requirements_namespace.model('Requirement', {
    'name': fields.String(required=True, description= 'The name of the requirement.'),
    'description': fields.String(required=True, description='Short details to give an idea of what the underlying task will be.'),
    'section': fields.String(enum=['FINANCIAL', 'IMPLEMENTATION', 'MEDIA'], description='The section these requirements belong to.')
})

answers_model = project_namespace.model('Answers', {
    'questionID': fields.Integer(required=True, description='ID of the answer'),
    'answerText': fields.String(description='Text-based answer for a text question'),
    'choiceID': fields.List(fields.Integer, description='List of choices')
})

comments_model = task_namespace.model('TaskComments',{
    'taskID': fields.Integer(required=True, description='Id of the task the comment belongs to'),
    'comment': fields.String(required=True, description= 'The comment written by the user'),
    'date': fields.Date(required=True, description='Date on which the comment was made')
})

edit_comments_model = task_namespace.model('EditTaskComments',{
    'commentID': fields.Integer(required=True, description='Id of the comment'),
    'newComment': fields.String(required=True, description= 'The comment written by the user')
})

assessment_question_model = assessment_namespace.model('AssessmentQuestion', {
    'questionText': fields.String(required=True, description='The actual question to be asked.')
})

assessment_answer_model = assessment_namespace.model('AssessmentAnswer', {
    'questionID': fields.Integer(required=True, description='The ID of the question'),
    'answerText': fields.String(required=True, description='The answer provided'),
    'notes': fields.String( description='The extra notes if needed')
})

assessment_model = assessment_namespace.model('ProjectAssessment', {
    'projectID': fields.Integer(required=True, description='The ID of the project this assessment is for'),
    'answers': fields.List(fields.Nested(assessment_answer_model), description='List of answers for the assessment')
})

checklist_model = task_namespace.model('CheckListItem', {
    'item': fields.String(required=True, description='The checklist item name/description'),
    'checked': fields.Boolean(required=True, description='Whether this is checked out or not')
})

activity_model = activity_namespace.model('ActivityInput',{
    'activityName': fields.String(required=True),
    'regionID': fields.Integer(required=True),
    'programID': fields.Integer(required=False),
    'description': fields.String(required=True),
    'costRequired': fields.Float(required=True),
    'duration': fields.String(required=True),
    'deadline': fields.Date(required=True),
    'assignedTo': fields.List(fields.Integer, description='List of user IDs assigned to the activity'),
})

activity_stat = activity_namespace.model('ActivityStatusData',{
    'data': fields.Raw(required=True),
    'status': fields.String(enum=[stat.value for stat in ActStatus], required=True)
})


# Define a model for the input data (assuming JSON format)
new_task_model = task_namespace.model('NewTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    'attached_files': fields.String(description='File attachments for the task'),
    'checklist': fields.List(fields.Nested(checklist_model),description='optional checklist'),
    'startDate': fields.Date(required=True, description='start date of the task (YYYY-MM-DD)')
})


assign_task = task_namespace.model('AssignTask', {
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task') 
})

edit_task_model = task_namespace.model('EditTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    'attached_files': fields.String(description='File attachments for the task'),
    'checklist': fields.List(fields.Nested(checklist_model),description='optional checklist'),
    'startDate': fields.Date(required=True, description='start date of the task (YYYY-MM-DD)')
})

# Define the expected input model using Flask-RESTx fields
project_input_model = project_namespace.model('ProjectInput', {
    'projectName': fields.String(required=True, description='Name of the project'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the project'),
    'projectScope': fields.String(description='Scope of the project'),
    'category': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the project'),
    'userID': fields.Integer(description='ID of the user associated with the project'),
    'answers': fields.List(fields.Nested(answers_model), description='List of answers for the project')
})

projects_data_model = project_namespace.model('ProjectsDataInput', {
    'projectName': fields.String(required=True, description='Name of the project'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'createdBy': fields.Integer(description='ID of the user associated with the project'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the project'),
    'projectScope': fields.Integer(description='Scope of the project'),
    'projectIdea': fields.String(description='Idea and justification of the project'),
    'solution': fields.String(description='Solution provided by the project'),
    'addedValue': fields.String(description='Added value of the project'),
    'projectNature': fields.Integer(description='Nature of the project'),
    'beneficiaryCategory': fields.Integer(description='Beneficiary category of the project'),
    'commitment': fields.Integer(description='Is there a commitment from external party'),
    'commitmentType': fields.Integer(description='Commitment type'),
    'supportingOrg': fields.String(description='Details of the supporting organization'),
    'documents': fields.List(fields.String, description='List the document types'),
    'recommendationLetter': fields.Integer(description='Is there a recomemendation letter'),
    'projectType': fields.String(enum=[type.value for type in ProType],required=True,description='Project or Program')
})

project_update_status_model = project_namespace.model('ProjectUpdateStatus', {
    'projectStatus': fields.String(required=True, enum=['approved', 'pending','rejected'], description='Status of the project'),
    'status_data': fields.Raw(description='Status data associated with the project'),
})

project_input_model2 = project_namespace.model('ProjectInput2', {
    
    'status_data': fields.Raw(description='Status data associated with the project'),
})

project_status = project_namespace.model('ProjectStatus',{
    'projectStatus': fields.String(required=True, enum=['approved', 'pending','rejected'], description='Status of the project'),
})

edited_answers_model = project_namespace.model('EditedAnswers', {
    'questionID': fields.Integer(required=True, description='ID of the question'),
    'answerText': fields.String(description='Text-based answer for a text question'),
    'choiceID': fields.List(fields.Integer, description='List of choices')
})

edit_choice = project_namespace.model(
    'EditChoice', {
        'new_choice_text': fields.String(required=True, description='New choice text'),
        'points': fields.Integer(required=True, description='New points')
    }
)

edit_choice_with_choice_id = project_namespace.model('EditChoiceWithChoiceID', {
    'choiceID': fields.Integer(description='ID of the added choice')
})

project_edit_model = project_namespace.model('ProjectEdit', {
    'edited_answers': fields.List(fields.Nested(edited_answers_model), description='List of edited answers for the project')
})

project_edit_details_model = project_namespace.model('ProjectEditDetails', {
    'projectName': fields.String(required=True, description='Name of the project'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the project'),
    'projectStatus': fields.String(required=True, enum=['approved', 'pending','rejected'], description='Status of the project'),
    'projectScope': fields.String(description='Scope of the project'),
    'category': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the project'),
    'startDate': fields.Date(description='Start date of the project'),
    'dueDate': fields.Date(description='Due date of the project')
}
)


question_input_model = project_namespace.model('QuestionInput', {
    'questionText': fields.String(required=True, description='Text of the question'),
    'questionType': fields.String(required=True, description='Type of the question'),
    'points': fields.Integer(required=True, description='Points for the question'),
    'choices': fields.List(fields.String, description='List of choices for multiple-choice questions')
})

# Define a model for the input data (assuming JSON format)
link_project_to_stage_model = stage_namespace.model('LinkProjectToStageModel', {
    'project_id': fields.Integer(required=True, description='ID of the project'),
    'stage_id': fields.Integer(required=True, description='ID of the stage'),
    'started': fields.Boolean(required=True, description="If the stages started"),
    'completed': fields.Boolean(required=True, description="If the stages completed"),
    'completionDate': fields.Date(description="Completion Date")
})

regions_data_model = project_namespace.model('RegionData', {
    'regionID': fields.Integer(description='ID of the region'),
    'regionName': fields.String(description='Name of the region')
})

users_data_model = project_namespace.model('UserData', {
    'userID': fields.Integer(description='ID of the user'),
    'userFullName': fields.String(description='Full name of the user'),
    'username': fields.String(description='Username of the user')
})

projects_result_model = project_namespace.model('ProjectsData', {
    'projectID': fields.Integer(description='ID of the project'),
    'projectName': fields.String(description='Name of the project'),
    'region': fields.Nested(regions_data_model, description='Details of the region'),
    'user': fields.Nested(users_data_model, description='Details of the user'),
    'budgetRequired': fields.Float(description='Required budget for the project'),
    'budgetApproved': fields.Float(description='Approved budget for the project'),
    'projectStatus': fields.String(description='Status of the project'),
    'projectScope': fields.Integer(description='Scope of the project'),
    'projectIdea': fields.String(description='Idea and justification of the project'),
    'solution': fields.String(description='Solution provided by the project'),
    'category': fields.String(description='The category'),
    'addedValue': fields.String(description='Added value of the project'),
    'projectNature': fields.Integer(description='Nature of the project'),
    'beneficiaryCategory': fields.Integer(description='Beneficiary category of the project'),
    'commitment': fields.Integer(description='Is there a commitment from external party'),
    'commitmentType': fields.Integer(description='Commitment type'),
    'supportingOrg': fields.String(description='Details of the supporting organization'),
    'documents': fields.List(fields.Integer, description='List the document Ids'),
    'recommendationLetter': fields.Integer(description='Is there a recommendation letter'),
    'createdAt': fields.DateTime(description='Creation date of the project'),
    'dueDate': fields.Date(description='Due date of the project')
})


@project_namespace.route('/add_or_edit', methods=['POST','PUT'])
class ProjectAddResource(Resource):
    @jwt_required()  
    @project_namespace.expect(projects_data_model)
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Parse the input data
        project_data = request.json
         

        # Check if a project with the given name already exists
        existing_project = ProjectsData.query.filter_by(projectName=project_data['projectName']).first()
        if existing_project:
            return {'message': 'Project with this name already exists'}, HTTPStatus.CONFLICT

        # Create a new project instance
        new_project = ProjectsData(
            projectName=project_data['projectName'],
            regionID=project_data['regionID'],
            createdBy=current_user.userID,
            budgetRequired=project_data['budgetRequired'],
            budgetApproved=project_data.get('budgetApproved', 0),
            projectStatus=Status.ASSESSMENT,
            projectScope=project_data.get('projectScope'),
            projectIdea=project_data.get('projectIdea'),
            solution=project_data.get('solution'),
            addedValue=project_data.get('addedValue'),
            projectNature=project_data.get('projectNature'),
            beneficiaryCategory=project_data.get('beneficiaryCategory'),
            commitment=project_data.get('commitment'),
            commitmentType=project_data.get('commitmentType'),
            supportingOrg=project_data.get('supportingOrg'),
            documents=project_data.get('documents', []),
            recommendationLetter=project_data.get('recommendationLetter'),
            createdAt=datetime.utcnow(),
            project_type = project_data['projectType']
        )

        # Save the project to the database
        try:
            new_project.save()

            # Add the current user to the ProjectUsers table for the new project
            project_user = ProjectUser(projectID=new_project.projectID, userID=current_user.userID)
            project_user.save()

            return {'message': 'Project added successfully',
                    'project_id': new_project.projectID}, HTTPStatus.CREATED
        except Exception as e:
            current_app.logger.error(f"Error adding requirements: {str(e)}")
            return {'message': f'Error adding project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    @jwt_required()
    @project_namespace.expect(projects_data_model)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            project_data = request.json

            project_id = project_data.get('projectID')
            if not project_id:
                return {'message': 'Project ID is required for updating a project'}, HTTPStatus.BAD_REQUEST

            existing_project = ProjectsData.query.get_or_404(project_id)

            # Update the project fields
            existing_project.projectName = project_data['projectName']
            existing_project.regionID = project_data['regionID']
            existing_project.createdBy = current_user.userID
            existing_project.budgetRequired = project_data['budgetRequired']
            existing_project.budgetApproved = project_data.get('budgetApproved', 0)
            existing_project.projectScope = project_data.get('projectScope')
            existing_project.projectIdea = project_data.get('projectIdea')
            existing_project.solution = project_data.get('solution')
            existing_project.addedValue = project_data.get('addedValue')
            existing_project.projectNature = project_data.get('projectNature')
            existing_project.beneficiaryCategory = project_data.get('beneficiaryCategory')
            existing_project.commitment = project_data.get('commitment')
            existing_project.commitmentType = project_data.get('commitmentType')
            existing_project.supportingOrg = project_data.get('supportingOrg')
            existing_project.documents = project_data.get('documents', [])
            existing_project.recommendationLetter = project_data.get('recommendationLetter')
            existing_project.project_type = project_data.get('projectType', existing_project.project_type)
            existing_project.active = project_data.get('active', existing_project.active)

            existing_project.save()

            return {'message': 'Project updated successfully',
                    'project_id': existing_project.projectID}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating project: {str(e)}")
            return {'message': f'Error updating project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/get_all', methods=['GET'])
class ProjectGetAllResource(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            if not current_user.is_admin():
                # Fetch all projects the user has access to
                projects = (
                    ProjectsData.query.join(Users, Users.userID == ProjectsData.createdBy)
                    .filter(Users.userID == current_user.userID)
                    .all()
                )

                # Fetch all projects associated with the user through ProjectUser
                project_user_projects = (
                    ProjectsData.query.join(ProjectUser, ProjectsData.projectID == ProjectUser.projectID)
                    .filter(ProjectUser.userID == current_user.userID)
                    .all()
                )
            
                # Combine the projects and remove duplicates
                all_projects = list(set(projects + project_user_projects))
            else:
                all_projects = ProjectsData.query.all()
                
            # Check if all_cases is empty
            if not all_projects:
                return [], HTTPStatus.OK  # Return an empty list    
            
            # Prepare the list of projects with additional details
            projects_data = []
            for project in all_projects:
                region_details = {'regionID': project.regionID, 'regionName': Regions.query.get(project.regionID).regionName}
                user = Users.query.get(project.createdBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                
                users_assigned_to_project = (
                    Users.query.join(ProjectUser, Users.userID == ProjectUser.userID)
                    .filter(ProjectUser.projectID == project.projectID)
                    .all()
                )

                project_details = {
                    'projectID': project.projectID,
                    'projectName': project.projectName,
                    'region': region_details,
                    'user': user_details,
                    'budgetRequired': project.budgetRequired,
                    'budgetApproved': project.budgetApproved,
                    'projectStatus': 'Assessment' if project.projectStatus == Status.ASSESSMENT else project.projectStatus.value,
                    'category': project.category.value if project.category else None,
                    'projectScope': project.projectScope,
                    'projectIdea': project.projectIdea,
                    'solution': project.solution,
                    'addedValue': project.addedValue,
                    'projectNature': project.projectNature,
                    'beneficiaryCategory': project.beneficiaryCategory,
                    'commitment': project.commitment,
                    'commitmentType': project.commitmentType,
                    'supportingOrg': project.supportingOrg,
                    'documents': project.documents,
                    'recommendationLetter': project.recommendationLetter,
                    'createdAt': project.createdAt.isoformat(),
                    'dueDate': project.dueDate.isoformat() if project.dueDate else None,
                    'startDate': project.startDate.isoformat() if project.startDate else None,
                    'totalPoints': project.totalPoints,
                    'projectType': project.project_type.value,
                    'assignedUsers': [user.userID for user in users_assigned_to_project] if users_assigned_to_project else [],
                    "active": project.active
                }

                projects_data.append(project_details)

            return projects_data, HTTPStatus.OK
        except Exception as e:
            return {'message': f'Error fetching projects: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/get_all_approved_only', methods=['GET'])
class ProjectGetAllApprovedResource(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            if not current_user.is_admin():
                # Fetch all projects the user has access to
                projects = (
                    ProjectsData.query.join(Users, Users.userID == ProjectsData.createdBy)
                    .filter(Users.userID == current_user.userID, ProjectsData.projectStatus == Status.APPROVED)
                    .all()
                )

                # Fetch all projects associated with the user through ProjectUser
                project_user_projects = (
                    ProjectsData.query.join(ProjectUser, ProjectsData.projectID == ProjectUser.projectID)
                    .filter(ProjectUser.userID == current_user.userID, ProjectsData.projectStatus == Status.APPROVED)
                    .all()
                )
            
                # Combine the projects and remove duplicates
                all_projects = list(set(projects + project_user_projects))
            else:
                all_projects = ProjectsData.query.all()
                
            # Check if all_cases is empty
            if not all_projects:
                return [], HTTPStatus.OK  # Return an empty list    
            
            # Prepare the list of projects with additional details
            projects_data = []
            for project in all_projects:
                region_details = {'regionID': project.regionID, 'regionName': Regions.query.get(project.regionID).regionName}
                user = Users.query.get(project.createdBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                
                users_assigned_to_project = (
                    Users.query.join(ProjectUser, Users.userID == ProjectUser.userID)
                    .filter(ProjectUser.projectID == project.projectID)
                    .all()
                )
                
                stages = ProjectStage.query.filter_by(projectID=project.projectID).all()
                stages_data = []
                for stage in stages:
                    # Fetch all tasks for the linked stage
                    tasks = ProjectTask.query.filter_by(projectID=project.projectID, stageID=stage.stageID).all()
                    total_tasks = len(tasks)
                    completed_tasks = 0
                    inprogress_tasks = 0
                    overdue_tasks = 0
                    not_started_tasks = 0
                    completionPercent = 0
                    if total_tasks > 0:

                        total_tasks = len(tasks)
                        for task in tasks:
                            if task.status == TaskStatus.DONE:
                                completed_tasks += 1
                            if task.status == TaskStatus.OVERDUE:
                                overdue_tasks += 1
                            if task.status == TaskStatus.INPROGRESS:
                                inprogress_tasks += 1
                            if task.status == TaskStatus.TODO:
                                not_started_tasks += 1
                        completionPercent = (completed_tasks/total_tasks) * 100
                    stage_details = {'stageID': stage.stage.stageID, 'name': stage.stage.name,
                                   'started': stage.started, 'completed': stage.completed,
                                   'completionDate': stage.completionDate.isoformat() if stage.completionDate else None,
                                   'totalTasks': total_tasks, 'completedTasks': completed_tasks, 'completionPercent': completionPercent,
                                   'notStartedTasks': not_started_tasks, 'overdueTasks': overdue_tasks, 'inprogressTasks': inprogress_tasks}
                    stages_data.append(stage_details)

                project_details = {
                    'projectID': project.projectID,
                    'projectName': project.projectName,
                    'region': region_details,
                    'user': user_details,
                    'budgetRequired': project.budgetRequired,
                    'budgetApproved': project.budgetApproved,
                    'projectStatus': 'Assessment' if project.projectStatus == Status.ASSESSMENT else project.projectStatus.value,
                    'category': project.category.value if project.category else None,
                    'projectScope': project.projectScope,
                    'projectIdea': project.projectIdea,
                    'solution': project.solution,
                    'addedValue': project.addedValue,
                    'projectNature': project.projectNature,
                    'beneficiaryCategory': project.beneficiaryCategory,
                    'commitment': project.commitment,
                    'commitmentType': project.commitmentType,
                    'supportingOrg': project.supportingOrg,
                    'documents': project.documents,
                    'recommendationLetter': project.recommendationLetter,
                    'createdAt': project.createdAt.isoformat(),
                    'dueDate': project.dueDate.isoformat() if project.dueDate else None,
                    'startDate': project.startDate.isoformat() if project.startDate else None,
                    'totalPoints': project.totalPoints,
                    'projectType': project.project_type.value,
                    'assignedUsers': [user.userID for user in users_assigned_to_project] if users_assigned_to_project else [],
                    'stages_data': stages_data,
                    "active": project.active
                }

                projects_data.append(project_details)

            return projects_data, HTTPStatus.OK
        except Exception as e:
            return {'message': f'Error fetching projects: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/add/requirements/<int:project_id>')
class ProjectAddRequirementsResource(Resource):
    @jwt_required()
    @project_namespace.expect(project_input_model2)
    def post(self, project_id):
        try:
            
            # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            
            if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
                return {'message': 'Unauthorized. Only admin users can add requirements.'}, HTTPStatus.FORBIDDEN
            
            project = ProjectsData.get_by_id(project_id)
            # Parse the input data
            project_data = request.json
            status_data = project_data.pop('status_data', {})  # Assuming status_data is part of the input
            
            # Assign status data to the project
            project.assign_status_data(status_data)
            
            # Instead of popping the 'predefined_req', just access it directly
            requirementsList = status_data.get('predefined_req', [])
    
            processor = ProjectRequirementProcessor(project, current_user.userID)
            #call the corresponding function to handle making a Task for that requirement
            for value in requirementsList:
                function_name = f"requirement_{value}"
                case_function = getattr(processor, function_name, processor.default_case)
                case_function()
            
            approvedAmount = status_data.get('approvedAmount')
            scope = status_data.get('projectScope')

            region_account = RegionAccount.query.filter_by(regionID=project.regionID).first()
            if approvedAmount and region_account and scope:
                project_fund = ProjectFunds(
                    accountID = region_account.accountID,
                    fundsAllocated = approvedAmount,
                    projectID = project.projectID  
                )
                project_fund.save()
                
            return {'message': 'Project requirements added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding project requirements: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/deactivate_program/<int:program_id>')
class DeactivateProgramResource(Resource):
    @jwt_required()
    def put(self, program_id):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
                return {'message': 'Unauthorized. Only admin users can convert programs.'}, HTTPStatus.FORBIDDEN
            
            program = ProjectsData.get_by_id(program_id)
            if(program.project_type != ProType.PROGRAM):
                return {'message': 'Denied. This is not a program. projects cannot be deactivated.'}, HTTPStatus.BAD_REQUEST
            
            program.active = False
            program.save()
            return {'message': 'Program deactivated successfully.'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error converting project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/activate_program/<int:program_id>')
class ActivateProgramResource(Resource):
    @jwt_required()
    def put(self, program_id):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
                return {'message': 'Unauthorized. Only admin users can convert programs.'}, HTTPStatus.FORBIDDEN
            
            program = ProjectsData.get_by_id(program_id)
            if(program.project_type != ProType.PROGRAM):
                return {'message': 'Denied. This is not a program. projects cannot be reactivated.'}, HTTPStatus.BAD_REQUEST
            
            program.active = True
            program.save()
            return {'message': 'Program activated successfully.'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error converting project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        

@project_namespace.route('/convert_to_program/<int:project_id>')
class ProjectConverToProgramResource(Resource):
    @jwt_required()
    @project_namespace.expect(project_input_model2)
    def post(self, project_id):
        try:
            
            # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            
            if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
                return {'message': 'Unauthorized. Only admin users can convert projects.'}, HTTPStatus.FORBIDDEN
            
            project = ProjectsData.get_by_id(project_id)
            if(project.project_type != ProType.PROJECT):
                return {'message': 'Denied. The Project is already a program.'}, HTTPStatus.BAD_REQUEST
            # Parse the input data
            project_data = request.json
            status_data = project_data.pop('status_data', {})  # Assuming status_data is part of the input
            
            project.project_type = ProType.PROGRAM
            # Assign status data to the project
            project.assign_status_data(status_data)
            
            # Instead of popping the 'predefined_req', just access it directly
            requirementsList = status_data.get('predefined_req', [])
    
            processor = ProjectRequirementProcessor(project.projectID, current_user.userID)
            #call the corresponding function to handle making a Task for that requirement
            for value in requirementsList:
                function_name = f"requirement_{value}"
                case_function = getattr(processor, function_name, processor.default_case)
                case_function()
            
            approvedAmount = status_data.get('approvedAmount')
            scope = status_data.get('projectScope')

            region_account = RegionAccount.query.filter_by(regionID=project.regionID).first()
            if approvedAmount and region_account and scope:
                project_fund = ProjectFunds(
                    accountID = region_account.accountID,
                    fundsAllocated = approvedAmount,
                    projectID = project.projectID  
                )
                project_fund.save()
                
            return {'message': 'Project converted successfully.'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error converting project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/get/requirements/<int:project_id>')
class ProjectRequirementResource(Resource):
   
    @jwt_required()
    def get(self, project_id):
        try:
            # Retrieve JSONB data based on project ID
            status_data = ProjectStatusData.get_status_data_by_project_id(project_id)

            if status_data is not None:
                return {'status_data': status_data}, HTTPStatus.OK
            else:
                return {'message': 'No status data found for the project'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error retrieving status data: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@requirements_namespace.route('/add', methods=['POST'])
class AddRequirementsResource(Resource):
    @jwt_required()
    @requirements_namespace.expect([requirements_model])
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
         # Check if the current user is an admin
        if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
            return {'message': 'Unauthorized. Only admin users can add requirements.'}, HTTPStatus.FORBIDDEN
        # Parse the input data
        requirements_data = request.json
        try:
            for requirement in requirements_data:
                new_requirement = Requirements(
                    name=requirement['name'],
                    description=requirement['description'],
                    section=requirement['section']
                )
                new_requirement.save()
            return {'message': 'All requirements added successfully.'}, HTTPStatus.OK
                
        except Exception as e:
            current_app.logger.error(f"Error adding requirements: {str(e)}")
            db.session.rollback()
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@requirements_namespace.route('/get/all', methods=['GET'])
class GetRequirementsResource(Resource):
    @jwt_required()
    def get(self):
         # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is authorized to access requirements
        if not current_user:
            return {'message': 'Unauthorized'}, HTTPStatus.UNAUTHORIZED

        # Check if the current user is an admin
        # if not current_user.is_admin():
        #     return {'message': 'Unauthorized. Only admin users can retrieve all requirements.'}, HTTPStatus.FORBIDDEN

        try:
            # Fetch all requirements from the database
            all_requirements = Requirements.query.all()

            # Serialize the requirements data
            requirements_list = []
            for requirement in all_requirements:
                requirement_data = {
                    'requirementID': requirement.requirementID,
                    'name': requirement.name,
                    'description': requirement.description,
                    'section': requirement.section.value  # Convert Enum to its value
                }
                requirements_list.append(requirement_data)

            return {'requirements': requirements_list}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error retrieving requirements: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        

@project_namespace.route('/change_status/<int:project_id>', methods=['PUT'])
class ProjectChangeStatusResource(Resource):
    @jwt_required()
    @project_namespace.expect(project_namespace.model('ProjectStatus', {
        'projectStatus': fields.String(required=True, description='New project status')
    }))
    def put(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the project by ID
        project = ProjectsData.query.get(project_id)
        if not project:
            return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has permission to change the status
        if current_user.is_admin() or current_user.userID == project.userID:
            # Parse the new status from the request
            new_status = request.json.get('projectStatus')

            # Update the project status
            project.projectStatus = new_status
            project.startDate = datetime.utcnow().date()

            # Save the updated project status to the database
            try:
                db.session.commit()
                # Check if the new status is 'Approved' and add stages if true
                if new_status == "APPROVED":
                    #Delete linked stages
                    ProjectStage.query.filter_by(projectID=project.projectID).delete()
                    # Add three stages for the project
                    initiated_stage = Stage.query.filter_by(name='Project Initiated').first()
                    progress_stage = Stage.query.filter_by(name='In Progress').first()
                    closed_stage = Stage.query.filter_by(name='Closed').first()

                    # Add the stages to the project
                    project_stages = [
                        ProjectStage(project=project, stage=initiated_stage, started=True),
                        ProjectStage(project=project, stage=progress_stage, started=True),
                        ProjectStage(project=project, stage=closed_stage, started=True)
                    ]

                    # Commit the new stages to the database
                    db.session.add_all(project_stages)
                    db.session.commit()

                return {'message': 'Project status changed successfully', 'new_status': new_status}, HTTPStatus.OK

            except Exception as e:
                db.session.rollback()
                return {'message': f'Error changing project status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            return {'message': 'Unauthorized. You do not have permission to change the status of this project.'}, HTTPStatus.FORBIDDEN


@project_namespace.route('/user-projects/<string:username>', methods=['GET'])
class UserProjectsResource(Resource):
    def get(self, username):
        # Replace 'user_id' with the actual way you get the user ID
        user = Users.query.filter_by(username=username).first()

        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Fetch projects associated with the user using the ProjectUser model
        projects = (
            ProjectsData.query.join(ProjectUser)
            .filter(ProjectUser.userID == user.userID)
            .distinct(ProjectsData.projectID)
            .all()
        )

        # Convert the list of projects to a JSON response
        projects_data = [
            {
                'projectID': project.projectID,
                'projectName': project.projectName,
                'projectStatus': project.projectStatus.value,
            }
            for project in projects
        ]

        return jsonify({'projects': projects_data})


@project_namespace.route('/project_users/<int:project_id>')
class ProjectUsersResource(Resource):
    @jwt_required()
    def get(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the project by ID
        project = ProjectsData.query.get(project_id)
        if not project:
            return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has access to the project
        if current_user.is_admin() or current_user in project.users:
            # Retrieve all users who have access to the project
            project_users = (
                db.session.query(Users)
                .join(ProjectUser, Users.userID == ProjectUser.userID)
                .filter(ProjectUser.projectID == project_id)
                .all()
            )

            # Extract user information
            users_data = [{'userID': user.userID, 'username': user.username} for user in project_users]

            return {'project_users': users_data}, HTTPStatus.OK
        else:
            return {'message': 'Unauthorized. You do not have permission to view users for this project.'}, HTTPStatus.FORBIDDEN




#####################################################
# STAGE ENDPOINTS
#####################################################
@stage_namespace.route('/add_stage', methods=['POST'])
class AddStageResource(Resource):
    @jwt_required()
    @project_namespace.expect(stage_model)
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user has permission to add a stage
        if not current_user.is_admin():  # Adjust the condition based on your specific requirements
            return {'message': 'Unauthorized. Only admin users can add stages.'}, HTTPStatus.FORBIDDEN

        # Parse input data
        stage_data = request.json

        # Create a new stage instance
        new_stage = Stage(
            name=stage_data['name']
            # status=stage_data['status']
        )

        # Save the stage to the database
        try:
            # db.session.add(new_stage)
            # db.session.commit()
            new_stage.save()

            return {'message': 'Stage added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error adding stage: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
@stage_namespace.route('/delete_stage/<int:stage_id>', methods=['DELETE'])
class DeleteStageResource(Resource):
    @jwt_required()
    def delete(self, stage_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user has permission to delete a stage
        if not current_user.is_admin():  # Adjust the condition based on your specific requirements
            return {'message': 'Unauthorized. Only admin users can delete stages.'}, HTTPStatus.FORBIDDEN

        # Get the stage by ID
        stage_to_delete = Stage.query.get(stage_id)

        # Check if the stage exists
        if not stage_to_delete:
            return {'message': 'Stage not found'}, HTTPStatus.NOT_FOUND

        # Delete the stage from the database
        try:
            stage_to_delete.delete()

            return {'message': 'Stage deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error deleting stage: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
@stage_namespace.route('/all_stages', methods=['GET'])
class AllStagesResource(Resource):
    def get(self):
        try:
            # Get all stages
            stages = Stage.query.all()

            # Convert the list of stages to a JSON response
            stages_data = [{'stageID': stage.stageID, 'name': stage.name} for stage in stages]

            return jsonify({'stages': stages_data})

        except Exception as e:
            current_app.logger.error(f"Error retrieving stages: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


    
@stage_namespace.route('/stages_for_project/<int:project_id>', methods=['GET'])
class StagesForProjectResource(Resource):
    @jwt_required()
    def get(self, project_id):
        try:
            # Check if the project exists in the database
            project = ProjectsData.query.get(project_id)

            if project is None:
                return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

            # Get all stages linked to the project
            linked_stages = ProjectStage.query.filter_by(projectID=project_id).all()

            # Convert the list of linked stages to a JSON response
            linked_stages_data = [{'stageID': stage.stage.stageID, 'name': stage.stage.name,
                                   'started': stage.started, 'completed': stage.completed,
                                   'completionDate': stage.completionDate} for stage in linked_stages]

            return jsonify({'linked_stages': linked_stages_data})

        except Exception as e:
            current_app.logger.error(f"Error retrieving linked stages for project: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
@stage_namespace.route('/complete_stage_for_project/<int:project_id>/<int:stage_id>', methods=['PUT'])
@stage_namespace.doc(
    params={
        'project_id': 'Specify the ID of the project',
        'stage_id': 'Specify the ID of the stage'
    },
    description = "Change the stage to complete"
)
class CompleteStageForProjectResource(Resource):
    @jwt_required()
    def put(self, project_id, stage_id):
        try:
            # Check if the project exists in the database
            project = ProjectsData.query.get(project_id)

            if project is None:
                return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

            # Check if the linked stage exists for the project
            linked_stage = ProjectStage.query.filter_by(projectID=project_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified project'}, HTTPStatus.NOT_FOUND

            # Update the linked stage as completed
            linked_stage.completed = True
            linked_stage.completionDate = datetime.today().date()

            # Commit the changes to the database
            db.session.commit()

            return {'message': 'Linked stage marked as completed successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error marking linked stage as completed: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@stage_namespace.route('/remove_stage/<int:project_id>/<int:stage_id>', methods=['DELETE'])
class RemoveStageResource(Resource):
    @jwt_required()
    def delete(self, project_id, stage_id):
        try:
            # Check if the linked stage exists for the project
            linked_stage = ProjectStage.query.filter_by(projectID=project_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified project'}, HTTPStatus.NOT_FOUND

            # Remove the linked stage
            db.session.delete(linked_stage)
            db.session.commit()

            return {'message': 'Stage removed successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error removing stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
#####################################################
# STAGE Tasks ENDPOINTS
#####################################################
@task_namespace.route('/add_task_for_stage/<int:project_id>/<int:stage_id>', methods=['POST'])
class AddTaskForStageResource(Resource):
    @task_namespace.expect(new_task_model, validate=True)
    @jwt_required()
    def post(self, project_id, stage_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        try:
            # Check if the linked stage exists for the project
            linked_stage = ProjectStage.query.filter_by(projectID=project_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified project'}, HTTPStatus.NOT_FOUND

            # Extract task data from the request payload
            data = task_namespace.payload
            title = data.get('title')
            deadline = data.get('deadline')
            description = data.get('description')
            assigned_to_ids = data.get('assigned_to', [])
            cc_ids = data.get('cc', [])
            created_by = current_user.userID
            attached_files = data.get('attached_files')
            checklist = data.get('checklist',{})

            # Fetch user instances based on IDs
            assigned_to_users = Users.query.filter(Users.userID.in_(assigned_to_ids)).all()
            cc_users = Users.query.filter(Users.userID.in_(cc_ids)).all()

            # Create a new task for the linked stage
            new_task = ProjectTask(
                projectID=project_id,
                title=title,
                deadline=deadline,
                description=description,
                assignedTo=assigned_to_users,
                cc=cc_users,
                createdBy=created_by,
                attachedFiles=attached_files,
                stageID=stage_id,
                status = TaskStatus.TODO,
                checklist = checklist,
                startDate = data.get('startDate',datetime.now().date())
            )

            # Save the new task to the database
            db.session.add(new_task)
            db.session.commit()

            return {'message': 'Task added for the linked stage successfully',
                    'task_id': new_task.taskID}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding task for linked stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/edit_task/<int:task_id>', methods=['PUT'])
class EditTaskForStageResource(Resource):
    @task_namespace.expect(edit_task_model, validate=True)
    @jwt_required()
    def put(self, task_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        

        try:
            # Get the task
            task = ProjectTask.get_by_id(task_id)

            if task is None:
                return {'message': 'Task not found'}, HTTPStatus.NOT_FOUND

            # Extract task data from the request payload
            data = task_namespace.payload
            
            task.title = data.get('title', task.title)
            task.deadline = data.get('deadline', task.deadline)
            task.description = data.get('description', task.description)
            task.startDate = data.get('startDate', func.now().date())
            assigned_to_ids = data.get('assigned_to', [])
            cc_ids = data.get('cc', [])
            if task.attachedFiles.endswith(","):
                task.attachedFiles = task.attachedFiles + " " + data.get('attached_files', '')
            else:
                task.attachedFiles = task.attachedFiles + ", " + data.get('attached_files', task.attachedFiles)
            task.checklist = data.get('checklist', task.checklist)

            # Fetch user instances based on IDs
            assigned_to_users = Users.query.filter(Users.userID.in_(assigned_to_ids)).all()
            cc_users = Users.query.filter(Users.userID.in_(cc_ids)).all()
            
            task.assignedTo = assigned_to_users
            task.cc = cc_users

            db.session.commit()

            return {'message': 'Task updated successfully',
                    'task_id': task.taskID}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error updating task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/assign_task/<int:task_id>', methods=['PUT'])
class AssignTaskResource(Resource):
    @task_namespace.expect(assign_task, validate=True)
    @jwt_required()
    def put(self, task_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # Check if the current user has permission to delete a stage
        if not current_user.is_admin():  # Adjust the condition based on your specific requirements
            return {'message': 'Unauthorized. Only admin users can edit Task details.'}, HTTPStatus.FORBIDDEN

        try:
            # Get the task
            task = ProjectTask.get_by_id(task_id)

            if task is None:
                return {'message': 'Task not found'}, HTTPStatus.NOT_FOUND

            # Extract task data from the request payload
            data = task_namespace.payload
            
            assigned_to_ids = data.get('assigned_to', [])
            cc_ids = data.get('cc', [])
            
            # Fetch user instances based on IDs
            assigned_to_users = Users.query.filter(Users.userID.in_(assigned_to_ids)).all()
            cc_users = Users.query.filter(Users.userID.in_(cc_ids)).all()
            
            task.assignedTo = assigned_to_users
            task.cc = cc_users

            db.session.commit()

            return {'message': 'Task updated successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error updating task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/mark_as_started/<int:task_id>',methods=['PUT'])
class MarkTaskAsStartedResource(Resource):
    @jwt_required()
    @task_namespace.doc(
        description = "Assign the In Progress status to the provided task"
    )
    def put(self, task_id):
        try:
            task = ProjectTask.get_by_id(task_id)
            if(task.status == TaskStatus.TODO):
                task.status = TaskStatus.INPROGRESS
                task.save()
                return {'message': 'Task has been marked as In Progress successfully'}, HTTPStatus.OK
            else:
                return {'message': 'Not allowed. A task must be in a TODO state to mark at as In Progress'}, HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"Error marking task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR  
        

@task_namespace.route('/mark_as_done/<int:task_id>',methods=['PUT'])
class MarkTaskAsDoneResource(Resource):
    @jwt_required()
    @task_namespace.doc(
        description = "Assign the DONE status to the provided task."
    )
    def put(self, task_id):
        try:
            task = ProjectTask.get_by_id(task_id)
            #
            if(task.status == TaskStatus.INPROGRESS or task.status == TaskStatus.OVERDUE):
                task.status = TaskStatus.DONE
                # Set completionDate to the current date
                task.completionDate = date.today()
                task.save()
                return {'message': 'Task marked as done successfully.'}, HTTPStatus.OK
            else:
                return {'message': 'Cannot mark a Task as done if it was not IN PROGRESS.'}, HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"Error marking task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/delete/<int:task_id>',methods=['DELETE'])
class DeleteTaskResource(Resource):
    @jwt_required()
    @task_namespace.doc(
        description = "Delete the task."
    )
    def delete(self, task_id):
        try:
            task = ProjectTask.get_by_id(task_id)
            #
            if task:
                task.delete()
                return {'message': 'Task deleted successfully.'}, HTTPStatus.OK
            else:
                return {'message': 'Task not found.'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            current_app.logger.error(f"Error deleting task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/mark_as_overdue/<int:task_id>',methods=['PUT'])
class MarkTaskAsOverdueResource(Resource):
    @jwt_required()
    @task_namespace.doc(
        description = "Assign the OVERDUE status to the provided task"
    )
    def put(self, task_id):
        try:
            task = ProjectTask.get_by_id(task_id)
            #only mark the task as overdue if it neither DONE nor already OVERDUE
            if(task.status != TaskStatus.DONE or task.status != TaskStatus.OVERDUE):
                if task.is_overdue:
                    task.status = TaskStatus.OVERDUE
                    task.save()
                    return {'message': 'Task has been marked as overdue'}, HTTPStatus.OK
                else:
                    return {'message': 'Ingored, Task is not yet overdue'}, HTTPStatus.OK
            else:
                return {'message': 'Cannot mark Task as OVERDUE, it is either DONE or already OVERDUE'}, HTTPStatus.BAD_REQUEST
                
        except Exception as e:
            current_app.logger.error(f"Error marking task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/add_comment_for_task', methods=['POST'])
class AddTaskComments(Resource):
    @jwt_required()
    @task_namespace.expect(comments_model, validate=True)
    @task_namespace.doc(
        description = "Post comments to a Task"
    )
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Parse the input data
        comment_data = request.json
        
        #get data from json
        taskID = comment_data['taskID']
        comment = comment_data['comment']
        date = comment_data['date']
        
        new_comment = TaskComments(
            taskID = taskID,
            userID = current_user.userID,
            comment = comment,
            date = date
        )
        
        try:
            # db.session.add(new_stage)
            # db.session.commit()
            new_comment.save()

            return {'message': 'Comment added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error adding comment: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/edit_comment_for_task', methods=['PUT'])
class EditTaskComments(Resource):
    @jwt_required()
    @task_namespace.expect(edit_comments_model, validate=True)
    @task_namespace.doc(
        description="Edit a comment for a Task"
    )
    def put(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Parse the input data
        edit_comment_data = request.json

        # Get data from JSON
        comment_id = edit_comment_data['commentID']
        new_comment_text = edit_comment_data['newComment']

        try:
            # Fetch the comment to be edited
            comment_to_edit = TaskComments.query.get_or_404(comment_id)

            # Check if the current user is the owner of the comment
            if comment_to_edit.userID == current_user.userID:
                # Update the comment text
                comment_to_edit.comment = new_comment_text
                db.session.commit()
                return {'message': 'Comment edited successfully'}, HTTPStatus.OK
            else:
                return {'message': 'Unauthorized to edit this comment'}, HTTPStatus.UNAUTHORIZED

        except Exception as e:
            db.session.rollback()
            return {'message': f'Error editing comment: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/delete/task_comment/<int:comment_id>',methods=['DELETE'])
class DeleteComment(Resource):
    @jwt_required()
    def delete(self, comment_id):
        try:
            comment = TaskComments.get_by_id(comment_id)
            
            if comment:
                comment.delete()
                return {'message': 'Comment deleted successfully'}, HTTPStatus.OK
            else:
                return {'message': 'Comment not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            current_app.logger.error(f"Error deleting comment: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
        
@task_namespace.route('/get/task_comments/<int:task_id>',methods=['GET'])
class GetTaskCommentsResource(Resource):
    @jwt_required()
    def get(self, task_id):
        try:
            comments = TaskComments.query.filter_by(taskID=task_id).all()
            
            comments_list = []
            
            for comment in comments:
                # Fetch user's name based on userID
                user = Users.query.get(comment.userID)
                user_name = user.username if user else "Unknown User"
                
                # Convert TaskComments instance to dictionary
                comment_dict = {
                    'taskID': comment.taskID,
                    'user': user_name,
                    'comment': comment.comment,
                    'date': comment.date.strftime('%Y-%m-%d') if comment.date else None,
                }
                
                # Append the dictionary to comments_list
                comments_list.append(comment_dict)

            return {'comments': comments_list}, HTTPStatus.OK
            
        except Exception as e:
            current_app.logger.error(f"Error task comments: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
            
@assessment_namespace.route('/assessment/questions/add')
class AddAssessmentQuestionResource(Resource):
    @jwt_required()
    @assessment_namespace.expect([assessment_question_model])
    def post(self):
        # Get the current user from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is an admin
        if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
            return {'message': 'Unauthorized. Only admin users can add questions.'}, HTTPStatus.FORBIDDEN

        # Parse the input data for questions
        questions_data = request.json
        
        try:
            for question in questions_data:
                new_question = AssessmentQuestions(
                    questionText= question['questionText']
                )
                
                new_question.save()
            return {'message': 'All Assessment Questions were saved.'}, HTTPStatus.OK      
        except Exception as e:
            current_app.logger.error(f"Error In adding AssessmentQuestion: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@assessment_namespace.route('/assessment/questions/all')
class GetAllAssessmentQuestionsResource(Resource):
    @jwt_required()
    def get(self):
        # Get all assessment questions
        try:
            questions = AssessmentQuestions.query.all()
            
            # Serialize the questions data
            questions_data = []
            for question in questions:
                question_data = {
                    'questionID': question.questionID,
                    'questionText': question.questionText
                }
                questions_data.append(question_data)
            
            return {'questions': questions_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error in retrieving Assessment Questions: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@assessment_namespace.route('/assessment/answers/add')
class AddAssessmentAnswerResource(Resource):
    @jwt_required()
    @assessment_namespace.expect(assessment_model)
    def post(self):
        # Get the current user from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is an admin
        if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
            return {'message': 'Unauthorized. Only admin users can add answers.'}, HTTPStatus.FORBIDDEN

        # Parse the input data for answers
        assessment_data = request.json
        answers_data = assessment_data.pop('answers', [])
        try:
            # get the project this assessment is for
            project = ProjectsData.get_by_id(assessment_data['projectID'])
            if not project:
                return {'message': 'Project not found'}, HTTPStatus.BAD_REQUEST
            
            
            for answer in answers_data:
                question_id = answer['questionID']
                question = AssessmentQuestions.get_by_id(question_id)
                if not question:
                    pass
                existing_answer = AssessmentAnswers.query.filter_by(
                    questionID=question_id,
                    projectID=assessment_data['projectID']
                ).first()

                if existing_answer:
                    # If an answer already exists for the question, update it
                    existing_answer.answerText = answer['answerText']
                    existing_answer.notes = answer.get('notes', '')
                    db.session.commit()
                else:
                    # If no answer exists, create a new one
                    new_answer = AssessmentAnswers(
                        questionID=question_id,
                        projectID=assessment_data['projectID'],
                        answerText=answer['answerText'],
                        notes=answer.get('notes', '')
                    )
                
                    new_answer.save()
            #now update project status to PENDING
            project.projectStatus = Status.PENDING
            db.session.commit()
            # Fetch all assessment answers for the given project_id
            assessment_answers = (
                AssessmentAnswers.query
                .join(AssessmentQuestions)
                .filter(AssessmentAnswers.projectID == assessment_data['projectID'])
                .add_columns(AssessmentQuestions.questionText, AssessmentAnswers.answerText, AssessmentAnswers.notes)
                .all()
            )

            # Convert the list of answers to a JSON response
            answers_data = [
                answer.answerText
                for answer in assessment_answers
            ]
            categoryCalculator = ProjectCategoryCalculator(project, answers_data)
            categoryCalculator.calculateCategory()
            return {'message': 'All Assessment Answers were saved.'}, HTTPStatus.OK
                
        except Exception as e:
            current_app.logger.error(f"Error In adding AssessmentQuestion: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@assessment_namespace.route('/assessment/calculate-category/<int:project_id>')
class CalculateCategoryResource(Resource):
    def put(self, project_id):
        try:
            project = ProjectsData.get_by_id(project_id)
            assessment_answers = (
                AssessmentAnswers.query
                .join(AssessmentQuestions)
                .filter(AssessmentAnswers.projectID == project_id)
                .add_columns(AssessmentQuestions.questionText, AssessmentAnswers.answerText, AssessmentAnswers.notes)
                .all()
            )

            # Correct way of constructing answers_data
            answers_data = [
                answer.answerText
                for answer in assessment_answers
            ]
            categoryCalculator = ProjectCategoryCalculator(project, answers_data)
            categoryCalculator.calculateCategory()
            return {'message': f'Calculation Complete. Category is {project.category.value} and total points is {project.totalPoints}'}, HTTPStatus.OK
        except Exception as e:
            print(e)
            current_app.logger.error(f"Error Calculating Category: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@assessment_namespace.route('/assessment/answers/get/<int:project_id>', methods=['GET'])
class GetAssessmentResource(Resource):
    @jwt_required()
    def get(self, project_id):
        try:
            # Fetch all assessment answers for the given project_id
            assessment_answers = (
                AssessmentAnswers.query
                .join(AssessmentQuestions)
                .filter(AssessmentAnswers.projectID == project_id)
                .add_columns(AssessmentQuestions.questionText, AssessmentAnswers.answerText, AssessmentAnswers.notes)
                .all()
            )

            # Convert the list of answers to a JSON response
            answers_data = [
                {
                    'questionText': question_text,
                    'answerText': answer_text,
                    'notes': notes
                }
                for _, question_text, answer_text, notes in assessment_answers
            ]

            return {'assessment_answers': answers_data}, HTTPStatus.OK
            
        except Exception as e:
            current_app.logger.error(f"Error In fetching Assessment: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@assessment_namespace.route('/assessment/delete/<int:project_id>', methods=['DELETE'])
class DeleteAssessmentResource(Resource):
    @jwt_required()
    def delete(self, project_id):
        # Get the current user from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is an admin
        if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
            return {'message': 'Unauthorized. Only admin users can delete answers.'}, HTTPStatus.FORBIDDEN

        try:
            # Delete all AssessmentAnswers for the specified project_id
            AssessmentAnswers.query.filter_by(projectID=project_id).delete()
            db.session.commit()

            return {'message': 'Assessment answers deleted successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error in deleting assessment answers: {str(e)}")
            db.session.rollback()
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@assessment_namespace.route('/question/delete/<int:question_id>', methods=['DELETE'])
class DeleteAssessmentQuestionResource(Resource):
    @jwt_required()
    def delete(self, question_id):
        # Get the current user from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is an admin
        if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
            return {'message': 'Unauthorized. Only admin users can delete questions.'}, HTTPStatus.FORBIDDEN

        try:
            # Delete the AssessmentQuestion with the specified question_id
            question = AssessmentQuestions.get_by_id(question_id)
            if question:
                question.delete()
                return {'message': 'Assessment question deleted successfully'}, HTTPStatus.OK
            else:
                return {'message': 'Assessment question not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error in deleting assessment question: {str(e)}")
            db.session.rollback()
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
            
        

@task_namespace.route('/get_tasks_for_stage/<int:project_id>/<int:stage_id>', methods=['GET'])
class GetTasksForStageResource(Resource):
    @jwt_required()
    def get(self, project_id, stage_id):
        try:
            # Check if the linked stage exists for the project
            linked_stage = ProjectStage.query.filter_by(projectID=project_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified project'}, HTTPStatus.NOT_FOUND

            # Fetch all tasks for the linked stage
            tasks = ProjectTask.query.filter_by(projectID=project_id, stageID=stage_id).all()

            # Convert tasks to a list of dictionaries for response
            tasks_list = []

            for task in tasks:
                # Fetch the first 5 comments for each task
                comments = TaskComments.query.filter_by(taskID=task.taskID).limit(5).all()

                comments_list = [
                    {
                        'user': Users.query.get(comment.userID).username if Users.query.get(comment.userID) else "Unknown User",
                        'comment': comment.comment,
                        'date': comment.date.strftime('%Y-%m-%d') if comment.date else None
                    }
                    for comment in comments
                ]

                tasks_list.append({
                    'taskID': task.taskID,
                    'title': task.title,
                    'deadline': str(task.deadline),
                    'description': task.description,
                    'assignedTo': [user.username for user in task.assignedTo],
                    'assignedTo_ids': [user.userID for user in task.assignedTo],
                    'cc': [user.username for user in task.cc],
                    'cc_ids': [user.userID for user in task.cc],
                    'createdBy': task.createdBy,
                    'attachedFiles': task.attachedFiles,
                    'status': task.status.value,
                    'completionDate': str(task.completionDate) if task.completionDate else None,
                    'comments': comments_list,
                    'checklist': task.checklist,
                    'creationDate': task.creationDate.isoformat(),
                    'startDate': task.startDate.strftime('%Y-%m-%d') if task.startDate else None
                })

            return {'tasks': tasks_list}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting tasks for linked stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/get_all_project_tasks/<int:project_id>', methods=['GET'])
class GetTasksForProjectResource(Resource):
    @jwt_required()
    def get(self, project_id):
        try:
            # get the project 
            project = ProjectsData.get_by_id(project_id)
            
            if project is None:
                return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

            # Fetch all tasks for the linked stage
            tasks = ProjectTask.query.filter_by(projectID=project_id).all()

            # Convert tasks to a list of dictionaries for response
            tasks_list = []
            
            # Guard clause to check if there are tasks available
            if not tasks:
                return {'tasks': tasks_list}, HTTPStatus.OK

            for task in tasks:
                # Fetch the first 5 comments for each task
                comments = TaskComments.query.filter_by(taskID=task.taskID).limit(5).all()

                comments_list = [
                    {
                        'user': Users.query.get(comment.userID).username if Users.query.get(comment.userID) else "Unknown User",
                        'comment': comment.comment,
                        'date': comment.date.strftime('%Y-%m-%d') if comment.date else None
                    }
                    for comment in comments
                ]

                tasks_list.append({
                    'taskID': task.taskID,
                    'stageID': task.stageID,
                    'stageName': task.stage.name,
                    'title': task.title,
                    'deadline': str(task.deadline),
                    'description': task.description,
                    'assignedTo': [user.username for user in task.assignedTo],
                    'assignedTo_ids': [user.userID for user in task.assignedTo],
                    'cc': [user.username for user in task.cc],
                    'cc_ids': [user.userID for user in task.cc],
                    'createdBy': task.createdBy,
                    'attachedFiles': task.attachedFiles,
                    'status': task.status.value,
                    'completionDate': str(task.completionDate) if task.completionDate else None,
                    'comments': comments_list,
                    'checklist': task.checklist,
                    'creationDate': task.creationDate.isoformat(),
                    'startDate': task.startDate.strftime('%Y-%m-%d') if task.startDate else None
                })

            return {'tasks': tasks_list}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting tasks for project: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/get_all_project_tasks/current_user', methods=['GET'])
class GetAllAssignedTasksResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Get the current user from the JWT token
            user = Users.query.filter_by(username=get_jwt_identity()).first()
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
            
            all_assigned_tasks = {
                'project_tasks': [{'taskID': task.taskID,
                               'title': task.title,
                               'description': task.description,
                               'status': task.status.value,
                               'checklist': task.checklist,
                               'stageName': task.stage.name,
                               'projectName': ProjectsData.query.get(task.projectID).projectName,
                               'startDate': task.startDate.strftime('%Y-%m-%d') if task.startDate else None,
                               'deadline': task.deadline.strftime('%Y-%m-%d') if task.deadline else None,
                               'completionDate': task.completionDate.isoformat() if task.completionDate else None} for task in project_tasks] if project_tasks else [],
                'project_tasks_summary': {'total_p_tasks': total_p_tasks,'completed_p_tasks': completed_p_tasks, 'overdue_p_tasks': overdue_p_tasks,
                                     'not_started_p_tasks': not_started_p_tasks, 'inprogress_p_tasks': inprogress_p_tasks},
            }
            
            return all_assigned_tasks, HTTPStatus.OK
               
        except Exception as e:
            current_app.logger.error(f"Error getting all assigned project tasks: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR    

@activity_namespace.route('/add_or_edit', methods=['POST','PUT'])
class AddorEditActivityResource(Resource):
    @jwt_required()
    @activity_namespace.expect(activity_model)
    def post(self):
        try:
            # Get the current user from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            activity_data = request.json
            programID = activity_data.get('programID', 0)
            
            if programID != 0:
                program = ProjectsData.get_by_id(programID)
                if program is None:
                    return {'message': 'Program not found'}, HTTPStatus.NOT_FOUND
                
                if program.project_type != ProType.PROGRAM:
                    return {'message': 'The provided program ID is not a program, but a Project'}, HTTPStatus.BAD_REQUEST
            
            assigned_ids = activity_data.get('assignedTo', [])
            assigned_to_users = Users.query.filter(Users.userID.in_(assigned_ids)).all()
            
            activity = Activities(
                activityName = activity_data['activityName'],
                regionID = activity_data['regionID'],
                programID = programID if programID != 0 else None,
                description = activity_data['description'],
                costRequired = activity_data['costRequired'],
                duration = activity_data['duration'],
                deadline = activity_data.get('deadline'),
                activityStatus = ActStatus.PENDING,
                assignedTo = assigned_to_users,
                createdBy = current_user.userID
            )
            activity.save()

            return {'message': 'Activity recorded successfully.',
                    'activity_data': {
                        'activityID': activity.activityID,
                        'status': activity.activityStatus.value,
                        'activityName': activity.activityName,
                        'createdAt': activity.createdAt.isoformat(),
                        'program': ProjectsData.query.get(programID).projectName if programID != 0 else 'Out Of Program',
                        'assignedUsers': assigned_ids,
                        'createdBy': f'{current_user.firstName} {current_user.lastName}',
                        'created_id': current_user.userID
                    }
                    }, HTTPStatus.CREATED
                    
        
        except Exception as e:
            current_app.logger.error(f"Error adding activity: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
       
    @jwt_required()
    @activity_namespace.expect(activity_model) 
    def put(self):
        
            try:
                current_user = Users.query.filter_by(username=get_jwt_identity()).first()
                activity_data = request.json

                act_id = activity_data.get('activityID')
                if act_id is None:
                    return {'message': 'Activty ID is required for updating an activity'}, HTTPStatus.BAD_REQUEST

                activity = Activities.query.get_or_404(act_id)
                
                activity.activityName = activity_data['activityName']
                activity.regionID = activity_data['regionID']
                activity.programID = activity_data.get('programID', activity.programID)
                activity.description = activity_data['description']
                activity.costRequired = activity_data.get('costRequired', activity.costRequired)
                activity.deadline = activity_data.get('deadline', activity.deadline)
                activity.duration = activity_data['duration']
                activity.activityStatus = activity_data.get('activityStauts', activity.activityStatus)
                
                assigned_users = activity_data.get('assignedTo',[])
                if len(assigned_users) != 0:
                    assigned_to_users = Users.query.filter(Users.userID.in_(assigned_users)).all()
                    activity.assignedTo = assigned_to_users
                activity.save()
                
                return {'message': 'Activity updated successfully.',
                    'activity_data': {
                        'activityID': activity.activityID,
                        'status': activity.activityStatus.value,
                        'activityName': activity.activityName,
                        'createdAt': activity.createdAt.isoformat(),
                        'program': ProjectsData.query.get(activity.programID).projectName if activity.programID != None else 'None',
                        'assignedUsers': assigned_users,
                        'createdBy': f'{current_user.firstName} {current_user.lastName}',
                        'created_id': current_user.userID
                    }
                    }, HTTPStatus.OK
                    
            except Exception as e:
                current_app.logger.error(f"Error adding activity: {str(e)}")
                return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@activity_namespace.route('/get_all_activities', methods=['GET'])
class GetAllActivitiesResource(Resource):
    @jwt_required()
    def get(self):
        
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            if not current_user.is_admin():
                # Fetch all activities the user has access to because they created it
                created_activities = Activities.query.filter_by(createdBy=current_user.userID).all()

                # Fetch all activities associated with the user through ActivityUsers
                assigned_activities = (
                    Activities.query.join(ActivityUsers, Activities.activityID == ActivityUsers.activityID)
                    .filter(ActivityUsers.userID == current_user.userID)
                    .all()
                )

                # Combine the created and assigned activities and remove duplicates
                all_activities = list(set(created_activities + assigned_activities))
            else:
                all_activities = Activities.query.all()

            # Check if all_activities is empty
            if not all_activities:
                return [], HTTPStatus.OK

            # Convert SQLAlchemy objects to dictionaries with additional details
            activities_dict = [{
                "activityID": activity.activityID,
                "activityName": activity.activityName,
                "region": self.get_region(activity.regionID),
                "program": self.get_program_details(activity.programID),
                "description": activity.description,
                "costRequired": activity.costRequired,
                "duration": activity.duration,
                "deadline": activity.deadline.strftime('%Y-%m-%d') if activity.deadline else None,
                "activityStatus": activity.activityStatus.value,
                "assignedTo": self.get_assigned_users(activity.assignedTo),
                "assignedToIDs": [user.userID for user in activity.assignedTo],
                "createdAt": activity.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
                "createdBy": self.get_user_details(activity.createdBy),
                "statusData": activity.statusData
            } for activity in all_activities]

            return activities_dict, HTTPStatus.OK
        
        except Exception as e:
                current_app.logger.error(f"Error getting activities: {str(e)}")
                return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    def get_program_details(self, programID):
        if not programID:
            return None
        program = ProjectsData.query.get(programID)
        if not program:
            return None
        return {
            "projectID": programID,
            "projectName": program.projectName,
            "createdAt": program.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            "budgetRequired": program.budgetRequired,
            "budgetApproved": program.budgetApproved,
            "projectStatus": program.projectStatus.value,
            "projectIdea": program.projectIdea,
            "solution": program.solution,
            "startDate": program.startDate.strftime('%Y-%m-%d') if program.startDate else None,
            "active": program.active
        }

    def get_user_details(self, userID):
        user = Users.query.get(userID)
        if not user:
            return None
        return {
            "userID": user.userID,
            "fullName": f"{user.firstName} {user.lastName}",
            "username": user.username,
            "email": user.email
        }
    def get_region(self, regionID):
        return {'regionID': regionID, 'regionName': Regions.query.get(regionID).regionName}

    def get_assigned_users(self, assignedTo):
        return [self.get_user_details(user.userID) for user in assignedTo]

@activity_namespace.route('/get_activities/program/<int:programID>')
class GetActivitiesPerProgram(Resource):
    @jwt_required()
    def get(self, programID):
        
        try:
            program = ProjectsData.get_by_id(programID)
            if program is None:
                    return {'message': 'Program not found'}, HTTPStatus.NOT_FOUND
                
            if program.project_type != ProType.PROGRAM:
                return {'message': 'The provided program ID is not a program, but a Project'}, HTTPStatus.BAD_REQUEST
            
            activities = Activities.query.filter_by(programID=programID).all()
            
            if len(activities) == 0:
                return [], HTTPStatus.OK
            
            activities_dict = [{
                "activityID": activity.activityID,
                "activityName": activity.activityName,
                "region": self.get_region(activity.regionID),
                "description": activity.description,
                "costRequired": activity.costRequired,
                "duration": activity.duration,
                "deadline": activity.deadline.strftime('%Y-%m-%d') if activity.deadline else None,
                "activityStatus": activity.activityStatus.value,
                "assignedTo": self.get_assigned_users(activity.assignedTo),
                "assignedToIDs": [user.userID for user in activity.assignedTo],
                "createdAt": activity.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
                "createdBy": self.get_user_details(activity.createdBy),
                "statusData": activity.statusData
            } for activity in activities]

            return activities_dict, HTTPStatus.OK
            
        
        except Exception as e:
                current_app.logger.error(f"Error getting activities: {str(e)}")
                return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    def get_program_details(self, programID):
        if not programID:
            return None
        program = ProjectsData.query.get(programID)
        if not program:
            return None
        return {
            "projectID": programID,
            "projectName": program.projectName,
            "createdAt": program.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            "budgetRequired": program.budgetRequired,
            "budgetApproved": program.budgetApproved,
            "projectStatus": program.projectStatus.value,
            "projectIdea": program.projectIdea,
            "solution": program.solution,
            "startDate": program.startDate.strftime('%Y-%m-%d') if program.startDate else None,
            "active": program.active
        }

    def get_user_details(self, userID):
        user = Users.query.get(userID)
        if not user:
            return None
        return {
            "userID": user.userID,
            "fullName": f"{user.firstName} {user.lastName}",
            "username": user.username,
            "email": user.email
        }
    def get_region(self, regionID):
        return {'regionID': regionID, 'regionName': Regions.query.get(regionID).regionName}

    def get_assigned_users(self, assignedTo):
        return [self.get_user_details(user.userID) for user in assignedTo]

@activity_namespace.route('/change_status/<int:activityID>')
class ChangeActivityStatusResource(Resource):
    @jwt_required()
    @activity_namespace.expect(activity_stat)
    def put(self, activityID):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            if not current_user.is_admin():
                return {'message': 'Only admins can change activity status'}, HTTPStatus.FORBIDDEN
            activity = Activities.query.get_or_404(activityID)
            request_data = request.json
            
            activity.activityStatus = request_data['status']
            activity.statusData = request_data['data']
            activity.save()
            return {'message': 'Activity status changed successfully.'}, HTTPStatus.OK
        except Exception as e:
                current_app.logger.error(f"Error changing status: {str(e)}")
                return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
            
            

            
                