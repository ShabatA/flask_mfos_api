from flask import request
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus
from ..models.projects import Projects, Questions, QuestionChoices
from ..utils.db import db
from ..models.users import Users

project_namespace = Namespace('project', description="A namespace for projects")

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
    'dueDate': fields.Date(description='Due date of the project')
})


question_input_model = project_namespace.model('QuestionInput', {
    'questionText': fields.String(required=True, description='Text of the question'),
    'questionType': fields.String(required=True, description='Type of the question'),
    'points': fields.Integer(required=True, description='Points for the question'),
    'choices': fields.List(fields.String, description='List of choices for multiple-choice questions')
})

@project_namespace.route('/add')
class ProjectAddResource(Resource):
    @jwt_required()  # Requires a valid JWT token
    @project_namespace.expect(project_input_model)  # Expecting input in the specified format
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Parse the input data
        project_data = request.json

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
            return {'message': 'Project added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding project: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        
@project_namespace.route('/add_questions')
class ProjectAddQuestionsResource(Resource):
    @jwt_required()  # Requires a valid JWT token
    @project_namespace.expect([question_input_model])  # Expecting input in the specified format
    def post(self):
        # Get the current user from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is an admin
        if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
            return {'message': 'Unauthorized. Only admin users can add questions.'}, HTTPStatus.FORBIDDEN

        # Parse the input data for questions
        questions_data = request.json

        # Add questions to the database
        try:
            for question_data in questions_data:
                new_question = Questions(
                    questionText=question_data['questionText'],
                    questionType=question_data['questionType'],
                    points=question_data['points'],
                    # projectID=None  # This will be updated later
                )

                # If the question is multiple choice, add choices
                if question_data['questionType'] == 'multiple_choice':
                    choices_data = question_data.get('choices', [])
                    for choice_text in choices_data:
                        new_choice = QuestionChoices(
                            question=new_question,
                            choiceText=choice_text
                        )
                        db.session.add(new_choice)

                db.session.add(new_question)

            db.session.commit()

            # # Update the projectID in each question
            # for new_question in Questions.query.filter_by(projectID=None):
            #     new_question.projectID = current_project.projectID

            db.session.commit()

            return {'message': 'Questions added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            db.session.rollback()
            return {'message': f'Error adding questions: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        finally:
            db.session.close()
