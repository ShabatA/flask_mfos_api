from flask import request
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus
from ..models.projects import Projects, Questions, QuestionChoices, Answers, ProjectUser
from ..utils.db import db
from ..models.users import Users
from flask import jsonify


project_namespace = Namespace('project', description="A namespace for projects")


answers_model = project_namespace.model('Answers', {
    'question_id': fields.Integer(required=True, description='ID of the answer'),
    'answer_text': fields.String(description='Text-based answer for a text question'),
    'choice_id': fields.Integer(description='ID of the selected choice for a single-choice question')
})

# Define the expected input model using Flask-RESTx fields
project_input_model = project_namespace.model('ProjectInput', {
    'projectName': fields.String(required=True, description='Name of the project'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the project'),
    'budgetAvailable': fields.Float(required=True, description='Available budget for the project'),
    'projectStatus': fields.String(required=True, enum=['initialized', 'closed', 'pending', 'in progress', 'rejected'], description='Status of the project'),
    'projectScope': fields.String(description='Scope of the project'),
    'category': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the project'),
    'userID': fields.Integer(description='ID of the user associated with the project'),
    'startDate': fields.Date(description='Start date of the project'),
    'dueDate': fields.Date(description='Due date of the project'),
    'answers': fields.List(fields.Nested(answers_model), description='List of answers for the project')
})

project_status = project_namespace.model('ProjectStatus',{
    'projectStatus': fields.String(required=True, enum=['initialized', 'closed', 'pending', 'in progress', 'rejected'], description='Status of the project'),
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
    'projectStatus': fields.String(required=True, enum=['initialized', 'closed', 'pending', 'in progress', 'rejected'], description='Status of the project'),
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
    #[
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
        projects_data = [{'projectID': project.projectID, 'projectName': project.projectName} for project in projects]

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

        # Check if the current user has the necessary permissions (e.g., project owner or admin)
        # Adjust the condition based on your specific requirements
        if not current_user.is_admin and current_user.userID != project_to_access.ownerID:
            return {'message': 'Unauthorized. You do not have permission to give access to this project.'}, HTTPStatus.FORBIDDEN

        # Get the project by ID
        project_to_access = Projects.query.get(project_id)
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

            # Check if the new status is valid
            if new_status not in ['INITIALIZED', 'CLOSED', 'PENDING', 'IN_PROGRESS', 'REJECTED']:
                return {'message': 'Invalid project status'}, HTTPStatus.BAD_REQUEST

            # Update the project status
            project.projectStatus = new_status

            # Save the updated project status to the database
            try:
                db.session.commit()
                return {'message': 'Project status changed successfully', 'new_status': new_status}, HTTPStatus.OK
            except Exception as e:
                db.session.rollback()
                return {'message': f'Error changing project status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            return {'message': 'Unauthorized. You do not have permission to change the status of this project.'}, HTTPStatus.FORBIDDEN



# project with username
        