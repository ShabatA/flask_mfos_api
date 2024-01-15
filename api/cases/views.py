from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from http import HTTPStatus

from api.utils.case_requirement_processor import CaseRequirementProcessor
from ..models.cases import Cases, CaseStatus, CaseUser, CQuestions, CQuestionChoices, CAnswers, CaseTaskAssignedTo, CaseStage, CaseToStage, CaseTaskComments, CaseStatusData, CaseTask, CaseTaskCC, CaseTaskStatus
from ..models.users import Users
from ..models.regions import Regions
from ..utils.db import db
from datetime import datetime, date
from flask import jsonify, current_app
from flask import request
import json
from collections import OrderedDict


def get_region_id_by_name(region_name):
    region = Regions.query.filter_by(regionName=region_name).first()

    if region:
        return region.regionID
    else:
        return None  # Or any other value to indicate that the regionName was not found

case_namespace = Namespace("Cases", description="Namespace for cases")
case_stage_namespace = Namespace('Case Stages', description="A namespace for case Stages")
case_task_namespace = Namespace('Case Tasks', description="A namespace for case Tasks")

stage_model = case_stage_namespace.model(
    'Stage', {
        'name': fields.String(required=True, description='Name of the stage'),
    }
)

case_update_status_model = case_namespace.model('CaseUpdateStatus', {
    'caseStatus': fields.String(required=True, enum=['approved', 'pending','rejected', 'inprogress', 'completed'], description='Status of the case'),
    'status_data': fields.Raw(description='Status data associated with the case'),
})

case_status_data = case_namespace.model('CaseStatus', {
    
    'status_data': fields.Raw(description='Status data associated with the case'),
})

answers_model = case_namespace.model('CAnswers', {
    'questionID': fields.Integer(required=True, description='ID of the answer'),
    'answerText': fields.String(description='Text-based answer for a text question'),
    'choiceID': fields.List(fields.Integer, description='List of choices')
})

comments_model = case_task_namespace.model('CaseTaskComments',{
    'taskID': fields.Integer(required=True, description='Id of the task the comment belongs to'),
    'comment': fields.String(required=True, description= 'The comment written by the user'),
    'date': fields.Date(required=True, description='Date on which the comment was made')
})

question_input_model = case_namespace.model('QuestionInput', {
    'questionText': fields.String(required=True, description='Text of the question'),
    'questionType': fields.String(required=True, description='Type of the question'),
    'points': fields.Integer(required=True, description='Points for the question'),
    'choices': fields.List(fields.String, description='List of choices for multiple-choice questions')
})

# Define a model for the input data (assuming JSON format)
new_task_model = case_task_namespace.model('NewTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    # 'created_by': fields.Integer(required=True, description='User ID of the task creator'),
    'attached_files': fields.String(description='File attachments for the task'),
    # 'stage_id': fields.Integer(required=True, description='ID of the linked stage'),
})

edit_task_model = case_task_namespace.model('EditTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    'attached_files': fields.String(description='File attachments for the task')
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

# Define the expected input model using Flask-RESTx fields
case_input_model = case_namespace.model('CaseInput', {
    'caseName': fields.String(required=True, description='Name of the case'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the case'),
    'budgetAvailable': fields.Float(required=True, description='Available budget for the case'),
    'caseStatus': fields.String(required=True, enum=['approved', 'pending','inprogress','rejected', 'completed'], description='Status of the case'),
    'serviceRequired': fields.String(required=True, description='The service that is needed'),
    'category': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the case'),
    'userID': fields.Integer(description='ID of the user associated with the case'),
    'dueDate': fields.Date(description='Due date of the case'),
    'answers': fields.List(fields.Nested(answers_model), description='List of answers for the case')
})



case_model_2 = case_namespace.model(
    'Case2', {
        'caseName': fields.String(required=True, description="A case name"),
        'budgetRequired': fields.Float(required=True, description="Budget required"),
        'budgetAvailable': fields.Float(required=True, description="Budget available"),
        'caseCategory': fields.String(description="Case category"),
        'caseStatus': fields.String(enum=[status.value for status in CaseStatus], description="Case status"),
    })

edited_answers_model = case_namespace.model('EditedAnswers', {
    'questionID': fields.Integer(required=True, description='ID of the question'),
    'answerText': fields.String(description='Text-based answer for a text question'),
    'choiceID': fields.List(fields.Integer, description='List of choices')
})

case_edit_model = case_namespace.model('CaseEdit', {
    'caseName': fields.String(required=True, description='Name of the case'),
    'regionID': fields.Integer(required=True, description='ID of the region'),
    'budgetRequired': fields.Float(required=True, description='Required budget for the case'),
    'budgetAvailable': fields.Float(required=True, description='Available budget for the case'),
    'caseStatus': fields.String(required=True, enum=['approved', 'pending','inprogress','rejected', 'completed'], description='Status of the case'),
    'serviceRequired': fields.String(required=True, description='The service that is needed'),
    'category': fields.String(enum=['A', 'B', 'C', 'D'], description='Category of the case'),
    'userID': fields.Integer(description='ID of the user associated with the case'),
    'edited_answers': fields.List(fields.Nested(answers_model), description='List of answers for the case')
})

# Define a model for the input data (assuming JSON format)
link_case_to_stage_model = case_stage_namespace.model('LinkCaseToStageModel', {
    'case_id': fields.Integer(required=True, description='ID of the case'),
    'stage_id': fields.Integer(required=True, description='ID of the stage'),
    'started': fields.Boolean(required=True, description="If the stage has been started"),
    'completed': fields.Boolean(required=True, description="If the stage has been completed"),
    'completionDate': fields.Date(description="Completion Date")
})


@case_namespace.route('/add')
class CaseAddResource(Resource):
    @jwt_required()  
    @case_namespace.expect(case_input_model)
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
        
        
        # Create a new case instance
        new_case = Cases(
            caseName = case_data['caseName'],
            regionID = case_data['regionID'],
            budgetRequired = case_data['budgetRequired'],
            budgetAvailable = case_data['budgetAvailable'],
            caseStatus = case_data['caseStatus'],
            caseCategory = case_data['category'],
            serviceRequired = case_data['serviceRequired'],
            userID=current_user.userID,
            createdAt = datetime.utcnow().date(),
            startDate = datetime.utcnow().date(),
            dueDate = datetime.utcnow().date()
        )

        # Save the case to the database
        try:
            new_case.save()

            # Assign answers to the case
            new_case.assign_answers(answers_data)

            # Add the current user to the CaseUsers table for the new case
            case_user = CaseUser(caseID=new_case.caseID, userID=current_user.userID)
            case_user.save()

            return {'message': 'case added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding case: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_namespace.route('/add_questions')
class CaseAddQuestionsResource(Resource):
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
                    choices_data = question_data.get('choices',[])
                    for choice_data in choices_data:
                        new_choice = CQuestionChoices(
                            question=new_question,
                            choiceText=choice_data['choiceText'],
                            points=choice_data['points']
                        )
                        db.session.add(new_choice)
                elif question_data['questionType'] == 'multi choice':
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
    @jwt_required()
    def get(self):
        try:
            # Get all questions
            questions = CQuestions.query.order_by(CQuestions.order).all()

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


@case_namespace.route('/admin/all_cases_with_answers', methods=['GET'])
class AllCasesWithAnswersResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Ensure the current user is authorized to edit the case
            if current_user.userID != case.userID and not current_user.is_admin:
                return {'message': 'Viewing all cases is reserved only for admins'}, HTTPStatus.FORBIDDEN
            # Get all cases
            cases = Cases.query.all()
            
            if not cases:
                return {'message': 'no cases found'}, HTTPStatus.NOT_FOUND

            # Initialize a list to store case data
            cases_data = []

            # Iterate through each case
            for case in cases:
                
                # Fetch all answers associated with the case
                all_answers = CAnswers.query.filter_by(caseID=case.caseID).all()

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
                    question = CQuestions.get_by_id(question_id)

                    if question.questionType == 'single choice':
                        # For single-choice questions, include the selected choice details in the response
                        response_data.append(OrderedDict([
                            ('questionID', question_id),
                            ('answer', {
                                'choiceID': question_data['answers'][0].choiceID,
                                'choiceText': CQuestionChoices.get_by_id(question_data['answers'][0].choiceID).choiceText
                            })
                        ]))
                    elif question.questionType == 'multi choice':
                        # For multi-choice questions, include all selected choices in the response
                        response_data.append(OrderedDict([
                            ('questionID', question_id),
                            ('answer', {
                                'choices': [choice.choiceID for choice in question_data['answers']],
                                'choiceText': [CQuestionChoices.get_by_id(choice.choiceID).choiceText for choice in
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
                
                # Get cases details
                case_details = {
                    'caseID': case.caseID,
                    'caseName': case.caseName,
                    'caseStatus': case.caseStatus.value,
                    'category': case.caseCategory.value,
                    'serviceRequired': case.serviceRequired,
                    'startDate': case.startDate,
                    'dueDate': case.dueDate,
                    'startDate': case.startDate,
                    'answers': order_answers
                }
                cases_data.append(case_details)
                

            return jsonify({'cases_with_answers': cases_data})

        except Exception as e:
            current_app.logger.error(f"Error retrieving cases with answers: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/user/all_cases_with_answers', methods=['GET'])
class UserCasesWithAnswersResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            # Fetch all CaseUser records for the current user
            user_cases = CaseUser.query.filter_by(userID=current_user.userID).all()

            # Initialize a list to store case data
            cases_data = []

            # Iterate through each user's case
            for user_case in user_cases:
                case = Cases.query.get(user_case.caseID)

                # Get all answers associated with the case
                all_answers = CAnswers.query.filter_by(caseID=case.caseID).all()

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
                    question = CQuestions.get_by_id(question_id)

                    if question.questionType == 'single choice':
                        # For single-choice questions, include the selected choice details in the response
                        response_data.append(OrderedDict([
                            ('questionID', question_id),
                            ('answer', {
                                'choiceID': question_data['answers'][0].choiceID,
                                'choiceText': CQuestionChoices.get_by_id(question_data['answers'][0].choiceID).choiceText
                            })
                        ]))
                    elif question.questionType == 'multi choice':
                        # For multi-choice questions, include all selected choices in the response
                        response_data.append(OrderedDict([
                            ('questionID', question_id),
                            ('answer', {
                                'choices': [choice.choiceID for choice in question_data['answers']],
                                'choiceText': [CQuestionChoices.get_by_id(choice.choiceID).choiceText for choice in
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

                # Get cases details
                case_details = {
                    'caseID': case.caseID,
                    'caseName': case.caseName,
                    'caseStatus': case.caseStatus.value,
                    'category': case.caseCategory.value,
                    'serviceRequired': case.serviceRequired,
                    'startDate': case.startDate,
                    'dueDate': case.dueDate,
                    'startDate': case.startDate,
                    'answers': order_answers
                }
                cases_data.append(case_details)

            return jsonify({'user_cases_with_answers': cases_data})

        except Exception as e:
            # Handle exceptions appropriately
            return {'message': str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/answers_only/<int:case_id>', methods=['GET'])
class CaseAnswersOnlyResource(Resource):
    @jwt_required()
    def get(self, case_id):
        # Get the case by ID
        case = Cases.get_by_id(case_id)

        if not case:
            return jsonify({'message': 'Case not found'}), HTTPStatus.NOT_FOUND

        # Fetch all answers associated with the case
        all_answers = CAnswers.query.filter_by(caseID=case_id).all()

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
            question = CQuestions.get_by_id(question_id)

            if question.questionType == 'single choice':
                # For single-choice questions, include the selected choice details in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('questionText', question.questionText),
                    ('questionType', 'single choice'),
                    ('answers', [{
                        'answerID': answer.answerID,
                        'choiceID': answer.choiceID,
                        'choiceText': CQuestionChoices.get_by_id(answer.choiceID).choiceText,
                        'points': CQuestionChoices.get_by_id(answer.choiceID).points
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
                        'choiceText': CQuestionChoices.get_by_id(choice_id).choiceText,
                        'points': CQuestionChoices.get_by_id(choice_id).points
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

@case_namespace.route('/answers-only/minified/<int:case_id>', methods=['GET'])
class CaseMinifiedAnswersOnlyResource(Resource):
    @jwt_required()
    def get(self, case_id):
        # Get the case by ID
        case = Cases.get_by_id(case_id)

        if not case:
            return jsonify({'message': 'Case not found'}), HTTPStatus.NOT_FOUND

        # Fetch all answers associated with the case
        all_answers = CAnswers.query.filter_by(caseID=case_id).all()

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
            question = CQuestions.get_by_id(question_id)

            if question.questionType == 'single choice':
                # For single-choice questions, include the selected choice details in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('answer', {
                        'choiceID': question_data['answers'][0].choiceID,
                        'choiceText': CQuestionChoices.get_by_id(question_data['answers'][0].choiceID).choiceText
                    })
                ]))
            elif question.questionType == 'multi choice':
                # For multi-choice questions, include all selected choices in the response
                response_data.append(OrderedDict([
                    ('questionID', question_id),
                    ('answer', {
                        'choiceID': [choice.choiceID for choice in question_data['answers']],
                        'choiceText': [CQuestionChoices.get_by_id(choice.choiceID).choiceText for choice in
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
    

@case_namespace.route('/edit_answers/<int:case_id>', methods=['PUT'])
class CaseEditAnswersResource(Resource):
    @jwt_required()
    @case_namespace.expect(case_edit_model)
    def put(self, case_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the case by ID
        case = Cases.query.get_or_404(case_id)

        # Ensure the current user is authorized to edit the case
        if current_user.userID != case.userID and not current_user.is_admin:
            return {'message': 'Unauthorized. You do not have permission to edit this case.'}, HTTPStatus.FORBIDDEN

        # Parse the input data
        case_data = request.json
        edited_answers_data = case_data.pop('edited_answers', [])  # Extract edited answers from case_data

        # Update the case details
        case.caseName = case_data.get('caseName', case.caseName)
        case.regionID = case_data.get('regionID', case.regionID)
        case.budgetRequired = case_data.get('budgetRequired', case.budgetRequired)
        case.budgetAvailable = case_data.get('budgetAvailable', case.budgetAvailable)
        case.caseStatus = case_data.get('caseStatus', case.caseStatus)
        case.caseCategory = case_data.get('caseCategory', case.caseCategory)
        case.startDate = case_data.get('startDate', case.startDate)
        case.serviceRequired = case_data.get('serviceRequired',case.serviceRequired)
        case.dueDate = case_data.get('dueDate', case.dueDate)

        # Save the updated case details to the database
        try:
            db.session.commit()

            # Update the answers for the case
            case.edit_answers(edited_answers_data)

            return {'message': 'Case details and answers updated successfully'}, HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            return {'message': f'Error updating case details and answers: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/add/requirements/<int:case_id>')
class CaseAddRequirementsResource(Resource):
    @jwt_required()
    @case_namespace.expect(case_status_data)
    def post(self, case_id):
        try:
            
             # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            
            if not current_user.is_admin:  # Assuming you have an 'is_admin' property in the Users model
                return {'message': 'Unauthorized. Only admin users can add requirements.'}, HTTPStatus.FORBIDDEN
        
            case = Cases.get_by_id(case_id)
            # Parse the input data
            case_data = request.json
            status_data = case_data.pop('status_data', {})  # Assuming status_data is part of the input

            # Assign status data to the case
            case.assign_status_data(status_data)
            
            #handle making tasks from the requirements
            requirementsList = status_data.pop('predefined_req')
            processor = CaseRequirementProcessor(case.caseID, current_user.userID)
            #call the corresponding function to handle making a Task for that requirement
            for value in requirementsList:
                function_name = f"requirement_{value}"
                case_function = getattr(processor, function_name, processor.default_case)
                case_function()

            return {'message': 'Case requirements added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding case requirements: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/get/requirements/<int:case_id>')
class CaseRequirementResource(Resource):
   
    @jwt_required()
    def get(self, case_id):
        try:
            # Retrieve JSONB data based on case ID
            status_data = CaseStatusData.get_status_data_by_case_id(case_id)

            if status_data is not None:
                return {'status_data': status_data}, HTTPStatus.OK
            else:
                return {'message': 'No status data found for the case'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error retrieving status data: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR



@case_namespace.route('/change_status/<int:case_id>', methods=['PUT'])
class CaseChangeStatusResource(Resource):
    @jwt_required()
    @case_namespace.expect(case_namespace.model('CaseStatus', {
        'caseStatus': fields.String(required=True, description='New case status')
    }))
    def put(self, case_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the case by ID
        case = Cases.query.get(case_id)
        if not case:
            return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has permission to change the status
        if current_user.is_admin or current_user.userID == case.userID:
            # Parse the new status from the request
            new_status = request.json.get('caseStatus')
            
            case.caseStatus = new_status

            # Save the updated case status to the database
            try:
                db.session.commit()
                # Check if the new status is 'Approved' and add stages if true
                if new_status == "APPROVED":
                    # Add all stages for the case
                    stage1 = CaseStage.query.filter_by(name='Information Collected').first()
                    stage2 = CaseStage.query.filter_by(name='Service Initiated').first()
                    stage3 = CaseStage.query.filter_by(name='Case Informed').first()
                    stage4 = CaseStage.query.filter_by(name='Service Delivered').first()
                    stage5 = CaseStage.query.filter_by(name='Service Validated').first()
                    stage6 = CaseStage.query.filter_by(name='Case Closed').first()

                    # Add the stages to the case
                    case_stages = [
                        CaseToStage(case=case, stage=stage1, started=True),
                        CaseToStage(case=case, stage=stage2, started=True),
                        CaseToStage(case=case, stage=stage3, started=True),
                        CaseToStage(case=case, stage=stage4, started=True),
                        CaseToStage(case=case, stage=stage5, started=True),
                        CaseToStage(case=case, stage=stage6, started=True)
                    ]

                    # Commit the new stages to the database
                    db.session.add_all(case_stages)
                    db.session.commit()

                return {'message': 'Case status changed successfully', 'new_status': new_status}, HTTPStatus.OK

            except Exception as e:
                db.session.rollback()
                return {'message': f'Error changing case status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            return {'message': 'Unauthorized. You do not have permission to change the status of this case.'}, HTTPStatus.FORBIDDEN

@case_namespace.route('/delete/<int:case_id>')
class CaseDeleteResource(Resource):
    @jwt_required()  
    def delete(self, case_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the case exists and belongs to the current user
        if current_user.is_admin:
            case_to_delete = Cases.query.filter_by(caseID=case_id).first()
        else:
            case_to_delete = Cases.query.filter_by(caseID=case_id, userID=current_user.userID).first()
        if not case_to_delete:
            return {'message': 'case not found or unauthorized'}, HTTPStatus.NOT_FOUND

        # Delete the answers related to the case
        CAnswers.query.filter_by(caseID=case_id).delete()

        # Delete the case from the database
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
        
        # Delete the choices related to the question
        CQuestionChoices.query.filter_by(questionID=question_id).delete()

        # Delete the question from the database
        try:
            question_to_delete.delete()

            return {'message': 'Question, question choices, and associated answers deleted successfully'}, HTTPStatus.OK
        except Exception as e:
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error deleting question: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/give_access/<int:case_id>/<int:user_id>')
class GiveAccessResource(Resource):
    @jwt_required()
    def post(self, case_id, user_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # Get the case by ID
        case_to_access = Cases.query.get(case_id)
        # Check if the current user has the necessary permissions (e.g., case owner or admin)
        # Adjust the condition based on your specific requirements
        if not current_user.is_admin and current_user.userID != case_to_access.userID:
            return {'message': 'Unauthorized. You do not have permission to give access to this case.'}, HTTPStatus.FORBIDDEN

        
        if not case_to_access:
            return {'message': 'case not found'}, HTTPStatus.NOT_FOUND

        # Get the user by ID
        user_to_give_access = Users.query.get(user_id)
        if not user_to_give_access:
            return {'message': 'User not found'}, HTTPStatus.NOT_FOUND

        # Check if the user already has access to the case
        if CaseUser.query.filter_by(caseID=case_id, userID=user_id).first():
            return {'message': 'User already has access to the case'}, HTTPStatus.BAD_REQUEST

        # Add the user to the case's list of users
        case_user = CaseUser(caseID=case_id, userID=user_id)
        case_user.save()

        return {'message': 'User granted access to the case successfully'}, HTTPStatus.OK

#####################################################
# STAGE ENDPOINTS
#####################################################
@case_stage_namespace.route('/add', methods=['POST'])
class AddStageResource(Resource):
    @jwt_required()
    @case_namespace.expect(stage_model)
    def post(self):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user has permission to add a stage
        if not current_user.is_admin:  # Adjust the condition based on your specific requirements
            return {'message': 'Unauthorized. Only admin users can add stages.'}, HTTPStatus.FORBIDDEN

        # Parse input data
        stage_data = request.json

        # Create a new stage instance
        new_stage = CaseStage(
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
    
@case_stage_namespace.route('/delete_stage/<int:stage_id>', methods=['DELETE'])
class DeleteStageResource(Resource):
    @jwt_required()
    def delete(self, stage_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user has permission to delete a stage
        if not current_user.is_admin:  # Adjust the condition based on your specific requirements
            return {'message': 'Unauthorized. Only admin users can delete stages.'}, HTTPStatus.FORBIDDEN

        # Get the stage by ID
        stage_to_delete = CaseStage.query.get(stage_id)

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
        
@case_stage_namespace.route('/all_stages', methods=['GET'])
class AllStagesResource(Resource):
    def get(self):
        try:
            # Get all stages
            stages = CaseStage.query.all()

            # Convert the list of stages to a JSON response
            stages_data = [{'stageID': stage.stageID, 'name': stage.name} for stage in stages]

            return jsonify({'stages': stages_data})

        except Exception as e:
            current_app.logger.error(f"Error retrieving stages: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

  
@case_stage_namespace.route('/stages_for_case/<int:case_id>', methods=['GET'])
class StagesForCaseResource(Resource):
    def get(self, case_id):
        try:
            # Check if the case exists in the database
            case = Cases.query.get(case_id)

            if case is None:
                return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

            # Get all stages linked to the case
            linked_stages = CaseToStage.query.filter_by(caseID=case_id).all()

            # Convert the list of linked stages to a JSON response
            linked_stages_data = [{'stageID': stage.stage.stageID, 'name': stage.stage.name,
                                   'started': stage.started, 'completed': stage.completed,
                                   'completionDate': stage.completionDate} for stage in linked_stages]

            return jsonify({'linked_stages': linked_stages_data})

        except Exception as e:
            current_app.logger.error(f"Error retrieving linked stages for case: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
@case_stage_namespace.route('/complete_stage_for_case/<int:case_id>/<int:stage_id>', methods=['PUT'])
@case_stage_namespace.doc(
    params={
        'case_id': 'Specify the ID of the case',
        'stage_id': 'Specify the ID of the stage'
    },
    description = "Change the stage to complete"
)
class CompleteStageForCaseResource(Resource):
    def put(self, case_id, stage_id):
        try:
            # Check if the case exists in the database
            case = Cases.query.get(case_id)

            if case is None:
                return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

            # Check if the linked stage exists for the case
            linked_stage = CaseToStage.query.filter_by(caseID=case_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified case'}, HTTPStatus.NOT_FOUND

            # Update the linked stage as completed
            linked_stage.completed = True
            linked_stage.completionDate = datetime.today().date()

            # Commit the changes to the database
            db.session.commit()

            return {'message': 'Linked stage marked as completed successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error marking linked stage as completed: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_stage_namespace.route('/remove_stage/<int:case_id>/<int:stage_id>', methods=['DELETE'])
class RemoveStageResource(Resource):
    @jwt_required()
    def delete(self, case_id, stage_id):
        try:
            # Check if the linked stage exists for the case
            linked_stage = CaseStage.query.filter_by(caseID=case_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified case'}, HTTPStatus.NOT_FOUND

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
@case_task_namespace.route('/add_task_for_stage/<int:case_id>/<int:stage_id>', methods=['POST'])
class AddTaskForStageResource(Resource):
    @case_task_namespace.expect(new_task_model, validate=True)
    @jwt_required()
    def post(self, case_id, stage_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        try:
            # Check if the linked stage exists for the case
            linked_stage = CaseToStage.query.filter_by(caseID=case_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified case'}, HTTPStatus.NOT_FOUND

            # Extract task data from the request payload
            data = case_task_namespace.payload
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
            new_task = CaseTask(
                caseID=case_id,
                title=title,
                deadline=deadline,
                description=description,
                assignedTo=assigned_to_users,
                cc=cc_users,
                createdBy=created_by,
                attachedFiles=attached_files,
                stageID=stage_id,
                status = CaseTaskStatus.TODO
            )

            # Save the new task to the database
            db.session.add(new_task)
            db.session.commit()

            return {'message': 'Task added for the linked stage successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding task for linked stage: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_task_namespace.route('/mark_as_started/<int:task_id>',methods=['PUT'])
class MarkTaskAsStartedResource(Resource):
    @jwt_required()
    @case_task_namespace.doc(
        description = "Assign the In Progress status to the provided task"
    )
    def put(self, task_id):
        try:
            task = CaseTask.get_by_id(task_id)
            if(task.status == CaseTaskStatus.TODO):
                task.status = CaseTaskStatus.INPROGRESS
                task.save()
                return {'message': 'Task has been marked as In Progress successfully'}, HTTPStatus.OK
            else:
                return {'message': 'Not allowed. A task must be in a TODO state to mark at as In Progress'}, HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"Error marking task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR  
        

@case_task_namespace.route('/mark_as_done/<int:task_id>',methods=['PUT'])
class MarkTaskAsDoneResource(Resource):
    @jwt_required()
    @case_task_namespace.doc(
        description = "Assign the DONE status to the provided task."
    )
    def put(self, task_id):
        try:
            task = CaseTask.get_by_id(task_id)
            #
            if(task.status == CaseTaskStatus.INPROGRESS or task.status == CaseTaskStatus.OVERDUE):
                task.status = CaseTaskStatus.DONE
                # Set completionDate to the current date
                task.completionDate = date.today()
                task.save()
                return {'message': 'Task marked as done successfully.'}, HTTPStatus.OK
            else:
                return {'message': 'Cannot mark a Task as done if it was not IN PROGRESS.'}, HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"Error marking task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_task_namespace.route('/mark_as_overdue/<int:task_id>',methods=['PUT'])
class MarkTaskAsOverdueResource(Resource):
    @jwt_required()
    @case_task_namespace.doc(
        description = "Assign the OVERDUE status to the provided task"
    )
    def put(self, task_id):
        try:
            task = CaseTask.get_by_id(task_id)
            #only mark the task as overdue if it neither DONE nor already OVERDUE
            if(task.status != CaseTaskStatus.DONE or task.status != CaseTaskStatus.OVERDUE):
                if task.is_overdue:
                    task.status = CaseTaskStatus.OVERDUE
                    task.save()
                    return {'message': 'Task has been marked as overdue'}, HTTPStatus.OK
                else:
                    return {'message': 'Ingored, Task is not yet overdue'}, HTTPStatus.OK
            else:
                return {'message': 'Cannot mark Task as OVERDUE, it is either DONE or already OVERDUE'}, HTTPStatus.BAD_REQUEST
                
        except Exception as e:
            current_app.logger.error(f"Error marking task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_task_namespace.route('/add_comment_for_task', methods=['POST'])
class AddTaskComments(Resource):
    @jwt_required()
    @case_task_namespace.expect(comments_model, validate=True)
    @case_task_namespace.doc(
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
        
        new_comment = CaseTaskComments(
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
        
@case_task_namespace.route('/get/task_comments/<int:task_id>',methods=['GET'])
class GetTaskCommentsResource(Resource):
    @jwt_required()
    def get(self, task_id):
        try:
            comments = CaseTaskComments.query.filter_by(taskID=task_id).all()
            
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

@case_task_namespace.route('/get_tasks_for_stage/<int:case_id>/<int:stage_id>', methods=['GET'])
class GetTasksForStageResource(Resource):
    @jwt_required()
    def get(self, case_id, stage_id):
        try:
            # Check if the linked stage exists for the case
            linked_stage = CaseToStage.query.filter_by(caseID=case_id, stageID=stage_id).first()

            if linked_stage is None:
                return {'message': 'Stage not linked to the specified case'}, HTTPStatus.NOT_FOUND

            # Fetch all tasks for the linked stage
            tasks = CaseTask.query.filter_by(caseID=case_id, stageID=stage_id).all()

            # Convert tasks to a list of dictionaries for response
            tasks_list = []

            for task in tasks:
                # Fetch the first 5 comments for each task
                comments = CaseTaskComments.query.filter_by(taskID=task.taskID).limit(5).all()

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

@case_task_namespace.route('/edit_task/<int:task_id>', methods=['PUT'])
class EditTaskForStageResource(Resource):
    @case_task_namespace.expect(edit_task_model, validate=True)
    @jwt_required()
    def put(self, task_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        # Check if the current user has permission to delete a stage
        if not current_user.is_admin:  # Adjust the condition based on your specific requirements
            return {'message': 'Unauthorized. Only admin users can edit Task details.'}, HTTPStatus.FORBIDDEN

        try:
            # Get the task
            task = CaseTask.get_by_id(task_id)

            if task is None:
                return {'message': 'Task not found'}, HTTPStatus.NOT_FOUND

            # Extract task data from the request payload
            data = case_task_namespace.payload
            
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



