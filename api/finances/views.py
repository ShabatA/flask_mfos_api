from decimal import Decimal
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus

from api.models.accountfields import *
from api.models.cases import *
from api.models.projects import *
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

sub_fund_data_model = finance_namespace.model('SubFinancialFundData',{
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
    'phoneNumber': fields.String(required=True),
    'imageLink': fields.String(required=False)
})

donor_data_model = finance_namespace.model('DonorData', {
    'name': fields.String(required=True, description='name of the donor'),
    'donorType': fields.String(required=True, description='could be organization or individual', enum=[type.value for type in DonorTypes]),
    'country': fields.String(required=True, description='country where donor is from'),
    'email': fields.String(required=True),
    'phoneNumber': fields.String(required=True),
    'notes': fields.String(required=False),
    'representatives': fields.List(fields.Nested(donor_rep_model), description='list of representatives'),
    'imageLink': fields.String(required=False)
})

donor_edit_model = finance_namespace.model('DonorEdit', {
    'donorID': fields.Integer(required=True, description='the donor ID'),
    'name': fields.String(required=True, description='name of the donor'),
    'donorType': fields.String(required=True, description='could be organization or individual', enum=[type.value for type in DonorTypes]),
    'country': fields.String(required=True, description='country where donor is from'),
    'email': fields.String(required=True),
    'phoneNumber': fields.String(required=True),
    'notes': fields.String(required=False),
    'representatives': fields.List(fields.Nested(donor_rep_model), description='list of representatives'),
    'imageLink': fields.String(required=False)
})

donations_data_model = finance_namespace.model('DonationData', {
    'donorID': fields.Integer(required=True, description='The donor who is donating'),
    'accountID': fields.Integer(required=True, description='The region account to donate to'),
    'fundID': fields.Integer(required=True, description='The account bank account the money will be deposited to'),
    'subFundID': fields.Integer(required=False, description='Specify the sub fund the money will be deposited to if applicable.'),
    'notes': fields.String(required=True, description='Supply any notes/details'),
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
    'paymentCount': fields.Integer(required=True, description='Specify which payment you are requesting out of the payment breakdown'),
    'paymentMethod': fields.String(required=True, enum=[type.value for type in TransferType], description='The payment method.'),
    'notes': fields.String(required=False, description='any notes if applicable.')
})

case_fund_release_request =finance_namespace.model('CaseFundReleaseRequest', {
    'caseID': fields.Integer(required=True, description='The case the request is for'),
    'fundsRequested': fields.Float(required=True, description='The amount to be requested'),
    'paymentCount': fields.Integer(required=True, description='Specify which payment you are requesting out of the payment breakdown'),
    'paymentMethod': fields.String(required=True, enum=[type.value for type in TransferType], description='The payment method.'),
    'notes': fields.String(required=False, description='any notes if applicable.')
})

approve_p_fund_release_request = finance_namespace.model('ProjectFundReleaseApproval', {
    'requestID': fields.Integer(required=True, description='The request ID'),
    'approvedAmount': fields.Float(required=True),
    'notes': fields.String(required=False, description='any notes if applicable.'),
    'accountID': fields.Integer(required=True, description='The region account to spend on'),
    'fundID': fields.Integer(required=True, description='The actual bank account the money will be spent on'),
    'paymentMethod': fields.String(required=True, enum=[type.value for type in TransferType], description='The payment method.'),
})

approve_c_fund_release_request = finance_namespace.model('CaseFundReleaseApproval', {
    'requestID': fields.Integer(required=True, description='The request ID'),
    'approvedAmount': fields.Float(required=True),
    'notes': fields.String(required=False, description='any notes if applicable.'),
    'accountID': fields.Integer(required=True, description='The region account to spend on'),
    'fundID': fields.Integer(required=True, description='The actual bank account the money will be spent on'),
    'paymentMethod': fields.String(required=True, enum=[type.value for type in TransferType], description='The payment method.'),
})

fund_transfer_model = finance_namespace.model('FundTransfer', {
    'from_fund': fields.Integer(required=True, description= 'the fund to take from'),
    'to_fund': fields.Integer(required=True, description= 'the fund to transfer to'),
    'transferAmount': fields.Float(required=True, description='The amount to be transfered'),
    'notes': fields.String(required=False, description='Supply any notes/details'),
    'transfer_type': fields.String(required=True, enum=[type.value for type in TransferType] , description='EFT, Cash, or Check'),
    'currencyID': fields.Integer(required=True, description='the currency to be used for transfer')
})

# payments_model = finance_namespace.model('Payments', {
#     'from_fund': fields.Integer(required=True, description= 'the actual bank account the money will come from'),
#     'subFundID': fields.Integer(required=False, description='the sub fund of the main if applicable'),
#     'paymentFor': fields.String(enum=[payment.value for payment in PaymentFor], description="What the payment is for"),
#     'paymentName': fields.String(required=True, description='the name of the case/project is for, or something else'),
#     'paymentMethod': fields.String(required=True, enum=[type.value for type in TransferType] , description='EFT, Cash, or Check'),
#     'amount': fields.Float(required=True, description='The amount to be paid'),
#     'currencyID': fields.Integer(required=True, description='The currency the payment is made in'),
#     'transferExpenses': fields.Float(required=False, description='Transfer expenses if any.'),
#     'projectScope': fields.String(required=False, enum=[scope.value for scope in ProjectScopes], description='In what scope or field will the money be spent on'),
#     'notes': fields.String(required=False, description='any notes if applicable.')
# })

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
    'type': fields.String(required=True),
    'reportId': fields.String(required=True),
    'pdfUrl': fields.String(required=True)
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
            return {'message': 'Currency added successfully.', 'currencyID': currency.currencyID}, HTTPStatus.OK
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

@finance_namespace.route('/get_all_currencies')
class GetAllCurrenciesResource(Resource):
    @jwt_required()
    def get(self):
        try:
            currencies = Currencies.query.all()
            currencies_data = [{'currencyID': currency.currencyID, 'currencyCode': currency.currencyCode, 'currencyName': currency.currencyName, 'lastUpdated': currency.lastUpdated.isoformat()} for currency in currencies]
            return {'currencies': currencies_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all currencies: {str(e)}")
            return {'message': f'Error getting all currencies: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/get_all_currencies_with_balances')
class GetAllCurrenciesWithBalancesResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Perform a left join to include all currencies, even those without a balance record
            # Use coalesce to default to 0 when there are no balances
            currencies_with_balances = db.session.query(
                Currencies.currencyID,
                Currencies.currencyCode,
                Currencies.currencyName,
                Currencies.exchangeRateToUSD,
                Currencies.lastUpdated,
                db.func.coalesce(db.func.sum(FinancialFundCurrencyBalance.availableFund), 0).label('available_amount')
            ).outerjoin(FinancialFundCurrencyBalance, FinancialFundCurrencyBalance.currencyID == Currencies.currencyID) \
             .group_by(Currencies.currencyID, Currencies.currencyCode, Currencies.currencyName) \
             .all()

            currencies_data = [
                {
                    'currencyID': currency.currencyID,
                    'currencyCode': currency.currencyCode,
                    'exchangeRateToUSD': currency.exchangeRateToUSD,
                    'currencyName': currency.currencyName,
                    'available_amount': float(currency.available_amount),  # Ensure available_amount is a float
                    'lastUpdated': currency.lastUpdated.strftime('%d %b %Y')
                } for currency in currencies_with_balances
            ]

            return {'currencies': currencies_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all currencies with balances: {str(e)}")
            return {'message': f'Error getting all currencies with balances: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    

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
            
            if len(fund_data['currencies']) > 0:
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
                    notes= fund_data.get('notes', ''),
                    accountType = fund_data['accountType']
                )
                new_sub_fund.save()
                new_balance = SubFundCurrencyBalance(
                    subFundID = new_sub_fund.subFundID,
                    currencyID = 1
                )
                new_balance.save()
                
                if len(fund_data['currencies']) > 0:
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
                accountType = fund_data['accountType']
            )
            new_fund.save()
            
            new_balance = SubFundCurrencyBalance(
                    subFundID = new_fund.subFundID,
                    currencyID = 1
                )
            new_balance.save()
            
            if len(fund_data['currencies']) > 0:
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
                accountName = region.regionName,
                regionID=region_id
            )
            new_account.save()
            
            #add the USD default
            new_currency = RegionAccountCurrencyBalance(
                        accountID = new_account.accountID,
                        currencyID = 1
                    )
            new_currency.save()
            
            if len(account_data['currencies']) > 0:
                for currency in account_data['currencies']:
                    if currency != 1:
                        new_currency = RegionAccountCurrencyBalance(
                                            accountID = new_account.accountID,
                                            currencyID = currency
                                        )
                        new_currency.save()
                    
            
            return {'message': 'Region Account was added successfully.', 'accountID': new_account.accountID}, HTTPStatus.OK
        
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
                notes = donor_data.get('notes', None),
                imageLink = donor_data.get('imageLink', None)
            )
            
            new_donor.save()
            
            if(len(donor_data['representatives']) > 0):
                for rep in donor_data['representatives']:
                    new_rep = Representative(
                        donorID = new_donor.donorID,
                        name = rep['name'],
                        jobPosition = rep['jobPosition'],
                        email = rep['email'],
                        phoneNumber = rep['phoneNumber'],
                        imageLink = rep.get('imageLink', None)
                    )
                    new_rep.save()
            
            return {'message': 'Donor was added successfully.', 'donorID': new_donor.donorID}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding Donor: {str(e)}")
            return {'message': f'Error adding Donor: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    
    @jwt_required()
    @finance_namespace.expect(donor_edit_model)
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
            existing_donor.imageLink = donor_data.get('imageLink', '')
            
            existing_donor.save()
            return {'message': 'Donor was updated successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error updating donor: {str(e)}")
            return {'message': f'Error updating donor: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/add_balance', methods=['POST'])
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
            sub_fund_id = donation_data.get('subFundID')
            
            project_id = donation_data.get('projectID')
            case_id = donation_data.get('caseID')
            
            if project_id == 0:
                project_id = None
            if case_id == 0:
                case_id = None
            
            # Corrected validation logic
            if account_id is None or fund_id is None or donor_id is None:
                return {'message': 'Either no account ID, fund ID, or donor ID provided'}, HTTPStatus.BAD_REQUEST
            
           
            
            account = RegionAccount.query.get_or_404(account_id)
            fund = FinancialFund.query.get_or_404(fund_id)
            donor = Donor.query.get_or_404(donor_id)
            if sub_fund_id:
                sub_fund = SubFunds.query.get_or_404(sub_fund_id)
            else:
                sub_fund = None
            
            project_scope_mapping = {
                "Healthcare": "HEALTH",
                "Education Support": "EDUCATION",
                "Relief Aid": "RELIEF",
                "Sponsership": "SPONSERSHIP",
                "General": "GENERAL",
                "Housing": "SHELTER"
            }
            
            # Assuming donation_info is a dictionary that includes 'projectScope'
            human_readable_scope = donation_data.get('project_scope')
            
            # Step 3: Translate the human-readable project scope to the enum value
            enum_project_scope = project_scope_mapping.get(human_readable_scope)
            
            if not enum_project_scope:
                # Handle invalid project scope
                return {'message': f'Invalid project scope: {human_readable_scope}'}, HTTPStatus.INTERNAL_SERVER_ERROR
            
            new_donation = Donations(
                donorID = donor_id,
                accountID = account_id,
                fundID = fund_id,
                subFundID = sub_fund_id,
                details = donation_data.get('notes', ''),
                currencyID = donation_data['currencyID'],
                amount = donation_data['amount'],
                donationType = donation_data['donationType'].upper(),
                caseID = case_id,
                projectID = project_id,
                projectScope = enum_project_scope.upper(),
                allocationTags = donation_data.get('allocationTags', '')
            )
            new_donation.save()
            #call the add function to handle the logic
            account.add_fund(donation_data['amount'],donation_data.get('currency',1), None,project_id, case_id, None,donation_data.get('project_scope', 'General'))
            fund.add_fund(donation_data['amount'],donation_data.get('currency',1))
            if sub_fund:
                sub_fund.add_fund(donation_data['amount'],donation_data.get('currency',1))
            db.session.commit()
        
            return {'message': 'Donation added successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding donation: {str(e)}")
            return {'message': f'Error adding donation: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
    

@finance_namespace.route('/donations/no_case_project')
class DonationsNoCaseProjectResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Query for donations where caseID and ProjectID are None
            donations = Donations.query.filter_by(caseID=None, projectID=None).all()
            donation_list = []
            for donation in donations:
                donation_dict = {
                    'donationID': donation.id,
                    'donor': {
                        'donorID': donation.donor.donorID,
                        'donorName': donation.donor.donorName,
                        'donorEmail': donation.donor.email,
                        # Add other donor information as needed
                    },
                    'amount': donation.amount,
                    'currencyName': donation.currency.currencyName,
                    'donationType': donation.donationType.value,
                    'createdAt': donation.createdAt.isoformat()
                }
                donation_list.append(donation_dict)
        
            return {'donations': donation_list}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error retrieving donations with no case or project: {str(e)}")
            return {'message': f'Error retrieving donations: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/donations/no_case_project/donor/<int:donorID>')
class DonationsNoCaseProjectByDonorResource(Resource):
    @jwt_required()
    def get(self, donorID):
        try:
            # Query for donations where caseID and ProjectID are None
            donations = Donations.query.filter_by(caseID=None, projectID=None, donorID=donorID).all()
            donation_list = []
            for donation in donations:
                donation_dict = {
                    'donationID': donation.id,
                    'amount': donation.amount,
                    'currencyName': donation.currency.currencyName,
                    'donationType': donation.donationType.value,
                    'createdAt': donation.createdAt.isoformat()
                }
                donation_list.append(donation_dict)
        
            return {'donations': donation_list}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error retrieving donations with no case or project: {str(e)}")
            return {'message': f'Error retrieving donations: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

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
                converted_balances = {key: float(value) if isinstance(value, Decimal) else value for key, value in balances.items()}
                accounts_data.append(account_data | converted_balances)
            
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
                'availableCurrencies': account.get_available_currencies(),
                'transactions': account.get_account_transactions(),
                'scope_percentages': account.get_scope_percentages(),
                'scope_balances': {key: float(value) if isinstance(value, Decimal) else value for key, value in account.get_category_balances().items()}  
            }
            #get balances based on the currency conversion
            balances = account.get_fund_balance(currency_conversion)
            converted_balances = {key: float(value) if isinstance(value, Decimal) else value for key, value in balances.items()}
            return {'account': account_data | converted_balances}, HTTPStatus.OK
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
                'availableCurrencies': fund.get_available_currencies(),
                'subFunds': fund.get_all_sub_funds(),
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
            
            project_id = request_data.get('projectID')
            
            if not project_id:
                return {'message': 'project ID is required to make a request.'}, HTTPStatus.BAD_REQUEST
            
            project = ProjectsData.query.get_or_404(project_id)
            
            release = ProjectFundReleaseRequests(
                projectID = project_id,
                fundsRequested = request_data['fundsRequested'],
                requestedBy = current_user.userID,
                paymentCount = request_data['paymentCount'],
                notes = request_data['notes']
            )
            
            release.save()
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
            
            case_id = request_data.get('caseID')
            
            if not case_id:
                return {'message': 'case ID is required to make a request.'}, HTTPStatus.BAD_REQUEST
            
            case = CasesData.query.get_or_404(case_id)
            
            release = CaseFundReleaseRequests(
                caseID = case_id,
                fundsRequested = request_data['fundsRequested'],
                requestedBy = current_user.userID,
                paymentCount = request_data['paymentCount'],
                notes = request_data['notes']
            )
            
            release.save()
            
            return {'message': 'Request posted successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/make_fund_transfer')
class MakeFundTransferResource(Resource):
    @jwt_required()
    @finance_namespace.expect(fund_transfer_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json
            
            from_fund = FinancialFund.query.get_or_404(request_data['from_fund'])
            to_fund = FinancialFund.query.get_or_404(request_data['to_fund'])
            
            transfer = FundTransfers(
                from_fund = request_data['from_fund'],
                to_fund = request_data['to_fund'],
                transferAmount = request_data['transferAmount'],
                notes = request_data['notes'],
                createdBy = current_user.userID,
                transferType = request_data['transfer_type']
            )
            
            transfer.save()
            
            return {'message': 'Transfer posted successfully.',
                    'transferID': transfer.transferID}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/close_fund_transfer/<int:transfer_id>')
class CloseFundTransferResource(Resource):
    @jwt_required()
    def put(self, transfer_id):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            transfer = FundTransfers.query.get_or_404(transfer_id)
            
            if transfer.closed:
                return {'message': 'Transfer is already closed'}, HTTPStatus.CONFLICT
            
            transfer.closed = True
            transfer.status = 'Closed'
            transfer.save()
            
            from_fund = FinancialFund.query.get_or_404(transfer.from_fund)
            to_fund = FinancialFund.query.get_or_404(transfer.to_fund)
            
            from_fund.use_fund(transfer.transferAmount, transfer.currencyID)
            to_fund.add_fund(transfer.transferAmount, transfer.currencyID)
            
            return {'message': 'Transfer closed successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error closing transfer: {str(e)}")
            return {'message': f'Error closing transfer: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

# @finance_namespace.route('/record_payments')
# class RecordPaymentsResource(Resource):
#     @jwt_required()
#     @finance_namespace.expect(payments_model)
#     def post(self):
#         try:
#             current_user = Users.query.filter_by(username=get_jwt_identity()).first()
#             request_data = request.json
            
#             fund_id = request_data.get('from_fund')
            
#             if not current_user.is_admin():
#                 return {'message': 'only admins can make payments.'}, HTTPStatus.FORBIDDEN
            
#             if not fund_id:
#                 return {'message': 'Fund ID not provided'},HTTPStatus.BAD_REQUEST
            
#             fund = FinancialFund.query.get_or_404(fund_id)
            
#             request = Payments(
#                 from_fund = request_data['from_fund'],
#                 paymentFor = request_data['paymentFor'],
#                 notes = request_data['notes'],
#                 paymentName = request_data['paymentName'],
#                 paymentMethod = request_data['paymentMethod'],
#                 amount = request_data['amount'],
#                 currencyID = request_data['currencyID'],
#                 transferExpenses = request_data.get('transferExpenses', 0),
#                 projectScope = request_data.get('projectScope', None),
#                 subFundID = request_data.get('subFundID',None)
#             )
            
#             request.save()
#             if request_data.get('subFundID',None) is not None:
#                 sub_fund = SubFunds.query.get_or_404(request_data['subFundID'])
#                 sub_fund.use_fund(request_data['amount'], request_data['currencyID'])
            
#             fund.use_fund(request_data['amount'], request_data['currencyID'])
            
#             return {'message': 'Payment recorded successfully.'}, HTTPStatus.OK
        
#         except Exception as e:
#             current_app.logger.error(f"Error adding request: {str(e)}")
#             return {'message': f'Error adding request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

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


@finance_namespace.route('/get_all_fund_transfers')
class GetAllFundTransfers(Resource):
    @jwt_required()
    def get(self):
        try:
            transfers = FundTransfers.query.order_by(desc(FundTransfers.createdAt)).all()
            transfers_data = []
            for transfer in transfers:
                user = Users.query.get(transfer.createdBy)
                from_fund = FinancialFund.query.get(transfer.from_fund)
                to_fund = FinancialFund.query.get(transfer.to_fund)
                
                
                transfer_details = {
                    'transferID': transfer.transferID,
                    'from_fund': {
                        'fundID': from_fund.fundID,
                        'fundName': from_fund.fundName,
                        'balances': to_fund.get_fund_balance(1)
                        
                    },
                    'to_fund': {
                        'fundID': to_fund.fundID,
                        'fundName': to_fund.fundName,
                        'balances': to_fund.get_fund_balance(1)  
                    },
                    'createdBy': {
                        'userID': user.userID,
                        'userFullName': f'{user.firstName} {user.lastName}',
                        'username': user.username
                    },
                    'transferAmount': transfer.transferAmount,
                    'createdAt': transfer.createdAt.isoformat(),
                    'notes': transfer.notes,
                    'status': transfer.status,
                    'closed': transfer.closed   
                }
                
                transfers_data.append(transfer_details)
            
            return {'all_transfers': transfers_data}, HTTPStatus.OK
                
                
        except Exception as e:
            current_app.logger.error(f"Error getting fund transfers: {str(e)}")
            return {'message': f'Error getting fund transfers: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

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
                region_acc = RegionAccount.query.get(case_data.regionID)
                region_acc_details = {'accountName': region_acc.accountName, 'availableFund': float(region_acc.availableFund)}
                beneficiary = CaseBeneficiary.query.filter_by(caseID=case_data.caseID).first()
                
                request_details = {
                    'requestID': request.requestID,
                    'case': case_details,
                    'requestedBy': user_details,
                    'fundsRequested': request.fundsRequested,
                    'createdAt': request.createdAt.isoformat(),
                    'approved': request.approved,
                    'approvedAt': request.approvedAt.isoformat() if request.approvedAt else None,
                    'receivedAmount': f'{request.approvedAmount}/{request.fundsRequested}',
                    'regionName': Regions.query.get(case_data.regionID).regionName,
                    'region_account_details': region_acc_details,
                    'approved_funding': f"${case_data.status_data.data.get('approvedFunding', 0)}/${beneficiary.totalSupportCost}",
                    'paymentCount': f"{request.paymentCount}/{case_data.status_data.data.get('paymentCount', 0)}",
                    'bulkName': '-',
                    'paymentDueDate': f"{case_data.dueDate}",
                    'projectScope': '-',
                    'status': request.status  
                }
                
                case_requests_data.append(request_details)
            
            project_requests = ProjectFundReleaseRequests.query.order_by(desc(ProjectFundReleaseRequests.createdAt)).all()
            project_requests_data = []
            for request in project_requests:
                user = Users.query.get(request.requestedBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                project_data = ProjectsData.query.get(request.projectID)
                project_details = {'projectID': project_data.projectID, 'projectName': project_data.projectName, 'category': project_data.category.value, 'status': project_data.projectStatus.value}
                region_acc = RegionAccount.query.get(project_data.regionID)
                region_acc_details = {'accountName': region_acc.accountName, 'availableFund': float(region_acc.availableFund)}
                
                request_details = {
                    'requestID': request.requestID,
                    'project': project_details,
                    'requestedBy': user_details,
                    'fundsRequested': request.fundsRequested,
                    'createdAt': request.createdAt.isoformat(),
                    'approved': request.approved,
                    'approvedAt': request.approvedAt.isoformat() if request.approvedAt else None,
                    'receivedAmount': f'{request.approvedAmount}/{request.fundsRequested}',
                    'regionName': Regions.query.get(project_data.regionID).regionName ,
                    'region_account_details': region_acc_details,
                    'approved_funding': f"${project_data.status_data.data.get('approvedFunding', 0)} / ${project_data.budgetRequired}",
                    'paymentCount': f"{request.paymentCount}/{project_data.status_data.data.get('paymentCount', 0)}",
                    'bulkName': '-',
                    'paymentDueDate': f"{project_data.dueDate}",
                    'projectScope': f"{project_data.status_data.data.get('projectScope', '-')}",
                    'status': request.status   
                }
                
                project_requests_data.append(request_details)
            
            return {'case_requests': case_requests_data, 'project_requests': project_requests_data}, HTTPStatus.OK
                
                
        except Exception as e:
            current_app.logger.error(f"Error getting fund release requests: {str(e)}")
            return {'message': f'Error getting fund release requests: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR 

@finance_namespace.route('/release_project_fund_requested')
class ReleaseProjectFundResource(Resource):
    @jwt_required()
    @finance_namespace.expect(approve_p_fund_release_request)
    def post(self):
        try:
             current_user = Users.query.filter_by(username=get_jwt_identity()).first()
             post_data = request.json
             
             approval = ProjectFundReleaseApproval(
                    requestID = post_data['requestID'],
                    approvedBy = current_user.userID,
                    approvedAmount = post_data['approvedAmount'],
                    accountID = post_data['accountID'],
                    fundID = post_data['fundID'],
                    notes = post_data['notes']
                )
             approval.save()
             
             project_request = ProjectFundReleaseRequests.query.get_or_404(post_data['requestID'])
             project_request.status = 'Awaiting Approval (Submit Docs)'
             project_request.approvedAmount = post_data['approvedAmount']
             db.session.commit()
             
             return {'message': 'Project Funds released successfully.'}, HTTPStatus.OK
       
        except Exception as e:
            current_app.logger.error(f"Error releasing project funds: {str(e)}")
            return {'message': f'Error releasing project funds: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/release_case_fund_requested')
class ReleaseCaseFundResource(Resource):
    @jwt_required()
    @finance_namespace.expect(approve_c_fund_release_request)
    def post(self):
        try:
             current_user = Users.query.filter_by(username=get_jwt_identity()).first()
             post_data = request.json
             
             approval = CaseFundReleaseApproval(
                    requestID = post_data['requestID'],
                    approvedBy = current_user.userID,
                    approvedAmount = post_data['approvedAmount'],
                    accountID = post_data['accountID'],
                    fundID = post_data['fundID'],
                    notes = post_data['notes']
                )
             approval.save()
             
             case_request = CaseFundReleaseRequests.query.get_or_404(post_data['requestID'])
             case_request.status = 'Awaiting Approval (Submit Docs)'
             case_request.approvedAmount = post_data['approvedAmount']
             db.session.commit()
             
             return {'message': 'Case Funds released successfully.'}, HTTPStatus.OK
       
        except Exception as e:
            current_app.logger.error(f"Error releasing case funds: {str(e)}")
            return {'message': f'Error releasing case funds: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR   

        
@finance_namespace.route('/update_case_fund_request_status/<int:requestID>/<string:status>')    
class UpdateCFundReleaseStatus(Resource):
    @jwt_required()
    def put(self, requestID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = CaseFundReleaseRequests.query.get_or_404(requestID)
            
            request.status = status
            db.session.commit()
            
            return {'message': 'Request status updated successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating request status: {str(e)}")
            return {'message': f'Error updating request status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/update_project_fund_request_status/<int:requestID>/<string:status>')    
class UpdatePFundReleaseStatus(Resource):
    @jwt_required()
    def put(self, requestID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = ProjectFundReleaseRequests.query.get_or_404(requestID)
            
            request.status = status
            db.session.commit()
            
            return {'message': 'Request status updated successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating request status: {str(e)}")
            return {'message': f'Error updating request status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/approve_case_fund_request/<int:requestID>/yes_or_no/<string:decision>')
class ApproveCaseFundReq(Resource):
    @jwt_required()
    def put(self, requestID, decision):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = CaseFundReleaseRequests.query.get_or_404(requestID)
            approval = CaseFundReleaseApproval.query.filter_by(requestID = request.requestID).first()
            
            if decision == 'yes':
                request.approved = True
                request.status = f'Approved - Track ApprovalID {approval.approvalID}'
                approval.status = 'Approved'
            else:
                request.approved = False
                approval.status = 'Rejected'
                request.status = 'Rejected'
                
            db.session.commit()
            
            return {'message': 'Request approved successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error approving request: {str(e)}")
            return {'message': f'Error approving request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/approve_project_fund_request/<int:requestID>/yes_or_no/<string:decision>')
class ApproveProjectFundReq(Resource):
    @jwt_required()
    def put(self, requestID, decision):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = ProjectFundReleaseRequests.query.get_or_404(requestID)
            approval = ProjectFundReleaseApproval.query.filter_by(requestID = request.requestID).first()
            
            if decision == 'yes':
                request.approved = True
                request.status = f'Approved - Track ApprovalID {approval.approvalID}'
                approval.status = 'Approved'
            else:
                request.approved = False
                approval.status = 'Rejected'
                request.status = 'Rejected'
                
            db.session.commit()
            
            return {'message': 'Request approved successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error approving request: {str(e)}")
            return {'message': f'Error approving request: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/get_all_fund_release_approvals')
class GetFundReleaseHistory(Resource):
    @jwt_required()
    def get(self):
        try:
            case_approvals = CaseFundReleaseApproval.query.order_by(desc(CaseFundReleaseApproval.approvedAt)).all()
            project_approvals = ProjectFundReleaseApproval.query.order_by(desc(ProjectFundReleaseApproval.approvedAt)).all()
            
            case_approvals_data = []
            for approval in case_approvals:
                user = Users.query.get(approval.approvedBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                request = CaseFundReleaseRequests.query.get(approval.requestID)
                case_data = CasesData.query.get(request.caseID)
                case_details = {'caseID': case_data.caseID, 'caseName': case_data.caseName, 'category': case_data.category.value, 'status': case_data.caseStatus.value}
                
                approval_details = {
                    'approvalID': approval.approvalID,
                    'case': case_details,
                    'approvedBy': user_details,
                    'approvedAmount': approval.approvedAmount,
                    'approvedAt': approval.approvedAt.isoformat(),
                    'notes': approval.notes,
                    'status': approval.status,
                    'closed': approval.closed
                }
                
                case_approvals_data.append(approval_details)
            
            project_approvals_data = []
            for approval in project_approvals:
                user = Users.query.get(approval.approvedBy)
                user_details = {'userID': user.userID, 'userFullName': f'{user.firstName} {user.lastName}', 'username': user.username}
                request = ProjectFundReleaseRequests.query.get(approval.requestID)
                project_data = ProjectsData.query.get(request.projectID)
                project_details = {'projectID': project_data.projectID, 'projectName': project_data.projectName, 'category': project_data.category.value, 'status': project_data.projectStatus.value}
                
                approval_details = {
                    'approvalID': approval.approvalID,
                    'project': project_details,
                    'approvedBy': user_details,
                    'approvedAmount': approval.approvedAmount,
                    'approvedAt': approval.approvedAt.isoformat(),
                    'notes': approval.notes,
                    'status': approval.status,
                    'closed': approval.closed
                }
                
                project_approvals_data.append(approval_details)
            
            return {'case_approvals': case_approvals_data, 'project_approvals': project_approvals_data}, HTTPStatus.OK
            
            
        except Exception as e:
            current_app.logger.error(f"Error getting fund release approvals: {str(e)}")
            return {'message': f'Error getting fund release approvals: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR 
        
@finance_namespace.route('/update_project_fund_approval_status/<int:approvalID>/<string:status>')    
class UpdatePFundApprovalStatus(Resource):
    @jwt_required()
    def put(self, approvalID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = ProjectFundReleaseApproval.query.get_or_404(approvalID)
            
            approval.status = status
            db.session.commit()
            
            return {'message': 'Approval status updated successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating approval status: {str(e)}")
            return {'message': f'Error updating approval status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/update_case_fund_approval_status/<int:approvalID>/<string:status>')    
class UpdateCFundApprovalStatus(Resource):
    @jwt_required()
    def put(self, approvalID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = CaseFundReleaseApproval.query.get_or_404(approvalID)
            
            approval.status = status
            db.session.commit()
            
            return {'message': 'Approval status updated successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating approval status: {str(e)}")
            return {'message': f'Error updating approval status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/update_fund_transfer_status/<int:transferID>/<string:status>')    
class UpdateFundTransferStatus(Resource):
    @jwt_required()
    def put(self, transferID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            transfer = FundTransfers.query.get_or_404(transferID)
            
            transfer.status = status
            db.session.commit()
            
            return {'message': 'Transfer status updated successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating transfer status: {str(e)}")
            return {'message': f'Error updating transfer status: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        

@finance_namespace.route('/close_case_fund_release_approval/<int:approvalID>')
class CloseCFundReleaseApproval(Resource):
    @jwt_required()
    def put(self, approvalID):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = CaseFundReleaseApproval.query.get_or_404(approvalID)
            
            approval.closed = True
            approval.status = 'Closed'
            db.session.commit()
            
            from_fund = FinancialFund.query.get_or_404(approval.fundID)
            region_account = RegionAccount.query.get_or_404(approval.accountID)
            
            #spend money
            from_fund.use_fund(approval.approvedAmount, 1)
            
            
            
            request = CaseFundReleaseRequests.query.get(approval.requestID)
            case = CasesData.query.get(request.caseID)
            
            #spend money from region_account
            # use_fund(self, amount, currencyID=None, transaction_subtype=None, projectID=None, caseID=None, payment_number=None, category=None)
            # since cases do not have a scope, I made category to be none
            region_account.use_fund(approval.approvedAmount, 1, 'case_payment',None, case.caseID,request.paymentCount, None)
            
            return {'message': 'Approval closed successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error closing approval: {str(e)}")
            return {'message': f'Error closing approval: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/close_project_fund_release_approval/<int:approvalID>')
class ClosePFundReleaseApproval(Resource):
    @jwt_required()
    def put(self, approvalID):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = ProjectFundReleaseApproval.query.get_or_404(approvalID)
            
            approval.closed = True
            approval.status = 'Closed'
            db.session.commit()
            
            from_fund = FinancialFund.query.get_or_404(approval.fundID)
            region_account = RegionAccount.query.get_or_404(approval.accountID)
            
            #spend money from fund account
            from_fund.use_fund(approval.approvedAmount, 1)
            
            
            #get the project scope
            request = ProjectFundReleaseRequests.query.get(approval.requestID)
            project = ProjectsData.query.get(request.projectID)
            scope = project.status_data.data['projectScope']
            
            #spend money from region_account
            # use_fund(self, amount, currencyID=None, transaction_subtype=None, projectID=None, caseID=None, payment_number=None, category=None)
            region_account.use_fund(approval.approvedAmount, 1, 'project_payment',project.projectID, None,request.paymentCount, scope)
            
            return {'message': 'Approval closed successfully.'}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error closing approval: {str(e)}")
            return {'message': f'Error closing approval: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route('/get_all_donors')
class GetAllDonorsResource(Resource):
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
                    fund_details = {'fundID': fund.fundID, 'fundName': fund.fundName, 'totalFund': fund.totalFund}
                    account = RegionAccount.query.get(donation.accountID) 
                    account_details = {'accountID': account.accountID, 'accountName': account.accountName, 'totalFund': float(account.totalFund)}
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
                
                 # Fetch cases and projects the donor has contributed to
                cases = (
                    CasesData.query.join(Donations, CasesData.caseID == Donations.caseID)
                    .filter(Donations.donorID == donor.donorID, Donations.caseID.isnot(None))
                    .all()
                )
                
                projects = (
                    ProjectsData.query.join(Donations, ProjectsData.projectID == Donations.projectID)
                    .filter(Donations.donorID == donor.donorID, Donations.projectID.isnot(None))
                    .all()
                )
                projects_ = []
                project_statuses = ProjectsData.query.filter_by(projectStatus='APPROVED').all()
                for project_st in project_statuses:
                    if project_st.status_data.data.get('donorNames') is None:
                        continue
                    if donor.donorName in project_st.status_data.data.get('donorNames'):
                        projects_.append(project_st)

                cases_ = []
                case_statuses = CasesData.query.filter_by(caseStatus='APPROVED').all()
                for case_st in case_statuses:
                    if case_st.status_data.data.get('donorNames') is None:
                        continue
                    if donor.donorName in case_st.status_data.data.get('donorNames'):
                        cases_.append(case_st)

                all_projects = list(set(projects + projects_))
                all_cases = list(set(cases + cases_))
                
                donor_info = donor.get_donor_info()
                donor_info['totalDonationAmount'] = total_donation_amount
                donor_info['donations'] = donations_data
                donor_info['latestDonation'] = latest_donation.strftime("%d %b %Y") if latest_donation else None  # Format latest_donation as "20 Sept 2023"
                donor_info['cases'] = [case.serialize() for case in all_cases],
                donor_info['projects'] = [project.serialize() for project in all_projects]
                donors_data.append(donor_info)
            
            return {'donors': donors_data}, HTTPStatus.OK
                
              
        except Exception as e:
            current_app.logger.error(f"Error getting all donors: {str(e)}")
            return {'message': f'Error getting all donors: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

# @finance_namespace.route('/get_all_payments')
# class GetAllPaymentsResource(Resource):
#     @jwt_required()
#     def get(self):
#         try:
#             payments = Payments.query.order_by(desc(Payments.createdAt)).all()
            
#             payments_data = []
#             for payment in payments:
#                 from_fund = FinancialFund.query.get(payment.from_fund)
#                 from_fund_details = {'fundID': from_fund.fundID, 'fundName': from_fund.fundName, 'totalFund': from_fund.totalFund}
#                 payment_details = {
#                     'paymentID': payment.paymentID,
#                     'from_fund': from_fund_details,
#                     'paymentName': payment.paymentName,
#                     'paymentMethod': payment.paymentMethod.value,
#                     'paymentFor': payment.paymentFor.value,
#                     'projectScope': payment.projectScope.value,
#                     'notes': payment.notes,
#                     'amount': payment.amount,
#                     'currency': Currencies.query.get(payment.currencyID).currencyCode,
#                     'transferExpenses': payment.transferExpenses,
#                     'createdAt': payment.createdAt.isoformat()
#                 }
#                 payments_data.append(payment_details)
            
#             return {'all_payments': payments_data}, HTTPStatus.OK 
        
        
#         except Exception as e:
#             current_app.logger.error(f"Error getting all payments: {str(e)}")
#             return {'message': f'Error getting all payments: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/reports/create')
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
                createdBy = report_data.get('createdBy',f'{current_user.firstName} {current_user.lastName}'),
                type = report_data['type'],
                reportId = report_data['reportId'],
                pdfUrl = report_data['pdfUrl']
            )
            
            new_report.save()
            
            return {'message': 'Report added successfully.'}, HTTPStatus.OK
        
        except Exception as e:
            current_app.logger.error(f"Error adding report: {str(e)}")
            return {'message': f'Error adding report: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR
        
@finance_namespace.route('/reports/all')
class GetAllReports(Resource):
    @jwt_required()
    def get(self):
        try:
            reports = Reports.query.order_by(desc(Reports.dateCreated)).all()
            
            reports_data = []
            for report in reports:
                report_details = {
                    'reportID': report.id,
                    'title': report.title,
                    'reportTag': report.reportTag,
                    'createdAt': report.dateCreated.isoformat(),
                    'createdBy': report.createdBy,
                    'reportIdentity': report.reportId,
                    'pdfUrl': report.pdfUrl,
                    'type': report.type
                }
                reports_data.append(report_details)
            
            return {'all_reports': reports_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all reports: {str(e)}")
            return {'message': f'Error getting all reports: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/reports/by_tag/<string:reportTag>')
class GetReportByTag(Resource):
    @jwt_required()
    def get(self, reportTag):
        try:
            reports = Reports.query.filter_by(reportTag=reportTag).order_by(desc(Reports.dateCreated)).all()
            
            reports_data = []
            for report in reports:
                report_details = {
                    'reportID': report.id,
                    'title': report.title,
                    'reportTag': report.reportTag,
                    'createdAt': report.dateCreated.isoformat(),
                    'createdBy': report.createdBy,
                    'reportIdentity': report.reportId,
                    'pdfUrl': report.pdfUrl,
                    'type': report.type
                }
                reports_data.append(report_details)
            
            return {'all_reports': reports_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all reports: {str(e)}")
            return {'message': f'Error getting all reports: {str(e)}'}, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route('/reports/by_string_id/<string:reportId>')
class GetReportByTag(Resource):
    @jwt_required()
    def get(self, reportId):
        try:
            report = Reports.query.filter_by(reportId=reportId).first()
            
           
            report_details = {
                'reportID': report.id,
                'title': report.title,
                'reportTag': report.reportTag,
                'createdAt': report.dateCreated.isoformat(),
                'createdBy': report.createdBy,
                'reportIdentity': report.reportId,
                'pdfUrl': report.pdfUrl,
                'type': report.type
            }
                
            return report_details, HTTPStatus.OK
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
        
        

              
            
        
            
           
            
