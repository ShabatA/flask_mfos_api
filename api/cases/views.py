from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from http import HTTPStatus
from ..models.cases import Cases, CaseStatus, CaseUser, CQuestions, CQuestionChoices, CAnswers
from ..models.users import Users
from ..models.regions import Regions
from ..utils.db import db
from datetime import datetime
from flask import jsonify, current_app
from flask import request
import json


def get_region_id_by_name(region_name):
    region = Regions.query.filter_by(regionName=region_name).first()

    if region:
        return region.regionID
    else:
        return None  # Or any other value to indicate that the regionName was not found

case_namespace = Namespace("Cases", description="Namespace for cases")

answers_model = case_namespace.model('CAnswers', {
    'question_id': fields.Integer(required=True, description='ID of the answer'),
    'answer_text': fields.String(description='Text-based answer for a text question'),
    'choice_id': fields.Integer(description='ID of the selected choice for a single-choice question')
})

question_input_model = case_namespace.model('QuestionInput', {
    'questionText': fields.String(required=True, description='Text of the question'),
    'questionType': fields.String(required=True, description='Type of the question'),
    'points': fields.Integer(required=True, description='Points for the question'),
    'choices': fields.List(fields.String, description='List of choices for multiple-choice questions')
})

case_model = case_namespace.model(
    'Case', {
        'caseName': fields.String(required=True, description="A case name"),
        'budgetRequired': fields.Float(required=True, description="Budget required"),
        'budgetAvailable': fields.Float(required=True, description="Budget available"),
        'caseCategory': fields.String(description="Case category"),
        'caseStatus': fields.String(enum=[status.value for status in CaseStatus], description="Case status"),
        'serviceRequired': fields.String(description="Service Required"),
        'regionName': fields.String(required=True, description="Region Name"),
        'answers': fields.List(fields.Nested(answers_model), description='List of answers for the case')
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

edited_answers_model = case_namespace.model('EditedAnswers', {
    'answer_id': fields.Integer(required=True, description='ID of the answer'),
    'new_answer_text': fields.String(description='Text-based answer for a text question'),
    'new_choice_id': fields.Integer(description='ID of the selected choice for a single-choice question')
})

case_edit_model = case_namespace.model('CaseEdit', {
    'caseName': fields.String(required=True, description='Name of the case'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the case'),
    'budgetAvailable': fields.Float(required=True, description='Available budget for the case'),
    'caseStatus': fields.String(required=True, enum=['initialized', 'closed', 'pending', 'in progress', 'rejected'], description='Status of the case'),
    # 'projectScope': fields.String(description='Scope of the project'),
    'caseCategory': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the case'),
    'userID': fields.Integer(description='ID of the user associated with the case'),
    'startDate': fields.Date(description='Start date of the case'),
    'dueDate': fields.Date(description='Due date of the case'),
    'edited_answers': fields.List(fields.Nested(edited_answers_model), description='List of edited answers for the case')
})


@case_namespace.route('/add')
class CaseAddResource(Resource):
    @jwt_required()  
    @case_namespace.expect(case_model)
    @case_namespace.doc(
        description='Add a new case',
        responses={
            201: 'Case added successfully',
            409: 'Case with the same name already exists',
            500: 'Internal Server Error'
        },
        body=case_model,
        examples={
            'success': {
                'description': 'Case added successfully',
                'summary': 'Successful Response',
                'value': {'message': 'Case added successfully'}
            },
            'conflict': {
                'description': 'Case with this name already exists',
                'summary': 'Conflict Response',
                'value': {'message': 'Case with this name already exists'}
            },
            'error': {
                'description': 'Error adding case: Internal Server Error',
                'summary': 'Internal Server Error Response',
                'value': {'message': 'Error adding case: Internal Server Error'}
            }
        }
    )
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Parse the input data
        case_data = request.json
        answers_data = case_data.pop('answers', [])  

        # Check if a case with the given name already exists
        existing_case = Cases.query.filter_by(caseName=case_data['caseName']).first()
        if existing_case:
            return {'message': 'Case with this name already exists'}, HTTPStatus.CONFLICT
        
        # get the regionID from the regionName
        region_id = get_region_id_by_name(case_data['regionName'])

        # Create a new case instance
        new_case = Cases(
            caseName = case_data['caseName'],
            regionID = region_id,
            budgetRequired = case_data['budgetRequired'],
            budgetAvailable = case_data['budgetAvailable'],
            caseStatus = case_data['caseStatus'],
            caseCategory = case_data['caseCategory'],
            serviceRequired = case_data['serviceRequired'],
            userID=current_user.userID,
            createdAt = datetime.utcnow().date(),
            startDate = datetime.utcnow().date(),
            dueDate = datetime.utcnow().date()
        )

        # Save the project to the database
        try:
            new_case.save()

            # Assign answers to the project
            new_case.assign_answers(answers_data)

            # Add the current user to the ProjectUsers table for the new project
            project_user = CaseUser(caseID=new_case.caseID, userID=current_user.userID)
            project_user.save()

            return {'message': 'case added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding case: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_namespace.route('/add_questions')
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
    @case_namespace.expect([question_input_model]) 
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
                new_question = CQuestions(
                    questionText=question_data['questionText'],
                    questionType=question_data['questionType'],
                    points=0,
                )

                # If the question is multiple choice, add choices
                if question_data['questionType'] == 'single choice':
                    choices_data = question_data.get('choices', [])
                    for choice_data in choices_data:
                        new_choice = CQuestionChoices(
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
        
@case_namespace.route('/all_questions', methods=['GET'])
class AllQuestionsResource(Resource):
    def get(self):
        try:
            # Get all questions
            questions = CQuestions.query.all()

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
                    choices = CQuestionChoices.query.filter_by(questionID=question.questionID).all()
                    choices_data = [{'choiceID': choice.choiceID, 'choiceText': choice.choiceText, 'points': choice.points} for choice in choices]
                    question_details['choices'] = choices_data

                # Append question details to the list
                questions_data.append(question_details)

            return jsonify({'questions': json.loads(json.dumps(questions_data, sort_keys=True))})

        except Exception as e:
            current_app.logger.error(f"Error retrieving questions: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_namespace.route('/all_cases_with_answers', methods=['GET'])
class AllProjectsWithAnswersResource(Resource):
    def get(self):
        try:
            # Get all projects
            cases = Cases.query.all()

            # Initialize a list to store project data
            cases_data = []

            # Iterate through each project
            for case in cases:
                # Get project details
                case_details = {
                    'caseID': case.caseID,
                    'caseName': case.caseName,
                    'caseStatus': case.caseStatus.value,
                    'startDate': case.startDate,
                    'dueDate': case.dueDate
                }

                # Get answers associated with the project
                text_answers = CAnswers.query.filter_by(caseID=case.caseID, choiceID=None).all()
                choice_answers = CAnswers.query.filter(CAnswers.caseID == case.caseID,
                                                       CAnswers.choiceID.isnot(None)).all()

                # Include text-based answers in the project details
                text_answers_data = [{'answerID': answer.answerID, 'questionID': answer.questionID,
                                      'answerText': answer.answerText} for answer in text_answers]

                # Include choice-based answers in the project details, including choice details
                choice_answers_data = [{
                    'answerID': answer.answerID,
                    'questionID': answer.questionID,
                    'choiceID': answer.choiceID,
                    'choiceText': answer.choice.choiceText,  # Include choice details in the response
                    'points': answer.choice.points
                } for answer in choice_answers]

                # Add answers data to project details
                case_details['text_answers'] = text_answers_data
                case_details['choice_answers'] = choice_answers_data

                # Append project details to the list
                cases_data.append(case_details)

            return jsonify({'projects_with_answers': cases_data})

        except Exception as e:
            current_app.logger.error(f"Error retrieving projects with answers: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/<int:case_id>/answers', methods=['GET'])
class CaseAnswersResource(Resource):
    def get(self, case_id):
        # Get the project by ID
        case = Cases.get_by_id(case_id)

        if not case:
            return jsonify({'message': 'Project not found'}), HTTPStatus.NOT_FOUND

        # Fetch both text-based and choice-based answers associated with the project
        text_answers = CAnswers.query.filter_by(caseID=case_id, choiceID=None).all()
        choice_answers = CAnswers.query.filter(CAnswers.caseID == case_id, CAnswers.choiceID.isnot(None)).all()

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
    

@case_namespace.route('/edit_answers/<int:case_id>', methods=['PUT'])
class CaseEditAnswersResource(Resource):
    @jwt_required()
    @case_namespace.expect(case_edit_model)
    def put(self, case_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the case by ID
        case = Cases.query.get_or_404(case_id)

        # Ensure the current user is authorized to edit the project
        if current_user.userID != case.userID:
            return {'message': 'Unauthorized. You do not have permission to edit this project.'}, HTTPStatus.FORBIDDEN

        # Parse the input data
        project_data = request.json
        edited_answers_data = project_data.pop('edited_answers', [])  # Extract edited answers from project_data

        # Update the case details
        case.projectName = project_data.get('caseName', case.caseName)
        case.regionID = project_data.get('regionID', case.regionID)
        case.budgetRequired = project_data.get('budgetRequired', case.budgetRequired)
        case.budgetAvailable = project_data.get('budgetAvailable', case.budgetAvailable)
        case.projectStatus = project_data.get('projectStatus', case.projectStatus)
        case.caseCategory = project_data.get('caseCategory', case.caseCategory)
        case.startDate = project_data.get('startDate', case.startDate)
        case.dueDate = project_data.get('dueDate', case.dueDate)

        # Save the updated project details to the database
        try:
            db.session.commit()

            # Update the answers for the project
            case.edit_answers(edited_answers_data)

            return {'message': 'Project details and answers updated successfully'}, HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error updating project details and answers: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/delete/<int:case_id>')
class CaseDeleteResource(Resource):
    @jwt_required()  
    def delete(self, case_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the project exists and belongs to the current user
        if current_user.is_admin:
            case_to_delete = Cases.query.filter_by(caseID=case_id).first()
        else:
            case_to_delete = Cases.query.filter_by(caseID=case_id, userID=current_user.userID).first()
        if not case_to_delete:
            return {'message': 'case not found or unauthorized'}, HTTPStatus.NOT_FOUND

        # Delete the answers related to the project
        CAnswers.query.filter_by(caseID=case_id).delete()

        # Delete the project from the database
        try:
            case_to_delete.delete()

            return {'message': 'Case and associated answers deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error deleting case: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
@case_namespace.route('/delete_question/<int:question_id>')
class QuestionDeleteResource(Resource):
    @jwt_required()  
    def delete(self, question_id):
        # Check if the question exists
        question_to_delete = CQuestions.query.get(question_id)
        if not question_to_delete:
            return {'message': 'Question not found'}, HTTPStatus.NOT_FOUND

        # Delete the answers related to the question
        CAnswers.query.filter_by(questionID=question_id).delete()

        # Delete the question from the database
        try:
            question_to_delete.delete()

            return {'message': 'Question and associated answers deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error deleting question: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/give_access/<int:case_id>/<int:user_id>')
class GiveAccessResource(Resource):
    @jwt_required()
    def post(self, case_id, user_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # Get the project by ID
        case_to_access = Cases.query.get(case_id)
        # Check if the current user has the necessary permissions (e.g., project owner or admin)
        # Adjust the condition based on your specific requirements
        if not current_user.is_admin and current_user.userID != case_to_access.userID:
            return {'message': 'Unauthorized. You do not have permission to give access to this case.'}, HTTPStatus.FORBIDDEN

        
        if not case_to_access:
            return {'message': 'case not found'}, HTTPStatus.NOT_FOUND

        # Get the user by ID
        user_to_give_access = Users.query.get(user_id)
        if not user_to_give_access:
            return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        # Check if the user already has access to the project
        if CaseUser.query.filter_by(caseID=case_id, userID=user_id).first():
            return {'message': 'User already has access to the case'}, HTTPStatus.BAD_REQUEST

        # Add the user to the project's list of users
        case_user = CaseUser(caseID=case_id, userID=user_id)
        case_user.save()

        return {'message': 'User granted access to the case successfully'}, HTTPStatus.OK











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
