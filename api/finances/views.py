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

currency_model = finance_namespace.model('Currency',{
    'currencyName': fields.String(required=True, description='The name of the currency'),
    'dollarRate': fields.Float(required=True, description='Exchange rate to 1 USD')
})

sub_fund_model = finance_namespace.model('SubFund',{
    'fundName': fields.String(required=True, description='Name of the sub fund'),
})

fund_data_model = finance_namespace.model('FinancialFundData',{
    'fundName': fields.String(required=True, description='Name of the actual account'),
    'accountType': fields.String(required=True, description='Type of Account (Bank/Cash/Other)'),
    'notes': fields.String(required=False, description='Additional notes if applicable'),
    'currencies': fields.List(fields.Integer, description='Optional list of currencies excluding the default USD'),
    'administrator': fields.Integer(required=True, description='The user ID of the employee responsible for this account'),
    'subFunds': fields.List(fields.Nested(sub_fund_model),description='optional sub fund names')
})

sub_fund_data_model = finance_namespace.model('FinancialFundData',{
    'fundName': fields.String(required=True, description='Name of the actual account'),
    'fundID': fields.String(required=True, description='ID of the parent fund account'),
    'accountType': fields.String(required=True, description='Type of Account (Bank/Cash/Other)'),
    'currencies': fields.List(fields.Integer, description='Optional list of currencies excluding the default USD'),
    'administrator': fields.Integer(required=True, description='The user ID of the employee responsible for this account')
})

region_account_data = finance_namespace.model('RegionAccountData', {
    'regionID': fields.Integer(required=True, description='The region the account is for'),
    'currencies': fields.List(fields.Integer, description='Optional list of currencies excluding the default USD')
})

donor_rep_model = finance_namespace.model('DonorRepresentative',{
    'name': fields.String(required=True, description='name of the donor'),
    'jobPosition': fields.String(required=True),
    'email': fields.String(required=True),
    'phoneNumber': fields.String(required=True)
})

donor_data_model = finance_namespace.model('DonorData', {
    'name': fields.String(required=True, description='name of the donor'),
    'donorType': fields.String(required=True, description='could be organization or individual', enum=[type.value for type in DonorTypes]),
    'country': fields.String(required=True, description='country where donor is from'),
    'email': fields.String(required=True),
    'phoneNumber': fields.String(required=True),
    'notes': fields.String(required=False),
    'representatives': fields.List(fields.Nested(donor_rep_model), description='list of representatives')
})

donations_data_model = finance_namespace.model('DonationData', {
    'donorID': fields.Integer(required=True, description='The donor who is donating'),
    'accountID': fields.Integer(required=True, description='The region account to donate to'),
    'fundID': fields.Integer(required=True, description='The account bank account the money will be deposited to'),
    'subFundID': fields.Integer(required=False, description='Specify the sub fund the money will be deposited to if applicable.'),
    'details': fields.String(required=True, description='Supply any notes/details'),
    'amount': fields.Float(required=True, description='The donation amount'),
    'donationType': fields.String(required=True, description='whether it is for a Case, Project, or General', enum=[type.value for type in DonationTypes]),
    'caseID': fields.Integer(description='Only provide if donation type is Case'),
    'projectID': fields.Integer(description='Only provide if donation type is Project'),
    'currencyID': fields.Integer(required=True, description='The currency the amount originates from'),
    'project_scope': fields.String(required=True, enum=[scope.value for scope in ProjectScopes], description='The project scope.'),
    'allocationTags': fields.String(required=False, description='tags to use if the project/case is not in the system.')
})

project_fund_release_request =finance_namespace.model('ProjectFundReleaseRequest', {
    'projectID': fields.Integer(required=True, description='The project the request is for'),
    'fundsRequested': fields.Float(required=True, description='The amount to be requested'),
    'paymentCount': fields.Integer(required=True, description='Specify which payment you are requesting out of the payment breakdown')
})

case_fund_release_request =finance_namespace.model('CaseFundReleaseRequest', {
    'caseID': fields.Integer(required=True, description='The case the request is for'),
    'fundsRequested': fields.Float(required=True, description='The amount to be requested'),
    'paymentCount': fields.Integer(required=True, description='Specify which payment you are requesting out of the payment breakdown')
})

fund_transfer_model = finance_namespace.model('FundTransfer', {
    'from_fund': fields.Integer(required=True, description= 'the fund to take from'),
    'to_fund': fields.Integer(required=True, description= 'the fund to transfer to'),
    'transferAmount': fields.Float(required=True, description='The amount to be transfered'),
    'notes': fields.String(required=False, description='Supply any notes/details'),
    'transfer_type': fields.String(required=True, enum=[type.value for type in TransferType] , description='EFT, Cash, or Check')
})

payments_model = finance_namespace.model('Payments', {
    'from_fund': fields.Integer(required=True, description= 'the actual bank account the money will come from'),
    'subFundID': fields.Integer(required=False, description='the sub fund of the main if applicable'),
    'paymentFor': fields.String(enum=[payment.value for payment in PaymentFor], description="What the payment is for"),
    'paymentName': fields.String(required=True, description='the name of the case/project is for, or something else'),
    'paymentMethod': fields.String(required=True, enum=[type.value for type in TransferType] , description='EFT, Cash, or Check'),
    'amount': fields.Float(required=True, description='The amount to be paid'),
    'currencyID': fields.Integer(required=True, description='The currency the payment is made in'),
    'transferExpenses': fields.Float(required=False, description='Transfer expenses if any.'),
    'projectScope': fields.String(required=False, enum=[scope.value for scope in ProjectScopes], description='In what scope or field will the money be spent on'),
    'notes': fields.String(required=False, description='any notes if applicable.')
})

project_funds_model = finance_namespace.model('ProjectFunds', {
    'projectID': fields.Integer(required=True),
    'fundsAllocated': fields.Float(required=True),
    'field': fields.String(enum=[scope.value for scope in ProjectScopes],required=True ,description="What field of the project")
})

case_funds_model = finance_namespace.model('CaseFunds', {
    'caseID': fields.Integer(required=True),
    'fundsAllocated': fields.Float(required=True),
    'field': fields.String(enum=[scope.value for scope in ProjectScopes],required=True ,description="What field of the case")
})

reports_data_model = finance_namespace.model('Reports',{
    'reportTag': fields.String(required=True),
    'title': fields.String(required=True),
    'createdBy': fields.String(required=True),
    'pdfBytes': fields.String(required=True)
})

currencies_model = finance_namespace.model('CurrencyData',{
    'currencyCode' : fields.String(required=True, description='The code of the currency e.g USD'),
    'currencyName' : fields.String(required=True, description='The name of the currency e.g United States Dollar'),
    'exchangeRateToUSD': fields.Float(required=True)
})

@finance_namespace.route('/currencies/create', methods=['POST','PUT'])
class CreateCurrency(Resource):
    @jwt_required()
    @finance_namespace.expect(currencies_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            currency_data = request.json
            if not current_user.is_admin():
                return {'message': 'Forbidden, only admins can add currencies'}, HTTPStatus.FORBIDDEN
            
            currency = Currencies(
                currencyCode = currency_data['currencyCode'],
                currencyName = currency_data['currencyName'],
                exchangeRateToUSD = currency_data['exchangeRateToUSD']
            )
            currency.save()
            return {'message': 'Currency added successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding currency: {str(e)}")
            return {'message': f'Error adding currency: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    @jwt_required()
    @finance_namespace.expect(currencies_model)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            currency_data = request.json
            if not current_user.is_admin():
                return {'message': 'Forbidden, only admins can add currencies'}, HTTPStatus.FORBIDDEN
            
            currency = Currencies.query.get_or_404(currency_data['currencyID'])
            currency.currencyCode = currency_data['currencyCode']
            currency.currencyName = currency_data['currencyName']
            currency.exchangeRateToUSD = currency_data['exchangeRateToUSD']
            currency.save()
            return {'message': 'Currency updated successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating currency: {str(e)}")
            return {'message': f'Error updating currency: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    

@finance_namespace.route('/finacial_funds/create', methods=['POST', 'PUT'])
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
                usedFund = 0,
                notes= fund_data.get('notes', ''),
                accountType = fund_data['accountType'],
                administrator = fund_data['administrator'],
            )
            
            new_fund.save()
             #add the USD default
            new_currency = FinancialFundCurrencyBalance(
                        fundID = new_fund.fundID,
                        currencyID = 1
                    )
            new_currency.save()
            
            if len(fund_data['currencies'] > 0):
                for currency in fund_data['currencies']:
                    if currency != 1:
                        new_currency = FinancialFundCurrencyBalance(
                                            fundID = new_fund.fundID,
                                            currencyID = currency
                                        )
                        new_currency.save()
            
            #now let's add the sub funds
            sub_funds = fund_data.get('subFunds', {})
            
            for sub in sub_funds:
                new_sub_fund = SubFunds(
                    fundID = new_fund.fundID,
                    subFundName = sub['fundName'],
                    currencyID = fund_data['currencyID'],
                    notes= fund_data.get('notes', ''),
                    accountType = fund_data['accountType'],
                    administrator = fund_data['administrator'],
                )
                new_sub_fund.save()
                new_balance = SubFundCurrencyBalance(
                    subFundID = new_sub_fund.subFundID,
                    currencyID = 1
                )
                new_balance.save()
                
                if len(fund_data['currencies'] > 0):
                    for currency in fund_data['currencies']:
                        if currency != 1:
                            balance = SubFundCurrencyBalance(
                                subFundID = new_sub_fund.subFundID,
                                currencyID = 1
                            )
                            balance.save()
            
            return {'message': 'Sub Fund was added successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding financial fund: {str(e)}")
            return {'message': f'Error adding finacial fund: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
@finance_namespace.route('/financial_funds/sub_fund_create')
class SubFundCreateResource(Resource):
    @jwt_required()
    @finance_namespace.expect(sub_fund_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            fund_data = request.json
            
            if not current_user.is_admin():
                return {'message': 'Forbidden, only admins can add Financial Funds'}, HTTPStatus.FORBIDDEN

            # Check if a fund with the given name already exists
            existing_fund = FinancialFund.query.get_or_404(fund_data['fundID'])
            if not existing_fund:
                return {'message': 'Parent fund does not exist'}, HTTPStatus.NOT_FOUND
            
            new_fund = SubFunds(
                fundID = fund_data['fundID'],
                subFundName = fund_data['fundName'],
                notes= fund_data.get('notes', ''),
                accountType = fund_data['accountType'],
                administrator = fund_data['administrator'],
            )
            new_fund.save()
            
            new_balance = SubFundCurrencyBalance(
                    subFundID = new_fund.subFundID,
                    currencyID = 1
                )
            new_balance.save()
            
            if len(fund_data['currencies'] > 0):
                for currency in fund_data['currencies']:
                    if currency != 1:
                        balance = SubFundCurrencyBalance(
                            subFundID = new_fund.subFundID,
                            currencyID = 1
                        )
                        balance.save()
        except Exception as e:
            current_app.logger.error(f"Error adding sub-fund Account: {str(e)}")
            return {'message': f'Error adding sub-fund Account: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
            
                

@finance_namespace.route('/region_accounts/create', methods=['POST', 'PUT'])
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
                regionID=region_id
            )
            new_account.save()
            
            #add the USD default
            new_currency = RegionAccountCurrencyBalance(
                        accountID = new_account.accountID,
                        currencyID = 1
                    )
            new_currency.save()
            
            if len(account_data['currencies'] > 0):
                for currency in account_data['currencies']:
                    if currency != 1:
                        new_currency = RegionAccountCurrencyBalance(
                                            accountID = new_account.accountID,
                                            currencyID = currency
                                        )
                        new_currency.save()
                    
            
            return {'message': 'Region Account was added successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding region Account: {str(e)}")
            return {'message': f'Error adding region Account: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    


@finance_namespace.route('/donors/add_or_edit', methods=['POST', 'PUT'])
class AddEditDonorsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(donor_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donor_data = request.json
            
           
            # Check if a donor with the given name already exists
            existing_donor = Donor.query.filter_by(donorName=donor_data['name']).first()
            if existing_donor:
                return {'message': 'Donor with this name already exists'}, HTTPStatus.CONFLICT
            
            new_donor = Donor(
                donorName = donor_data['name'],
                donorType = donor_data['donorType'],
                placeOfResidence = donor_data['country'],
                email = donor_data['email'],
                phoneNumber = donor_data['phoneNumber'],
                notes = donor_data.get('notes', None)
            )
            
            new_donor.save()
            
            if(len(donor_data['representatives']) > 0):
                for rep in donor_data['representatives']:
                    new_rep = Representative(
                        donorID = new_donor.donorID,
                        name = rep['name'],
                        jobPosition = rep['jobPosition'],
                        email = rep['email'],
                        phoneNumber = rep['phoneNumber']
                    )
                    new_rep.save()
            
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

            existing_donor = Donor.query.get_or_404(donor_id)
            
            existing_donor.donorName = donor_data['name']
            existing_donor.donorType = donor_data['donorType']
            existing_donor.placeOfResidence = donor_data['country']
            existing_donor.email = donor_data['email']
            existing_donor.phoneNumber = donor_data['phoneNumber']
            existing_donor.notes = donor_data['notes']
            
            existing_donor.save()
            return {'message': 'Donor was updated successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error updating donor: {str(e)}")
            return {'message': f'Error updating donor: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/add_balance')
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
            donor = Donor.query.get_or_404(donor_id)
            
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
            #call the add function to handle the logic
            account.add_fund(donation_data['amount'],donation_data.get('currency',1), None,donation_data.get('projectID', None), donation_data.get('caseID', None), None)
            fund.add_fund(donation_data['amount'],donation_data.get('currency',1))
            db.session.commit()
        
            return {'message': 'Donation added successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding donation: {str(e)}")
            return {'message': f'Error adding donation: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/region_accounts/all/summary/currency/<int:currency_conversion>')
class RegionAccountSummaryResource(Resource):
    @jwt_required()
    def get(self, currency_conversion):
        try:
            accounts = RegionAccount.query.all()
            accounts_data = []
            for account in accounts:
                account_data = {
                    'accountID': account.accountID,
                    'accountName': account.accountName,
                    'lastUpdate': account.lastUpdate.isoformat()
                }
                #get balances based on the currency conversion
                balances = account.get_fund_balance(currency_conversion)
                accounts_data.append(account_data | balances)
            return {'accounts': accounts_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting account summary: {str(e)}")
            return {'message': f'Error getting account summary: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/region_accounts/single/<int:account_id>/details/<int:currency_conversion>')
class SingleRegionAccountSummaryResource(Resource):
    @jwt_required()
    def get(self,account_id, currency_conversion):
        try:
            account = RegionAccount.query.get_or_404(account_id)
            account_data = {
                'accountID': account.accountID,
                'accountName': account.accountName,
                'lastUpdate': account.lastUpdate.isoformat(),
                'availableCurrencies': account.get_available_currencies,
                'transactions': account.get_account_transactions()
            }
            #get balances based on the currency conversion
            balances = account.get_fund_balance(currency_conversion)
            return {'account': account_data | balances}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting account summary: {str(e)}")
            return {'message': f'Error getting account summary: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR



@finance_namespace.route('/financial_funds/all/summary/currency/<int:currency_conversion>')
class FinancialFundSummaryResource(Resource):
    @jwt_required()
    def get(self, currency_conversion):
        try:
            funds = FinancialFund.query.all()
            funds_data = []
            for fund in funds:
                fund_data = {
                    'fundID': fund.fundID,
                    'fundName': fund.fundName,
                    'lastUpdate': fund.lastUpdate.isoformat()
                }
                #get balances based on the currency conversion
                balances = fund.get_fund_balance(currency_conversion)
                funds_data.append(fund_data | balances)
            return {'funds': funds_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting fund summary: {str(e)}")
            return {'message': f'Error getting fund summary: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/financial_funds/single/<int:fund_id>/details/<int:currency_conversion>')
class SingleFinancialFundSummaryResource(Resource):
    @jwt_required()
    def get(self,fund_id, currency_conversion):
        try:
            fund = FinancialFund.query.get_or_404(fund_id)
            fund_data = {
                'fundID': fund.fundID,
                'fundName': fund.fundName,
                'lastUpdate': fund.lastUpdate.isoformat(),
                'availableCurrencies': fund.get_available_currencies,
                'subFunds': fund.get_all_sub_funds(),
                'transactions': fund.get_all_payments(),
                'donations': fund.get_all_donations()
            }
            #get balances based on the currency conversion
            balances = fund.get_fund_balance(currency_conversion)
            return {'fund': fund_data | balances}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting fund summary: {str(e)}")
            return {'message': f'Error getting fund summary: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
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
                requestedBy = current_user.userID,
                paymentCount = request_data['paymentCount']
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
                requestedBy = current_user.userID,
                paymentCount = request_data['paymentCount']
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
                requestedBy = current_user.userID,
                transferType = request_data['transferType']
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
                amount = request_data['amount'],
                currencyID = request_data['currencyID'],
                transferExpenses = request_data.get('transferExpenses', 0),
                projectScope = request_data.get('projectScope', None),
                subFundID = request_data.get('subFundID',None)
            )
            
            request.save()
            if request_data.get('subFundID',None) is not None:
                sub_fund = SubFunds.query.get_or_404(request_data['subFundID'])
                sub_fund.use_fund(request_data['amount'], request_data['currencyID'])
            
            fund.use_fund(request_data['amount'], request_data['currencyID'])
            
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
                # make the transfer
                from_fund.use_fund(transfer.transferAmount, 1)
                to_fund.add_fund(transfer.transferAmount, 1)
                
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
                from_fund = FinancialFund.query.get(request.from_fund)
                to_fund = FinancialFund.query.get(request.to_fund)
                
                
                request_details = {
                    'requestID': request.requestID,
                    'from_fund': {
                        'fundID': from_fund.fundID,
                        'fundName': from_fund.fundName,
                        'totalFund': from_fund.totalFund,
                        'currency': from_fund.currency.currencyCode
                    },
                    'to_fund': {
                        'fundID': to_fund.fundID,
                        'fundName': to_fund.fundName,
                        'totalFund': to_fund.totalFund,
                        'currency': to_fund.currency.currencyCode
                    },
                    'requestedBy': {
                        'userID': user.userID,
                        'userFullName': f'{user.firstName} {user.lastName}',
                        'username': user.username
                    },
                    'transferAmount': request.transferAmount,
                    'createdAt': request.createdAt.isoformat(),
                    'notes': request.notes,
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
            
            donors = Donor.query.all()
            
            donors_data = []
            for donor in donors:
                donations = Donations.query.filter_by(donorID=donor.donorID).order_by(desc(Donations.createdAt)).all()
                donations_data = []
                total_donation_amount = 0
                latest_donation = None  # Initialize latest_donation variable
                for donation in donations:
                    fund = FinancialFund.query.get(donation.fundID)
                    fund_details = {'fundID': fund.fundID, 'fundName': fund.fundName, 'totalFund': fund.totalFund, 'currency': Currencies.query.get(fund.currencyID).currencyCode}
                    account = RegionAccount.query.get(donation.accountID) 
                    account_details = {'accountID': account.accountID, 'accountName': account.accountName, 'totalFund': account.totalFund, 'currency': Currencies.query.get(account.currencyID).currencyCode}
                    donations_details = {
                        'donationID': donation.id,
                        'fund_account_details': fund_details,
                        'region_account_details': account_details,
                        'details': donation.details,
                        'currency': Currencies.query.get(donation.currencyID).currencyCode,
                        'projectScope': donation.projectScope.value,
                        'donationType': donation.donationType.value,
                        'amount': donation.amount,
                        'allocationTags': donation.allocationTags,
                        'createdAt': donation.createdAt.isoformat()
                    }
                    donations_data.append(donations_details)
                    total_donation_amount += donation.amount
                    if latest_donation is None or donation.createdAt > latest_donation:
                        latest_donation = donation.createdAt
                
                donor_info = donor.get_donor_info()
                donor_info['totalDonationAmount'] = total_donation_amount
                donor_info['donations'] = donations_data
                donor_info['latestDonation'] = latest_donation.strftime("%d %b %Y") if latest_donation else None  # Format latest_donation as "20 Sept 2023"
                donors_data.append(donor_info)
            
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
                    'paymentMethod': payment.paymentMethod.value,
                    'paymentFor': payment.paymentFor.value,
                    'projectScope': payment.projectScope.value,
                    'notes': payment.notes,
                    'amount': payment.amount,
                    'currency': Currencies.query.get(payment.currencyID).currencyCode,
                    'transferExpenses': payment.transferExpenses,
                    'createdAt': payment.createdAt.isoformat()
                }
                payments_data.append(payment_details)
            
            return {'all_payments': payments_data}, HTTPStatus.OK 
        
        
        except Exception as e:
            current_app.logger.error(f"Error getting all payments: {str(e)}")
            return {'message': f'Error getting all payments: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('reports/create')
class AddReportResource(Resource):
    @jwt_required()
    @finance_namespace.expect(reports_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            report_data = request.json
            
            new_report = Reports(
                title = report_data['title'],
                reportTag = report_data['reportTag'],
                pdfBytes = report_data['pdfBytes'],
                createdBy = report_data.get('createdBy',f'{current_user.firstName} {current_user.lastName}')
            )
            
            new_report.save()
            
            return {'message': 'Report added successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding report: {str(e)}")
            return {'message': f'Error adding report: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
@finance_namespace.route('reports/all')
class GetAllReports(Resource):
    @jwt_required()
    def get(self):
        try:
            reports = Reports.query.order_by(desc(Reports.createdAt)).all()
            
            reports_data = []
            for report in reports:
                report_details = {
                    'reportID': report.reportID,
                    'title': report.title,
                    'reportTag': report.reportTag,
                    'createdAt': report.createdAt.isoformat(),
                    'createdBy': report.createdBy
                }
                reports_data.append(report_details)
            
            return {'all_reports': reports_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all reports: {str(e)}")
            return {'message': f'Error getting all reports: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('reports/single/<string:reportTag>')
class GetReportByTag(Resource):
    @jwt_required()
    def get(self, reportTag):
        try:
            reports = Reports.query.filter_by(reportTag=reportTag).order_by(desc(Reports.createdAt)).all()
            
            reports_data = []
            for report in reports:
                report_details = {
                    'reportID': report.reportID,
                    'title': report.title,
                    'reportTag': report.reportTag,
                    'createdAt': report.createdAt.isoformat(),
                    'createdBy': report.createdBy
                }
                reports_data.append(report_details)
            
            return {'all_reports': reports_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all reports: {str(e)}")
            return {'message': f'Error getting all reports: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

# @finance_namespace.route('/get_all_region_accounts')
# class GetAllRegionAccount(Resource):
#     @jwt_required()
#     def get(self):
#         try:
            
#             region_accounts = RegionAccount.query.all()
#             accounts_data = []
            
#             for account in region_accounts:
#                 project_funds = ProjectFunds.query.filter_by(accountID= account.accountID).all()
#                 case_funds = CaseFunds.query.filter_by(accountID= account.accountID).all()
#                 donations = Donations.query.filter_by(accountID=account.accountID).order_by(desc(Donations.createdAt)).all()
#                 project_funds_data = []
#                 case_funds_data = []
#                 donations_data = []
#                 for fund in project_funds:
#                     project = ProjectsData.query.get(fund.projectID)
#                     project_data = {'projectID': project.projectID, 'projectName': project.projectName, 'budgetApproved': project.budgetApproved,
#                                     'category': project.category.value, 'status': project.projectStatus.value, 'startDate': project.startDate.isoformat() if project.startDate else None,
#                                     'solution': project.solution, 'dueDate': project.dueDate.isoformat() if project.dueDate else None}
#                     fund_details = {
#                         'fundID': fund.fundID,
#                         'project_details': project_data,
#                         'fundsAllocated': fund.fundsAllocated
#                     }
#                     project_funds_data.append(fund_details)
                    
#                 for fund in case_funds:
#                     case = CasesData.query.get(fund.caseID)
#                     case_data = {'caseID': case.caseID, 'caseName': case.caseName, 'budgetApproved': case.budgetApproved,
#                                     'category': case.category.value, 'status': case.caseStatus.value, 'startDate': case.startDate.isoformat() if case.startDate else None,
#                                     'dueDate': case.dueDate.isoformat() if case.dueDate else None}
#                     fund_details = {
#                         'fundID': fund.fundID,
#                         'case_details': case_data,
#                         'fundsAllocated': fund.fundsAllocated
#                     }
#                     case_funds_data.append(fund_details)
                
#                 for donation in donations:
#                     fund = FinancialFund.query.get(donation.fundID)
#                     fund_details = {'fundID': fund.fundID, 'fundName': fund.fundName, 'totalFund': fund.totalFund}
#                     donations_details = {
#                         'donationID': donation.id,
#                         'fund_account_details': fund_details,
#                         'details': donation.details,
#                         'currency': donation.currency,
#                         'field': donation.field,
#                         'amount': donation.amount,
#                         'createdAt': donation.createdAt.isoformat()
#                     }
#                     donations_data.append(donations_details)
                
#                 account_details = {
#                     'accountID': account.accountID,
#                     'accountName': account.accountName,
#                     'totalFund': account.totalFund,
#                     'usedFund': account.usedFund,
#                     'currency': account.currency,
#                     'accountType': account.accountType,
#                     'notes': account.notes,
#                     'lastTransaction': account.lastTransaction.isoformat() if account.lastTransation else None,
#                     'health_funds': account.health_funds,
#                     'education_funds': account.education_funds,
#                     'general_funds': account.general_funds,
#                     'shelter_funds': account.shelter_funds,
#                     'sponsorship_funds': account.sponsorship_funds,
#                     'donations': donations_data,
#                     'funded_projects': project_funds_data,
#                     'funded_cases': case_funds_data
#                 }
#                 accounts_data.append(account_details)
            
#             return {'all_accounts': accounts_data}, HTTPStatus.OK
                
#         except Exception as e:
#             current_app.logger.error(f"Error getting all region accounts: {str(e)}")
#             return {'message': f'Error getting all region accounts: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

# @finance_namespace.route('/get_all_financial_funds')
# class GetAllFinancialFunds(Resource):
#     @jwt_required()
#     def get(self):
#         try:
#             fund_accounts = FinancialFund.query.all()
#             accounts_data = []
            
#             for fund in fund_accounts:
#                 donations = Donations.query.filter_by(fundID=fund.fundID).order_by(desc(Donations.createdAt)).all()
#                 donations_data = []
#                 for donation in donations:
#                     account = RegionAccount.query.get(donation.accountID) 
#                     account_details = {'accountID': account.accountID, 'accountName': account.accountName, 'totalFund': account.totalFund}
#                     donations_details = {
#                         'donationID': donation.id,
#                         'region_account_details': account_details,
#                         'details': donation.details,
#                         'currency': donation.currency,
#                         'field': donation.field,
#                         'amount': donation.amount,
#                         'createdAt': donation.createdAt.isoformat()
#                     }
#                     donations_data.append(donations_details)
                    
#                 payments = Payments.query.filter_by(from_fund=fund.fundID).order_by(desc(Payments.createdAt)).all()
#                 payments_data = []
#                 for payment in payments:
#                     payment_details = {
#                         'paymentID': payment.paymentID,
#                         'paymentName': payment.paymentName,
#                         'paymentMethod': payment.paymentMethod,
#                         'notes': payment.notes,
#                         'amount': payment.amount,
#                         'currency': payment.currency,
#                         'transferExpenses': payment.transferExpenses,
#                         'exchangeRate': payment.exchangeRate,
#                         'supportingFiles': payment.supportingFiles,
#                         'createdAt': payment.createdAt.isoformat()
#                     }
#                     payments_data.append(payment_details)
                    
#                 account_details = {
#                     'fundID': fund.fundID,
#                     'fundName': fund.fundName,
#                     'totalFund': fund.totalFund,
#                     'usedFund': fund.usedFund,
#                     'currency': fund.currency,
#                     'accountType': fund.accountType,
#                     'notes': fund.notes,
#                     'createdAt': fund.createdAt.isoformat(),
#                     'donations': donations_data,
#                     'payments': payments_data
#                 }
#                 accounts_data.append(account_details)
            
#             return {'fund_accounts': accounts_data}
                
#         except Exception as e:
#             current_app.logger.error(f"Error getting all financial fund accounts: {str(e)}")
#             return {'message': f'Error getting all financial fund accounts: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
        

              
            
        
            
           
            
