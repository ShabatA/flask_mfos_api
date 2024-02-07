from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import NotFound
from http import HTTPStatus

from api.utils.case_requirement_processor import CaseRequirementProcessor
from ..models.cases import CaseCat, CasesData, CaseStat, CaseUser, CaseBeneficiary, CaseStage, CaseToStage, CaseTaskComments, CaseStatusData, CaseTask, BeneficiaryForm, CaseTaskStatus, CaseAssessmentAnswers, CaseAssessmentQuestions
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
    'checklist': fields.List(fields.Nested(checklist_model),description='optional checklist')
})

edit_task_model = case_task_namespace.model('EditTaskModel', {
    'title': fields.String(required=True, description='Title of the task'),
    'deadline': fields.Date(required=True, description='Deadline of the task (YYYY-MM-DD)'),
    'description': fields.String(description='Description of the task'),
    'assigned_to': fields.List(fields.Integer, description='List of user IDs assigned to the task'),
    'cc': fields.List(fields.Integer, description='List of user IDs to be CCed on the task'),
    'attached_files': fields.String(description='File attachments for the task'),
    'checklist': fields.List(fields.Nested(checklist_model),description='optional checklist')
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
                caseName=case_data['caseName'],
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
            
            
            return {'message': 'Case added successfully',
                    'case_id': new_case.caseID}, HTTPStatus.CREATED
        except Exception as e:
            current_app.logger.error(f"Error adding case: {str(e)}")
            return {'message': f'Error adding case: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

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
            existing_case.caseName = case_data['caseName']
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

            return {'message': 'Case updated successfully'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating case: {str(e)}")
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
                region_details = {'regionID': case.regionID, 'regionName': Regions.query.get(case.regionID).regionName}
                user_details = {'userID': current_user.userID, 'userFullName': current_user.firstName + current_user.lastName, 'username': current_user.username}

                case_details = {
                    'caseID': case.caseID,
                    'caseName': case.caseName,
                    'region': region_details,
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
                    'startDate': case.startDate.isoformat() if case.startDate else None
                }

                cases_data.append(case_details)

            return cases_data, HTTPStatus.OK
        except Exception as e:
            return {'message': f'Error fetching cases: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR




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
    @jwt_required()
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
    
    @jwt_required()
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
                checklist = checklist
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
                    'cc': [user.username for user in task.cc],
                    'createdBy': task.createdBy,
                    'attachedFiles': task.attachedFiles,
                    'status': task.status.value,
                    'completionDate': str(task.completionDate) if task.completionDate else None,
                    'comments': comments_list,
                    'checklist': task.checklist
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
        if not current_user.is_admin():  # Adjust the condition based on your specific requirements
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
                    'cc': [user.username for user in task.cc],
                    'createdBy': task.createdBy,
                    'attachedFiles': task.attachedFiles,
                    'status': task.status.value,
                    'completionDate': str(task.completionDate) if task.completionDate else None,
                    'comments': comments_list,
                    'checklist': task.checklist
                })

            return {'tasks': tasks_list}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting tasks for project: {str(e)}")
            return {'message': 'Internal Server Error'}, HTTPStatus.INTERNAL_SERVER_ERROR



