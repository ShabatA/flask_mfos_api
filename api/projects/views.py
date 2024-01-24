from flask import request, current_app
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus

from api.utils.project_requirement_processor import ProjectRequirementProcessor
from ..models.projects import Projects, Questions, QuestionChoices, Answers, ProjectUser, Stage, ProjectStage, ProjectTask, ProjectStatus, ProjectStatusData, TaskComments, TaskStatus, ProjectTaskAssignedTo, ProjectTaskCC, AssessmentAnswers, AssessmentQuestions, Requirements, RequirementSection
from ..utils.db import db
from ..models.users import Users
from flask import jsonify
import json
from datetime import datetime, date
from collections import OrderedDict





project_namespace = Namespace('Projects', description="A namespace for Projects")
stage_namespace = Namespace('Project Stages', description="A namespace for Project Stages")
task_namespace = Namespace('Project Tasks', description="A namespace for Project Tasks")
assessment_namespace = Namespace('Project Assessment', description="A namespace for Project Assessment")

requirements_namespace = Namespace('Requirements', description="A namespace for requirements. These will be universal for both Case and Project Approval")

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
    'answerText': fields.String(required=True, description='The answer provided')
})

assessment_model = assessment_namespace.model('ProjectAssessment', {
    'projectID': fields.Integer(required=True, description='The ID of the project this assessment is for'),
    'answers': fields.List(fields.Nested(assessment_answer_model), description='List of answers for the assessment')
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
    'attached_files': fields.String(description='File attachments for the task')
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
            budgetAvailable=0,
            projectStatus=ProjectStatus.ASSESSMENT,
            projectScope=project_data.get('projectScope'),
            category=project_data.get('category'),
            userID=current_user.userID
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

@project_namespace.route('/add/requirements/<int:project_id>')
class ProjectAddRequirementsResource(Resource):
    @jwt_required()
    @project_namespace.expect(project_input_model2)
    def post(self, project_id):
        try:
            
            # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            
            if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
                return {'message': 'Unauthorized. Only admin users can add requirements.'}, HTTPStatus.FORBIDDEN
            
            project = Projects.get_by_id(project_id)
            # Parse the input data
            project_data = request.json
            status_data = project_data.pop('status_data', {})  # Assuming status_data is part of the input
            
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

            return {'message': 'Project requirements added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding project requirements: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

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
        if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
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
        # if not current_user.is_admin:
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
        project = Projects.query.get(project_id)
        if not project:
            return {'message': 'Project not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has permission to change the status
        if current_user.is_admin or current_user.userID == project.userID:
            # Parse the new status from the request
            new_status = request.json.get('projectStatus')
            # valid_statuses = [status for status in ProjectStatus]

            # Check if the new status is valid
            # if new_status not in valid_statuses:
            #     return {'message': 'Invalid project status'}, HTTPStatus.BAD_REQUEST

            # Update the project status
            project.projectStatus = new_status
            project.startDate = datetime.utcnow().date()

            # Save the updated project status to the database
            try:
                db.session.commit()
                # Check if the new status is 'Approved' and add stages if true
                if new_status == "APPROVED":
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
                new_question.save()
                # If the question is multiple choice, add choices
                if question_data['questionType'] == 'single choice':
                    choices_data = question_data.get('choices',[])
                    for choice_data in choices_data:
                        new_choice = QuestionChoices(
                            questionID=new_question.questionID,
                            choiceText=choice_data['choiceText'],
                            points=choice_data['points']
                        )
                        db.session.add(new_choice)
                elif question_data['questionType'] == 'multi choice':
                    choices_data = question_data.get('choices', [])
                    for choice_data in choices_data:
                        new_choice = QuestionChoices(
                            questionID=new_question.questionID,
                            choiceText=choice_data['choiceText'],
                            points=choice_data['points']
                        )
                        db.session.add(new_choice)
                else:
                    new_question.points = question_data['points']
                    
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

@project_namespace.route('/user-projects/<string:username>', methods=['GET'])
class UserProjectsResource(Resource):
    def get(self, username):
        # Replace 'user_id' with the actual way you get the user ID
        user = Users.query.filter_by(username=username).first()

        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Fetch projects associated with the user using the ProjectUser model
        projects = (
            Projects.query.join(ProjectUser)
            .filter(ProjectUser.userID == user.userID)
            .distinct(Projects.projectID)
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

@project_namespace.route('/<int:project_id>/answers', methods=['GET'])
class ProjectAnswersResource(Resource):
    def get(self, project_id):
        # Get the project by ID
        project = Projects.get_by_id(project_id)

        if not project:
            return jsonify({'message': 'Project not found'}), HTTPStatus.NOT_FOUND

        # Fetch all answers associated with the project
        all_answers = Answers.query.filter_by(projectID=project_id).all()

        # Prepare an ordered dictionary to store answers by question ID
        answers_by_question = OrderedDict()
        for answer in all_answers:
            if answer.questionID not in answers_by_question:
                answers_by_question[answer.questionID] = {'questionID': answer.questionID, 'answers': []}
            answers_by_question[answer.questionID]['answers'].append(answer)

        # Convert the list of answers to a JSON response
        response_data = []

        # Process each question and its associated answers
        for question_id, question_data in answers_by_question.items():
            question = Questions.get_by_id(question_id)

            if question.questionType == 'single choice':
                # For single-choice questions, include the selected choice details in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('questionText', question.questionText),
                    ('questionType', 'single choice'),
                    ('answers', [{
                        'answerID': answer.answerID,
                        'choiceID': answer.choiceID,
                        'choiceText': QuestionChoices.get_by_id(answer.choiceID).choiceText,
                        'points': QuestionChoices.get_by_id(answer.choiceID).points
                    } for answer in question_data['answers']])
                ]))
            elif question.questionType == 'multi choice':
                # For multi-choice questions, include all selected choices in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('questionText', question.questionText),
                    ('questionType', 'multi choice'),
                    ('answers', [{
                        'answerID': answer.answerID,
                        'choiceID': choice_id,
                        'choiceText': QuestionChoices.get_by_id(choice_id).choiceText,
                        'points': QuestionChoices.get_by_id(choice_id).points
                    } for answer in question_data['answers'] for choice_id in (
                        [answer.choiceID] if isinstance(answer.choiceID, int) else answer.choiceID)
                    ])
                ]))
            else:
                # For text-based questions, include the answer text in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('questionText', question.questionText),
                    ('questionType', 'text'),
                    ('answers', [{
                        'answerID': answer.answerID,
                        'answerText': answer.answerText
                    } for answer in question_data['answers']])
                ]))

        return jsonify(OrderedDict([('answers', response_data)]))

@project_namespace.route('/<int:project_id>/answers/minified', methods=['GET'])
class ProjectMinifiedAnswersResource(Resource):
    def get(self, project_id):
        # Get the project by ID
        project = Projects.get_by_id(project_id)

        if not project:
            return jsonify({'message': 'Project not found'}), HTTPStatus.NOT_FOUND

        # Fetch all answers associated with the project
        all_answers = Answers.query.filter_by(projectID=project_id).all()

        # Prepare an ordered dictionary to store answers by question ID
        answers_by_question = OrderedDict()
        for answer in all_answers:
            if answer.questionID not in answers_by_question:
                answers_by_question[answer.questionID] = {'questionID': answer.questionID, 'answers': []}
            answers_by_question[answer.questionID]['answers'].append(answer)

        # Convert the list of answers to a JSON response
        response_data = []

        # Process each question and its associated answers
        for question_id, question_data in answers_by_question.items():
            question = Questions.get_by_id(question_id)

            if question.questionType == 'single choice':
                # For single-choice questions, include the selected choice details in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('answer', {
                        'choiceID': question_data['answers'][0].choiceID,
                        'choiceText': QuestionChoices.get_by_id(question_data['answers'][0].choiceID).choiceText
                    })
                ]))
            elif question.questionType == 'multi choice':
                # For multi-choice questions, include all selected choices in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('answer', {
                        'choiceID': [choice.choiceID for choice in question_data['answers']],
                        'choiceText': [QuestionChoices.get_by_id(choice.choiceID).choiceText for choice in
                                       question_data['answers']]
                    })
                ]))
            else:
                # For text-based questions, include the answer text in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('answer', {'answerText': question_data['answers'][0].answerText})
                ]))

        return jsonify(OrderedDict([('answers', response_data)]))


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
        if current_user.userID != project.userID and not current_user.is_admin:
            return {'message': 'Unauthorized. You do not have permission to edit this project.'}, HTTPStatus.FORBIDDEN

        # Parse the input data
        project_data = request.json
        edited_answers_data = project_data.pop('edited_answers', [])  # Extract edited answers from project_data


        # Save the updated project details to the database
        try:
            # 

            # Update the answers for the project
            project.edit_answers(project_id,edited_answers_data)
            db.session.commit()

            return {'message': 'Project details and answers updated successfully'}, HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error updating project details and answers: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@project_namespace.route('/edit_details/<int:project_id>', methods=['PATCH'])
class ProjectEditDetailsResource(Resource):
    @jwt_required()
    @project_namespace.expect(project_edit_details_model)
    def patch(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the project by ID
        project = Projects.query.get_or_404(project_id)

        # Ensure the current user is authorized to edit the project
        if current_user.userID != project.userID and not current_user.is_admin:
            return {'message': 'Unauthorized. You do not have permission to edit this project.'}, HTTPStatus.FORBIDDEN

        # Parse the input data
        project_data = request.json

        # Update the project details conditionally
        for field in ['projectName', 'regionID', 'budgetRequired', 'projectStatus',
                      'projectScope', 'category', 'startDate', 'dueDate']:
            if field in project_data:
                setattr(project, field, project_data[field])

        # Save the updated project details to the database
        try:
            db.session.commit()
            return {'message': 'Project details updated successfully'}, HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error updating project details: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@project_namespace.route('/delete/<int:project_id>')
class ProjectDeleteResource(Resource):
    @jwt_required()  
    def delete(self, project_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the project exists and belongs to the current user
        if current_user.is_admin:
            project_to_delete = Projects.query.get_or_404(project_id)
        else:
            project_to_delete = Projects.query.filter_by(projectID=project_id, userID=current_user.userID).first()

            if not project_to_delete:
                return {'message': 'Project not found or unauthorized'}, HTTPStatus.NOT_FOUND

        try:
            # Delete associated data
            self.delete_associated_data(project_to_delete)

            # Delete the project
            project_to_delete.delete()

            return {'message': 'Project and associated data deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error deleting project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

    def delete_associated_data(self, project):
        # Delete associated data (use this method to handle relationships)
        Answers.query.filter_by(projectID=project.projectID).delete()
        AssessmentAnswers.query.filter_by(projectID=project.projectID).delete()

        # Delete linked projects
        ProjectUser.query.filter_by(projectID=project.projectID).delete()
        
        #Delete linked stages
        ProjectStage.query.filter_by(projectID=project.projectID).delete()
        # Delete Tasks
        task_ids = [task.taskID for task in ProjectTask.query.filter_by(projectID=project.projectID).all()]

        # Delete associated TaskComments rows
        TaskComments.query.filter(TaskComments.taskID.in_(task_ids)).delete()
        #Delete Tasks
        ProjectTask.query.filter_by(projectID=project.projectID).delete()

        #Delete Project Status Data
        ProjectStatusData.query.filter_by(projectID=project.projectID).delete()
        
        
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

        # Delete the choices related to the question
        QuestionChoices.query.filter_by(questionID=question_id).delete()

        # Delete the question from the database
        try:
            question_to_delete.delete()

            return {'message': 'Question and associated answers and choices deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error deleting question: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
   
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





@project_namespace.route('/all_with_answers', methods=['GET'])
class AllProjectsWithAnswersResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            if not current_user:
                return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

            # Check if the user is an admin
            if current_user.is_admin:
                # If admin, fetch all projects
                projects = Projects.query.all()
            else:
                # If not admin, fetch projects linked to the user through ProjectUser model
                user_projects = ProjectUser.query.filter_by(userID=current_user.userID).all()
                projects = [project_user.project for project_user in user_projects]
                

            if not projects:
                return {'message': 'No projects found'}, HTTPStatus.NOT_FOUND

            # Initialize a list to store project data
            projects_data = []

            # Iterate through each project
            for project in projects:
                
                # Fetch all answers associated with the project
                all_answers = Answers.query.filter_by(projectID=project.projectID).all()

                # Prepare an ordered dictionary to store answers by question ID
                answers_by_question = OrderedDict()
                for answer in all_answers:
                    if answer.questionID not in answers_by_question:
                        answers_by_question[answer.questionID] = {'questionID': answer.questionID, 'answers': []}
                    answers_by_question[answer.questionID]['answers'].append(answer)

                # Convert the list of answers to a JSON response
                response_data = []

                # Process each question and its associated answers
                for question_id, question_data in answers_by_question.items():
                    question = Questions.get_by_id(question_id)

                    extras = question_data['answers'][0].extras if hasattr(question_data['answers'][0], 'extras') else None
                    if question.questionType == 'single choice':
                        # For single-choice questions, include the selected choice details in the response
                        response_data.append(OrderedDict([
                            ('questionID', question_id),
                            ('answer', {
                                'choiceID': question_data['answers'][0].choiceID,
                                'choiceText': QuestionChoices.get_by_id(question_data['answers'][0].choiceID).choiceText,
                                'extras': extras
                            })
                        ]))
                    elif question.questionType == 'multi choice':
                        # For multi-choice questions, include all selected choices in the response
                        response_data.append(OrderedDict([
                            ('questionID', question_id),
                            ('answer', {
                                'choices': [choice.choiceID for choice in question_data['answers']],
                                'choiceText': [QuestionChoices.get_by_id(choice.choiceID).choiceText for choice in
                                            question_data['answers']]
                            })
                        ]))
                    else:
                        # For text-based questions, include the answer text in the response
                        response_data.append(OrderedDict([
                            ('questionID', question_id),
                            ('answer', {'answerText': question_data['answers'][0].answerText})
                        ]))

                order_answers = response_data

                # Include answers and corresponding questions in the project details
                project_details = {
                    'projectID': project.projectID,
                    'projectName': project.projectName,
                    'projectStatus': project.projectStatus.value,
                    'createdAt': project.createdAt,
                    'startDate': project.startDate,
                    'dueDate': project.dueDate,
                    'userID': project.userID,
                    'userFullName': current_user.firstName + current_user.lastName,
                    'username': current_user.username,
                    'regionID': project.regionID,
                    'budgetRequired': project.budgetRequired,
                    'budgetAvailable': project.budgetAvailable,
                    'projectScope': project.projectScope,
                    'category': project.category.value,
                    'answers': order_answers
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
            questions = Questions.query.order_by(Questions.order).all()

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
                if question.questionType == 'single choice' or  question.questionType == 'multi choice':
                    choices = QuestionChoices.query.filter_by(questionID=question.questionID).all()
                    choices_data = [{'choiceID': choice.choiceID, 'choiceText': choice.choiceText, 'points': choice.points} for choice in choices]
                    question_details['choices'] = choices_data

                # Append question details to the list
                questions_data.append(question_details)

            return jsonify({'questions': json.loads(json.dumps(questions_data, sort_keys=True))})

        except Exception as e:
            current_app.logger.error(f"Error retrieving questions: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@project_namespace.route('/add_choice/<int:question_id>', methods=['POST'])
class AddChoiceToQuestionResource(Resource):
    @project_namespace.expect(edit_choice)
    @project_namespace.doc(
        params={
            'question_id': 'Specify the ID of the question'
        },
        description = "Add a choice to a question"
    )
    @project_namespace.marshal_with(edit_choice_with_choice_id, code=201)
    def post(self, question_id):
        try:
            # Get the existing question by ID
            question = Questions.query.get_or_404(question_id)

            # Extract choice data from the request
            data = request.get_json()
            choice_text = data.get('new_choice_text')
            points = data.get('points')

            # Validate input
            if not choice_text or not points:
                return jsonify({'error': 'Choice text and points are required'}), 400

            # Create and add the new choice to the question
            new_choice = question.add_choice(choice_text, points)
            # question.add_choice(choice_text, points)

            return new_choice, 201

        except Exception as e:
            current_app.logger.error(f"Error adding choice to question: {str(e)}")
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
    @stage_namespace.doc(
        description = "Link a project to a stage"
    )
    def post(self):
        try:
            # Get project and stage IDs from the request data
            data = stage_namespace.payload
            project_id = data.get('project_id')
            stage_id = data.get('stage_id')
            started = data.get('started')
            completed = data.get('completed')
            completionDate = data.get('completionDate')

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
                                              started=started, completed=completed,
                                              completionDate=completionDate)
            db.session.add(project_stage_link)
            db.session.commit()

            return {'message': 'Project linked to stage successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error linking project to stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
@stage_namespace.route('/stages_for_project/<int:project_id>', methods=['GET'])
class StagesForProjectResource(Resource):
    @jwt_required()
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
    @jwt_required()
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
                status = TaskStatus.TODO
            )

            # Save the new task to the database
            db.session.add(new_task)
            db.session.commit()

            return {'message': 'Task added for the linked stage successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding task for linked stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@task_namespace.route('/edit_task/<int:task_id>', methods=['PUT'])
class EditTaskForStageResource(Resource):
    @task_namespace.expect(edit_task_model, validate=True)
    @jwt_required()
    def put(self, task_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # Check if the current user has permission to delete a stage
        if not current_user.is_admin:  # Adjust the condition based on your specific requirements
            return {'message': 'Unauthorized. Only admin users can edit Task details.'}, HTTPStatus.FORBIDDEN

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
            assigned_to_ids = data.get('assigned_to', [])
            cc_ids = data.get('cc', [])
            task.attachedFiles = data.get('attached_files', task.attachedFiles)

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

@task_namespace.route('/assign_task/<int:task_id>', methods=['PUT'])
class AssignTaskResource(Resource):
    @task_namespace.expect(assign_task, validate=True)
    @jwt_required()
    def put(self, task_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # Check if the current user has permission to delete a stage
        if not current_user.is_admin:  # Adjust the condition based on your specific requirements
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
        if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
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
        if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
            return {'message': 'Unauthorized. Only admin users can add answers.'}, HTTPStatus.FORBIDDEN

        # Parse the input data for answers
        assessment_data = request.json
        answers_data = assessment_data.pop('answers', [])
        try:
            # get the project this assessment is for
            project = Projects.get_by_id(assessment_data['projectID'])
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
                    db.session.commit()
                else:
                    # If no answer exists, create a new one
                    new_answer = AssessmentAnswers(
                        questionID=question_id,
                        projectID=assessment_data['projectID'],
                        answerText=answer['answerText']
                    )
                
                    new_answer.save()
            #now update project status to PENDING
            project.projectStatus = ProjectStatus.PENDING
            db.session.commit()
            return {'message': 'All Assessment Answers were saved.'}, HTTPStatus.OK
                
        except Exception as e:
            current_app.logger.error(f"Error In adding AssessmentQuestion: {str(e)}")
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
                .add_columns(AssessmentQuestions.questionText, AssessmentAnswers.answerText)
                .all()
            )

            # Convert the list of answers to a JSON response
            answers_data = [
                {
                    'questionText': question_text,
                    'answerText': answer_text,
                }
                for _, question_text, answer_text in assessment_answers
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
        if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
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
        if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
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
                    'cc': [user.username for user in task.cc],
                    'createdBy': task.createdBy,
                    'attachedFiles': task.attachedFiles,
                    'status': task.status.value,
                    'completionDate': str(task.completionDate) if task.completionDate else None,
                    'comments': comments_list
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
            project = Projects.get_by_id(project_id)
            
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
                    'title': task.title,
                    'deadline': str(task.deadline),
                    'description': task.description,
                    'assignedTo': [user.username for user in task.assignedTo],
                    'cc': [user.username for user in task.cc],
                    'createdBy': task.createdBy,
                    'attachedFiles': task.attachedFiles,
                    'status': task.status.value,
                    'completionDate': str(task.completionDate) if task.completionDate else None,
                    'comments': comments_list
                })

            return {'tasks': tasks_list}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting tasks for project: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR