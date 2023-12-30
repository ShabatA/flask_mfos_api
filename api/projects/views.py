from flask import request, current_app
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus
from ..models.projects import Projects, Questions, QuestionChoices, Answers, ProjectUser, Stage, ProjectStage, ProjectTask
from ..utils.db import db
from ..models.users import Users
from flask import jsonify
import json
from datetime import datetime



project_namespace = Namespace('project', description="A namespace for projects")
stage_namespace = Namespace('project stages', description="A namespace for project stage")
task_namespace = Namespace('Project Tasks', description="A namespace for project Tasks")

stage_model = stage_namespace.model(
    'Stage', {
        'name': fields.String(required=True, description='Name of the stage'),
    }
)
answers_model = project_namespace.model('Answers', {
    'questionID': fields.Integer(required=True, description='ID of the answer'),
    'answerText': fields.String(description='Text-based answer for a text question'),
    'choiceID': fields.List(fields.Integer, description='List of choices')
})

# Define a model for the input data (assuming JSON format)
new_task_model = task_namespace.model('NewTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    # 'created_by': fields.Integer(required=True, description='User ID of the task creator'),
    'attached_files': fields.String(description='File attachments for the task'),
    # 'stage_id': fields.Integer(required=True, description='ID of the linked stage'),
})

# Define the expected input model using Flask-RESTx fields
project_input_model = project_namespace.model('ProjectInput', {
    'projectName': fields.String(required=True, description='Name of the project'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the project'),
    'budgetAvailable': fields.Float(required=True, description='Available budget for the project'),
    'projectStatus': fields.String(required=True, enum=['approved', 'pending','rejected'], description='Status of the project'),
    'projectScope': fields.String(description='Scope of the project'),
    'category': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the project'),
    'userID': fields.Integer(description='ID of the user associated with the project'),
    'startDate': fields.Date(description='Start date of the project'),
    'dueDate': fields.Date(description='Due date of the project'),
    'answers': fields.List(fields.Nested(answers_model), description='List of answers for the project')
})

project_status = project_namespace.model('ProjectStatus',{
    'projectStatus': fields.String(required=True, enum=['approved', 'pending','rejected'], description='Status of the project'),
})

edited_answers_model = project_namespace.model('EditedAnswers', {
    'answer_id': fields.Integer(required=True, description='ID of the answer'),
    'new_answer_text': fields.String(description='Text-based answer for a text question'),
    'new_choice_id': fields.Integer(description='ID of the selected choice for a single-choice question')
})

project_edit_model = project_namespace.model('ProjectEdit', {
    'projectName': fields.String(required=True, description='Name of the project'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the project'),
    'budgetAvailable': fields.Float(required=True, description='Available budget for the project'),
    'projectStatus': fields.String(required=True, enum=['approved', 'pending','rejected'], description='Status of the project'),
    'projectScope': fields.String(description='Scope of the project'),
    'category': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the project'),
    'userID': fields.Integer(description='ID of the user associated with the project'),
    'startDate': fields.Date(description='Start date of the project'),
    'dueDate': fields.Date(description='Due date of the project'),
    'edited_answers': fields.List(fields.Nested(edited_answers_model), description='List of edited answers for the project')
})


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
    'completed': fields.Boolean(required=True, description="If the stages completed")
})

@project_namespace.route('/add')
class ProjectAddResource(Resource):
    @jwt_required()  
    @project_namespace.expect(project_input_model)
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Parse the input data
        project_data = request.json
        answers_data = project_data.pop('answers', [])  

        # Check if a project with the given name already exists
        existing_project = Projects.query.filter_by(projectName=project_data['projectName']).first()
        if existing_project:
            return {'message': 'Project with this name already exists'}, HTTPStatus.CONFLICT

        # Create a new project instance
        new_project = Projects(
            projectName=project_data['projectName'],
            regionID=project_data['regionID'],
            budgetRequired=project_data['budgetRequired'],
            budgetAvailable=project_data['budgetAvailable'],
            projectStatus=project_data['projectStatus'],
            projectScope=project_data.get('projectScope'),
            category=project_data.get('category'),
            userID=current_user.userID,
            startDate=project_data.get('startDate'),
            dueDate=project_data.get('dueDate')
        )

        # Save the project to the database
        try:
            new_project.save()

            # Assign answers to the project
            new_project.assign_answers(answers_data)

            # Add the current user to the ProjectUsers table for the new project
            project_user = ProjectUser(projectID=new_project.projectID, userID=current_user.userID)
            project_user.save()

            return {'message': 'Project added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@project_namespace.route('/add_questions')
class ProjectAddQuestionsResource(Resource):
#     [
#   {
#     "questionText": "How satisfied are you with our service?",
#     "questionType": "single choice",
#     "choices": [
#       {"choiceText": "Very Satisfied", "points": 5},
#       {"choiceText": "Satisfied", "points": 4},
#       {"choiceText": "Neutral", "points": 3},
#       {"choiceText": "Unsatisfied", "points": 2},
#       {"choiceText": "Very Unsatisfied", "points": 1}
#     ]
#   }, 
# {
#     "questionText": "Test text question?",
#     "questionType": "text",
#     "points": 33
#   }
# ]
    @jwt_required()  
    @project_namespace.expect([question_input_model]) 
    def post(self):
        # Get the current user from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is an admin
        if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
            return {'message': 'Unauthorized. Only admin users can add questions.'}, HTTPStatus.FORBIDDEN

        # Parse the input data for questions
        questions_data = request.json
        try:
            for question_data in questions_data:
                new_question = Questions(
                    questionText=question_data['questionText'],
                    questionType=question_data['questionType'],
                    points=0,
                )

                # If the question is multiple choice, add choices
                if question_data['questionType'] == 'single choice':
                    choices_data = question_data.get('choices',[])
                    for choice_data in choices_data:
                        new_choice = QuestionChoices(
                            question=new_question,
                            choiceText=choice_data['choiceText'],
                            points=choice_data['points']
                        )
                        db.session.add(new_choice)
                elif question_data['questionType'] == 'multi choice':
                    choices_data = question_data.get('choices', [])
                    for choice_data in choices_data:
                        new_choice = QuestionChoices(
                            question=new_question,
                            choiceText=choice_data['choiceText'],
                            points=choice_data['points']
                        )
                        db.session.add(new_choice)
                else:
                    new_question.points = question_data['points']

                db.session.add(new_question)

            db.session.commit()

            return {'message': 'Questions added successfully'}, HTTPStatus.CREATED

        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, HTTPStatus.BAD_REQUEST


@project_namespace.route('/total_points/<int:project_id>', methods=['GET'])
class ProjectTotalPointsResource(Resource):
    def get(self, project_id):
        # Get the project by ID
        project = Projects.get_by_id(project_id)

        if not project:
            return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

        # Calculate total points using the calculate_total_points method
        total_points = project.calculate_total_points()

        return {'total_points': total_points}, HTTPStatus.OK

@project_namespace.route('/all', methods=['GET'])
class AllProjectsResource(Resource):
    def get(self):
        projects = Projects.query.all()

        # Convert the list of projects to a JSON response
        projects_data = [{'projectID': project.projectID, 'projectName': project.projectName, 'projectStatus': project.projectStatus.value} for project in projects]

        return jsonify({'projects': projects_data})

@project_namespace.route('/<int:project_id>/answers', methods=['GET'])
class ProjectAnswersResource(Resource):
    def get(self, project_id):
        # Get the project by ID
        project = Projects.get_by_id(project_id)

        if not project:
            return jsonify({'message': 'Project not found'}), HTTPStatus.NOT_FOUND

        # Fetch both text-based and choice-based answers associated with the project
        text_answers = Answers.query.filter_by(projectID=project_id, choiceID=None).all()
        choice_answers = Answers.query.filter(Answers.projectID == project_id, Answers.choiceID.isnot(None)).all()

        # Convert the list of text answers to a JSON response
        text_answers_data = [{'answerID': answer.answerID, 'questionID': answer.questionID, 'answerText': answer.answerText} for answer in text_answers]

        # Convert the list of choice answers to a JSON response, including choice details
        choice_answers_data = [{
            'answerID': answer.answerID,
            'questionID': answer.questionID,
            'choiceID': answer.choiceID,
            'choiceText': answer.choice.choiceText,  # Include choice details in the response
            'points': answer.choice.points
        } for answer in choice_answers]

        return jsonify({'text_answers': text_answers_data, 'choice_answers': choice_answers_data})

@project_namespace.route('/edit_answers/<int:project_id>', methods=['PUT'])
class ProjectEditAnswersResource(Resource):
    @jwt_required()
    @project_namespace.expect(project_edit_model)
    def put(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the project by ID
        project = Projects.query.get_or_404(project_id)

        # Ensure the current user is authorized to edit the project
        if current_user.userID != project.userID:
            return {'message': 'Unauthorized. You do not have permission to edit this project.'}, HTTPStatus.FORBIDDEN

        # Parse the input data
        project_data = request.json
        edited_answers_data = project_data.pop('edited_answers', [])  # Extract edited answers from project_data

        # Update the project details
        project.projectName = project_data.get('projectName', project.projectName)
        project.regionID = project_data.get('regionID', project.regionID)
        project.budgetRequired = project_data.get('budgetRequired', project.budgetRequired)
        project.budgetAvailable = project_data.get('budgetAvailable', project.budgetAvailable)
        project.projectStatus = project_data.get('projectStatus', project.projectStatus)
        project.projectScope = project_data.get('projectScope', project.projectScope)
        project.category = project_data.get('category', project.category)
        project.startDate = project_data.get('startDate', project.startDate)
        project.dueDate = project_data.get('dueDate', project.dueDate)

        # Save the updated project details to the database
        try:
            db.session.commit()

            # Update the answers for the project
            project.edit_answers(edited_answers_data)

            return {'message': 'Project details and answers updated successfully'}, HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error updating project details and answers: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/delete/<int:project_id>')
class ProjectDeleteResource(Resource):
    @jwt_required()  
    def delete(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the project exists and belongs to the current user
        if current_user.is_admin:
            project_to_delete = Projects.query.filter_by(projectID=project_id).first()
        else:
            project_to_delete = Projects.query.filter_by(projectID=project_id, userID=current_user.userID).first()
        if not project_to_delete:
            return {'message': 'Project not found or unauthorized'}, HTTPStatus.NOT_FOUND

        # Delete the answers related to the project
        Answers.query.filter_by(projectID=project_id).delete()

        # Delete the project from the database
        try:
            project_to_delete.delete()

            return {'message': 'Project and associated answers deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error deleting project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    

@project_namespace.route('/delete_question/<int:question_id>')
class QuestionDeleteResource(Resource):
    @jwt_required()  
    def delete(self, question_id):
        # Check if the question exists
        question_to_delete = Questions.query.get(question_id)
        if not question_to_delete:
            return {'message': 'Question not found'}, HTTPStatus.NOT_FOUND

        # Delete the answers related to the question
        Answers.query.filter_by(questionID=question_id).delete()

        # Delete the question from the database
        try:
            question_to_delete.delete()

            return {'message': 'Question and associated answers deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error deleting question: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@project_namespace.route('/give_access/<int:project_id>/<int:user_id>')
class GiveAccessResource(Resource):
    @jwt_required()
    def post(self, project_id, user_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        project_to_access = Projects.query.get(project_id)

        # Check if the current user has the necessary permissions (e.g., project owner or admin)
        # Adjust the condition based on your specific requirements
        if not current_user.is_admin and current_user.userID != project_to_access.userID:
            return {'message': 'Unauthorized. You do not have permission to give access to this project.'}, HTTPStatus.FORBIDDEN

        # Get the project by ID
        
        if not project_to_access:
            return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

        # Get the user by ID
        user_to_give_access = Users.query.get(user_id)
        if not user_to_give_access:
            return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        # Check if the user already has access to the project
        if ProjectUser.query.filter_by(projectID=project_id, userID=user_id).first():
            return {'message': 'User already has access to the project'}, HTTPStatus.BAD_REQUEST

        # Add the user to the project's list of users
        project_user = ProjectUser(projectID=project_id, userID=user_id)
        project_user.save()

        return {'message': 'User granted access to the project successfully'}, HTTPStatus.OK
    
    
@project_namespace.route('/project_users/<int:project_id>')
class ProjectUsersResource(Resource):
    @jwt_required()
    def get(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the project by ID
        project = Projects.query.get(project_id)
        if not project:
            return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has access to the project
        if current_user.is_admin or current_user in project.users:
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

@project_namespace.route('/change_status/<int:project_id>', methods=['PUT'])
class ProjectChangeStatusResource(Resource):
    @jwt_required()
    @project_namespace.expect(project_status)
    def put(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the project by ID
        project = Projects.query.get(project_id)
        if not project:
            return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has permission to change the status
        if current_user.is_admin or current_user.userID == project.userID:
            # Parse the new status from the request
            new_status = request.json['projectStatus']
            st = ['APPROVED', 'PENDING','REJECTED']
            # st = [s.upper() for s in st]

            # Check if the new status is valid
            if new_status not in st:
                return {'message': 'Invalid project status'}, HTTPStatus.BAD_REQUEST

            # Update the project status
            project.projectStatus = new_status

            # Save the updated project status to the database
            try:
                db.session.commit()
                # Check if the new status is 'Approved' and add stages if true
                if new_status == 'APPROVED':
                    # Add three stages for the project
                    initiated_stage = Stage(name='Project Initiated', status='in progress')
                    in_progress_stage = Stage(name='In Progress', status='in progress')
                    closed_stage = Stage(name='Project Closed', status='pending')

                    # Add the stages to the project
                    project_stages = [
                        ProjectStage(project=project, stage=initiated_stage, started=True),
                        ProjectStage(project=project, stage=in_progress_stage, started=True),
                        ProjectStage(project=project, stage=closed_stage)
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

@project_namespace.route('/link-user/<int:project_id>/<string:username>')
class LinkUserToProjectResource(Resource):
    @jwt_required()
    def post(self, project_id, username):
        try:
            # Get the current user from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Check if the current user has the necessary permissions (e.g., project owner or admin)
            # Adjust the condition based on your specific requirements
            if not current_user.is_admin():
                return {'message': 'Unauthorized. You do not have permission to link users to projects.'}, HTTPStatus.FORBIDDEN

            # Get the project by ID
            project = Projects.query.get(project_id)
            if not project:
                return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

            # Get the user by username
            user = Users.query.filter_by(username=username).first()
            if not user:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

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

@project_namespace.route('/all_with_answers', methods=['GET'])
class AllProjectsWithAnswersResource(Resource):
    def get(self):
        try:
            # Get all projects
            projects = Projects.query.all()

            # Initialize a list to store project data
            projects_data = []

            # Iterate through each project
            for project in projects:
                # Get answers associated with the project
                answers = Answers.query.filter_by(projectID=project.projectID).all()

                # Include answers and corresponding questions in the project details
                project_details = {
                    'projectID': project.projectID,
                    'projectName': project.projectName,
                    'projectStatus': project.projectStatus.value,
                    'startDate': project.startDate,
                    'dueDate': project.dueDate,
                    'userID': project.userID,
                    'regionID': project.regionID,
                    'budgetRequired': project.budgetRequired,
                    'budgetAvailable': project.budgetAvailable,
                    'projectScope': project.projectScope,
                    'category': project.category.value,
                    'answers': [{'answerID': answer.answerID,
                                 'questionID': answer.questionID,
                                 'questionText': answer.question.questionText,
                                 'answerText': answer.answerText,
                                 'choiceID': answer.choiceID
                                 } for answer in answers]
                }

                # Append project details to the list
                projects_data.append(project_details)

            return jsonify({'projects_with_answers': projects_data})

        except Exception as e:
            current_app.logger.error(f"Error retrieving projects with answers: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
@project_namespace.route('/all_questions', methods=['GET'])
class AllQuestionsResource(Resource):
    def get(self):
        try:
            # Get all questions
            questions = Questions.query.all()

            # Initialize a list to store question data
            questions_data = []

            # Iterate through each question
            for question in questions:
                # Get question details
                question_details = {
                    'questionID': question.questionID,
                    'questionText': question.questionText,
                    'questionType': question.questionType,
                    'points': question.points
                }

                # If the question is a multiple-choice question, include choices
                if question.questionType == 'single choice':
                    choices = QuestionChoices.query.filter_by(questionID=question.questionID).all()
                    choices_data = [{'choiceID': choice.choiceID, 'choiceText': choice.choiceText, 'points': choice.points} for choice in choices]
                    question_details['choices'] = choices_data

                # Append question details to the list
                questions_data.append(question_details)

            return jsonify({'questions': json.loads(json.dumps(questions_data, sort_keys=True))})

        except Exception as e:
            current_app.logger.error(f"Error retrieving questions: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


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
        if not current_user.is_admin:  # Adjust the condition based on your specific requirements
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
        if not current_user.is_admin:  # Adjust the condition based on your specific requirements
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

@stage_namespace.route('/link_project_to_stage', methods=['POST'])
class LinkProjectToStageResource(Resource):
    @stage_namespace.expect(link_project_to_stage_model, validate=True)
    def post(self):
        try:
            # Get project and stage IDs from the request data
            data = stage_namespace.payload
            project_id = data.get('project_id')
            stage_id = data.get('stage_id')
            started = data.get('started')
            completed = data.get('completed')

            # Check if both project and stage IDs are provided
            if project_id is None or stage_id is None:
                return {'message': 'Both project_id and stage_id must be provided'}, HTTPStatus.BAD_REQUEST

            # Check if the project and stage exist in the database
            project = Projects.query.get(project_id)
            stage = Stage.query.get(stage_id)

            if project is None or stage is None:
                return {'message': 'Project or stage not found'}, HTTPStatus.NOT_FOUND

            # Check if the project is already linked to the stage
            existing_link = ProjectStage.query.filter_by(projectID=project_id, stageID=stage_id).first()

            if existing_link:
                return {'message': 'Project is already linked to the specified stage'}, HTTPStatus.BAD_REQUEST

            # Create a new link between the project and stage
            project_stage_link = ProjectStage(projectID=project_id, stageID=stage_id,
                                              started=started, completed=completed)
            db.session.add(project_stage_link)
            db.session.commit()

            return {'message': 'Project linked to stage successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error linking project to stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
@stage_namespace.route('/stages_for_project/<int:project_id>', methods=['GET'])
class StagesForProjectResource(Resource):
    def get(self, project_id):
        try:
            # Check if the project exists in the database
            project = Projects.query.get(project_id)

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
    def put(self, project_id, stage_id):
        try:
            # Check if the project exists in the database
            project = Projects.query.get(project_id)

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
                stageID=stage_id
            )

            # Save the new task to the database
            db.session.add(new_task)
            db.session.commit()

            return {'message': 'Task added for the linked stage successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding task for linked stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR