from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus

from api.models.accountfields import *
from api.models.cases import CasesData
from api.models.projects import ProjectsData
from ..models.users import Users
from ..models.regions import Regions
from ..utils.db import db
from datetime import datetime, date
from flask import jsonify, current_app
from flask import request
from ..models.finances import *
from sqlalchemy import desc

finance_namespace = Namespace("Finances", description="Namespace for Finances subsystem")

fund_data_model = finance_namespace.model('FinancialFundData',{
    'fundName': fields.String(required=True, description='Name of the actual account'),
    'totalFund': fields.Float(required=True, description='Balance (could be 0)'),
    'accountType': fields.String(required=True, description='Type of Account (Bank/Cash/Other)'),
    'notes': fields.String(required=False, description='Additional notes if applicable')
})

region_account_data = finance_namespace.model('RegionAccountData', {
    'regionID': fields.Integer(required=True, description='The region the account is for'),
    'totalFund': fields.Float(required=True, description='Balance (could be 0)'),
    'accountType': fields.String(required=True, description='Type of Account (Bank/Cash/Other)'),
    'notes': fields.String(required=False, description='Additional notes if applicable')
})

donor_data_model = finance_namespace.model('DonorData', {
    'name': fields.String(required=True, description='name of the donor'),
    'donorType': fields.String(required=True, description='could be organization or individual'),
    'country': fields.String(required=True, description='country where donor is from'),
    'email': fields.String(required=True),
    'phoneNumber': fields.String(required=True)
})

donations_data_model = finance_namespace.model('DonationData', {
    'donorID': fields.Integer(required=True, description='The donor who is donating'),
    'accountID': fields.Integer(required=True, description='The region account to donate to'),
    'fundID': fields.Integer(required=True, description='The account bank account the money will be deposited to'),
    'currency': fields.String(required=True, description='The currency of the donation'),
    'details': fields.String(required=True, description='Supply any notes/details'),
    'amount': fields.Float(required=True, description='The donation amount'),
    'field':  fields.String(enum=[field.value for field in FieldName],required=True ,description="What account field the donations falls under"),
    'donationType': fields.String(required=True, description='whether it is for a Case, Project, or General'),
    'caseID': fields.Integer(description='Only provide if donation type is Case'),
    'projectID': fields.Integer(description='Only provide if donation type is Project')
})

project_fund_release_request =finance_namespace.model('ProjectFundReleaseRequest', {
    'projectID': fields.Integer(required=True, description='The project the request is for'),
    'fundsRequested': fields.Float(required=True, description='The amount to be requested')
})

case_fund_release_request =finance_namespace.model('CaseFundReleaseRequest', {
    'caseID': fields.Integer(required=True, description='The case the request is for'),
    'fundsRequested': fields.Float(required=True, description='The amount to be requested')
})

fund_transfer_model = finance_namespace.model('FundTransfer', {
    'from_fund': fields.Integer(required=True, description= 'the fund to take from'),
    'to_fund': fields.Integer(required=True, description= 'the fund to transfer to'),
    'transferAmount': fields.Float(required=True, description='The amount to be transfered'),
    'notes': fields.String(required=False, description='Supply any notes/details'),
    'attachedFiles': fields.String(required=False, description='attached files'),   
})

payments_model = finance_namespace.model('Payments', {
    'from_fund': fields.Integer(required=True, description= 'the actual bank account the money will come from'),
    'paymentFor': fields.String(enum=[payment.value for payment in PaymentFor], description="What the payment is for"),
    'paymentName': fields.String(required=True, description='the name of the case/project is for, or something else'),
    'paymentMethod': fields.String(required=True, description='Method of payment'),
    'amount': fields.Float(required=True, description='The amount to be paid'),
    'notes': fields.String(required=False, description='any notes if applicable.')
})

project_funds_model = finance_namespace.model('ProjectFunds', {
    'projectID': fields.Integer(required=True),
    'fundsAllocated': fields.Float(required=True),
    'field': fields.String(enum=[field.value for field in FieldName],required=True ,description="What field of the project")
})

case_funds_model = finance_namespace.model('CaseFunds', {
    'caseID': fields.Integer(required=True),
    'fundsAllocated': fields.Float(required=True),
    'field': fields.String(enum=[field.value for field in FieldName],required=True ,description="What field of the case")
})

@finance_namespace.route('/finacial_fund/add_or_edit', methods=['POST', 'PUT'])
class AddEditFinancialFundResource(Resource):
    @jwt_required()
    @finance_namespace.expect(fund_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            fund_data = request.json
            
            if not current_user.is_admin():
                return {'message': 'Forbidden, only admins can add Financial Funds'}, HTTPStatus.FORBIDDEN

            # Check if a fund with the given name already exists
            existing_fund = FinancialFund.query.filter_by(fundName=fund_data['fundName']).first()
            if existing_fund:
                return {'message': 'Fund with this name already exists'}, HTTPStatus.CONFLICT
            
            new_fund = FinancialFund(
                fundName = fund_data['fundName'],
                totalFund = fund_data['totalFund'],
                accountType = fund_data['accountType'],
                usedFund = 0,
                notes= fund_data.get('notes', '')
            )
            
            new_fund.save()
            
            return {'message': 'Financial Fund was added successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding financial fund: {str(e)}")
            return {'message': f'Error adding financial fund: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    @jwt_required()
    @finance_namespace.expect(fund_data_model)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            fund_data = request.json
            
            if not current_user.is_admin():
                return {'message': 'Forbidden, only admins can add Financial Funds'}, HTTPStatus.FORBIDDEN

            # Check if a fund with the given name already exists
            fund_id = fund_data.get('fundID')
            if not fund_id:
                return {'message': 'Fund ID is required for updating a fund'}, HTTPStatus.BAD_REQUEST

            existing_fund = FinancialFund.query.get_or_404(fund_id)
            
            existing_fund.fundName = fund_data['fundName']
            existing_fund.totalFund = fund_data['totalFund']
            existing_fund.accountType = fund_data['accountType']
            existing_fund.notes = fund_data.get('notes', existing_fund.notes)
            
            existing_fund.save()
            return {'message': 'Financial Fund was updated successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding financial fund: {str(e)}")
            return {'message': f'Error adding financial fund: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/region_account/add_or_edit', methods=['POST', 'PUT'])
class AddEditRegionAccountResource(Resource):
    @jwt_required()
    @finance_namespace.expect(region_account_data)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            account_data = request.json
            
            if not current_user.is_admin():
                return {'message': 'Forbidden, only admins can add Region Accounts'}, HTTPStatus.FORBIDDEN
            
            region_id = account_data.get('regionID')
            
            region = Regions.query.get_or_404(region_id)
            # Check if a fund with the given name already exists
            existing_account = RegionAccount.query.filter_by(regionID=region_id).first()
            if existing_account:
                return {'message': f'An account in {region.regionName} already exists.'}, HTTPStatus.CONFLICT
            
            new_account = RegionAccount(
                acountName = region.regionName,
                totalFund = account_data['totalFund'],
                accountType = account_data['accountType'],
                usedFund = 0,
                notes= account_data.get('notes', ''),
                regionID=region_id
            )
            
            new_account.save()
            
            return {'message': 'Region Account was added successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding region Account fund: {str(e)}")
            return {'message': f'Error adding region Account: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    @jwt_required()
    @finance_namespace.expect(region_account_data)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            fund_data = request.json
            
            account_data = request.json
            
            if not current_user.is_admin():
                return {'message': 'Forbidden, only admins can add Region Accounts'}, HTTPStatus.FORBIDDEN
            
            region_id = account_data.get('regionID')
            
            region = Regions.query.get_or_404(region_id)
            # Check if a fund with the given name already exists
            existing_account = RegionAccount.query.filter_by(regionID=region_id).first()

            existing_account.accountName = region.regionName
            existing_account.totalFund = fund_data['totalFund']
            existing_account.accountType = fund_data['accountType']
            existing_account.notes = fund_data.get('notes', existing_account.notes)
            existing_account.regionID = region_id
            
            existing_account.save()
            return {'message': 'Region account was updated successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding region account: {str(e)}")
            return {'message': f'Error adding region account: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/donors/add_or_edit', methods=['POST', 'PUT'])
class AddEditDonorsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(donor_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donor_data = request.json
            
           
            # Check if a donor with the given name already exists
            existing_donor = Donors.query.filter_by(name=donor_data['name']).first()
            if existing_donor:
                return {'message': 'Donor with this name already exists'}, HTTPStatus.CONFLICT
            
            new_donor = Donors(
                name = donor_data['name'],
                donorType = donor_data['donorType'],
                country = donor_data['country'],
                email = donor_data['email'],
                phoneNumber = donor_data['phoneNumber'] 
            )
            
            new_donor.save()
            
            return {'message': 'Donor was added successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding Donor: {str(e)}")
            return {'message': f'Error adding Donor: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    @jwt_required()
    @finance_namespace.expect(donor_data_model)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donor_data = request.json
            
        
            # Check if a fund with the given name already exists
            donor_id = donor_data.get('donorID')
            if not donor_id:
                return {'message': 'Donor ID is required for updating a donor'}, HTTPStatus.BAD_REQUEST

            existing_donor = Donors.query.get_or_404(donor_id)
            
            existing_donor.fundName = donor_data['name']
            existing_donor.donorType = donor_data['donorType']
            existing_donor.country = donor_data['country']
            existing_donor.email = donor_data['email']
            existing_donor.phoneNumber = donor_data['phoneNumber']
            
            existing_donor.save()
            return {'message': 'Donor was updated successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error updating donor: {str(e)}")
            return {'message': f'Error updating donor: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/add_donation')
class AddDonationResource(Resource):
    @jwt_required()
    @finance_namespace.expect(donations_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donation_data = request.json
            
            account_id = donation_data.get('accountID')
            fund_id = donation_data.get('fundID')
            donor_id = donation_data.get('donorID')
            
            if not account_id or not fund_id or not donor_id:
                return {'message': 'Either no account ID fund ID, or donor ID provided'},HTTPStatus.BAD_REQUEST
            
            account = RegionAccount.query.get_or_404(account_id)
            fund = FinancialFund.query.get_or_404(fund_id)
            donor = Donors.query.get_or_404(donor_id)
            
            new_donation = Donations(
                donorID = donor_id,
                accountID = account_id,
                fundID = fund_id,
                details = donation_data.get('details', ''),
                currency = donation_data['currency'],
                amount = donation_data['amount'],
                field = donation_data['field'],
                donationType = donation_data['donationType'],
                caseID = donation_data.get('caseID', None),
                projectID = donation_data.get('projectID', None)
            )
            new_donation.save()
            
            #update the total funds
            account.totalFund += donation_data['amount']
            fund.totalFund += donation_data['amount']
            db.session.commit()
        
            return {'message': 'Donation added successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding donation: {str(e)}")
            return {'message': f'Error adding donation: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
@finance_namespace.route('/request_project_fund_release')
class RequestProjectFundReleaseResource(Resource):
    @jwt_required()
    @finance_namespace.expect(project_fund_release_request)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
            
            project_id = request.get('projectID')
            
            if not project_id:
                return {'message': 'project ID is required to make a request.'}, HTTPStatus.BAD_REQUEST
            
            project = ProjectsData.query.get_or_404(project_id)
            
            request = ProjectFundReleaseRequests(
                projectID = project_id,
                fundsRequested = request_data['fundsRequested'],
                requestedBy = current_user.userID
            )
            
            request.save()
            return {'message': 'Request posted successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/request_case_fund_release')
class RequestCaseFundReleaseResource(Resource):
    @jwt_required()
    @finance_namespace.expect(case_fund_release_request)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
            
            case_id = request.get('caseID')
            
            if not case_id:
                return {'message': 'case ID is required to make a request.'}, HTTPStatus.BAD_REQUEST
            
            case = CasesData.query.get_or_404(case_id)
            
            request = CaseFundReleaseRequests(
                caseID = case_id,
                fundsRequested = request_data['fundsRequested'],
                requestedBy = current_user.userID
            )
            
            request.save()
            
            return {'message': 'Request posted successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/request_fund_transfer')
class RequestFundTransferResource(Resource):
    @jwt_required()
    @finance_namespace.expect(fund_transfer_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
            
            request = FundTransferRequests(
                from_fund = request_data['from_fund'],
                to_fund = request_data['to_fund'],
                transferAmount = request_data['transferAmount'],
                notes = request_data['notes'],
                attachedFiles = request_data['attachedFiles'],
                requestedBy = current_user.userID
            )
            
            request.save()
            
            return {'message': 'Transfer posted successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/record_payments')
class RecordPaymentsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(payments_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
            
            fund_id = request_data.get('from_fund')
            
            if not current_user.is_admin():
                return {'message': 'only admins can make payments.'}, HTTPStatus.FORBIDDEN
            
            if not fund_id:
                return {'message': 'Fund ID not provided'},HTTPStatus.BAD_REQUEST
            
            fund = FinancialFund.query.get_or_404(fund_id)
            
            request = Payments(
                from_fund = request_data['from_fund'],
                paymentFor = request_data['paymentFor'],
                notes = request_data['notes'],
                paymentName = request_data['paymentName'],
                paymentMethod = request_data['paymentMethod'],
                amount = request_data['amount']
            )
            
            request.save()
            fund.totalFund -= request_data['amount']
            db.session.commit()
            
            return {'message': 'Payment recorded successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/add_project_funds')
class AddProjectFundsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(project_funds_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
            
            project_id = request_data.get('projectID')
            
            if not current_user.is_admin():
                return {'message': 'only admins can allocate funds.'}, HTTPStatus.FORBIDDEN
            
            if not project_id:
                return {'message': 'project ID not provided'},HTTPStatus.BAD_REQUEST
            
            project = ProjectsData.query.get_or_404(project_id)
            
            project_fund = ProjectFunds.query.filter_by(projectID=project_id)
            
            if project_fund:
                return {'message': 'This project was already allocated funds.'}, HTTPStatus.BAD_REQUEST
            
            region_account = RegionAccount.query.filter_by(regionID=project.regionID).first()
            new_fund = ProjectFunds(
                projectID=project_id,
                accountID=region_account.accountID,
                fundsAllocated= request_data['fundsAllocated']
            )
            scope = request_data['field']
            field = AccountFields.query.filter(AccountFields.fieldName.like(f'%{scope}%')).first()
            if field:
                attr_name = f'{field.fieldName.lower()}_funds'
                if hasattr(region_account, attr_name):
                    attr_value = getattr(region_account, attr_name)
                    new_value = attr_value + float(request_data['fundsAllocated'])
                    # Set the attribute value
                    setattr(region_account, attr_name, new_value)
            
            new_fund.save()
            return {'message': 'project has been allocated funds successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/add_case_funds')
class AddCaseFundsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(case_funds_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
            
            case_id = request_data.get('caseID')
            
            if not current_user.is_admin():
                return {'message': 'only admins can allocate funds.'}, HTTPStatus.FORBIDDEN
            
            if not case_id:
                return {'message': 'case ID not provided'},HTTPStatus.BAD_REQUEST
            
            case = CasesData.query.get_or_404(case_id)
            
            case_fund = ProjectFunds.query.filter_by(caseID=case_id)
            
            if case_fund:
                return {'message': 'This case was already allocated funds.'}, HTTPStatus.BAD_REQUEST
            
            region_account = RegionAccount.query.filter_by(regionID=case.regionID).first()
            new_fund = CaseFunds(
                projectID=case_id,
                accountID=region_account.accountID,
                fundsAllocated= request_data['fundsAllocated']
            )
            
            scope = request_data['field']
            field = AccountFields.query.filter(AccountFields.fieldName.like(f'%{scope}%')).first()
            if field:
                attr_name = f'{field.fieldName.lower()}_funds'
                if hasattr(region_account, attr_name):
                    attr_value = getattr(region_account, attr_name)
                    new_value = attr_value + float(request_data['fundsAllocated'])
                    # Set the attribute value
                    setattr(region_account, attr_name, new_value)
            
            new_fund.save()
            return {'message': 'project has been allocated funds successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/approve_case_fund_request/<int:case_id>/<int:request_id>')
class ApproveCaseFundRelease(Resource):
    @jwt_required()
    def put(self, case_id, request_id):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
           
            if not current_user.is_admin():
                return {'message': 'only admins can make approvals.'}, HTTPStatus.FORBIDDEN
            
            case = CasesData.query.get_or_404(case_id)
            fund_request = CaseFundReleaseRequests.query.get_or_404(request_id)
            case_fund = CaseFunds.query.filter_by(caseID=case_id).first_or_404()
            
            # if there is still money to be spent, decrease the total and approve the request
            if(fund_request.fundsRequested < case_fund.fundsAllocated):
                case_fund.fundsAllocated -= fund_request.fundsRequested
                fund_request.approved = True
                fund_request.approvedAt = datetime.utcnow()
                db.session.commit()
                return {'message': 'Request approved successfully and total funds allocated have been adjusted.'}, HTTPStatus.OK
            else:
                return {'message': f'Insufficient funds available to spend on this case. Available is {case_fund.fundsAllocated}'}, HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"Error approving request: {str(e)}")
            return {'message': f'Error approving request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/approve_project_fund_request/<int:project_id>/<int:request_id>')
class ApproveProjectFundRelease(Resource):
    @jwt_required()
    def put(self, project_id, request_id):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
           
            if not current_user.is_admin():
                return {'message': 'only admins can make approvals.'}, HTTPStatus.FORBIDDEN
            
            project = ProjectsData.query.get_or_404(project_id)
            fund_request = CaseFundReleaseRequests.query.get_or_404(request_id)
            project_fund = ProjectFunds.query.filter_by(projectID=project_id).first_or_404()
            
            # if there is still money to be spent, decrease the total and approve the request
            if(fund_request.fundsRequested < project_fund.fundsAllocated):
                project_fund.fundsAllocated -= fund_request.fundsRequested
                fund_request.approved = True
                fund_request.approvedAt = datetime.utcnow()
                db.session.commit()
                return {'message': 'Request approved successfully and total funds allocated have been adjusted.'}, HTTPStatus.OK
            else:
                return {'message': f'Insufficient funds available to spend on this project. Available is {project_fund.fundsAllocated}'}, HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"Error approving request: {str(e)}")
            return {'message': f'Error approving request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/change_transfer_request_stage/<int:request_id>')
class ChangeTransferRequestStage(Resource):
    @jwt_required()
    @finance_namespace.expect(finance_namespace.model('TransferStage', {
        'new_stage': fields.String(enum=[stage.value for stage in TransferStage],required=True ,description="What stage in the approval process")
    }))
    def put(self, request_id):
        
        try:
            
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
           
            if not current_user.is_admin():
                return {'message': 'only admins can make approvals.'}, HTTPStatus.FORBIDDEN
            
            transfer = FundTransferRequests.query.get_or_404(request_id)
            transfer.stage = request_data['new_stage']
           
            
            #set the approval time and make the transfer
            if request_data['new_stage'].lower() == 'approved':
                transfer.approvedAt = datetime.utcnow()
                from_fund = FinancialFund.query.get_or_404(transfer.from_fund)
                to_fund = FinancialFund.query.get_or_404(transfer.to_fund)
                from_fund.totalFund -= transfer.transferAmount
                from_fund.usedFund += transfer.transferAmount
                to_fund.totalFund += transfer.transferAmount
                
            db.session.commit()
            
            return {'message': 'Status changed successfully'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error changing stage request: {str(e)}")
            return {'message': f'Error changing stage request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route('/get_all_fund_transfer_requests')
class GetAllFundTransferRequests(Resource):
    @jwt_required()
    def get(self):
        try:
            requests = FundTransferRequests.query.order_by(desc(FundTransferRequests.createdAt)).all()
            requests_data = []
            for request in requests:
                user = Users.query.get(request.requestedBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                from_fund = FinancialFund.query.get(request.from_fund)
                from_fund_details = {'fundID': from_fund.fundID, 'fundName': from_fund.fundName, 'totalFund': from_fund.totalFund}
                to_fund = FinancialFund.query.get(request.to_fund)
                to_fund_details = {'fundID': to_fund.fundID, 'fundName': to_fund.fundName, 'totalFund': to_fund.totalFund}
                
                request_details = {
                    'requestID': request.requestID,
                    'from_fund': from_fund_details,
                    'to_fund': to_fund_details,
                    'requestedBy': user_details,
                    'transferAmount': request.transferAmount,
                    'createdAt': request.createdAt.isoformat(),
                    'notes': request.notes,
                    'attachedFiles': request.attachedFiles,
                    'stage': request.stage.value,
                    'approvedAt': request.approvedAt.isoformat() if request.approvedAt else None   
                }
                
                requests_data.append(request_details)
            
            return {'all_requests': requests_data}, HTTPStatus.OK
                
                
        except Exception as e:
            current_app.logger.error(f"Error getting fund transfer requests: {str(e)}")
            return {'message': f'Error getting fund transfer requests: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/get_all_fund_release_requests')
class GetAllFundReleaseRequests(Resource):
    @jwt_required()
    def get(self):
        try:
            case_requests = CaseFundReleaseRequests.query.order_by(desc(CaseFundReleaseRequests.createdAt)).all()
            case_requests_data = []
            for request in case_requests:
                user = Users.query.get(request.requestedBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                case_data = CasesData.query.get(request.caseID)
                case_details = {'caseID': case_data.caseID, 'caseName': case_data.caseName, 'category': case_data.category.value, 'status': case_data.caseStatus.value}
                
                request_details = {
                    'requestID': request.requestID,
                    'case': case_details,
                    'requestedBy': user_details,
                    'fundsRequested': request.fundsRequested,
                    'createdAt': request.createdAt.isoformat(),
                    'approved': request.approved,
                    'approvedAt': request.approvedAt.isoformat() if request.approvedAt else None   
                }
                
                case_requests_data.append(request_details)
            
            project_requests = ProjectFundReleaseRequests.query.order_by(desc(ProjectFundReleaseRequests.createdAt)).all()
            project_requests_data = []
            for request in project_requests:
                user = Users.query.get(request.requestedBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                project_data = ProjectsData.query.get(request.projectID)
                project_details = {'projectID': project_data.projectID, 'projectName': project_data.projectName, 'category': project_data.category.value, 'status': project_data.projectStatus.value}
                
                request_details = {
                    'requestID': request.requestID,
                    'project': project_details,
                    'requestedBy': user_details,
                    'fundsRequested': request.fundsRequested,
                    'createdAt': request.createdAt.isoformat(),
                    'approved': request.approved,
                    'approvedAt': request.approvedAt.isoformat() if request.approvedAt else None   
                }
                
                project_requests_data.append(request_details)
            
            return {'case_requests': case_requests_data, 'project_requests': project_requests_data}, HTTPStatus.OK
                
                
        except Exception as e:
            current_app.logger.error(f"Error getting fund release requests: {str(e)}")
            return {'message': f'Error getting fund release requests: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR  

@finance_namespace.route('/get_all_donors')
class GetAllDonationsResource(Resource):
    @jwt_required()
    def get(self):
        try:
            
            donors = Donors.query.all()
            
            donors_data = []
            for donor in donors:
                donations = Donations.query.filter_by(donorID=donor.donorID).order_by(desc(Donations.createdAt)).all()
                donations_data = []
                for donation in donations:
                    fund = FinancialFund.query.get(donation.fundID)
                    fund_details = {'fundID': fund.fundID, 'fundName': fund.fundName, 'totalFund': fund.totalFund}
                    account = RegionAccount.query.get(donation.accountID) 
                    account_details = {'accountID': account.accountID, 'accountName': account.accountName, 'totalFund': account.totalFund}
                    donations_details = {
                        'donationID': donation.id,
                        'fund_account_details': fund_details,
                        'region_account_details': account_details,
                        'details': donation.details,
                        'currency': donation.currency,
                        'field': donation.field,
                        'amount': donation.amount,
                        'createdAt': donation.createdAt.isoformat()
                    }
                    donations_data.append(donations_details)
                
                donor_details = {
                    'name': donor.name,
                    'donorType': donor.donorType,
                    'country': donor.country,
                    'donorID': donor.donorID,
                    'donations': donations_data
                }
                donors_data.append(donor_details)
            
            return {'donors': donors_data}, HTTPStatus.OK
                
              
        except Exception as e:
            current_app.logger.error(f"Error getting all donors: {str(e)}")
            return {'message': f'Error getting all donors: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/get_all_payments')
class GetAllPaymentsResource(Resource):
    @jwt_required()
    def get(self):
        try:
            payments = Payments.query.order_by(desc(Payments.createdAt)).all()
            
            payments_data = []
            for payment in payments:
                from_fund = FinancialFund.query.get(payment.from_fund)
                from_fund_details = {'fundID': from_fund.fundID, 'fundName': from_fund.fundName, 'totalFund': from_fund.totalFund}
                payment_details = {
                    'paymentID': payment.paymentID,
                    'from_fund': from_fund_details,
                    'paymentName': payment.paymentName,
                    'paymentMethod': payment.paymentMethod,
                    'notes': payment.notes,
                    'amount': payment.amount,
                    'createdAt': payment.createdAt.isoformat()
                }
                payments_data.append(payment_details)
            
            return {'all_payments': payments_data}, HTTPStatus.OK 
        
        
        except Exception as e:
            current_app.logger.error(f"Error getting all payments: {str(e)}")
            return {'message': f'Error getting all payments: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/get_all_payments_for_fund/<int:fund_id>')
class GetAllFundPaymentsResource(Resource):
    @jwt_required()
    def get(self, fund_id):
        try:
            fund = FinancialFund.query.get_or_404(fund_id)
            payments = Payments.query.filter_by(from_fund=fund_id).order_by(desc(Payments.createdAt)).all()
            
            payments_data = []
            for payment in payments:
                payment_details = {
                    'paymentID': payment.paymentID,
                    'paymentName': payment.paymentName,
                    'paymentMethod': payment.paymentMethod,
                    'notes': payment.notes,
                    'amount': payment.amount,
                    'createdAt': payment.createdAt.isoformat()
                }
                payments_data.append(payment_details)
            
            return {'all_payments': payments_data}, HTTPStatus.OK 
        
        
        except Exception as e:
            current_app.logger.error(f"Error getting all payments: {str(e)}")
            return {'message': f'Error getting all payments: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/get_all_region_accounts')
class GetAllRegionAccount(Resource):
    @jwt_required()
    def get(self):
        try:
            
            region_accounts = RegionAccount.query.all()
            accounts_data = []
            
            for account in region_accounts:
                project_funds = ProjectFunds.query.filter_by(accountID= account.accountID).all()
                case_funds = CaseFunds.query.filter_by(accountID= account.accountID).all()
                donations = Donations.query.filter_by(accountID=account.accountID).order_by(desc(Donations.createdAt)).all()
                project_funds_data = []
                case_funds_data = []
                donations_data = []
                for fund in project_funds:
                    project = ProjectsData.query.get(fund.projectID)
                    project_data = {'projectID': project.projectID, 'projectName': project.projectName, 'budgetApproved': project.budgetApproved,
                                    'category': project.category.value, 'status': project.projectStatus.value, 'startDate': project.startDate.isoformat() if project.startDate else None,
                                    'solution': project.solution, 'dueDate': project.dueDate.isoformat() if project.dueDate else None}
                    fund_details = {
                        'fundID': fund.fundID,
                        'project_details': project_data,
                        'fundsAllocated': fund.fundsAllocated
                    }
                    project_funds_data.append(fund_details)
                    
                for fund in case_funds:
                    case = CasesData.query.get(fund.caseID)
                    case_data = {'caseID': case.caseID, 'caseName': case.caseName, 'budgetApproved': case.budgetApproved,
                                    'category': case.category.value, 'status': case.caseStatus.value, 'startDate': case.startDate.isoformat() if case.startDate else None,
                                    'dueDate': case.dueDate.isoformat() if case.dueDate else None}
                    fund_details = {
                        'fundID': fund.fundID,
                        'case_details': case_data,
                        'fundsAllocated': fund.fundsAllocated
                    }
                    case_funds_data.append(fund_details)
                
                for donation in donations:
                    fund = FinancialFund.query.get(donation.fundID)
                    fund_details = {'fundID': fund.fundID, 'fundName': fund.fundName, 'totalFund': fund.totalFund}
                    donations_details = {
                        'donationID': donation.id,
                        'fund_account_details': fund_details,
                        'details': donation.details,
                        'currency': donation.currency,
                        'field': donation.field,
                        'amount': donation.amount,
                        'createdAt': donation.createdAt.isoformat()
                    }
                    donations_data.append(donations_details)
                
                account_details = {
                    'accountID': account.accountID,
                    'accountName': account.accountName,
                    'totalFund': account.totalFund,
                    'usedFund': account.usedFund,
                    'accountType': account.accountType,
                    'notes': account.notes,
                    'lastTransaction': account.lastTransaction.isoformat() if account.lastTransation else None,
                    'health_funds': account.health_funds,
                    'education_funds': account.education_funds,
                    'general_funds': account.general_funds,
                    'shelter_funds': account.shelter_funds,
                    'sponsorship_funds': account.sponsorship_funds,
                    'donations': donations_data,
                    'funded_projects': project_funds_data,
                    'funded_cases': case_funds_data
                }
                accounts_data.append(account_details)
            
            return {'all_accounts': accounts_data}, HTTPStatus.OK
                
        except Exception as e:
            current_app.logger.error(f"Error getting all region accounts: {str(e)}")
            return {'message': f'Error getting all region accounts: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/get_all_financial_funds')
class GetAllFinancialFunds(Resource):
    @jwt_required()
    def get(self):
        try:
            fund_accounts = FinancialFund.query.all()
            accounts_data = []
            
            for fund in fund_accounts:
                donations = Donations.query.filter_by(fundID=fund.fundID).order_by(desc(Donations.createdAt)).all()
                donations_data = []
                for donation in donations:
                    account = RegionAccount.query.get(donation.accountID) 
                    account_details = {'accountID': account.accountID, 'accountName': account.accountName, 'totalFund': account.totalFund}
                    donations_details = {
                        'donationID': donation.id,
                        'region_account_details': account_details,
                        'details': donation.details,
                        'currency': donation.currency,
                        'field': donation.field,
                        'amount': donation.amount,
                        'createdAt': donation.createdAt.isoformat()
                    }
                    donations_data.append(donations_details)
                    
                payments = Payments.query.filter_by(from_fund=fund.fundID).order_by(desc(Payments.createdAt)).all()
                payments_data = []
                for payment in payments:
                    payment_details = {
                        'paymentID': payment.paymentID,
                        'paymentName': payment.paymentName,
                        'paymentMethod': payment.paymentMethod,
                        'notes': payment.notes,
                        'amount': payment.amount,
                        'createdAt': payment.createdAt.isoformat()
                    }
                    payments_data.append(payment_details)
                    
                account_details = {
                    'fundID': fund.fundID,
                    'fundName': fund.fundName,
                    'totalFund': fund.totalFund,
                    'usedFund': fund.usedFund,
                    'accountType': fund.accountType,
                    'notes': fund.notes,
                    'createdAt': fund.createdAt.isoformat(),
                    'donations': donations_data,
                    'payments': payments_data
                }
                accounts_data.append(account_details)
            
            return {'fund_accounts': accounts_data}
                
        except Exception as e:
            current_app.logger.error(f"Error getting all financial fund accounts: {str(e)}")
            return {'message': f'Error getting all financial fund accounts: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        

              
            
        
            
           
            
