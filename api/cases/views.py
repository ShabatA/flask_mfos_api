from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from http import HTTPStatus
from ..models.cases import Cases, CaseStatus, CaseUser, CQuestions, CQuestionChoices, CAnswers, CaseTaskAssignedTo, CaseStage, CaseToStage, CaseTaskComments, CaseStatusData, CaseTask, CaseTaskCC
from ..models.users import Users
from ..models.regions import Regions
from ..utils.db import db
from datetime import datetime
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
stage_namespace = Namespace('Case Stages', description="A namespace for case Stages")
task_namespace = Namespace('Case Tasks', description="A namespace for case Tasks")

stage_model = stage_namespace.model(
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

comments_model = task_namespace.model('CaseTaskComments',{
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
link_case_to_stage_model = stage_namespace.model('LinkCaseToStageModel', {
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
        
            case = Cases.get_by_id(case_id)
            # Parse the input data
            case_data = request.json
            status_data = case_data.pop('status_data', {})  # Assuming status_data is part of the input

            # Assign status data to the case
            case.assign_status_data(status_data)

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



