from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from http import HTTPStatus
from api.models.finances import CaseFunds, RegionAccount
from api.utils.case_category_calculator import CaseCategoryCalculator

from api.utils.case_requirement_processor import CaseRequirementProcessor
from ..models.cases import CaseCat, CasesData, CaseStat, CaseUser, CaseBeneficiary, CaseStage, CaseToStage, CaseTaskComments, CaseStatusData, CaseTask, BeneficiaryForm, CaseTaskStatus, CaseAssessmentAnswers, CaseAssessmentQuestions
from ..models.users import Users
from ..models.regions import Regions
from ..utils.db import db
from datetime import datetime, date
from flask import jsonify, current_app
from flask import request
from sqlalchemy import func


def get_region_id_by_name(region_name):
    region = Regions.query.filter_by(regionName=region_name).first()

    if region:
        return region.regionID
    else:
        return None  # Or any other value to indicate that the regionName was not found

case_namespace = Namespace("Cases", description="Namespace for cases")
case_stage_namespace = Namespace('Case Stages', description="A namespace for case Stages")
case_task_namespace = Namespace('Case Tasks', description="A namespace for case Tasks")
case_assessment_namespace = Namespace('Case Assessment', description="A namespace for Case Assessment")

assessment_question_model = case_assessment_namespace.model('AssessmentQuestion', {
    'questionText': fields.String(required=True, description='The actual question to be asked.')
})

assessment_answer_model = case_assessment_namespace.model('CaseAssessmentAnswer', {
    'questionID': fields.Integer(required=True, description='The ID of the question'),
    'answerText': fields.String(required=True, description='The answer provided'),
    'extras': fields.Raw(description='Answers for the subquestion as key-value pair')
})

assessment_model = case_assessment_namespace.model('CaseAssessment', {
    'projectID': fields.Integer(required=True, description='The ID of the project this assessment is for'),
    'answers': fields.List(fields.Nested(assessment_answer_model), description='List of answers for the assessment')
})

stage_model = case_stage_namespace.model(
    'Stage', {
        'name': fields.String(required=True, description='Name of the stage'),
    }
)

case_update_status_model = case_namespace.model('CaseUpdateStatus', {
    'caseStatus': fields.String(required=True, enum=['approved', 'pending','rejected', 'inprogress', 'completed'], description='Status of the case'),
    'status_data': fields.Raw(description='Status data associated with the case'),
})

case_status_data = case_namespace.model('CaseStatusData', {
    
    'status_data': fields.Raw(description='Status data associated with the case'),
})

answers_model = case_namespace.model('CAnswers', {
    'questionID': fields.Integer(required=True, description='ID of the answer'),
    'answerText': fields.String(description='Text-based answer for a text question'),
    'choiceID': fields.List(fields.Integer, description='List of choices'),
    'extras': fields.Raw(description='Answers for the subquestion as key-value pair')
})

comments_model = case_task_namespace.model('CaseTaskComments',{
    'taskID': fields.Integer(required=True, description='Id of the task the comment belongs to'),
    'comment': fields.String(required=True, description= 'The comment written by the user'),
    'date': fields.Date(required=True, description='Date on which the comment was made')
})

edit_comments_model = case_task_namespace.model('EditTaskComments',{
    'commentID': fields.Integer(required=True, description='Id of the comment'),
    'newComment': fields.String(required=True, description= 'The comment written by the user')
})

question_input_model = case_namespace.model('QuestionInput', {
    'questionText': fields.String(required=True, description='Text of the question'),
    'questionType': fields.String(required=True, description='Type of the question'),
    'points': fields.Integer(required=True, description='Points for the question'),
    'choices': fields.List(fields.String, description='List of choices for multiple-choice questions')
})

checklist_model = case_task_namespace.model('CheckListItem', {
    'item': fields.String(required=True, description='The checklist item name/description'),
    'checked': fields.Boolean(required=True, description='Whether this is checked out or not')
})


# Define a model for the input data (assuming JSON format)
new_task_model = case_task_namespace.model('NewTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    'attached_files': fields.String(description='File attachments for the task'),
    'checklist': fields.List(fields.Nested(checklist_model),description='optional checklist'),
    'startDate': fields.Date(required=True, description='start date of the task (YYYY-MM-DD)')
})

edit_task_model = case_task_namespace.model('EditTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    'attached_files': fields.String(description='File attachments for the task'),
    'checklist': fields.List(fields.Nested(checklist_model),description='optional checklist'),
    'startDate': fields.Date(required=True, description='start date of the task (YYYY-MM-DD)')
})

case_model = case_namespace.model(
    'Case', {
        'caseName': fields.String(required=True, description="A case name"),
        'budgetRequired': fields.Float(required=True, description="Budget required"),
        'caseCategory': fields.String(description="Case category"),
        'serviceRequired': fields.String(description="Service Required"),
        'regionName': fields.String(required=True, description="Region Name"),
        'answers': fields.List(fields.Nested(answers_model), description='List of answers for the case')
    }
)

cases_data_model = case_namespace.model('CasesDataInput', {
    'regionID': fields.Integer(required=True,description='ID of the region'),
    'caseName': fields.String(required=True, description='Name of the case'),
    'sponsorAvailable': fields.String(required=True),
    'question1': fields.Raw(required=True, description='Question 1'),
    'question2': fields.Raw(required=True, description='Question 2'),
    'question3': fields.Raw(required=True, description='Question 3'),
    'question4': fields.Raw(description='Question 4 (JSONB)'),
    'question5': fields.Raw(description='Question 5 (JSONB)'),
    'question6': fields.Raw(description='Question 6 (JSONB)'),
    'question7': fields.Raw(description='Question 7 (JSONB)'),
    'question8': fields.Raw(description='Question 8 (JSONB)'),
    'question9': fields.Raw(description='Question 9 (JSONB)'),
    'question10': fields.Raw(required=True, description='Question 10'),
    'question11': fields.Float(required=True, description='Question 11'),
    'question12': fields.Integer(required=True, description='Question 12')

})

beneficiary_data_model = case_namespace.model('BeneficiaryData', {
    'caseID': fields.Integer(required=True),
    'firstName': fields.String(required=True),
    'surName': fields.String(required=True),
    'gender': fields.String(required=True),
    'birthDate': fields.Date(required=True),
    'birthPlace': fields.String(required=True),
    'nationality': fields.String(required=True),
    'idType': fields.String(required=True),
    'idNumber': fields.String(required=True),
    'phoneNumber': fields.String(required=True),
    'altPhoneNumber': fields.String(),
    'email': fields.String(required=True),
    'serviceRequired': fields.String(required=True),
    'otherServiceRequired': fields.String(),
    'problemDescription': fields.String(),
    'serviceDescription': fields.String(),
    'totalSupportCost': fields.Float(),
    'receiveFundDate': fields.Date(),
    'paymentMethod': fields.String(),
    'paymentsType': fields.String(),
    'otherPaymentType': fields.String(),
    'incomeType': fields.String(),
    'otherIncomeType': fields.String(),
    'housing': fields.String(),
    'otherHousing': fields.String(),
    'housingType': fields.String(),
    'otherHousingType': fields.String(),
    'totalFamilyMembers': fields.Integer(),
    'childrenUnder15': fields.String(),
    'isOldPeople': fields.Boolean(),
    'isDisabledPeople': fields.Boolean(),
    'isStudentsPeople': fields.Boolean(),
    'serviceDate': fields.String()
})

edit_beneficiary_data_model = case_namespace.model('EditBeneficiaryData', {
    'beneficiaryID': fields.Integer(required=True),
    'caseID': fields.Integer(required=True),
    'firstName': fields.String(required=True),
    'surName': fields.String(required=True),
    'gender': fields.String(required=True),
    'birthDate': fields.Date(required=True),
    'birthPlace': fields.String(required=True),
    'nationality': fields.String(required=True),
    'idType': fields.String(required=True),
    'idNumber': fields.String(required=True),
    'phoneNumber': fields.String(required=True),
    'altPhoneNumber': fields.String(),
    'email': fields.String(required=True),
    'serviceRequired': fields.String(required=True),
    'otherServiceRequired': fields.String(),
    'problemDescription': fields.String(),
    'serviceDescription': fields.String(),
    'totalSupportCost': fields.Float(),
    'receiveFundDate': fields.Date(),
    'paymentMethod': fields.String(),
    'paymentsType': fields.String(),
    'otherPaymentType': fields.String(),
    'incomeType': fields.String(),
    'otherIncomeType': fields.String(),
    'housing': fields.String(),
    'otherHousing': fields.String(),
    'housingType': fields.String(),
    'otherHousingType': fields.String(),
    'totalFamilyMembers': fields.Integer(),
    'childrenUnder15': fields.String(),
    'isOldPeople': fields.Boolean(),
    'isDisabledPeople': fields.Boolean(),
    'isStudentsPeople': fields.Boolean(),
    'serviceDate': fields.String()
})

case_beneficiary_form = case_namespace.model('BeneficiaryForm',{
    'url': fields.String(required=True, description="The url with the uuid as a URL param.")
})

case_beneficiary_form_edit = case_namespace.model('EditBeneficiaryForm',{
    'url': fields.String(required=True, description="The url with the uuid as a URL param."),
    'used': fields.Boolean(required=True)
})

case_model_2 = case_namespace.model(
    'Case2', {
        'caseName': fields.String(required=True, description="A case name"),
        'budgetRequired': fields.Float(required=True, description="Budget required"),
        'caseCategory': fields.String(description="Case category"),
        'caseStatus': fields.String(enum=[status.value for status in CaseStat], description="Case status"),
    })

edited_answers_model = case_namespace.model('EditedAnswers', {
    'questionID': fields.Integer(required=True, description='ID of the question'),
    'answerText': fields.String(description='Text-based answer for a text question'),
    'choiceID': fields.List(fields.Integer, description='List of choices')
})


# Define a model for the input data (assuming JSON format)
link_case_to_stage_model = case_stage_namespace.model('LinkCaseToStageModel', {
    'case_id': fields.Integer(required=True, description='ID of the case'),
    'stage_id': fields.Integer(required=True, description='ID of the stage'),
    'started': fields.Boolean(required=True, description="If the stage has been started"),
    'completed': fields.Boolean(required=True, description="If the stage has been completed"),
    'completionDate': fields.Date(description="Completion Date")
})


@case_namespace.route('/add_or_edit', methods=['POST', 'PUT'])
class CasesAddResource(Resource):
    @jwt_required()
    @case_namespace.expect(cases_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            case_data = request.json

            # Check if a case with the given name already exists
            existing_case = CasesData.query.filter_by(caseName=case_data['caseName']).first()
            if existing_case:
                return {'message': 'Case with this name already exists'}, HTTPStatus.CONFLICT

            # Create a new case instance
            new_case = CasesData(
                userID=current_user.userID,
                regionID=case_data.get('regionID'),
                caseName= f'New Case {datetime.utcnow().date()}',
                sponsorAvailable=case_data['sponsorAvailable'],
                question1=case_data['question1'],
                question2=case_data['question2'],
                question3=case_data['question3'],
                question4=case_data.get('question4', {}),
                question5=case_data.get('question5', {}),
                question6=case_data.get('question6', {}),
                question7=case_data.get('question7', {}),
                question8=case_data.get('question8', {}),
                question9=case_data.get('question9', {}),
                question10=case_data.get('question10', {}),
                question11=case_data['question11'],
                question12=case_data['question12'],
                caseStatus=CaseStat.ASSESSMENT,
                createdAt=datetime.utcnow()
            )

            # Save the case to the database
            new_case.save()

            # Add the current user to the CaseUsers table for the new case
            case_user = CaseUser(caseID=new_case.caseID, userID=current_user.userID)
            case_user.save()
            
            categoryCalculator = CaseCategoryCalculator(new_case)
            categoryCalculator.calculate_category()
            
            region_details = {'regionID': new_case.regionID, 'regionName': Regions.query.get(new_case.regionID).regionName}
            user = Users.query.get(new_case.userID)
            user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
            case_details = {
                'caseID': new_case.caseID,
                'caseName': new_case.caseName,
                'region': region_details,
                'user': user_details,
                'budgetApproved': new_case.budgetApproved,
                'sponsorAvailable': new_case.sponsorAvailable,
                'question1': new_case.question1,
                'question2': new_case.question2,
                'question3': new_case.question3,
                'question4': new_case.question4,
                'question5': new_case.question5,
                'question6': new_case.question6,
                'question7': new_case.question7,
                'question8': new_case.question8,
                'question9': new_case.question9,
                'question10': new_case.question10,
                'question11': new_case.question11,
                'question12': new_case.question12,
                'caseStatus': 'Assessment' if new_case.caseStatus == CaseStat.ASSESSMENT else new_case.caseStatus.value,
                'category': new_case.category.value if new_case.category else None,
                'createdAt': new_case.createdAt.isoformat(),
                'dueDate': new_case.dueDate.isoformat() if new_case.dueDate else None,
                'startDate': new_case.startDate.isoformat() if new_case.startDate else None,
                'totalPoints': new_case.total_points
                    
                }
            
            return {'message': 'Case added successfully',
                    'case_details': case_details}, HTTPStatus.CREATED
        except Exception as e:
            current_app.logger.error(f"Error adding case: {str(e)}")
            return {'message': f'Error adding case, please review inputs and try again.'}, HTTPStatus.INTERNAL_SERVER_ERROR

    @jwt_required()
    @case_namespace.expect(cases_data_model)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            case_data = request.json

            case_id = case_data.get('caseID')
            if not case_id:
                return {'message': 'Case ID is required for updating a case'}, HTTPStatus.BAD_REQUEST

            existing_case = CasesData.query.get_or_404(case_id)

            # Update the case fields
            existing_case.userID = current_user.userID
            existing_case.regionID = case_data.get('regionID')
            existing_case.sponsorAvailable = case_data['sponsorAvailable']
            existing_case.question1 = case_data['question1']
            existing_case.question2 = case_data['question2']
            existing_case.question3 = case_data['question3']
            existing_case.question4 = case_data.get('question4', {})
            existing_case.question5 = case_data.get('question5', {})
            existing_case.question6 = case_data.get('question6', {})
            existing_case.question7 = case_data.get('question7', {})
            existing_case.question8 = case_data.get('question8', {})
            existing_case.question9 = case_data.get('question9', {})
            existing_case.question10 = case_data['question10']
            existing_case.question11 = case_data['question11']
            existing_case.question12 = case_data['question12']
            existing_case.startDate = case_data.get('startDate', existing_case.startDate)
            existing_case.dueDate = case_data.get('dueDate', existing_case.dueDate)

            existing_case.save()
            categoryCalculator = CaseCategoryCalculator(existing_case)
            categoryCalculator.calculate_category()

            return {'message': 'Case updated successfully'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating case: {str(e)}")
            return {'message': f'Error updating case, please review inputs and try again.'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/calculate-case-category/<int:case_id>', methods=['PUT'])
class CalculateCaseCategoryResource(Resource):
    @jwt_required()
    def put(self, case_id):
        try:
            case_data = CasesData.query.get_or_404(case_id)
            categoryCalculator = CaseCategoryCalculator(case_data)
            categoryCalculator.calculate_category()
            return {'message': f'Success, category is {case_data.category.value}, and {case_data.total_points} total points'}
        except Exception as e:
            current_app.logger.error(f"Error calculating category: {str(e)}")
            return {'message': f'Error updating case: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        

@case_namespace.route('/get_all', methods=['GET'])
class CaseGetAllResource(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            if not current_user.is_admin():
                # Fetch all cases the user has access to
                cases = (
                    CasesData.query.join(Users, Users.userID == CasesData.userID)
                    .filter(Users.userID == current_user.userID)
                    .all()
                )

                # Fetch all cases associated with the user through CaseUser
                case_user_cases = (
                    CasesData.query.join(CaseUser, CasesData.caseID == CaseUser.caseID)
                    .filter(CaseUser.userID == current_user.userID)
                    .all()
                )
            
                # Combine the cases and remove duplicates
                all_cases = list(set(cases + case_user_cases))
            else:
                all_cases = CasesData.query.all()

            # Check if all_cases is empty
            if not all_cases:
                return [], HTTPStatus.OK  # Return an empty list

            # Prepare the list of cases with additional details
            cases_data = [] 
            for case in all_cases:
                beneficiaries = CaseBeneficiary.query.filter_by(caseID=case.caseID).all()
                users_assigned_to_case = (
                    Users.query.join(CaseUser, Users.userID == CaseUser.userID)
                    .filter(CaseUser.caseID == case.caseID)
                    .all()
                )
                
                serialized_beneficiaries = []
                if beneficiaries:
                    for beneficiary in beneficiaries:
                        serialized_beneficiary = {
                            'beneficiaryID': beneficiary.beneficiaryID,
                            'caseID': case.caseID,
                            'firstName': beneficiary.firstName,
                            'surName': beneficiary.surName,
                            'gender': beneficiary.gender,
                            'birthDate': beneficiary.birthDate,
                            'birthPlace': beneficiary.birthPlace,
                            'nationality': beneficiary.nationality,
                            'idType': beneficiary.idType,
                            'idNumber': beneficiary.idNumber,
                            'phoneNumber': beneficiary.phoneNumber,
                            'altPhoneNumber': beneficiary.altPhoneNumber,
                            'email': beneficiary.email,
                            'serviceRequired': beneficiary.serviceRequired,
                            'otherServiceRequired': beneficiary.otherServiceRequired,
                            'problemDescription': beneficiary.problemDescription,
                            'serviceDescription': beneficiary.serviceDescription,
                            'totalSupportCost': beneficiary.totalSupportCost,
                            'receiveFundDate': beneficiary.receiveFundDate.isoformat(),
                            'paymentMethod': beneficiary.paymentMethod,
                            'paymentsType': beneficiary.paymentsType,
                            'otherPaymentType': beneficiary.otherPaymentType,
                            'incomeType': beneficiary.incomeType,
                            'otherIncomeType': beneficiary.otherIncomeType,
                            'housing': beneficiary.housing,
                            'otherHousing': beneficiary.otherHousing,
                            'housingType': beneficiary.housingType,
                            'otherHousingType': beneficiary.otherHousingType,
                            'totalFamilyMembers': beneficiary.totalFamilyMembers,
                            'childrenUnder15': beneficiary.childrenUnder15,
                            'isOldPeople': beneficiary.isOldPeople,
                            'isDisabledPeople': beneficiary.isDisabledPeople,
                            'isStudentsPeople': beneficiary.isStudentsPeople,
                            'serviceDate': beneficiary.serviceDate
                        }
                        serialized_beneficiaries.append(serialized_beneficiary)
                
                region_details = {'regionID': case.regionID, 'regionName': Regions.query.get(case.regionID).regionName}
                user = Users.query.get(case.userID)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                
                stages = CaseToStage.query.filter_by(caseID=case.caseID).all()
                completed_stages = [stage for stage in stages if stage.completed]

                if completed_stages:
                    # If there are completed stages, find the one with the latest completionDate
                    latest_completed_stage = max(completed_stages, key=lambda stage: stage.stageID)
                    
                else:
                    # If no stages are completed, return the first stage object
                    # Assuming stages are ordered in the way they are added or by a specific field
                    latest_completed_stage = min(stages, key=lambda stage: stage.stageID) if stages else None

                case_details = {
                    'caseID': case.caseID,
                    'caseName': case.caseName,
                    'region': region_details,
                    'stageName': latest_completed_stage.stage.name if latest_completed_stage else 'N/A',
                    'user': user_details,
                    'budgetApproved': case.budgetApproved,
                    'sponsorAvailable': case.sponsorAvailable,
                    'question1': case.question1,
                    'question2': case.question2,
                    'question3': case.question3,
                    'question4': case.question4,
                    'question5': case.question5,
                    'question6': case.question6,
                    'question7': case.question7,
                    'question8': case.question8,
                    'question9': case.question9,
                    'question10': case.question10,
                    'question11': case.question11,
                    'question12': case.question12,
                    'caseStatus': 'Assessment' if case.caseStatus == CaseStat.ASSESSMENT else case.caseStatus.value,
                    'category': case.category.value if case.category else None,
                    'createdAt': case.createdAt.isoformat(),
                    'dueDate': case.dueDate.isoformat() if case.dueDate else None,
                    'startDate': case.startDate.isoformat() if case.startDate else None,
                    'totalPoints': case.total_points,
                    'beneficaries': serialized_beneficiaries,
                    'assignedUsers': [user.userID for user in users_assigned_to_case] if users_assigned_to_case else [],
                }

                cases_data.append(case_details)

            return cases_data, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error calculating category: {str(e)}")
            return {'message': f'Error fetching cases, please try again later.'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_namespace.route('/get_all_approved_only', methods=['GET'])
class CaseGetAllApprovedResource(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()

            if not current_user.is_admin():
                # Fetch all cases the user has access to
                cases = (
                    CasesData.query.join(Users, Users.userID == CasesData.userID)
                    .filter(Users.userID == current_user.userID)
                    .filter(CasesData.caseStatus == CaseStat.APPROVED)
                    .all()
                )

                # Fetch all cases associated with the user through CaseUser
                case_user_cases = (
                    CasesData.query.join(CaseUser, CasesData.caseID == CaseUser.caseID)
                    .filter(CaseUser.userID == current_user.userID)
                    .filter(CasesData.caseStatus == CaseStat.APPROVED)
                    .all()
                )
            
                # Combine the cases and remove duplicates
                all_cases = list(set(cases + case_user_cases))
            else:
                all_cases = CasesData.query.filter_by(caseStatus= CaseStat.APPROVED).all()

            # Check if all_cases is empty
            if not all_cases:
                return [], HTTPStatus.OK  # Return an empty list

            # Prepare the list of cases with additional details
            cases_data = [] 
            for case in all_cases:
                beneficiaries = CaseBeneficiary.query.filter_by(caseID=case.caseID).all()
                users_assigned_to_case = (
                    Users.query.join(CaseUser, Users.userID == CaseUser.userID)
                    .filter(CaseUser.caseID == case.caseID)
                    .all()
                )
                
                serialized_beneficiaries = []
                if beneficiaries:
                    for beneficiary in beneficiaries:
                        serialized_beneficiary = {
                            'beneficiaryID': beneficiary.beneficiaryID,
                            'caseID': case.caseID,
                            'firstName': beneficiary.firstName,
                            'surName': beneficiary.surName,
                            'gender': beneficiary.gender,
                            'birthDate': beneficiary.birthDate,
                            'birthPlace': beneficiary.birthPlace,
                            'nationality': beneficiary.nationality,
                            'idType': beneficiary.idType,
                            'idNumber': beneficiary.idNumber,
                            'phoneNumber': beneficiary.phoneNumber,
                            'altPhoneNumber': beneficiary.altPhoneNumber,
                            'email': beneficiary.email,
                            'serviceRequired': beneficiary.serviceRequired,
                            'otherServiceRequired': beneficiary.otherServiceRequired,
                            'problemDescription': beneficiary.problemDescription,
                            'serviceDescription': beneficiary.serviceDescription,
                            'totalSupportCost': beneficiary.totalSupportCost,
                            'receiveFundDate': beneficiary.receiveFundDate.isoformat(),
                            'paymentMethod': beneficiary.paymentMethod,
                            'paymentsType': beneficiary.paymentsType,
                            'otherPaymentType': beneficiary.otherPaymentType,
                            'incomeType': beneficiary.incomeType,
                            'otherIncomeType': beneficiary.otherIncomeType,
                            'housing': beneficiary.housing,
                            'otherHousing': beneficiary.otherHousing,
                            'housingType': beneficiary.housingType,
                            'otherHousingType': beneficiary.otherHousingType,
                            'totalFamilyMembers': beneficiary.totalFamilyMembers,
                            'childrenUnder15': beneficiary.childrenUnder15,
                            'isOldPeople': beneficiary.isOldPeople,
                            'isDisabledPeople': beneficiary.isDisabledPeople,
                            'isStudentsPeople': beneficiary.isStudentsPeople,
                            'serviceDate': beneficiary.serviceDate
                        }
                        serialized_beneficiaries.append(serialized_beneficiary)
                
                region_details = {'regionID': case.regionID, 'regionName': Regions.query.get(case.regionID).regionName}
                user = Users.query.get(case.userID)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                
                stages = CaseToStage.query.filter_by(caseID=case.caseID).all()
                stages_data = []
                for stage in stages:
                    # Fetch all tasks for the linked stage
                    tasks = CaseTask.query.filter_by(caseID=case.caseID, stageID=stage.stageID).all()
                    total_tasks = len(tasks)
                    completed_tasks = 0
                    inprogress_tasks = 0
                    overdue_tasks = 0
                    not_started_tasks = 0
                    completionPercent = 0
                    if total_tasks > 0:

                        for task in tasks:
                            if task.status == CaseTaskStatus.DONE:
                                completed_tasks += 1
                            if task.status == CaseTaskStatus.OVERDUE:
                                overdue_tasks += 1
                            if task.status == CaseTaskStatus.INPROGRESS:
                                inprogress_tasks += 1
                            if task.status == CaseTaskStatus.TODO:
                                not_started_tasks += 1
                        completionPercent = (completed_tasks/total_tasks) * 100
                    stage_details = {'stageID': stage.stage.stageID, 'name': stage.stage.name,
                                   'started': stage.started, 'completed': stage.completed,
                                   'completionDate': stage.completionDate.isoformat() if stage.completionDate else None,
                                   'totalTasks': total_tasks, 'completedTasks': completed_tasks, 'completionPercent': completionPercent,
                                   'notStartedTasks': not_started_tasks, 'overdueTasks': overdue_tasks, 'inprogressTasks': inprogress_tasks}
                    stages_data.append(stage_details)
               
                completed_stages = [stage for stage in stages if stage.completed]

                if completed_stages:
                    # If there are completed stages, find the one with the latest completionDate
                    latest_completed_stage = max(completed_stages, key=lambda stage: stage.stageID)
                    
                else:
                    # If no stages are completed, return the first stage object
                    # Assuming stages are ordered in the way they are added or by a specific field
                    latest_completed_stage = min(stages, key=lambda stage: stage.stageID) if stages else None
                    
                case_details = {
                    'caseID': case.caseID,
                    'caseName': case.caseName,
                    'region': region_details,
                    'stageName': latest_completed_stage.stage.name if latest_completed_stage else 'N/A',
                    'user': user_details,
                    'budgetApproved': case.budgetApproved,
                    'sponsorAvailable': case.sponsorAvailable,
                    'question1': case.question1,
                    'question2': case.question2,
                    'question3': case.question3,
                    'question4': case.question4,
                    'question5': case.question5,
                    'question6': case.question6,
                    'question7': case.question7,
                    'question8': case.question8,
                    'question9': case.question9,
                    'question10': case.question10,
                    'question11': case.question11,
                    'question12': case.question12,
                    'caseStatus': 'Assessment' if case.caseStatus == CaseStat.ASSESSMENT else case.caseStatus.value,
                    'category': case.category.value if case.category else None,
                    'createdAt': case.createdAt.isoformat(),
                    'dueDate': case.dueDate.isoformat() if case.dueDate else None,
                    'startDate': case.startDate.isoformat() if case.startDate else None,
                    'totalPoints': case.total_points,
                    'beneficaries': serialized_beneficiaries,
                    'assignedUsers': [user.userID for user in users_assigned_to_case] if users_assigned_to_case else [],
                    'stages_data': stages_data
                }

                cases_data.append(case_details)

            return cases_data, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error calculating category: {str(e)}")
            return {'message': f'Error fetching cases, please try again later.'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_namespace.route('/beneficiary/add_or_edit', methods=['POST', 'PUT'])
class CaseBeneficiaryAddOrEditResource(Resource):
   
    @case_namespace.expect(beneficiary_data_model)
    def post(self):
        try:
            
            beneficiary_data = request.json
            case_id = beneficiary_data.get('caseID')
            if not case_id:
                return {'message': 'Case ID is required for updating a case'}, HTTPStatus.BAD_REQUEST

            existing_case = CasesData.query.get_or_404(case_id)
            if not existing_case:
                return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND
            
            existing_ben = CaseBeneficiary.query.filter_by(idNumber=beneficiary_data['idNumber']).first()
            
            if existing_ben:
                existing_case.category = CaseCat.C
            
            new_beneficiary = CaseBeneficiary(
                caseID=beneficiary_data['caseID'],
                firstName=beneficiary_data['firstName'],
                surName=beneficiary_data['surName'],
                gender=beneficiary_data['gender'],
                birthDate=beneficiary_data['birthDate'],
                birthPlace=beneficiary_data['birthPlace'],
                nationality=beneficiary_data['nationality'],
                idType=beneficiary_data['idType'],
                idNumber=beneficiary_data['idNumber'],
                phoneNumber=beneficiary_data['phoneNumber'],
                altPhoneNumber=beneficiary_data.get('altPhoneNumber'),
                email=beneficiary_data['email'],
                serviceRequired=beneficiary_data['serviceRequired'],
                otherServiceRequired=beneficiary_data.get('otherServiceRequired'),
                problemDescription=beneficiary_data.get('problemDescription'),
                serviceDescription=beneficiary_data.get('serviceDescription'),
                totalSupportCost=beneficiary_data.get('totalSupportCost'),
                receiveFundDate=beneficiary_data.get('receiveFundDate'),
                paymentMethod=beneficiary_data.get('paymentMethod'),
                paymentsType=beneficiary_data.get('paymentsType'),
                otherPaymentType=beneficiary_data.get('otherPaymentType'),
                incomeType=beneficiary_data.get('incomeType'),
                otherIncomeType=beneficiary_data.get('otherIncomeType'),
                housing=beneficiary_data.get('housing'),
                otherHousing=beneficiary_data.get('otherHousing'),
                housingType=beneficiary_data.get('housingType'),
                otherHousingType=beneficiary_data.get('otherHousingType'),
                totalFamilyMembers=beneficiary_data.get('totalFamilyMembers'),
                childrenUnder15=beneficiary_data.get('childrenUnder15'),
                isOldPeople=beneficiary_data.get('isOldPeople'),
                isDisabledPeople=beneficiary_data.get('isDisabledPeople'),
                isStudentsPeople=beneficiary_data.get('isStudentsPeople'),
                serviceDate=beneficiary_data.get('serviceDate')
            )

            new_beneficiary.save()
            form = BeneficiaryForm.query.filter_by(caseID=case_id).first()
            form.used = True
            form.save()
            
            existing_case.caseStatus = CaseStat.PENDING
            existing_case.caseName = f'{new_beneficiary.firstName} {new_beneficiary.surName}'
            existing_case.save()
            
            return {'message': 'CaseBeneficiary added successfully',
                    'beneficiary_id': new_beneficiary.beneficiaryID}, HTTPStatus.OK
       
        except Exception as e:
            current_app.logger.error(f"Error adding beneficiary: {str(e)}")
            return {'message': f'Error adding CaseBeneficiary, please review inputs and try again.',
                    'error': f"Error adding beneficiary: {str(e)}"}, HTTPStatus.INTERNAL_SERVER_ERROR

   
    @case_namespace.expect(edit_beneficiary_data_model)
    def put(self):
        try:
            
            beneficiary_data = request.json

            beneficiary_id = beneficiary_data.get('beneficiaryID')
            if not beneficiary_id:
                return {'message': 'Beneficiary ID is required for updating a beneficiary'}, HTTPStatus.BAD_REQUEST

            existing_beneficiary = CaseBeneficiary.query.get_or_404(beneficiary_id)

            # Update the beneficiary fields
            existing_beneficiary.caseID = beneficiary_data['caseID']
            existing_beneficiary.firstName = beneficiary_data['firstName']
            existing_beneficiary.surName = beneficiary_data['surName']
            existing_beneficiary.gender = beneficiary_data['gender']
            existing_beneficiary.birthDate = beneficiary_data['birthDate']
            existing_beneficiary.birthPlace = beneficiary_data['birthPlace']
            existing_beneficiary.nationality = beneficiary_data['nationality']
            existing_beneficiary.idType = beneficiary_data['idType']
            existing_beneficiary.idNumber = beneficiary_data['idNumber']
            existing_beneficiary.phoneNumber = beneficiary_data['phoneNumber']
            existing_beneficiary.altPhoneNumber = beneficiary_data.get('altPhoneNumber')
            existing_beneficiary.email = beneficiary_data['email']
            existing_beneficiary.serviceRequired = beneficiary_data['serviceRequired']
            existing_beneficiary.otherServiceRequired = beneficiary_data.get('otherServiceRequired')
            existing_beneficiary.problemDescription = beneficiary_data.get('problemDescription')
            existing_beneficiary.serviceDescription = beneficiary_data.get('serviceDescription')
            existing_beneficiary.totalSupportCost = beneficiary_data.get('totalSupportCost')
            existing_beneficiary.receiveFundDate = beneficiary_data.get('receiveFundDate')
            existing_beneficiary.paymentMethod = beneficiary_data.get('paymentMethod')
            existing_beneficiary.paymentsType = beneficiary_data.get('paymentsType')
            existing_beneficiary.otherPaymentType = beneficiary_data.get('otherPaymentType')
            existing_beneficiary.incomeType = beneficiary_data.get('incomeType')
            existing_beneficiary.otherIncomeType = beneficiary_data.get('otherIncomeType')
            existing_beneficiary.housing = beneficiary_data.get('housing')
            existing_beneficiary.otherHousing = beneficiary_data.get('otherHousing')
            existing_beneficiary.housingType = beneficiary_data.get('housingType')
            existing_beneficiary.otherHousingType = beneficiary_data.get('otherHousingType')
            existing_beneficiary.totalFamilyMembers = beneficiary_data.get('totalFamilyMembers')
            existing_beneficiary.childrenUnder15 = beneficiary_data.get('childrenUnder15')
            existing_beneficiary.isOldPeople = beneficiary_data.get('isOldPeople')
            existing_beneficiary.isDisabledPeople = beneficiary_data.get('isDisabledPeople')
            existing_beneficiary.isStudentsPeople = beneficiary_data.get('isStudentsPeople')
            existing_beneficiary.serviceDate = beneficiary_data.get('serviceDate')

            existing_beneficiary.save()

            return {'message': 'CaseBeneficiary updated successfully'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating beneficiary: {str(e)}")
            return {'message': f'Error updating CaseBeneficiary, please review inputs and try again.',
                    'error': f"Error adding beneficiary: {str(e)}"}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_namespace.route('/get/beneficiaries/<int:case_id>')
class CaseBeneficiaryByCaseIDResource(Resource):
    def get(self, case_id):
        try:
            
            case_data = CasesData.query.get_or_404(case_id)
            
            beneficiaries = CaseBeneficiary.query.filter_by(caseID=case_id).all()
            if not beneficiaries:
                return {'message': 'No beneficiaries found for the given case ID'}, HTTPStatus.NOT_FOUND
            serialized_beneficiaries = []
            for beneficiary in beneficiaries:
                serialized_beneficiary = {
                    'beneficiaryID': beneficiary.beneficiaryID,
                    'caseID': beneficiary.caseID,
                    'firstName': beneficiary.firstName,
                    'surName': beneficiary.surName,
                    'gender': beneficiary.gender,
                    'birthDate': beneficiary.birthDate,
                    'birthPlace': beneficiary.birthPlace,
                    'nationality': beneficiary.nationality,
                    'idType': beneficiary.idType,
                    'idNumber': beneficiary.idNumber,
                    'phoneNumber': beneficiary.phoneNumber,
                    'altPhoneNumber': beneficiary.altPhoneNumber,
                    'email': beneficiary.email,
                    'serviceRequired': beneficiary.serviceRequired,
                    'otherServiceRequired': beneficiary.otherServiceRequired,
                    'problemDescription': beneficiary.problemDescription,
                    'serviceDescription': beneficiary.serviceDescription,
                    'totalSupportCost': beneficiary.totalSupportCost,
                    'receiveFundDate': beneficiary.receiveFundDate.isoformat(),
                    'paymentMethod': beneficiary.paymentMethod,
                    'paymentsType': beneficiary.paymentsType,
                    'otherPaymentType': beneficiary.otherPaymentType,
                    'incomeType': beneficiary.incomeType,
                    'otherIncomeType': beneficiary.otherIncomeType,
                    'housing': beneficiary.housing,
                    'otherHousing': beneficiary.otherHousing,
                    'housingType': beneficiary.housingType,
                    'otherHousingType': beneficiary.otherHousingType,
                    'totalFamilyMembers': beneficiary.totalFamilyMembers,
                    'childrenUnder15': beneficiary.childrenUnder15,
                    'isOldPeople': beneficiary.isOldPeople,
                    'isDisabledPeople': beneficiary.isDisabledPeople,
                    'isStudentsPeople': beneficiary.isStudentsPeople,
                    'serviceDate': beneficiary.serviceDate
                }
                serialized_beneficiaries.append(serialized_beneficiary)
            return {'beneficiaries': serialized_beneficiaries}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting beneficiaries: {str(e)}")
            return {'message': f'Error getting beneficiaries: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR 


@case_namespace.route('/add/requirements/<int:case_id>')
class CaseAddRequirementsResource(Resource):
    @jwt_required()
    @case_namespace.expect(case_status_data)
    def post(self, case_id):
        try:
            
             # Get the current user ID from the JWT token
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            
            if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
                return {'message': 'Unauthorized. Only admin users can add requirements.'}, HTTPStatus.FORBIDDEN
        
            case = CasesData.get_by_id(case_id)
            # Parse the input data
            case_data = request.json
            status_data = case_data.pop('status_data', {})  # Assuming status_data is part of the input
            
            # Assign status data to the case
            case.assign_status_data(status_data)
            
            # Instead of popping the 'predefined_req', just access it directly
            requirementsList = status_data.get('predefined_req', [])
            processor = CaseRequirementProcessor(case, current_user.userID)
            #call the corresponding function to handle making a Task for that requirement
            for value in requirementsList:
                function_name = f"requirement_{value}"
                case_function = getattr(processor, function_name, processor.default_case)
                case_function()
            
            task =  CaseTask(
                caseID = case.caseID,
                title= 'Proof Of Service Delivery',
                description= 'Describe the service provided.',
                assignedTo = [],
                cc = [],
                createdBy= current_user.userID,
                attachedFiles= 'N/A',
                status= CaseTaskStatus.TODO,
                stageID=4,
                startDate = case.startDate,
                deadline= case.dueDate    
            )
            task.save()
            
            approvedAmount = status_data.get('approvedAmount')
            
            region_account = RegionAccount.query.filter_by(regionID=case.regionID).first()
            if approvedAmount and region_account:
                case_fund = CaseFunds(
                    accountID = region_account.accountID,
                    fundsAllocated = approvedAmount,
                    caseID = case.caseID  
                )
                
                case_fund.save()
                
            return {'message': 'Case requirements added successfully'}, HTTPStatus.CREATED
        except Exception as e:
            current_app.logger.error(f"Error adding requirements: {str(e)}")
            # Handle exceptions (e.g., database errors) appropriately
            return {'message': f'Error adding case requirements, please review inputs and try again.'}, HTTPStatus.INTERNAL_SERVER_ERROR

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
        case = CasesData.query.get(case_id)
        if not case:
            return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has permission to change the status
        if current_user.is_admin() or current_user.userID == case.userID:
            # Parse the new status from the request
            new_status = request.json.get('caseStatus')
            
            case.caseStatus = new_status

            # Save the updated case status to the database
            try:
                db.session.commit()
                # Check if the new status is 'Approved' and add stages if true
                if new_status == "APPROVED":
                    CaseToStage.query.filter_by(caseID=case.caseID).delete()
                    # Add all stages for the case
                    stage1 = CaseStage.query.filter_by(name='Information Collected').first()
                    stage2 = CaseStage.query.filter_by(name='Service Initiated').first()
                    stage3 = CaseStage.query.filter_by(name='Case Informed').first()
                    stage4 = CaseStage.query.filter_by(name='Service Delivered').first()
                    stage5 = CaseStage.query.filter_by(name='Service Validated').first()
                    stage6 = CaseStage.query.filter_by(name='Case Closed').first()
                    stage7 = CaseStage.query.filter_by(name='Print Report').first()

                    # Add the stages to the case
                    case_stages = [
                        CaseToStage(case=case, stage=stage1, started=True),
                        CaseToStage(case=case, stage=stage2, started=True),
                        CaseToStage(case=case, stage=stage3, started=True),
                        CaseToStage(case=case, stage=stage4, started=True),
                        CaseToStage(case=case, stage=stage5, started=True),
                        CaseToStage(case=case, stage=stage6, started=True),
                        CaseToStage(case=case, stage=stage7, started=True)
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

#######################################
# CASE BENEFICIARY
######################################


@case_namespace.route('/get/beneficiary_form/<int:case_id>', methods=['GET'])
class GetBeneficiaryFormByCaseResource(Resource):
    
    def get(self, case_id):
        
        try:
            case = CasesData.query.get(case_id)
       
            if not case:
                return {'message': 'Case not found.'}, HTTPStatus.NOT_FOUND
            
            form = BeneficiaryForm.query.filter_by(caseID=case_id).first()
            if not form:
                return {'message': 'no form found for this case.'}, HTTPStatus.NOT_FOUND
            form_dict = {
                'formID': form.formID,
                'caseID': form.caseID,
                'url': form.url,
                'used': form.used
            }
            return {'form': form_dict}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error retrieving form: {str(e)}")
            return {'message': f'Error getting form: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_namespace.route('/add_or_edit/beneficiary_form/<int:case_id>', methods=['POST', 'PUT'])
class AddBeneficiaryFormResource(Resource):
    
    @case_namespace.expect(case_beneficiary_form)
    def post(self, case_id):
        try:
            case = CasesData.query.get(case_id)
       
            if not case:
                return {'message': 'Case not found.'}, HTTPStatus.NOT_FOUND
            
            form_data = request.json
            
            form = BeneficiaryForm.query.filter_by(caseID=case_id).first()
            if form:
                form_dict = {
                'formID': form.formID,
                'caseID': form.caseID,
                'url': form.url,
                'used': form.used
                }
                return {'form': form_dict}, HTTPStatus.OK
            
            beneficiary_form = BeneficiaryForm(
                caseID=case.caseID, 
                url=form_data['url'],
                used=False
            )
            beneficiary_form.save()
            
            form_dict = {
                'formID': beneficiary_form.formID,
                'caseID': beneficiary_form.caseID,
                'url': beneficiary_form.url,
                'used': beneficiary_form.used
            }
            return {'form': form_dict}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding form: {str(e)}")
            return {'message': f'Error adding form: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
   
    @case_namespace.expect(case_beneficiary_form_edit)
    def put(self, case_id):
        try:
            
            form_data = request.json
            
            form = BeneficiaryForm.query.filter_by(caseID=case_id).first()
            if not form:
                
                return {'message': 'No form was found.'}, HTTPStatus.NOT_FOUND
            
            
            form.url = form_data['url']
            form.used = form_data['used']
            
            form.save()
            
            form_dict = {
                'formID': form.formID,
                'caseID': form.caseID,
                'url': form.url,
                'used': form.used
            }
            return {'form': form_dict}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding form: {str(e)}")
            return {'message': f'Error adding form: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


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
        if not current_user.is_admin():  # Adjust the condition based on your specific requirements
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
        if not current_user.is_admin():  # Adjust the condition based on your specific requirements
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
            case = CasesData.query.get(case_id)

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
            case = CasesData.query.get(case_id)

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

@case_namespace.route('/case_users/<int:case_id>')
class CaseUsersResource(Resource):
    @jwt_required()
    def get(self, case_id):
        # Get the current user ID from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Get the case by ID
        case = CasesData.query.get(case_id)
        if not case:
            return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

        # Check if the current user has access to the case
        if current_user.is_admin() or current_user in case.users:
            # Retrieve all users who have access to the case
            case_users = (
                db.session.query(Users)
                .join(CaseUser, Users.userID == CaseUser.userID)
                .filter(CaseUser.caseID == case_id)
                .all()
            )

            # Extract user information
            users_data = [{'userID': user.userID, 'username': user.username} for user in case_users]

            return {'case_users': users_data}, HTTPStatus.OK
        else:
            return {'message': 'Unauthorized. You do not have permission to view users for this case.'}, HTTPStatus.FORBIDDEN

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
            checklist = data.get('checklist',{})

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
                status = CaseTaskStatus.TODO,
                checklist = checklist,
                startDate = data.get('startDate',datetime.now().date())
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

@case_task_namespace.route('/delete/<int:task_id>',methods=['DELETE'])
class DeleteTaskResource(Resource):
    @jwt_required()
    @case_task_namespace.doc(
        description = "Delete the task."
    )
    def delete(self, task_id):
        try:
            task = CaseTask.get_by_id(task_id)
            #
            if task:
                task.delete()
                return {'message': 'Task deleted successfully.'}, HTTPStatus.OK
            else:
                return {'message': 'Task not found.'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            current_app.logger.error(f"Error deleting task: {str(e)}")
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

@case_task_namespace.route('/edit_comment_for_task', methods=['PUT'])
class EditTaskComments(Resource):
    @jwt_required()
    @case_task_namespace.expect(edit_comments_model, validate=True)
    @case_task_namespace.doc(
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
            comment_to_edit = CaseTaskComments.query.get_or_404(comment_id)

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

@case_task_namespace.route('/delete/task_comment/<int:comment_id>',methods=['DELETE'])
class DeleteComment(Resource):
    @jwt_required()
    def delete(self, comment_id):
        try:
            comment = CaseTaskComments.get_by_id(comment_id)
            
            if comment:
                comment.delete()
                return {'message': 'Comment deleted successfully'}, HTTPStatus.OK
            else:
                return {'message': 'Comment not found'}, HTTPStatus.NOT_FOUND
        except Exception as e:
            current_app.logger.error(f"Error deleting comment: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
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

@case_task_namespace.route('/edit_task/<int:task_id>', methods=['PUT'])
class EditTaskForStageResource(Resource):
    @case_task_namespace.expect(edit_task_model, validate=True)
    @jwt_required()
    def put(self, task_id):
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
       

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

            return {'message': 'Task updated successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error updating task: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_assessment_namespace.route('/assessment/questions/add')
class AddAssessmentQuestionResource(Resource):
    @jwt_required()
    @case_assessment_namespace.expect([assessment_question_model])
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
                new_question = CaseAssessmentQuestions(
                    questionText= question['questionText']
                )
                
                new_question.save()
            return {'message': 'All Assessment Questions were saved.'}, HTTPStatus.OK      
        except Exception as e:
            current_app.logger.error(f"Error In adding AssessmentQuestion: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_assessment_namespace.route('/assessment/questions/all')
class GetAllAssessmentQuestionsResource(Resource):
    @jwt_required()
    def get(self):
        # Get all assessment questions
        try:
            questions = CaseAssessmentQuestions.query.all()
            
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

@case_assessment_namespace.route('/assessment/answers/add')
class AddAssessmentAnswerResource(Resource):
    @jwt_required()
    @case_assessment_namespace.expect(assessment_model)
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
            # get the case this assessment is for
            case = CasesData.get_by_id(assessment_data['caseID'])
            if not case:
                return {'message': 'Case not found'}, HTTPStatus.BAD_REQUEST
            
            
            for answer in answers_data:
                question_id = answer['questionID']
                question = CaseAssessmentQuestions.get_by_id(question_id)
                if not question:
                    pass
                existing_answer = CaseAssessmentAnswers.query.filter_by(
                    questionID=question_id,
                    caseID=assessment_data['caseID']
                ).first()

                if existing_answer:
                    # If an answer already exists for the question, update it
                    existing_answer.answerText = answer['answerText']
                    existing_answer.extras = answer.get('extras', {})
                    db.session.commit()
                else:
                    # If no answer exists, create a new one
                    new_answer = CaseAssessmentAnswers(
                        questionID=question_id,
                        projectID=assessment_data['caseID'],
                        answerText=answer['answerText'],
                        extras=answer.get('extras', {})
                    )
                
                    new_answer.save()
            #now update case status to PENDING
            case.caseStatus = CaseStat.PENDING
            db.session.commit()
            return {'message': 'All Assessment Answers were saved.'}, HTTPStatus.OK
                
        except Exception as e:
            current_app.logger.error(f"Error In adding AssessmentQuestion: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_assessment_namespace.route('/assessment/answers/get/<int:case_id>', methods=['GET'])
class GetAssessmentResource(Resource):
    @jwt_required()
    def get(self, case_id):
        try:
            # Fetch all assessment answers for the given case_id
            assessment_answers = (
                CaseAssessmentAnswers.query
                .join(CaseAssessmentQuestions)
                .filter(CaseAssessmentAnswers.caseID == case_id)
                .add_columns(CaseAssessmentQuestions.questionText, CaseAssessmentAnswers.answerText, CaseAssessmentAnswers.extras)
                .all()
            )

            # Convert the list of answers to a JSON response
            answers_data = [
                {
                    'questionText': question_text,
                    'answerText': answer_text,
                    'extras': extras  # Include extras in the response
                }
                for _, question_text, answer_text, extras in assessment_answers
            ]

            return {'assessment_answers': answers_data}, HTTPStatus.OK
            
        except Exception as e:
            current_app.logger.error(f"Error In fetching Assessment: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR

@case_assessment_namespace.route('/assessment/delete/<int:case_id>', methods=['DELETE'])
class DeleteAssessmentResource(Resource):
    @jwt_required()
    def delete(self, case_id):
        # Get the current user from the JWT token
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Check if the current user is an admin
        if not current_user.is_admin():  # Assuming you have an 'is_admin()' property in the Users model
            return {'message': 'Unauthorized. Only admin users can delete answers.'}, HTTPStatus.FORBIDDEN

        try:
            # Delete all AssessmentAnswers for the specified case_id
            CaseAssessmentAnswers.query.filter_by(caseID=case_id).delete()
            db.session.commit()

            return {'message': 'Assessment answers deleted successfully'}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error in deleting assessment answers: {str(e)}")
            db.session.rollback()
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR


@case_assessment_namespace.route('/question/delete/<int:question_id>', methods=['DELETE'])
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
            question = CaseAssessmentQuestions.get_by_id(question_id)
            if question:
                question.delete()
                return {'message': 'Assessment question deleted successfully'}, HTTPStatus.OK
            else:
                return {'message': 'Assessment question not found'}, HTTPStatus.NOT_FOUND

        except Exception as e:
            current_app.logger.error(f"Error in deleting assessment question: {str(e)}")
            db.session.rollback()
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR



@case_task_namespace.route('/get_all_case_tasks/<int:case_id>', methods=['GET'])
class GetTasksForCaseResource(Resource):
    @jwt_required()
    def get(self, case_id):
        try:
            # get the case 
            case = CasesData.get_by_id(case_id)
            
            if case is None:
                return {'message': 'Case not found'}, HTTPStatus.NOT_FOUND

            # Fetch all tasks for the linked stage
            tasks =CaseTask.query.filter_by(caseID=case_id).all()

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

@case_task_namespace.route('/get_all_case_tasks/current_user', methods=['GET'])
class GetAllAssignedTasksResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Get the current user from the JWT token
            user = Users.query.filter_by(username=get_jwt_identity()).first()
            # Fetch all ProjectTasks the user is assigned to
            case_tasks = CaseTask.query.join(Users.case_assigned_tasks).filter(Users.userID == user.userID).all()
            total_c_tasks = len(case_tasks)
            completed_c_tasks = 0
            inprogress_c_tasks = 0
            overdue_c_tasks = 0
            not_started_c_tasks = 0
            if total_c_tasks > 0:

                for task in case_tasks:
                    if task.status == CaseTaskStatus.DONE:
                        completed_c_tasks += 1
                    if task.status == CaseTaskStatus.OVERDUE:
                        overdue_c_tasks += 1
                    if task.status == CaseTaskStatus.INPROGRESS:
                        inprogress_c_tasks += 1
                    if task.status == CaseTaskStatus.TODO:
                        not_started_c_tasks += 1
            
            all_assigned_tasks = {
                'case_tasks': [{'taskID': task.taskID,
                            'title': task.title,
                            'description': task.description,
                            'status': task.status.value,
                            'checklist': task.checklist,
                            'stageName': task.stage.name,
                            'caseName': CasesData.query.get(task.caseID).caseName,
                            'completionDate': task.completionDate.isoformat() if task.completionDate else None} for task in case_tasks] if case_tasks else [],
                'case_task_summary': {'total_c_tasks': total_c_tasks,'completed_c_tasks': completed_c_tasks, 'overdue_c_tasks': overdue_c_tasks,
                                     'not_started_c_tasks': not_started_c_tasks, 'inprogress_c_tasks': inprogress_c_tasks},
            }
            
            return all_assigned_tasks, HTTPStatus.OK
               
        except Exception as e:
            current_app.logger.error(f"Error getting all assigned project tasks: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR 



