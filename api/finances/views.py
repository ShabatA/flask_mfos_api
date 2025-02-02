from decimal import Decimal
from flask_restx import Resource, Namespace, fields
from flask_restx import reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus
from sqlalchemy.exc import SQLAlchemyError
from api.models.accountfields import *
from api.models.cases import *
from ..models.users import Users
from ..models.regions import Regions
from ..models.projects import ProjectsData
from ..models.cases import CasesData
from ..utils.db import db
from datetime import datetime, date, timedelta
from flask import jsonify, current_app
from flask import request
from ..models.finances import *
from sqlalchemy import desc, func, text, and_
import json
from flask import make_response
from sqlalchemy.orm import joinedload





finance_namespace = Namespace(
    "Finances", description="Namespace for Finances subsystem"
)

user_budget_namespace = Namespace(
    "UserBudget", description="Namespace for User Budget subsystem"
)



currency_model = finance_namespace.model(
    "Currency",
    {
        "currencyName": fields.String(
            required=True, description="The name of the currency"
        ),
        "dollarRate": fields.Float(required=True, description="Exchange rate to 1 USD"),
    },
)

sub_fund_model = finance_namespace.model(
    "SubFund",
    {
        "fundName": fields.String(required=True, description="Name of the sub fund"),
    },
)

fund_data_model = finance_namespace.model(
    "FinancialFundData",
    {
        "fundName": fields.String(
            required=True, description="Name of the actual account"
        ),
        "accountType": fields.String(
            required=True, description="Type of Account (Bank/Cash/Other)"
        ),
        "notes": fields.String(
            required=False, description="Additional notes if applicable"
        ),
        "currencies": fields.List(
            fields.Integer,
            description="Optional list of currencies excluding the default USD",
        ),
        "administrator": fields.Integer(
            required=True,
            description="The user ID of the employee responsible for this account",
        ),
        "subFunds": fields.List(
            fields.Nested(sub_fund_model), description="optional sub fund names"
        ),
    },
)



sub_fund_data_model = finance_namespace.model(
    "SubFinancialFundData",
    {
        "fundName": fields.String(
            required=True, description="Name of the actual account"
        ),
        "fundID": fields.String(
            required=True, description="ID of the parent fund account"
        ),
        "accountType": fields.String(
            required=True, description="Type of Account (Bank/Cash/Other)"
        ),
        "currencies": fields.List(
            fields.Integer,
            description="Optional list of currencies excluding the default USD",
        ),
        "administrator": fields.Integer(
            required=True,
            description="The user ID of the employee responsible for this account",
        ),
    },
)

region_account_data = finance_namespace.model(
    "RegionAccountData",
    {
        "regionID": fields.Integer(
            required=True, description="The region the account is for"
        ),
        "currencies": fields.List(
            fields.Integer,
            description="Optional list of currencies excluding the default USD",
        ),
    },
)

donor_rep_model = finance_namespace.model(
    "DonorRepresentative",
    {
        "name": fields.String(required=True, description="name of the donor"),
        "jobPosition": fields.String(required=True),
        "email": fields.String(required=True),
        "phoneNumber": fields.String(required=True),
        "imageLink": fields.String(required=False),
    },
)

donor_data_model = finance_namespace.model(
    "DonorData",
    {
        "name": fields.String(required=True, description="name of the donor"),
        "donorType": fields.String(
            required=True,
            description="could be organization or individual",
            enum=[type.value for type in DonorTypes],
        ),
        "country": fields.String(
            required=True, description="country where donor is from"
        ),
        "email": fields.String(required=True),
        "phoneNumber": fields.String(required=True),
        "notes": fields.String(required=False),
        "representatives": fields.List(
            fields.Nested(donor_rep_model), description="list of representatives"
        ),
        "imageLink": fields.String(required=False),
    },
)

donor_edit_model = finance_namespace.model(
    "DonorEdit",
    {
        "donorID": fields.Integer(required=True, description="the donor ID"),
        "name": fields.String(required=True, description="name of the donor"),
        "donorType": fields.String(
            required=True,
            description="could be organization or individual",
            enum=[type.value for type in DonorTypes],
        ),
        "country": fields.String(
            required=True, description="country where donor is from"
        ),
        "email": fields.String(required=True),
        "phoneNumber": fields.String(required=True),
        "notes": fields.String(required=False),
        "representatives": fields.List(
            fields.Nested(donor_rep_model), description="list of representatives"
        ),
        "imageLink": fields.String(required=False),
    },
)

donations_data_model = finance_namespace.model(
    "DonationData",
    {
        "donorID": fields.Integer(
            required=True, description="The donor who is donating"
        ),
        "accountID": fields.Integer(
            required=True, description="The region account to donate to"
        ),
        "fundID": fields.Integer(
            required=True,
            description="The account bank account the money will be deposited to",
        ),
        "subFundID": fields.Integer(
            required=False,
            description="Specify the sub fund the money will be deposited to if applicable.",
        ),
        "notes": fields.String(required=True, description="Supply any notes/details"),
        "amount": fields.Float(required=True, description="The donation amount"),
        "donationType": fields.String(
            required=True,
            description="whether it is for a Case, Project, or General",
            enum=[type.value for type in DonationTypes],
        ),
        "caseID": fields.Integer(description="Only provide if donation type is Case"),
        "projectID": fields.Integer(
            description="Only provide if donation type is Project"
        ),
        "currencyID": fields.Integer(
            required=True, description="The currency the amount originates from"
        ),
        "project_scope": fields.String(
            required=True,
            enum=[scope.value for scope in ProjectScopes],
            description="The project scope.",
        ),
        "allocationTags": fields.String(
            required=False,
            description="tags to use if the project/case is not in the system.",
        ),
    },
)

project_fund_release_request = finance_namespace.model(
    "ProjectFundReleaseRequest",
    {
        "projectID": fields.Integer(
            required=True, description="The project the request is for"
        ),
        "fundsRequested": fields.Float(
            required=True, description="The amount to be requested"
        ),
        "paymentCount": fields.Integer(
            required=True,
            description="Specify which payment you are requesting out of the payment breakdown",
        ),
        "paymentMethod": fields.String(
            required=True,
            enum=[type.value for type in TransferType],
            description="The payment method.",
        ),
        "notes": fields.String(required=False, description="any notes if applicable."),
    },
)

case_fund_release_request = finance_namespace.model(
    "CaseFundReleaseRequest",
    {
        "caseID": fields.Integer(
            required=True, description="The case the request is for"
        ),
        "fundsRequested": fields.Float(
            required=True, description="The amount to be requested"
        ),
        "paymentCount": fields.Integer(
            required=True,
            description="Specify which payment you are requesting out of the payment breakdown",
        ),
        "paymentMethod": fields.String(
            required=True,
            enum=[type.value for type in TransferType],
            description="The payment method.",
        ),
        "notes": fields.String(required=False, description="any notes if applicable."),
    },
)

approve_p_fund_release_request = finance_namespace.model(
    "ProjectFundReleaseApproval",
    {
        "requestID": fields.Integer(required=True, description="The request ID"),
        "approvedAmount": fields.Float(required=True),
        "notes": fields.String(required=False, description="any notes if applicable."),
        "accountID": fields.Integer(
            required=True, description="The region account to spend on"
        ),
        "fundID": fields.Integer(
            required=True,
            description="The actual bank account the money will be spent on",
        ),
        "paymentMethod": fields.String(
            required=True,
            enum=[type.value for type in TransferType],
            description="The payment method.",
        ),
    },
)

approve_c_fund_release_request = finance_namespace.model(
    "CaseFundReleaseApproval",
    {
        "requestID": fields.Integer(required=True, description="The request ID"),
        "approvedAmount": fields.Float(required=True),
        "notes": fields.String(required=False, description="any notes if applicable."),
        "accountID": fields.Integer(
            required=True, description="The region account to spend on"
        ),
        "fundID": fields.Integer(
            required=True,
            description="The actual bank account the money will be spent on",
        ),
        "paymentMethod": fields.String(
            required=True,
            enum=[type.value for type in TransferType],
            description="The payment method.",
        ),
    },
)

user_transfer_model = finance_namespace.model('Transfer', {
    'fromType': fields.String(required=True, description='Source type: user or fund'),
    'fromID': fields.Integer(required=True, description='ID of the source: fundID'),
    'toUserID': fields.Integer(required=True, description='Target userID'),
    'toFundID': fields.Integer(required=True, description='Target fundID'),
    'amount': fields.Float(required=True, description='Amount to transfer'),
    'currencyID': fields.Integer(required=True, description='Currency ID for the transfer'),
    'transferType': fields.String(required=False, default='Transfer', description='Type of the transfer'),
    'notes': fields.String(required=False, description='Additional notes')
})

fund_transfer_model = finance_namespace.model(
    "FundTransfer",
    {
        "from_fund": fields.Integer(required=True, description="the fund to take from"),
        "to_fund": fields.Integer(required=True, description="the fund to transfer to"),
        "transferAmount": fields.Float(
            required=True, description="The amount to be transfered"
        ),
        "notes": fields.String(required=False, description="Supply any notes/details"),
        "transfer_type": fields.String(
            required=True,
            enum=[type.value for type in TransferType],
            description="EFT, Cash, or Check",
        ),
        "currencyID": fields.Integer(
            required=True, description="the currency to be used for transfer"
        ),
    },
)



project_funds_model = finance_namespace.model(
    "ProjectFunds",
    {
        "projectID": fields.Integer(required=True),
        "fundsAllocated": fields.Float(required=True),
        "field": fields.String(
            enum=[scope.value for scope in ProjectScopes],
            required=True,
            description="What field of the project",
        ),
    },
)

case_funds_model = finance_namespace.model(
    "CaseFunds",
    {
        "caseID": fields.Integer(required=True),
        "fundsAllocated": fields.Float(required=True),
        "field": fields.String(
            enum=[scope.value for scope in ProjectScopes],
            required=True,
            description="What field of the case",
        ),
    },
)

reports_data_model = finance_namespace.model(
    "Reports",
    {
        "reportTag": fields.String(required=True),
        "title": fields.String(required=True),
        "createdBy": fields.String(required=True),
        "type": fields.String(required=True),
        "reportId": fields.String(required=True),
        "pdfUrl": fields.String(required=True),
    },
)

currencies_model = finance_namespace.model(
    "CurrencyData",
    {
        "currencyCode": fields.String(
            required=True, description="The code of the currency e.g USD"
        ),
        "currencyName": fields.String(
            required=True,
            description="The name of the currency e.g United States Dollar",
        ),
        "exchangeRateToUSD": fields.Float(required=True),
    },
)

# Define the parser and expected arguments
parser = reqparse.RequestParser()
parser.add_argument('start_date', type=str, required=True, help='Start date in the format YYYY-MM-DD')
parser.add_argument('end_date', type=str, required=True, help='End date in the format YYYY-MM-DD')



@finance_namespace.route("/fund_distribution", methods=["GET"])
@finance_namespace.expect(parser)
class FundDistribution(Resource):
    @jwt_required()
    def get(self):
        # Parse the arguments
        args = parser.parse_args()
        start_date_str = args['start_date']
        end_date_str = args['end_date']

        # Parse the dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return {"message": "Invalid date format. Please use YYYY-MM-DD."}, 400

        # Define all possible project scopes
        all_project_scopes = ["HEALTH", "SHELTER", "GENERAL", "SPONSORSHIP", "EDUCATION"]

        # Query to get all distinct account names
        account_names = (
            db.session.query(RegionAccount.accountName)
            .distinct()
            .all()
        )

        # Create a dictionary to hold the results
        distribution = {account.accountName: {scope: 0 for scope in all_project_scopes} for account in account_names}

        # Query to sum the amount grouped by projectScope and accountName, filtered by date range
        results = (
            db.session.query(
                Donations.projectScope,
                RegionAccount.accountName,
                db.func.sum(Donations.amount).label('total_amount')
            )
            .join(RegionAccount, Donations.accountID == RegionAccount.accountID)
            .filter(
                Donations.createdAt >= start_date,
                Donations.createdAt <= end_date
            )
            .group_by(Donations.projectScope, RegionAccount.accountName)
            .all()
        )

        # Populate the distribution dictionary with the results
        for result in results:
            distribution[result.accountName][result.projectScope.name] = float(result.total_amount)

        # Format the results into a list of dictionaries
        data = [
            {
                'accountName': account_name,
                **scopes
            }
            for account_name, scopes in distribution.items()
        ]

        return {'data': data}, 200


@finance_namespace.route("/status_amounts_by_region_account", methods=["GET"])
@finance_namespace.expect(parser)
class StatusAmountsByRegionAccount(Resource):
    @jwt_required()
    def get(self):
        # Parse the arguments
        args = parser.parse_args()
        start_date_str = args['start_date']
        end_date_str = args['end_date']

        # Parse the dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return {"message": "Invalid date format. Please use YYYY-MM-DD."}, 400

        # Query to sum the amounts by status and group by region account, filtered by date range
        results = (
            db.session.query(
                RegionAccount.accountName,
                db.func.sum(
                    db.case(
                        (Donations.status.in_(['Approved', 'Closed']), Donations.amount),
                        else_=0
                    )
                ).label('total_approved_closed'),
                db.func.sum(
                    db.case(
                        (~Donations.status.in_(['Approved', 'Closed']), Donations.amount),
                        else_=0
                    )
                ).label('total_other_statuses')
            )
            .join(RegionAccount, Donations.accountID == RegionAccount.accountID)
            .filter(
                Donations.createdAt >= start_date,
                Donations.createdAt <= end_date
            )
            .group_by(RegionAccount.accountName)
            .all()
        )

        # Format the results into a list of dictionaries
        data = [
            {
                'accountName': result.accountName,
                'total_approved_closed': float(result.total_approved_closed),
                'total_other_statuses': float(result.total_other_statuses)
            }
            for result in results
        ]

        return {'data': data}, 200


@finance_namespace.route("/unapproved_transactions_reminder", methods=["GET"])
@finance_namespace.expect(parser)
class UnapprovedTransactionsReminder(Resource):
    @jwt_required()
    def get(self):
         # Parse the arguments
        args = parser.parse_args()
        start_date_str = args['start_date']
        end_date_str = args['end_date']

        # Parse the dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return {"message": "Invalid date format. Please use YYYY-MM-DD."}, 400

        # Query for unapproved and non-rejected project fund release requests within the date range
        unapproved_project_requests = (
            db.session.query(ProjectFundReleaseRequests)
            .filter(
                ProjectFundReleaseRequests.approved == False,
                ProjectFundReleaseRequests.createdAt >= start_date,
                ProjectFundReleaseRequests.createdAt <= end_date,
                ProjectFundReleaseRequests.status != "Rejected"
            )
            .all()
        )

        # Query for unapproved and non-rejected case fund release requests within the date range
        unapproved_case_requests = (
            db.session.query(CaseFundReleaseRequests)
            .filter(
                CaseFundReleaseRequests.approved == False,
                CaseFundReleaseRequests.createdAt >= start_date,
                CaseFundReleaseRequests.createdAt <= end_date,
                CaseFundReleaseRequests.status != "Rejected"
            )
            .all()
        )

        # Format the results into reminder sentences
        reminders = []

        for request in unapproved_project_requests:
            project = db.session.query(ProjectsData).filter_by(projectID=request.projectID).first()
            if project:
                # Calculate days pending
                days_pending = (end_date - request.createdAt).days
                reminders.append(
                    f"Project '{project.projectName}' has requested funds on "
                    f"{request.createdAt.strftime('%Y-%m-%d')} and has been pending for {days_pending} days."
                )

        for request in unapproved_case_requests:
            case = db.session.query(CasesData).filter_by(caseID=request.caseID).first()
            if case:
                # Calculate days pending
                days_pending = (end_date - request.createdAt).days
                reminders.append(
                    f"Case '{case.caseName}' has requested funds on "
                    f"{request.createdAt.strftime('%Y-%m-%d')} and has been pending for {days_pending} days."
                )

        return {'reminders': reminders}, 200


@finance_namespace.route("/currencies/create", methods=["POST", "PUT"])
class CreateCurrency(Resource):
    @jwt_required()
    @finance_namespace.expect(currencies_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            currency_data = request.json
            if not current_user.is_admin():
                return {
                    "message": "Forbidden, only admins can add currencies"
                }, HTTPStatus.FORBIDDEN

            # Check if currencyCode already exists
            existing_currency = Currencies.query.filter_by(currencyCode=currency_data["currencyCode"]).first()
            if existing_currency:
                return {
                    "message": "Currency code already exists. Please choose a different currency code."
                }, HTTPStatus.BAD_REQUEST

            currency = Currencies(
                currencyCode=currency_data["currencyCode"],
                currencyName=currency_data["currencyName"],
                exchangeRateToUSD=currency_data["exchangeRateToUSD"],
            )
            currency.save()
            return {
                "message": "Currency added successfully.",
                "currencyID": currency.currencyID,
            }, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding currency: {str(e)}")
            return {
                "message": f"Error adding currency: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

    @jwt_required()
    @finance_namespace.expect(currencies_model)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            currency_data = request.json
            if not current_user.is_admin():
                return {
                    "message": "Forbidden, only admins can update currencies"
                }, HTTPStatus.FORBIDDEN

            # Check if currencyCode already exists
            existing_currency = Currencies.query.filter(Currencies.currencyID != currency_data["currencyID"], Currencies.currencyCode == currency_data["currencyCode"]).first()
            if existing_currency:
                return {
                    "message": "Currency code already exists. Please choose a different currency code."
                }, HTTPStatus.BAD_REQUEST

            currency = Currencies.query.get_or_404(currency_data["currencyID"])
            currency.currencyCode = currency_data["currencyCode"]
            currency.currencyName = currency_data["currencyName"]
            currency.exchangeRateToUSD = currency_data["exchangeRateToUSD"]
            currency.save()
            return {"message": "Currency updated successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating currency: {str(e)}")
            return {
                "message": f"Error updating currency: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/get_all_currencies")
class GetAllCurrenciesResource(Resource):
    @jwt_required()
    def get(self):
        try:
            currencies = Currencies.query.all()
            currencies_data = [
                {
                    "currencyID": currency.currencyID,
                    "currencyCode": currency.currencyCode,
                    "currencyName": currency.currencyName,
                    "lastUpdated": currency.lastUpdated.isoformat(),
                }
                for currency in currencies
            ]
            return {"currencies": currencies_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all currencies: {str(e)}")
            return {
                "message": f"Error getting all currencies: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/funds_summary")
class FundSummaryResource(Resource):
    @jwt_required()
    def get(self):
        # Query to get the sum of totalFund, usedFund, and availableFund
        fund_sums = db.session.query(
            func.sum(FinancialFund.totalFund).label('total_fund_sum'),
            func.sum(FinancialFund.usedFund).label('used_fund_sum'),
            func.sum(FinancialFund.availableFund).label('available_fund_sum')
        ).first()

        # Check if the result is None, in case there are no records
        if not fund_sums:
            return jsonify({'message': 'No funds available'}), 404

        # Prepare the response
        response = {
            'total_fund_sum': fund_sums.total_fund_sum if fund_sums.total_fund_sum else 0,
            'used_fund_sum': fund_sums.used_fund_sum if fund_sums.used_fund_sum else 0,
            'available_fund_sum': fund_sums.available_fund_sum if fund_sums.available_fund_sum else 0
        }

        # Return the response as JSON
        return jsonify(response)


@finance_namespace.route("/get_total_fund_pledged")
class TotalFundPledgedResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Query to get the sum of fundsRequested where approved is NULL
            total_pledged_cases = db.session.query(
                func.sum(CaseFundReleaseRequests.fundsRequested).label('total_pledged')
            ).filter(CaseFundReleaseRequests.approved == False).first()  # Checking where approved is NULL

            total_pledged_projects = db.session.query(
                func.sum(ProjectFundReleaseRequests.fundsRequested).label('total_pledged')
            ).filter(ProjectFundReleaseRequests.approved == False).first()  # Checking where approved is NULL
            
            # print(total_pledged_projects.total_pledged)
            # print(total_pledged_cases.total_pledged)

            total_pledged = total_pledged_cases.total_pledged + total_pledged_projects.total_pledged

            # If no records found, return 0
            if total_pledged is None:
                return jsonify({'total_pledged': 0}), 200
            
            # if total_pledged_projects is None or total_pledged_projects.total_pledged is None:
            #     return jsonify({'total_pledged': 0}), 200

            # Return the total pledged amount as JSON
            return jsonify({
                'total_pledged': total_pledged
            })

        except SQLAlchemyError as e:
            # Log the exception (optional) and return an error response
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'An error occurred while processing your request.'}), 500

        except Exception as e:
            # Handle any other general exceptions
            print(f"Unexpected error: {str(e)}")
            return jsonify({'error': 'An unexpected error occurred.'}), 500

@finance_namespace.route("/get_region_accounts")
class GetRegionAccountsResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Query to get the accountName, availableFund, totalFund, and usedFund
            accounts = db.session.query(
                RegionAccount.accountName,
                RegionAccount.availableFund,
                RegionAccount.totalFund,
                RegionAccount.usedFund
            ).all()

            # Convert query results to a list of dictionaries
            accounts_list = [
                {
                    'accountName': account.accountName,
                    'availableFund': account.availableFund,
                    'totalFund': account.totalFund,
                    'usedFund': account.usedFund
                }
                for account in accounts
            ]

            # Return the results as JSON
            return jsonify(accounts_list)

        except SQLAlchemyError as e:
            # Log the exception (optional) and return an error response
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'An error occurred while processing your request.'}), 500

        except Exception as e:
            # Handle any other general exceptions
            print(f"Unexpected error: {str(e)}")
            return jsonify({'error': 'An unexpected error occurred.'}), 500


@finance_namespace.route("/get_all_currencies_with_balances")
class GetAllCurrenciesWithBalancesResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Perform a left join to include all currencies, even those without a balance record
            # Use coalesce to default to 0 when there are no balances
            currencies_with_balances = (
                db.session.query(
                    Currencies.currencyID,
                    Currencies.currencyCode,
                    Currencies.currencyName,
                    Currencies.exchangeRateToUSD,
                    Currencies.lastUpdated,
                    db.func.coalesce(
                        db.func.sum(FinancialFundCurrencyBalance.availableFund), 0
                    ).label("available_amount"),
                )
                .outerjoin(
                    FinancialFundCurrencyBalance,
                    FinancialFundCurrencyBalance.currencyID == Currencies.currencyID,
                )
                .group_by(
                    Currencies.currencyID,
                    Currencies.currencyCode,
                    Currencies.currencyName,
                )
                .all()
            )

            currencies_data = [
                {
                    "currencyID": currency.currencyID,
                    "currencyCode": currency.currencyCode,
                    "exchangeRateToUSD": currency.exchangeRateToUSD,
                    "currencyName": currency.currencyName,
                    "available_amount": float(
                        currency.available_amount
                    ),  # Ensure available_amount is a float
                    "lastUpdated": currency.lastUpdated.strftime("%d %b %Y"),
                }
                for currency in currencies_with_balances
            ]

            return {"currencies": currencies_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(
                f"Error getting all currencies with balances: {str(e)}"
            )
            return {
                "message": f"Error getting all currencies with balances: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/finacial_funds/create", methods=["POST", "PUT"])
class AddEditFinancialFundResource(Resource):
    @jwt_required()
    @finance_namespace.expect(fund_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            fund_data = request.json

            if not current_user.is_admin():
                return {
                    "message": "Forbidden, only admins can add Financial Funds"
                }, HTTPStatus.FORBIDDEN

            # Check if a fund with the given name already exists
            existing_fund = FinancialFund.query.filter_by(
                fundName=fund_data["fundName"]
            ).first()
            if existing_fund:
                return {
                    "message": "Fund with this name already exists"
                }, HTTPStatus.CONFLICT

            new_fund = FinancialFund(
                fundName=fund_data["fundName"],
                usedFund=0,
                notes=fund_data.get("notes", ""),
                accountType=fund_data["accountType"],
                administrator=fund_data["administrator"],
            )

            new_fund.save()
            # add the USD default
            new_currency = FinancialFundCurrencyBalance(
                fundID=new_fund.fundID, currencyID=1
            )
            new_currency.save()

            if len(fund_data["currencies"]) > 0:
                for currency in fund_data["currencies"]:
                    if currency != 1:
                        new_currency = FinancialFundCurrencyBalance(
                            fundID=new_fund.fundID, currencyID=currency
                        )
                        new_currency.save()

            # now let's add the sub funds
            sub_funds = fund_data.get("subFunds", {})

            for sub in sub_funds:
                new_sub_fund = SubFunds(
                    fundID=new_fund.fundID,
                    subFundName=sub["fundName"],
                    notes=fund_data.get("notes", ""),
                    accountType=fund_data["accountType"],
                )
                new_sub_fund.save()
                new_balance = SubFundCurrencyBalance(
                    subFundID=new_sub_fund.subFundID, currencyID=1
                )
                new_balance.save()

                if len(fund_data["currencies"]) > 0:
                    for currency in fund_data["currencies"]:
                        if currency != 1:
                            balance = SubFundCurrencyBalance(
                                subFundID=new_sub_fund.subFundID, currencyID=currency
                            )
                            balance.save()

            return {"message": "Sub Fund was added successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding financial fund: {str(e)}")
            return {
                "message": f"Error adding finacial fund: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/financial_funds/sub_fund_create")
class SubFundCreateResource(Resource):
    @jwt_required()
    @finance_namespace.expect(sub_fund_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            fund_data = request.json

            if not current_user.is_admin():
                return {
                    "message": "Forbidden, only admins can add Financial Funds"
                }, HTTPStatus.FORBIDDEN

            # Check if a fund with the given name already exists
            existing_fund = FinancialFund.query.get_or_404(fund_data["fundID"])
            if not existing_fund:
                return {"message": "Parent fund does not exist"}, HTTPStatus.NOT_FOUND

            new_fund = SubFunds(
                fundID=fund_data["fundID"],
                subFundName=fund_data["fundName"],
                notes=fund_data.get("notes", ""),
                accountType=fund_data["accountType"],

            )
            new_fund.save()

            if len(fund_data["currencies"]) > 0:
                for currency in fund_data["currencies"]:
                    # new_balance = SubFundCurrencyBalance(
                    #     subFundID=new_fund.subFundID, currencyID=currency
                    # )
                    # new_balance.save()
                    if currency:
                        balance = SubFundCurrencyBalance(
                            subFundID=new_fund.subFundID, currencyID=currency
                        )
                        balance.save()
        except Exception as e:
            current_app.logger.error(f"Error adding sub-fund Account: {str(e)}")
            return {
                "message": f"Error adding sub-fund Account: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/region_accounts/create", methods=["POST", "PUT"])
class AddEditRegionAccountResource(Resource):
    @jwt_required()
    @finance_namespace.expect(region_account_data)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            account_data = request.json

            if not current_user.is_admin():
                return {
                    "message": "Forbidden, only admins can add Region Accounts"
                }, HTTPStatus.FORBIDDEN

            region_id = account_data.get("regionID")

            region = Regions.query.get_or_404(region_id)
            # Check if a fund with the given name already exists
            existing_account = RegionAccount.query.filter_by(regionID=region_id).first()
            if existing_account:
                return {
                    "message": f"An account in {region.regionName} already exists."
                }, HTTPStatus.CONFLICT

            new_account = RegionAccount(
                accountName=region.regionName, regionID=region_id
            )
            new_account.save()

            # add the USD default
            new_currency = RegionAccountCurrencyBalance(
                accountID=new_account.accountID, currencyID=1
            )
            new_currency.save()

            if len(account_data["currencies"]) > 0:
                for currency in account_data["currencies"]:
                    if currency != 1:
                        new_currency = RegionAccountCurrencyBalance(
                            accountID=new_account.accountID, currencyID=currency
                        )
                        new_currency.save()

            return {
                "message": "Region Account was added successfully.",
                "accountID": new_account.accountID,
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding region Account: {str(e)}")
            return {
                "message": f"Error adding region Account: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/donors/add_or_edit", methods=["POST", "PUT"])
class AddEditDonorsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(donor_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donor_data = request.json

            # Check if a donor with the given name already exists
            existing_donor = Donor.query.filter_by(donorName=donor_data["name"]).first()
            if existing_donor:
                return {
                    "message": "Donor with this name already exists"
                }, HTTPStatus.CONFLICT

            new_donor = Donor(
                donorName=donor_data["name"],
                donorType=donor_data["donorType"],
                placeOfResidence=donor_data["country"],
                email=donor_data["email"],
                phoneNumber=donor_data["phoneNumber"],
                notes=donor_data.get("notes", None),
                imageLink=donor_data.get("imageLink", None),
            )

            new_donor.save()

            if len(donor_data["representatives"]) > 0:
                for rep in donor_data["representatives"]:
                    new_rep = Representative(
                        donorID=new_donor.donorID,
                        name=rep["name"],
                        jobPosition=rep["jobPosition"],
                        email=rep["email"],
                        phoneNumber=rep["phoneNumber"],
                        imageLink=rep.get("imageLink", None),
                    )
                    new_rep.save()

            return {
                "message": "Donor was added successfully.",
                "donorID": new_donor.donorID,
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding Donor: {str(e)}")
            return {
                "message": f"Error adding Donor: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

    @jwt_required()
    @finance_namespace.expect(donor_edit_model)
    def put(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donor_data = request.json

            # Check if a fund with the given name already exists
            donor_id = donor_data.get("donorID")
            if not donor_id:
                return {
                    "message": "Donor ID is required for updating a donor"
                }, HTTPStatus.BAD_REQUEST

            existing_donor = Donor.query.get_or_404(donor_id)

            existing_donor.donorName = donor_data["name"]
            existing_donor.donorType = donor_data["donorType"]
            existing_donor.placeOfResidence = donor_data["country"]
            existing_donor.email = donor_data["email"]
            existing_donor.phoneNumber = donor_data["phoneNumber"]
            existing_donor.notes = donor_data["notes"]
            existing_donor.imageLink = donor_data.get("imageLink", "")

            existing_donor.save()
            return {"message": "Donor was updated successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error updating donor: {str(e)}")
            return {
                "message": f"Error updating donor: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/add_balance", methods=["POST"])
class AddDonationResource(Resource):
    @jwt_required()
    @finance_namespace.expect(donations_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donation_data = request.json

            account_id = donation_data.get("accountID")
            fund_id = donation_data.get("fundID")
            donor_id = donation_data.get("donorID")
            sub_fund_id = donation_data.get("subFundID")

            project_id = donation_data.get("projectID")
            case_id = donation_data.get("caseID")

            if project_id == 0:
                project_id = None
            if case_id == 0:
                case_id = None

            # Corrected validation logic
            if account_id is None or fund_id is None or donor_id is None:
                return {
                    "message": "Either no account ID, fund ID, or donor ID provided"
                }, HTTPStatus.BAD_REQUEST

            account = RegionAccount.query.get_or_404(account_id)
            fund = FinancialFund.query.get_or_404(fund_id)
            donor = Donor.query.get_or_404(donor_id)
            if sub_fund_id:
                sub_fund = SubFunds.query.get_or_404(sub_fund_id)
            else:
                sub_fund = None
            
            project_scope_mapping = {
                "HEALTH": "HEALTH",
                "EDUCATION": "EDUCATION",
                "SPONSERSHIP": "SPONSORSHIP",
                "GENERAL": "GENERAL",
                "GENERAL AND RELIEF": "GENERAL",
                "SHELTER": "SHELTER",
                "RELIEF": "RELIEF"
            }
            # This time, we'll keep it in title case to match the Enum values more closely
            human_readable_scope = donation_data.get("project_scope", "").strip().upper()
            print(human_readable_scope)
            print(project_scope_mapping.get(human_readable_scope))

            # Translate the human-readable project scope to the enum value
            enum_project_scope = project_scope_mapping.get(human_readable_scope)
            
            if not enum_project_scope:
                # Handle invalid project scope
                return {
                    "message": f"Invalid project scope: {human_readable_scope}"
                }, HTTPStatus.INTERNAL_SERVER_ERROR

            new_donation = Donations(
                donorID=donor_id,
                accountID=account_id,
                fundID=fund_id,
                subFundID=sub_fund_id,
                details=donation_data.get("notes", ""),
                currencyID=donation_data["currencyID"],
                amount=donation_data["amount"],
                donationType=donation_data["donationType"].upper(),
                caseID=case_id,
                projectID=project_id,
                projectScope=enum_project_scope,
                allocationTags=donation_data.get("allocationTags", enum_project_scope),

            )
            new_donation.save()

            # Update the sub-fund currency balance
            if sub_fund:
                sub_fund_balance = SubFundCurrencyBalance.query.filter_by(
                    subFundID=sub_fund_id, currencyID=donation_data["currencyID"]
                ).first()
                if sub_fund_balance:
                    sub_fund_balance.totalFund += donation_data["amount"]
                    sub_fund_balance.availableFund += donation_data["amount"]
                    db.session.commit()
                else:
                    return {
                        "message": "Sub-fund balance not found for the given currency."
                    }, HTTPStatus.NOT_FOUND
                
                # Update the Sub Fund balance
                # get the currency rate from dolar to the currency
                currency = Currencies.query.get_or_404(donation_data["currencyID"])
                exchange_rate = currency.exchangeRateToUSD
                # convert the amount to USD
                amount_usd = donation_data["amount"] / exchange_rate
                sub_fund.totalFund += amount_usd
                sub_fund.availableFund += amount_usd
                sub_fund.save()

            
            # sub_fund_balance.save()

            db.session.commit()

            return {
                "message": "Donation added successfully.",
                "donationID": new_donation.id  # Include the donationID in the response
            }, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding donation: {str(e)}")
            return {
                "message": f"Error adding donation: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/donations/no_case_project")
class DonationsNoCaseProjectResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Query for donations where caseID and ProjectID are None
            donations = Donations.query.filter_by(caseID=None, projectID=None).all()
            donation_list = []
            for donation in donations:
                donation_dict = {
                    "donationID": donation.id,
                    "donor": {
                        "donorID": donation.donor.donorID,
                        "donorName": donation.donor.donorName,
                        "donorEmail": donation.donor.email,
                        # Add other donor information as needed
                    },
                    "amount": donation.amount,
                    "currencyName": donation.currency.currencyName,
                    "donationType": donation.donationType.value,
                    "createdAt": donation.createdAt.isoformat(),
                }
                donation_list.append(donation_dict)

            return {"donations": donation_list}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(
                f"Error retrieving donations with no case or project: {str(e)}"
            )
            return {
                "message": f"Error retrieving donations: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/donations/no_case_project/donor/<int:donorID>")
class DonationsNoCaseProjectByDonorResource(Resource):
    @jwt_required()
    def get(self, donorID):
        try:
            # Query for donations where caseID and ProjectID are None
            donations = Donations.query.filter_by(
                caseID=None, projectID=None, donorID=donorID
            ).all()
            donation_list = []
            for donation in donations:
                donation_dict = {
                    "donationID": donation.id,
                    "amount": donation.amount,
                    "currencyName": donation.currency.currencyName,
                    "donationType": donation.donationType.value,
                    "createdAt": donation.createdAt.isoformat(),
                }
                donation_list.append(donation_dict)

            return {"donations": donation_list}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(
                f"Error retrieving donations with no case or project: {str(e)}"
            )
            return {
                "message": f"Error retrieving donations: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/region_accounts/all/summary/currency/<int:currency_conversion>"
)
class RegionAccountSummaryResource(Resource):
    @jwt_required()
    def get(self, currency_conversion):
        try:
            accounts = RegionAccount.query.all()
            accounts_data = []
            for account in accounts:
                account_data = {
                    "accountID": account.accountID,
                    "accountName": account.accountName,
                    "lastUpdate": account.lastUpdate.isoformat(),
                }
                # get balances based on the currency conversion
                balances = account.get_fund_balance(currency_conversion)
                converted_balances = {
                    key: float(value) if isinstance(value, Decimal) else value
                    for key, value in balances.items()
                }
                accounts_data.append(account_data | converted_balances)

            return {"accounts": accounts_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting account summary: {str(e)}")
            return {
                "message": f"Error getting account summary: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/region_accounts/single/<int:account_id>/details/<int:currency_conversion>"
)
class SingleRegionAccountSummaryResource(Resource):
    @jwt_required()
    def get(self, account_id, currency_conversion):
        try:
            account = RegionAccount.query.get_or_404(account_id)

            # Fetch all sub-funds related to the account
            # sub_funds = SubFunds.query.filter_by(fundID=account.accountID).all()



            account_data = {
                "accountID": account.accountID,
                "accountName": account.accountName,
                "lastUpdate": account.lastUpdate.isoformat(),
                "availableCurrencies": account.get_available_currencies(),
                "balances": account.get_fund_balance(currency_conversion),
                # "subFundBalance": sub_fund_balance,
                "transactions": account.get_account_transactions(),
                "scope_percentages": account.get_scope_percentages(),
                "scope_balances": account.get_category_balances(),
                "donations": account.get_all_donations(),
            }
            return {"account": account_data}, HTTPStatus.OK

            
        except Exception as e:
            current_app.logger.error(f"Error getting account summary: {str(e)}")
            return {
                "message": f"Error getting account summary: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/financial_funds/all/summary/currency/<int:currency_conversion>"
)
class FinancialFundSummaryResource(Resource):
    @jwt_required()
    def get(self, currency_conversion):
        try:
            funds = FinancialFund.query.all()
            funds_data = []
            for fund in funds:
                fund_data = {
                    "fundID": fund.fundID,
                    "fundName": fund.fundName,
                    "lastUpdate": fund.lastUpdate.isoformat(),
                }
                # get balances based on the currency conversion
                balances = fund.get_fund_balance(currency_conversion)
                funds_data.append(fund_data | balances)
            return {"funds": funds_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting fund summary: {str(e)}")
            return {
                "message": f"Error getting fund summary: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/financial_funds/single/<int:fund_id>/details/<int:currency_conversion>"
)
class SingleFinancialFundSummaryResource(Resource):
    @jwt_required()
    def get(self, fund_id, currency_conversion):
        try:
            fund = FinancialFund.query.get_or_404(fund_id)
            print("fund")
            transfers_out = FundTransfers.query.filter_by(from_fund=fund.fundID, closed=True).all()
            print("transfers_out")
            transfers_in = FundTransfers.query.filter_by(to_fund=fund.fundID, closed=True).all()
            print("transfers_in")
            case_payments = CaseFundReleaseApproval.query.filter_by(fundID=fund.fundID, closed=True).all()
            print("case_payments")
            project_payments = ProjectFundReleaseApproval.query.filter_by(fundID=fund.fundID, closed=True).all()
            print("project_payments")	
            fund_data = {
                "fundID": fund.fundID,
                "fundName": fund.fundName,
                "lastUpdate": fund.lastUpdate.isoformat(),
                "availableCurrencies": fund.get_available_currencies(),
                "subFunds": fund.get_all_sub_funds2(currency_conversion),
                "donations": fund.get_all_donations(),
                "transfers_out": [transfer.out_transfer_serialize(currency_conversion) for transfer in transfers_out],
                "transfers_in": [transfer.in_transfer_serialize(currency_conversion) for transfer in transfers_in],
                "cases_and_projects_paid":{
                    "cases": [case_payment.fund_serialize(currency_conversion) for case_payment in case_payments],
                    "projects": [project_payment.fund_serialize(currency_conversion) for project_payment in project_payments]
                },
            }
            # get balances based on the currency conversion
            balances = fund.get_fund_balance(currency_conversion)
            return {"fund": fund_data | balances}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting fund summary: {str(e)}")
            return {
                "message": f"Error getting fund summary: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/request_project_fund_release")
class RequestProjectFundReleaseResource(Resource):
    @jwt_required()
    @finance_namespace.expect(project_fund_release_request)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json

            project_id = request_data.get("projectID")
            payment_count = request_data.get("paymentCount")

            if not project_id:
                return {
                    "message": "project ID is required to make a request."
                }, HTTPStatus.BAD_REQUEST

            project = ProjectsData.query.get_or_404(project_id)
            
            existing_request = ProjectFundReleaseRequests.query.filter_by(
                projectID=project_id, paymentCount=payment_count
            ).first()

            if existing_request and existing_request.status.lower() != 'rejected':
                return {
                    "message": "A request with the same payment count already exists for this project."
                }, HTTPStatus.BAD_REQUEST

            release = ProjectFundReleaseRequests(
                projectID=project_id,
                fundsRequested=request_data["fundsRequested"],
                requestedBy=current_user.userID,
                paymentCount=request_data["paymentCount"],
                notes=request_data["notes"],
            )

            release.save()
            return {"message": "Request posted successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {
                "message": f"Error adding request: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/request_case_fund_release")
class RequestCaseFundReleaseResource(Resource):
    @jwt_required()
    @finance_namespace.expect(case_fund_release_request)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json

            case_id = request_data.get("caseID")
            payment_count = request_data.get("paymentCount")

            if not case_id:
                return {
                    "message": "case ID is required to make a request."
                }, HTTPStatus.BAD_REQUEST

            case = CasesData.query.get_or_404(case_id)

            existing_request = CaseFundReleaseRequests.query.filter_by(
                caseID=case_id, paymentCount=payment_count
            ).first()

            if existing_request and existing_request.status.lower() != 'rejected':
                
                return {
                    "message": "A request with the same payment count already exists for this case."
                }, HTTPStatus.BAD_REQUEST

            release = CaseFundReleaseRequests(
                caseID=case_id,
                fundsRequested=request_data["fundsRequested"],
                requestedBy=current_user.userID,
                paymentCount=payment_count,
                notes=request_data["notes"],
            )

            release.save()

            return {"message": "Request posted successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {
                "message": f"Error adding request: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/make_fund_transfer")
class MakeFundTransferResource(Resource):
    @jwt_required()
    @finance_namespace.expect(fund_transfer_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json

            from_fund = FinancialFund.query.get_or_404(request_data["from_fund"])
            to_fund = FinancialFund.query.get_or_404(request_data["to_fund"])

            transfer = FundTransfers(
                from_fund=request_data["from_fund"],
                to_fund=request_data["to_fund"],
                transferAmount=request_data["transferAmount"],
                notes=request_data["notes"],
                createdBy=current_user.userID,
                transferType=request_data["transfer_type"],
            )

            transfer.save()

            return {
                "message": "Transfer posted successfully.",
                "transferID": transfer.transferID,
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {
                "message": f"Error adding request: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/close_fund_transfer/<int:transfer_id>")
class CloseFundTransferResource(Resource):
    @jwt_required()
    def put(self, transfer_id):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            transfer = FundTransfers.query.get_or_404(transfer_id)

            if transfer.closed:
                return {"message": "Transfer is already closed"}, HTTPStatus.CONFLICT

            transfer.closed = True
            transfer.status = "Closed"
            transfer.save()

            from_fund = FinancialFund.query.get_or_404(transfer.from_fund)
            to_fund = FinancialFund.query.get_or_404(transfer.to_fund)

            from_fund.use_fund(transfer.transferAmount, transfer.currencyID)
            to_fund.add_fund(transfer.transferAmount, transfer.currencyID)

            return {"message": "Transfer closed successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error closing transfer: {str(e)}")
            return {
                "message": f"Error closing transfer: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/close_donation/<int:donationID>")
class CloseDonationResource(Resource):
    @jwt_required()
    def put(self, donationID):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donation = Donations.query.get_or_404(donationID)

            if donation.closed:
                return {"message": "Donation is already closed"}, HTTPStatus.CONFLICT

            donation.closed = True
            donation.status = "Closed"
            donation.save()

            fund = FinancialFund.query.get(donation.fundID)
            account = RegionAccount.query.get(donation.accountID)

            if donation.subFundID:
                sub_fund = SubFunds.query.get_or_404(donation.subFundID)
            else:
                sub_fund = None

            # call the add function to handle the logic
            account.add_fund(
                donation.amount,
                donation.currencyID,
                None,
                donation.projectID,
                donation.caseID,
                None,
                donation.projectScope.name.lower(),
            )
            fund.add_fund(donation.amount, donation.currencyID)
            if sub_fund:
                sub_fund.add_fund(donation.amount, donation.currencyID)

            return {"message": "Donation closed successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error closing donation: {str(e)}")
            return {
                "message": f"Error closing donation: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

# @finance_namespace.route("/project_cases_account_summary")
# class ProjectCasesAccountSummaryResource(Resource):
#     @jwt_required()
#     def get(self):
#         try:
#             # Execute the SQL query without computing availableFund in the query
#             result = db.session.execute(text('''
#                 SELECT ra."regionID", ra."accountName", 
#                     SUM(cfa."approvedAmount") AS total_approved_cases,
#                     SUM(pfa."approvedAmount") AS total_approved_projects,
#                     ra."totalFund",
#                     ra."usedFund"
#                 FROM region_account ra
#                 LEFT JOIN case_fund_release_approval cfa ON cfa."accountID" = ra."accountID"
#                 LEFT JOIN project_fund_release_approval pfa ON pfa."accountID" = ra."accountID"
#                 GROUP BY ra."regionID", ra."accountName", ra."totalFund", ra."usedFund";
#             '''))

#             # Process the result into a list of dictionaries
#             data = []
#             for row in result:
#                 totalFund = float(row.totalFund) if isinstance(row.totalFund, Decimal) else (row.totalFund if row.totalFund is not None else 0.0)
#                 usedFund = float(row.usedFund) if isinstance(row.usedFund, Decimal) else (row.usedFund if row.usedFund is not None else 0.0)
                
#                 # Compute availableFund in Python
#                 availableFund = totalFund - usedFund

#                 data.append({
#                     'regionID': row.regionID if row.regionID is not None else "",
#                     'accountName': row.accountName if row.accountName is not None else "",
#                     'total_approved_cases': float(row.total_approved_cases) if row.total_approved_cases is not None else 0.0,
#                     'total_approved_projects': float(row.total_approved_projects) if row.total_approved_projects is not None else 0.0,
#                     'totalFund': totalFund,
#                     'usedFund': usedFund,
#                     'availableFund': availableFund
#                 })

#             # Make the response object using Flask's make_response
#             response = make_response(json.dumps({'data': data}), 200)
#             response.headers["Content-Type"] = "application/json"
#             return response

#         except SQLAlchemyError as e:
#             # Handle SQLAlchemy errors
#             error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
#             return make_response(json.dumps({'error': 'Database error', 'message': error_message}), 500)

#         except Exception as e:
#             # Catch all other exceptions and return JSON response
#             return make_response(json.dumps({'error': 'An unexpected error occurred', 'message': str(e)}), 500)

@finance_namespace.route("/project_cases_account_summary")
@finance_namespace.expect(parser)
class ProjectCasesAccountSummaryResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Parse the arguments
            args = parser.parse_args()
            start_date_str = args['start_date']
            end_date_str = args['end_date']

            # Parse the dates
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                return make_response(json.dumps({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400)

            # Execute the SQL query with date filtering for case and project approvals
            result = db.session.execute(text('''
                SELECT ra."regionID", ra."accountName", 
                    SUM(CASE WHEN cfa."approvedAt" BETWEEN :start_date AND :end_date THEN cfa."approvedAmount" ELSE 0 END) AS total_approved_cases,
                    SUM(CASE WHEN pfa."approvedAt" BETWEEN :start_date AND :end_date THEN pfa."approvedAmount" ELSE 0 END) AS total_approved_projects,
                    ra."totalFund",
                    ra."usedFund"
                FROM region_account ra
                LEFT JOIN case_fund_release_approval cfa ON cfa."accountID" = ra."accountID"
                LEFT JOIN project_fund_release_approval pfa ON pfa."accountID" = ra."accountID"
                GROUP BY ra."regionID", ra."accountName", ra."totalFund", ra."usedFund";
            '''), {'start_date': start_date, 'end_date': end_date})

            # Process the result into a list of dictionaries
            data = []
            for row in result:
                totalFund = float(row.totalFund) if isinstance(row.totalFund, Decimal) else (row.totalFund if row.totalFund is not None else 0.0)
                usedFund = float(row.usedFund) if isinstance(row.usedFund, Decimal) else (row.usedFund if row.usedFund is not None else 0.0)
                
                # Compute availableFund in Python
                availableFund = totalFund - usedFund

                data.append({
                    'regionID': row.regionID if row.regionID is not None else "",
                    'accountName': row.accountName if row.accountName is not None else "",
                    'total_approved_cases': float(row.total_approved_cases) if row.total_approved_cases is not None else 0.0,
                    'total_approved_projects': float(row.total_approved_projects) if row.total_approved_projects is not None else 0.0,
                    'totalFund': totalFund,
                    'usedFund': usedFund,
                    'availableFund': availableFund
                })

            # Make the response object using Flask's make_response
            response = make_response(json.dumps({'data': data}), 200)
            response.headers["Content-Type"] = "application/json"
            return response

        except SQLAlchemyError as e:
            # Handle SQLAlchemy errors
            error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
            return make_response(json.dumps({'error': 'Database error', 'message': error_message}), 500)

        except Exception as e:
            # Catch all other exceptions and return JSON response
            return make_response(json.dumps({'error': 'An unexpected error occurred', 'message': str(e)}), 500)

        






@finance_namespace.route("/add_project_funds")
class AddProjectFundsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(project_funds_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json

            project_id = request_data.get("projectID")

            if not current_user.is_admin():
                return {
                    "message": "only admins can allocate funds."
                }, HTTPStatus.FORBIDDEN

            if not project_id:
                return {"message": "project ID not provided"}, HTTPStatus.BAD_REQUEST

            project = ProjectsData.query.get_or_404(project_id)

            project_fund = ProjectFunds.query.filter_by(projectID=project_id)

            if project_fund:
                return {
                    "message": "This project was already allocated funds."
                }, HTTPStatus.BAD_REQUEST

            region_account = RegionAccount.query.filter_by(
                regionID=project.regionID
            ).first()
            new_fund = ProjectFunds(
                projectID=project_id,
                accountID=region_account.accountID,
                fundsAllocated=request_data["fundsAllocated"],
            )

            new_fund.save()
            return {
                "message": "project has been allocated funds successfully."
            }, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {
                "message": f"Error adding request: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/add_case_funds")
class AddCaseFundsResource(Resource):
    @jwt_required()
    @finance_namespace.expect(case_funds_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request_data = request.json

            case_id = request_data.get("caseID")

            if not current_user.is_admin():
                return {
                    "message": "only admins can allocate funds."
                }, HTTPStatus.FORBIDDEN

            if not case_id:
                return {"message": "case ID not provided"}, HTTPStatus.BAD_REQUEST

            case = CasesData.query.get_or_404(case_id)

            case_fund = ProjectFunds.query.filter_by(caseID=case_id)

            if case_fund:
                return {
                    "message": "This case was already allocated funds."
                }, HTTPStatus.BAD_REQUEST

            region_account = RegionAccount.query.filter_by(
                regionID=case.regionID
            ).first()
            new_fund = CaseFunds(
                projectID=case_id,
                accountID=region_account.accountID,
                fundsAllocated=request_data["fundsAllocated"],
            )

            new_fund.save()
            return {
                "message": "project has been allocated funds successfully."
            }, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error adding request: {str(e)}")
            return {
                "message": f"Error adding request: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/get_all_fund_transfers")
class GetAllFundTransfers(Resource):
    @jwt_required()
    def get(self):
        try:
            transfers = FundTransfers.query.order_by(
                desc(FundTransfers.createdAt)
            ).all()
            transfers_data = []
            for transfer in transfers:
                user = Users.query.get(transfer.createdBy)
                from_fund = FinancialFund.query.get(transfer.from_fund)

                # Initialize `to_fund_data` to None
                to_fund_data = None

                # Check if the transfer is to a fund or to a user budget
                if transfer.to_fund:
                    to_fund = FinancialFund.query.get(transfer.to_fund)
                    to_fund_data = {
                        "fundID": to_fund.fundID,
                        "fundName": to_fund.fundName,
                        "balances": to_fund.get_fund_balance(1),
                    }
                elif transfer.to_user_budget:
                    to_user_budget = UserBudget.query.get(transfer.to_user_budget)
                    # get username of the user
                    username = Users.query.get(to_user_budget.userID).username
                    to_fund_data = {
                        "userBudgetID": to_user_budget.budgetId,
                        "userID": to_user_budget.userID,
                        "username": username,
                        "balances": to_user_budget.get_fund_balance(),
                    }

                # Prepare the transfer details dictionary
                transfer_details = {
                    "transferID": transfer.transferID,
                    "from_fund": {
                        "fundID": from_fund.fundID,
                        "fundName": from_fund.fundName,
                        "balances": from_fund.get_fund_balance(1),
                    },
                    "to": to_fund_data,  # This will be None if both are null
                    "createdBy": {
                        "userID": user.userID,
                        "userFullName": f"{user.firstName} {user.lastName}",
                        "username": user.username,
                    },
                    "transferAmount": transfer.transferAmount,
                    "createdAt": transfer.createdAt.isoformat(),
                    "notes": transfer.notes,
                    "status": transfer.status,
                    "closed": transfer.closed,
                }

                transfers_data.append(transfer_details)

            return {"all_transfers": transfers_data}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting fund transfers: {str(e)}")
            return {
                "message": f"Error getting fund transfers: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR



# @finance_namespace.route("/get_all_fund_transfers")
# class GetAllFundTransfers(Resource):
#     @jwt_required()
#     def get(self):
#         try:
#             transfers = FundTransfers.query.order_by(
#                 desc(FundTransfers.createdAt)
#             ).all()
#             transfers_data = []
#             for transfer in transfers:
#                 user = Users.query.get(transfer.createdBy)
#                 from_fund = FinancialFund.query.get(transfer.from_fund)
#                 to_fund = FinancialFund.query.get(transfer.to_fund)

#                 transfer_details = {
#                     "transferID": transfer.transferID,
#                     "from_fund": {
#                         "fundID": from_fund.fundID,
#                         "fundName": from_fund.fundName,
#                         "balances": to_fund.get_fund_balance(1),
#                     },
#                     "to_fund": {
#                         "fundID": to_fund.fundID,
#                         "fundName": to_fund.fundName,
#                         "balances": to_fund.get_fund_balance(1),
#                     },
#                     "createdBy": {
#                         "userID": user.userID,
#                         "userFullName": f"{user.firstName} {user.lastName}",
#                         "username": user.username,
#                     },
#                     "transferAmount": transfer.transferAmount,
#                     "createdAt": transfer.createdAt.isoformat(),
#                     "notes": transfer.notes,
#                     "status": transfer.status,
#                     "closed": transfer.closed,
#                 }

#                 transfers_data.append(transfer_details)

#             return {"all_transfers": transfers_data}, HTTPStatus.OK

#         except Exception as e:
#             current_app.logger.error(f"Error getting fund transfers: {str(e)}")
#             return {
#                 "message": f"Error getting fund transfers: {str(e)}"
#             }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/get_all_donations")
class GetAllDonationsResource(Resource):
    @jwt_required()
    def get(self):
        try:
            donations = Donations.query.order_by(desc(Donations.createdAt)).all()

            return [donation.track_serialize() for donation in donations], HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting donations: {str(e)}")
            return {
                "message": f"Error getting donations: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/get_all_fund_release_requests")
class GetAllFundReleaseRequests(Resource):
    @jwt_required()
    def get(self):
        try:
            case_requests = CaseFundReleaseRequests.query.order_by(
                desc(CaseFundReleaseRequests.createdAt)
            ).all()
            case_requests_data = []
            for request in case_requests:
                user = Users.query.get(request.requestedBy)
                user_budget = UserBudget.query.filter_by(userID=user.userID).first()
                user_details = {
                    "userID": user.userID,
                    "userFullName": f"{user.firstName} {user.lastName}",
                    "username": user.username,
                }
                default_budget = {
                    "totalFund": 0,
                    "usedFund": 0,
                    "availableFund": 0,
                    "currencyCode": '-',
                }
                case_data = CasesData.query.get(request.caseID)
                case_details = {
                    "caseID": case_data.caseID,
                    "caseName": case_data.caseName,
                    "category": case_data.category.value,
                    "status": case_data.caseStatus.value,
                }
                region_acc = RegionAccount.query.filter_by(regionID=case_data.regionID).first()
                region_acc_details = {
                    "accountName": region_acc.accountName,
                    "availableFund": float(region_acc.availableFund),
                }
                

                paymentList = case_data.status_data.data.get("paymentsList", [])
                # print(paymentList)
                paymentsList_ = []
                for index, item in enumerate(paymentList):
                    paymentsList_.append({"paymentNum": index + 1, "amount": item})

                # print(paymentsList_)
                request_details = {
                    "requestID": request.requestID,
                    "case": case_details,
                    "requestedBy": user_details,
                    "fundsRequested": request.fundsRequested,
                    "createdAt": request.createdAt.isoformat(),
                    "approved": request.approved,
                    "approvedAt": (
                        request.approvedAt.isoformat() if request.approvedAt else None
                    ),
                    "receivedAmount": f"{request.approvedAmount}/{request.fundsRequested}",
                    "regionName": Regions.query.get(case_data.regionID).regionName,
                    "region_account_details": region_acc_details,
                    "approved_funding": f"${case_data.approvedPayments}/${case_data.status_data.data.get('approvedFunding', 0)}",
                    "paymentCount": f"{request.paymentCount}/{case_data.status_data.data.get('paymentCount', 0)}",
                    "bulkName": "-",
                    "paymentDueDate": f"{case_data.dueDate}",
                    "projectScope": "-",
                    "status": request.status,
                    "paymentList": paymentsList_,
                    "user_budget": user_budget.get_fund_balance() if user_budget else default_budget,
                }

                case_requests_data.append(request_details)

            project_requests = ProjectFundReleaseRequests.query.order_by(
                desc(ProjectFundReleaseRequests.createdAt)
            ).all()
            print("Check Project Data")
            project_requests_data = []
            for request in project_requests:
                user = Users.query.get(request.requestedBy)
                user_details = {
                    "userID": user.userID,
                    "userFullName": f"{user.firstName} {user.lastName}",
                    "username": user.username,
                }
                project_data = ProjectsData.query.get(request.projectID)
                print("Project Data: ", project_data.category)   
                project_details = {
                    "projectID": project_data.projectID,
                    "projectName": project_data.projectName,
                    "category": project_data.category.value,
                    "status": project_data.projectStatus.value,
                }
                print("===============")
                print("region_id: ", project_data.regionID)
                # region_acc = RegionAccount.query.filter_by(regionID=case_data.regionID).first()
                region_acc = RegionAccount.query.filter_by(regionID=project_data.regionID).first()
                print("Account Name: ", region_acc.accountName)
                region_acc_details = {
                    "accountName": region_acc.accountName,
                    "availableFund": float(region_acc.availableFund),
                }
                # paymentList = case_data.status_data.data.get("paymentsList", [])
                # print("print project status", project_data.status_data)
                paymentList = project_data.status_data.data.get("paymentsList", [])
                print(paymentList)
                paymentsList_ = []
                for index, item in enumerate(paymentList):
                    paymentsList_.append({"paymentNum": index + 1, "amount": item})
                
                print(paymentsList_)
                request_details = {
                    "requestID": request.requestID,
                    "project": project_details,
                    "requestedBy": user_details,
                    "fundsRequested": request.fundsRequested,
                    "createdAt": request.createdAt.isoformat(),
                    "approved": request.approved,
                    "approvedAt": (
                        request.approvedAt.isoformat() if request.approvedAt else None
                    ),
                    "receivedAmount": f"{request.approvedAmount}/{request.fundsRequested}",
                    "regionName": Regions.query.get(project_data.regionID).regionName,
                    "region_account_details": region_acc_details,
                    "approved_funding": f"${project_data.approvedPayments}/${project_data.status_data.data.get('approvedFunding', 0)}",
                    "paymentCount": f"{request.paymentCount}/{project_data.status_data.data.get('paymentCount', 0)}",
                    "bulkName": "-",
                    "paymentDueDate": f"{project_data.dueDate}",
                    "projectScope": f"{project_data.status_data.data.get('projectScope', '-')}",
                    "status": request.status,
                    "paymentList": paymentsList_,
                }

                project_requests_data.append(request_details)

            return {
                "case_requests": case_requests_data,
                "project_requests": project_requests_data,
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting fund release requests: {str(e)}")
            return {
                "message": f"Error getting fund release requests: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR





# @finance_namespace.route("/transfer_to_user_budget")
# class TransferToUserBudget(Resource):
#     @jwt_required()
#     @finance_namespace.expect(transfer_to_user_budget_model)
#     def post(self):
#         try:
            
#             request_data = request.json

#             user = Users.query.get_or_404(request_data["userID"])
            
#             existing_budget = UserBudget.query.filter_by(userID=user.userID).first()
#             if not existing_budget:
#                 budget = UserBudget(
#                     userID=user.userID,
#                     currencyID= request_data["currencyID"]
#                 )

#                 budget.save()
#                 budget.add_fund(request_data['amount'])
#             else:
#                 existing_budget.add_fund(request_data['amount'])

#             return {
#                 "message": "Transfer made successfully.",
#                 "budget_details": budget.get_fund_balance(),
#             }, HTTPStatus.OK

#         except Exception as e:
#             current_app.logger.error(f"Error adding request: {str(e)}")
#             return {
#                 "message": f"Error adding request: {str(e)}"
#             }, HTTPStatus.INTERNAL_SERVER_ERROR




        # except ValueError as ve:
        #     return {'error': str(ve)}, 400
        # except Exception as e:
        #     return {'error': f'An unexpected error occurred: {str(e)}'}, 500

# @finance_namespace.route("/transfer_to_user_budget2")
# @finance_namespace.route('/transfer_to_user_budget2')
# class TransferToUserBudget2(Resource):
#     @jwt_required()
#     @finance_namespace.expect(user_transfer_model)
#     def post(self):
#         data = finance_namespace.payload

#         from_type = data.get('fromType')
#         from_id = data.get('fromID')
#         to_user_id = data.get('toUserID')
#         amount = data.get('amount')
#         currency_id = data.get('currencyID')
#         transfer_type = data.get('transferType', 'Transfer')
#         notes = data.get('notes', '')

#         # Validate request data
#         if from_type not in ['user', 'fund']:
#             return {'error': 'Invalid fromType'}, 400

#         try:
#             # Retrieve the recipient's UserBudget
#             to_budget = UserBudget.query.filter_by(userID=to_user_id, currencyID=currency_id).first()
#             if not to_budget:
#                 return {'error': 'Target user budget not found'}, 404

#             if from_type == 'user':
#                 # Transfer from another user's budget
#                 from_budget = UserBudget.query.filter_by(userID=from_id, currencyID=currency_id).first()
#                 if not from_budget:
#                     return {'error': 'Source user budget not found'}, 404

#                 # Perform the transfer
#                 from_budget.transfer_fund(to_budget, amount, currency_id, transfer_type, notes)

#             elif from_type == 'fund':
#                 # Transfer from a FinancialFund
#                 from_fund = FinancialFund.query.get(from_id)
#                 if not from_fund:
#                     return {'error': 'Source fund not found'}, 404

#                 # Perform the transfer from the fund
#                 from_fund.transfer_to_user(to_budget, amount, currency_id, transfer_type, notes)

#             return {'message': 'Transfer successful'}, 200

#         except ValueError as ve:
#             return {'error': str(ve)}, 400
#         except Exception as e:
#             return {'error': f'An unexpected error occurred: {str(e)}'}, 500



@finance_namespace.route("/release_project_fund_requested")
class ReleaseProjectFundResource(Resource):
    @jwt_required()
    @finance_namespace.expect(approve_p_fund_release_request)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            post_data = request.json

            approval = ProjectFundReleaseApproval(
                requestID=post_data["requestID"],
                approvedBy=current_user.userID,
                approvedAmount=post_data["approvedAmount"],
                accountID=post_data["accountID"],
                fundID=post_data["fundID"],
                notes=post_data["notes"],
            )
            approval.save()

            project_request = ProjectFundReleaseRequests.query.get_or_404(
                post_data["requestID"]
            )
            project_request.status = "Awaiting Approval (Submit Docs)"
            project_request.approvedAmount = post_data["approvedAmount"]
            db.session.commit()

            return {"message": "Project Funds released successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error releasing project funds: {str(e)}")
            return {
                "message": f"Error releasing project funds: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/release_case_fund_requested")
class ReleaseCaseFundResource(Resource):
    @jwt_required()
    @finance_namespace.expect(approve_c_fund_release_request)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            post_data = request.json

            approval = CaseFundReleaseApproval(
                requestID=post_data["requestID"],
                approvedBy=current_user.userID,
                approvedAmount=post_data["approvedAmount"],
                accountID=post_data["accountID"],
                fundID=post_data["fundID"],
                notes=post_data["notes"],
            )
            approval.save()

            case_request = CaseFundReleaseRequests.query.get_or_404(
                post_data["requestID"]
            )
            case_request.status = "Awaiting Approval (Submit Docs)"
            case_request.approvedAmount = post_data["approvedAmount"]
            db.session.commit()

            return {"message": "Case Funds released successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error releasing case funds: {str(e)}")
            return {
                "message": f"Error releasing case funds: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/update_case_fund_request_status/<int:requestID>/<string:status>"
)
class UpdateCFundReleaseStatus(Resource):
    @jwt_required()
    def put(self, requestID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = CaseFundReleaseRequests.query.get_or_404(requestID)

            request.status = status
            db.session.commit()

            return {"message": "Request status updated successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating request status: {str(e)}")
            return {
                "message": f"Error updating request status: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/update_project_fund_request_status/<int:requestID>/<string:status>"
)
class UpdatePFundReleaseStatus(Resource):
    @jwt_required()
    def put(self, requestID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = ProjectFundReleaseRequests.query.get_or_404(requestID)

            request.status = status
            db.session.commit()

            return {"message": "Request status updated successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating request status: {str(e)}")
            return {
                "message": f"Error updating request status: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/approve_case_fund_request/<int:requestID>/yes_or_no/<string:decision>"
)
class ApproveCaseFundReq(Resource):
    @jwt_required()
    def put(self, requestID, decision):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = CaseFundReleaseRequests.query.get_or_404(requestID)
            approval = CaseFundReleaseApproval.query.filter_by(
                requestID=request.requestID
            ).first()

            if decision == "yes":
                request.approved = True
                request.status = f"Approved - Track ApprovalID {approval.approvalID}"
                approval.status = "Approved"
            else:
                request.approved = False
                approval.status = "Rejected"
                request.status = "Rejected"

            db.session.commit()

            return {"message": "Request approved successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error approving request: {str(e)}")
            return {
                "message": f"Error approving request: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/approve_project_fund_request/<int:requestID>/yes_or_no/<string:decision>"
)
class ApproveProjectFundReq(Resource):
    @jwt_required()
    def put(self, requestID, decision):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            request = ProjectFundReleaseRequests.query.get_or_404(requestID)
            approval = ProjectFundReleaseApproval.query.filter_by(
                requestID=request.requestID
            ).first()

            if decision == "yes":
                request.approved = True
                request.status = f"Approved - Track ApprovalID {approval.approvalID}"
                approval.status = "Approved"
            else:
                request.approved = False
                approval.status = "Rejected"
                request.status = "Rejected"

            db.session.commit()

            return {"message": "Request approved successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error approving request: {str(e)}")
            return {
                "message": f"Error approving request: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/get_all_fund_release_approvals")
class GetFundReleaseHistory(Resource):
    @jwt_required()
    def get(self):
        try:
            case_approvals = CaseFundReleaseApproval.query.order_by(
                desc(CaseFundReleaseApproval.approvedAt)
            ).all()
            project_approvals = ProjectFundReleaseApproval.query.order_by(
                desc(ProjectFundReleaseApproval.approvedAt)
            ).all()

            case_approvals_data = []
            for approval in case_approvals:
                user = Users.query.get(approval.approvedBy)
                user_details = {
                    "userID": user.userID,
                    "userFullName": f"{user.firstName} {user.lastName}",
                    "username": user.username,
                }
                request = CaseFundReleaseRequests.query.get(approval.requestID)
                case_data = CasesData.query.get(request.caseID)
                case_details = {
                    "caseID": case_data.caseID,
                    "caseName": case_data.caseName,
                    "category": case_data.category.value,
                    "status": case_data.caseStatus.value,
                }

                approval_details = {
                    "approvalID": approval.approvalID,
                    "case": case_details,
                    "approvedBy": user_details,
                    "approvedAmount": approval.approvedAmount,
                    "approvedAt": approval.approvedAt.isoformat(),
                    "notes": approval.notes,
                    "status": approval.status,
                    "closed": approval.closed,
                }

                case_approvals_data.append(approval_details)

            project_approvals_data = []
            for approval in project_approvals:
                user = Users.query.get(approval.approvedBy)
                user_details = {
                    "userID": user.userID,
                    "userFullName": f"{user.firstName} {user.lastName}",
                    "username": user.username,
                }
                request = ProjectFundReleaseRequests.query.get(approval.requestID)
                project_data = ProjectsData.query.get(request.projectID)
                project_details = {
                    "projectID": project_data.projectID,
                    "projectName": project_data.projectName,
                    "category": project_data.category.value,
                    "status": project_data.projectStatus.value,
                }

                approval_details = {
                    "approvalID": approval.approvalID,
                    "project": project_details,
                    "approvedBy": user_details,
                    "approvedAmount": approval.approvedAmount,
                    "approvedAt": approval.approvedAt.isoformat(),
                    "notes": approval.notes,
                    "status": approval.status,
                    "closed": approval.closed,
                }

                project_approvals_data.append(approval_details)

            return {
                "case_approvals": case_approvals_data,
                "project_approvals": project_approvals_data,
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting fund release approvals: {str(e)}")
            return {
                "message": f"Error getting fund release approvals: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/update_project_fund_approval_status/<int:approvalID>/<string:status>"
)
class UpdatePFundApprovalStatus(Resource):
    @jwt_required()
    def put(self, approvalID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = ProjectFundReleaseApproval.query.get_or_404(approvalID)

            approval.status = status
            db.session.commit()

            return {"message": "Approval status updated successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating approval status: {str(e)}")
            return {
                "message": f"Error updating approval status: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/update_case_fund_approval_status/<int:approvalID>/<string:status>"
)
class UpdateCFundApprovalStatus(Resource):
    @jwt_required()
    def put(self, approvalID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = CaseFundReleaseApproval.query.get_or_404(approvalID)

            approval.status = status
            db.session.commit()

            return {"message": "Approval status updated successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating approval status: {str(e)}")
            return {
                "message": f"Error updating approval status: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route(
    "/update_fund_transfer_status/<int:transferID>/<string:status>"
)
class UpdateFundTransferStatus(Resource):
    @jwt_required()
    def put(self, transferID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            transfer = FundTransfers.query.get_or_404(transferID)

            transfer.status = status
            db.session.commit()

            return {"message": "Transfer status updated successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating transfer status: {str(e)}")
            return {
                "message": f"Error updating transfer status: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/update_donation_status/<int:donationID>/<string:status>")
class UpdateDonationStatus(Resource):
    @jwt_required()
    def put(self, donationID, status):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            donation = Donations.query.get_or_404(donationID)

            donation.status = status
            db.session.commit()

            return {"message": "Donation status updated successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error updating donation status: {str(e)}")
            return {
                "message": f"Error updating donation status: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/close_case_fund_release_approval/<int:approvalID>")
class CloseCFundReleaseApproval(Resource):
    @jwt_required()
    def put(self, approvalID):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = CaseFundReleaseApproval.query.get_or_404(approvalID)

            approval.closed = True
            approval.status = "Closed"
            db.session.commit()

            from_fund = FinancialFund.query.get_or_404(approval.fundID)
            region_account = RegionAccount.query.get_or_404(approval.accountID)

            # spend money
            from_fund.use_fund(approval.approvedAmount, 1)

            request = CaseFundReleaseRequests.query.get(approval.requestID)
            case = CasesData.query.get(request.caseID)

            # spend money from region_account
            # use_fund(self, amount, currencyID=None, transaction_subtype=None, projectID=None, caseID=None, payment_number=None, category=None)
            # since cases do not have a scope, I made category to be none
            region_account.use_fund(
                approval.approvedAmount,
                1,
                "case_payment",
                None,
                case.caseID,
                request.paymentCount,
                None,
            )
            
            case.approvedPayments += approval.approvedAmount
            db.session.commit()

            return {"message": "Approval closed successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error closing approval: {str(e)}")
            return {
                "message": f"Error closing approval: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/close_project_fund_release_approval/<int:approvalID>")
class ClosePFundReleaseApproval(Resource):
    @jwt_required()
    def put(self, approvalID):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            approval = ProjectFundReleaseApproval.query.get_or_404(approvalID)

            approval.closed = True
            approval.status = "Closed"
            db.session.commit()

            from_fund = FinancialFund.query.get_or_404(approval.fundID)
            region_account = RegionAccount.query.get_or_404(approval.accountID)

            # spend money from fund account
            from_fund.use_fund(approval.approvedAmount, 1)

            # get the project scope
            request = ProjectFundReleaseRequests.query.get(approval.requestID)
            project = ProjectsData.query.get(request.projectID)
            scope = project.status_data.data["projectScope"]

            # spend money from region_account
            # use_fund(self, amount, currencyID=None, transaction_subtype=None, projectID=None, caseID=None, payment_number=None, category=None)
            region_account.use_fund(
                approval.approvedAmount,
                1,
                "project_payment",
                project.projectID,
                None,
                request.paymentCount,
                scope,
            )
            
            project.approvedPayments += approval.approvedAmount
            db.session.commit()

            return {"message": "Approval closed successfully."}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error closing approval: {str(e)}")
            return {
                "message": f"Error closing approval: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


# @finance_namespace.route("/get_all_donors")
# class GetAllDonorsResource(Resource):
#     @jwt_required()
#     def get(self):
#         try:

#             donors = Donor.query.all()

#             donors_data = []
#             for donor in donors:
#                 donations = (
#                     Donations.query.filter_by(donorID=donor.donorID)
#                     .order_by(desc(Donations.createdAt))
#                     .all()
#                 )
#                 donations_data = []
#                 total_donation_amount = 0
#                 latest_donation = None  # Initialize latest_donation variable
#                 for donation in donations:
#                     fund = FinancialFund.query.get(donation.fundID)
#                     fund_details = {
#                         "fundID": fund.fundID,
#                         "fundName": fund.fundName,
#                         "totalFund": fund.totalFund,
#                     }
#                     account = RegionAccount.query.get(donation.accountID)
#                     account_details = {
#                         "accountID": account.accountID,
#                         "accountName": account.accountName,
#                         "totalFund": float(account.totalFund),
#                     }
#                     if donation.projectID is not None:
#                         project = ProjectsData.query.get(donation.projectID)
#                     else:
#                         project = None
#                     if donation.caseID is not None:
#                         case = CasesData.query.get(donation.caseID)
#                     else:
#                         case = None
#                     donations_details = {
#                         "donationID": donation.id,
#                         "fund_account_details": fund_details,
#                         "region_account_details": account_details,
#                         "details": donation.details,
#                         "currency": Currencies.query.get(
#                             donation.currencyID
#                         ).currencyCode,
#                         "projectScope": donation.projectScope.value,
#                         "donationType": donation.donationType.value,
#                         "amount": donation.amount,
#                         "allocationTags": donation.allocationTags,
#                         "createdAt": donation.createdAt.isoformat(),
#                         "project": project.serialize() if project else None,
#                         "case": case.serialize() if case else None,
#                     }
#                     donations_data.append(donations_details)
#                     total_donation_amount += donation.amount
#                     if latest_donation is None or donation.createdAt > latest_donation:
#                         latest_donation = donation.createdAt

#                 # Fetch cases and projects the donor has contributed to
#                 cases = (
#                     CasesData.query.join(
#                         Donations, CasesData.caseID == Donations.caseID
#                     )
#                     .filter(
#                         Donations.donorID == donor.donorID, Donations.caseID.isnot(None)
#                     )
#                     .all()
#                 )

#                 projects = (
#                     ProjectsData.query.join(
#                         Donations, ProjectsData.projectID == Donations.projectID
#                     )
#                     .filter(
#                         Donations.donorID == donor.donorID,
#                         Donations.projectID.isnot(None),
#                     )
#                     .all()
#                 )
#                 projects_ = []
#                 project_statuses = ProjectsData.query.filter(
#                     ProjectsData.projectStatus == "APPROVED",                  # Approved projects only
#                     ProjectsData.status_data != None,                          # Ensure status_data exists
#                 ).all()

#                 print(str(project_statuses))

#                 # for project_st in project_statuses:
#                 #     print(f"Project ID: {project_st.projectID}, status_data: {project_st.status_data}, type: {type(project_st.status_data)}")

#                 # for case_st in case_statuses:
#                 #     print(f"Case ID: {case_st.caseID}, status_data: {case_st.status_data}, type: {type(case_st.status_data)}")


#                 # for project_st in project_statuses:
#                 #     try:
#                 #         if project_st.status_data and "donorNames" in project_st.status_data:
#                 #             if donor.donorName in project_st.status_data["donorNames"]:
#                 #                 projects_.append(project_st)
#                 #     except Exception as e:
#                 #         print(f"Error processing project {project_st.projectID}: {e}")

#                 for project_st in project_statuses:
#                     try:
#                         if project_st.status_data and project_st.status_data.data:
#                             status_data = project_st.status_data.data

#                             # Check if donorNames exists and matches the donor name
#                             if "donorNames" in status_data and donor.donorName in status_data["donorNames"]:
#                                 projects_.append(project_st)
#                     except Exception as e:
#                         print(f"Error processing project {project_st.projectID}: {e}")


#                 cases_ = []
#                 # Fetch approved cases with valid status_data
#                 case_statuses = CasesData.query.filter(
#                         CasesData.caseStatus == "APPROVED",
#                         # CasesData.status_data!= None,  # Correct usage
#                         CaseStatusData.data.isnot(None)  # Correct usage
#                 ).all()

#                 for case_st in case_statuses:
#                     try:
#                         if case_st.case_status_data:
#                             for status in case_st.case_status_data:
#                                 if status.data and "donorNames" in status.data:
#                                     if donor.donorName in status.data["donorNames"]:
#                                         cases_.append(case_st)
#                                         break
#                         else:
#                             print(f"Case ID {case_st.caseID} has no status_data.")
#                     except Exception as e:
#                         print(f"Error processing case {case_st.caseID}: {e}")

#                 all_projects = list(set(projects + projects_))
#                 all_cases = list(set(cases + cases_))

#                 donor_info = donor.get_donor_info()
#                 donor_info["totalDonationAmount"] = total_donation_amount
#                 donor_info["donations"] = donations_data
#                 donor_info["latestDonation"] = (
#                     latest_donation.strftime("%d %b %Y") if latest_donation else None
#                 )  # Format latest_donation as "20 Sept 2023"
#                 donor_info["cases"] = ([case.serialize() for case in all_cases],)
#                 donor_info["projects"] = [
#                     project.serialize() for project in all_projects
#                 ]
#                 donors_data.append(donor_info)

#             return {"donors": donors_data}, HTTPStatus.OK

#         except Exception as e:
#             current_app.logger.error(f"Error getting all donors: {str(e)}")
#             return {
#                 "message": f"Error getting all donors: {str(e)}"
#             }, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route("/get_all_donors")
class GetAllDonorsResource(Resource):
    @jwt_required()
    def get(self):
        try:
            # Fetch all donors
            donors = Donor.query.all()
            donors_data = []

            for donor in donors:
                # Fetch all donations for this donor
                donations = (
                    Donations.query.filter_by(donorID=donor.donorID)
                    .order_by(desc(Donations.createdAt))
                    .all()
                )

                # Serialize donation details
                donations_data = [donation.track_serialize() for donation in donations]

                # Calculate total donation amount and find the latest donation date
                total_donation_amount = sum(donation["amount"] for donation in donations_data)
                latest_donation = max(
                    (donation["createdAt"] for donation in donations_data), default=None
                )

                # Fetch projects and cases related to the donor
                cases = (
                    CasesData.query.join(
                        Donations, CasesData.caseID == Donations.caseID
                    )
                    .filter(
                        Donations.donorID == donor.donorID, Donations.caseID.isnot(None)
                    )
                    .all()
                )

                projects = (
                    ProjectsData.query.join(
                        Donations, ProjectsData.projectID == Donations.projectID
                    )
                    .filter(
                        Donations.donorID == donor.donorID,
                        Donations.projectID.isnot(None),
                    )
                    .all()
                )

                # Combine case and project data
                donor_info = donor.get_donor_info()
                donor_info.update({
                    "totalDonationAmount": total_donation_amount,
                    "latestDonation": latest_donation,
                    "donations": donations_data,
                    "cases": [case.serialize() for case in cases],
                    "projects": [project.serialize() for project in projects],
                })

                donors_data.append(donor_info)

            return {"donors": donors_data}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting all donors: {str(e)}")
            return {
                "message": f"Error getting all donors: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

@finance_namespace.route("/donors/get/single/<int:donorID>")
class GetSingleDonorResource(Resource):
    @jwt_required()
    def get(self, donorID):
        try:
            donor = Donor.query.get_or_404(donorID)
            return donor.serialize(), HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting donor: {str(e)}")
            return {
                "message": f"Error getting donor: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/reports/create")
class AddReportResource(Resource):
    @jwt_required()
    @finance_namespace.expect(reports_data_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            report_data = request.json

            new_report = Reports(
                title=report_data["title"],
                reportTag=report_data["reportTag"],
                createdBy=report_data.get(
                    "createdBy", f"{current_user.firstName} {current_user.lastName}"
                ),
                type=report_data["type"],
                reportId=report_data["reportId"],
                pdfUrl=report_data["pdfUrl"],
            )

            new_report.save()

            return {"message": "Report added successfully."}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error adding report: {str(e)}")
            return {
                "message": f"Error adding report: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/reports/all")
class GetAllReports(Resource):
    @jwt_required()
    def get(self):
        try:
            reports = Reports.query.order_by(desc(Reports.dateCreated)).all()

            reports_data = []
            for report in reports:
                report_details = {
                    "reportID": report.id,
                    "title": report.title,
                    "reportTag": report.reportTag,
                    "createdAt": report.dateCreated.isoformat(),
                    "createdBy": report.createdBy,
                    "reportIdentity": report.reportId,
                    "pdfUrl": report.pdfUrl,
                    "type": report.type,
                }
                reports_data.append(report_details)

            return {"all_reports": reports_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all reports: {str(e)}")
            return {
                "message": f"Error getting all reports: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/reports/by_tag/<string:reportTag>")
class GetReportByTag(Resource):
    @jwt_required()
    def get(self, reportTag):
        try:
            reports = (
                Reports.query.filter_by(reportTag=reportTag)
                .order_by(desc(Reports.dateCreated))
                .all()
            )

            reports_data = []
            for report in reports:
                report_details = {
                    "reportID": report.id,
                    "title": report.title,
                    "reportTag": report.reportTag,
                    "createdAt": report.dateCreated.isoformat(),
                    "createdBy": report.createdBy,
                    "reportIdentity": report.reportId,
                    "pdfUrl": report.pdfUrl,
                    "type": report.type,
                }
                reports_data.append(report_details)

            return {"all_reports": reports_data}, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all reports: {str(e)}")
            return {
                "message": f"Error getting all reports: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route("/reports/by_string_id/<string:reportId>")
class GetReportByTag(Resource):
    @jwt_required()
    def get(self, reportId):
        try:
            report = Reports.query.filter_by(reportId=reportId).first()

            report_details = {
                "reportID": report.id,
                "title": report.title,
                "reportTag": report.reportTag,
                "createdAt": report.dateCreated.isoformat(),
                "createdBy": report.createdBy,
                "reportIdentity": report.reportId,
                "pdfUrl": report.pdfUrl,
                "type": report.type,
            }

            return report_details, HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error getting all reports: {str(e)}")
            return {
                "message": f"Error getting all reports: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


#####################UserBudget######################
transfer_to_user_budget_model = user_budget_namespace.model('TransferToUserBudget', {
    'userID': fields.Integer(required=True, description='The ID of the user'),
    'currencyID': fields.Integer(required=True, description='The ID of the currency'),
    'amount': fields.Float(required=True, description='The amount to transfer'),
    "notes": fields.String(required=False, description="Optional notes for the transaction"),
})

# add_fund_model = finance_namespace.model("AddFundModel", {
#     "userID": fields.Integer(required=True, description="ID of the user to whom funds are added"),
#     "currencyID": fields.Integer(required=True, description="ID of the currency for the transaction"),
#     "amount": fields.Float(required=True, description="Amount to be added to the user's budget"),
    
# })

@user_budget_namespace.route("/add_balance_to_user")
class AddBalanceToUser(Resource):
    @jwt_required()
    @user_budget_namespace.expect(transfer_to_user_budget_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            # Check if the current user is an admin
            if not current_user.is_admin():
                return {
                    "message": "Access denied. Only admins are allowed to add budgets."
                }, HTTPStatus.FORBIDDEN

            request_data = request.json

            # Validate required fields
            user_id = request_data.get("userID")
            currency_id = request_data.get("currencyID")
            amount = request_data.get("amount")

            if not all([user_id, currency_id, amount]):
                return {
                    "message": "Missing required fields: userID, currencyID, or amount."
                }, HTTPStatus.BAD_REQUEST

            # Ensure amount is a positive value
            if amount <= 0:
                return {
                    "message": "Amount must be greater than zero."
                }, HTTPStatus.BAD_REQUEST

            # Retrieve the user
            user = Users.query.get_or_404(user_id)

            # Retrieve or create UserBudget for the user
            user_budget = UserBudget.query.filter_by(userID=user.userID).first()

            if not user_budget:
                # Create a new budget if it doesn't exist
                user_budget = UserBudget(userID=user.userID, currencyID=currency_id)
                user_budget.save()

            # Add funds to the budget
            user_budget.add_fund(amount)

            # Log the transaction
            transaction = UserBudgetTransaction(
                fromBudgetID=None,  # No source budget for top-up
                toBudgetID=user_budget.budgetId,
                transferAmount=amount,
                transferType="Top-up",
                currencyID=currency_id,
                notes=request_data.get("notes", f"Top-up of {amount} to {user_budget.budgetId} budget"),
                transferDate=datetime.utcnow(),
                transactionScope=TransactionScope.USER,
                status="COMPLETED",
            )
            transaction.save()

            # Return the updated fund balance and transaction details
            return {
                "message": "Transfer made successfully.",
                "budget_details": user_budget.get_fund_balance(),
                "transaction": {
                    "transactionID": transaction.transactionID,
                    "transferAmount": transaction.transferAmount,
                    "transferType": transaction.transferType,
                    "currencyID": transaction.currencyID,
                    "notes": transaction.notes,
                    "transferDate": transaction.transferDate.isoformat(),
                    "status": transaction.status,
                },
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error during transfer to user budget: {str(e)}")
            return {
                "message": f"Error during transfer to user budget: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

transfer_from_fund_model = user_budget_namespace.model(
    "TransferFromFundModel",
    {
        "fundID": fields.Integer(required=True, description="The ID of the fund to transfer from"),
        "userID": fields.Integer(required=True, description="The ID of the user to transfer to"),
        "amount": fields.Float(required=True, description="The amount to transfer"),
        "notes": fields.String(required=False, description="Optional notes for the transfer"),
    },
)

@user_budget_namespace.route("/transfer_from_fund_to_user")
class TransferFromFundToUser(Resource):
    @jwt_required()
    @user_budget_namespace.expect(transfer_from_fund_model)
    def post(self):
        try:
            current_user = Users.query.filter_by(username=get_jwt_identity()).first()
            # Check if the current user is an admin
            if not current_user.is_admin():
                return {
                    "message": "Access denied. Only admins are allowed to perform this transaction."
                }, HTTPStatus.FORBIDDEN

            request_data = request.json

            # Validate required fields
            fund_id = request_data.get("fundID")
            user_id = request_data.get("userID")
            amount = request_data.get("amount")
            notes = request_data.get("notes", "")  # Optional notes

            if not all([fund_id, user_id, amount]):
                return {
                    "message": "Missing required fields: fundID, userID, or amount."
                }, HTTPStatus.BAD_REQUEST

            # Ensure amount is a positive value
            if amount <= 0:
                return {
                    "message": "Amount must be greater than zero."
                }, HTTPStatus.BAD_REQUEST

            # Retrieve the fund
            fund = FinancialFund.query.get_or_404(fund_id)

            # Check if the fund has sufficient balance
            if fund.availableFund < amount:
                return {
                    "message": "Insufficient balance in the fund."
                }, HTTPStatus.FORBIDDEN

            # Retrieve the user receiving the transfer
            recipient_user = Users.query.get_or_404(user_id)

            # Retrieve or create the recipient's budget
            recipient_budget = UserBudget.query.filter_by(userID=recipient_user.userID).first()
            if not recipient_budget:
                recipient_budget = UserBudget(userID=recipient_user.userID, currencyID=fund.currencyID)
                recipient_budget.save()

            # Deduct the amount from the fund and add to the user's budget
            fund.availableFund -= amount
            recipient_budget.add_fund(amount)

            # Log the transaction
            transaction = UserBudgetTransaction(
                fromFundID=fund.fundID,  # Reference the fund as the source
                toBudgetID=recipient_budget.budgetId,
                transferAmount=amount,
                transferType="Fund to User",
                currencyID=fund.currencyID,
                notes=notes,
                transferDate=datetime.utcnow(),
                transactionScope=TransactionScope.USER,
                status="COMPLETED",
            )
            transaction.save()

            # Return the updated fund and recipient budget details
            return {
                "message": "Transfer from fund to user budget completed successfully.",
                "fund_details": {
                    "fundID": fund.fundID,
                    "availableFund": fund.availableFund,
                },
                "recipient_budget_details": recipient_budget.get_fund_balance(),
                "transaction": {
                    "transactionID": transaction.transactionID,
                    "fromFundID": transaction.fromFundID,
                    "toBudgetID": transaction.toBudgetID,
                    "transferAmount": transaction.transferAmount,
                    "transferType": transaction.transferType,
                    "currencyID": transaction.currencyID,
                    "notes": transaction.notes,
                    "transferDate": transaction.transferDate.isoformat(),
                    "status": transaction.status,
                },
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error during transfer from fund to user: {str(e)}")
            return {
                "message": f"Error during transfer from fund to user: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@finance_namespace.route('/transfer_to_user_budget2')
class TransferToUserBudget2(Resource):
    @jwt_required()
    @finance_namespace.expect(user_transfer_model)
    def post(self):
        data = finance_namespace.payload

        from_type = data.get('fromType')
        from_id = data.get('fromID')
        to_user_id = data.get('toUserID')
        to_fund_id = data.get('toFundID')  # New field for transferring to a fund
        amount = data.get('amount')
        currency_id = data.get('currencyID')
        transfer_type = data.get('transferType')
        notes = data.get('notes', '')



        # get the current user
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()

        # Validate request data
        if from_type not in ['user', 'fund']:
            return {'error': 'Invalid fromType'}, 400

        try:
            transfer_data = {}

            # Transfer from Fund to User Budget
            if from_type == 'fund' and to_user_id:
                from_fund = FinancialFund.query.get(from_id)
                if not from_fund:
                    return {'error': 'Source fund not found'}, 404

                to_budget = UserBudget.query.filter_by(userID=to_user_id, currencyID=currency_id).first()
                # get username of the user
                username = Users.query.get(to_user_id).username

                if not to_budget:
                    # Create the UserBudget if it does not exist
                    to_budget = UserBudget(userID=to_user_id, currencyID=currency_id, totalFund=0, usedFund=0, availableFund=0)
                    db.session.add(to_budget)

                # Perform the transfer from the fund to the user budget
                transfer_id = from_fund.transfer_to_user(to_budget, amount, currency_id, current_user.userID,  transfer_type, notes)

                # Check after transfer
                db.session.refresh(to_budget)  # Refresh to see the latest state from the DB
                transfer_data = {
                    'from': {
                        'type': 'fund',
                        'fundID': from_id,
                        'currencyID': currency_id,
                        'amount': from_fund.availableFund,
                    },
                    'to': {
                        'type': 'user',
                        'userID': to_user_id,
                        'username': username,
                        'currencyID': currency_id,
                        'amount': to_budget.availableFund,
                    },
                    'amount_transferred': amount,
                    'currencyID': currency_id,
                    'transfer_type': transfer_type,
                    'notes': notes,
                    'transferID': transfer_id,
                }

            # Transfer from Fund to another Fund
            elif from_type == 'fund' and to_fund_id:
                from_fund = FinancialFund.query.get(from_id)
                if not from_fund:
                    return {'error': 'Source fund not found'}, 404

                to_fund = FinancialFund.query.get(to_fund_id)
                if not to_fund:
                    return {'error': 'Destination fund not found'}, 404

                # Perform the transfer from the fund to another fund
                transaction_id = from_fund.transfer_to_fund(to_fund, amount, currency_id, current_user.userID, transfer_type, notes)

                # Refresh to check the updated balances
                db.session.refresh(from_fund)
                db.session.refresh(to_fund)

                transfer_data = {
                    'from': {
                        'type': 'fund',
                        'fundID': from_id,
                        'currencyID': currency_id,
                        'amount': from_fund.availableFund,
                    },
                    'to': {
                        'type': 'fund',
                        'fundID': to_fund_id,
                        'currencyID': currency_id,
                        'amount': to_fund.availableFund,
                    },
                    'amount_transferred': amount,
                    'currencyID': currency_id,
                    'transfer_type': transfer_type,
                    'notes': notes,
                    'transferID': transaction_id,
                }

            return {'message': 'Transfer successful', 'transfer_data': transfer_data}, 200

        except ValueError as ve:
            return {'error': str(ve)}, 400
        except Exception as e:
            return {'error': f'An unexpected error occurred: {str(e)}'}, 500

# @finance_namespace.route("/add_fund_to_user_budget")
# class AddFundToUserBudget(Resource):
#     @jwt_required()
#     @finance_namespace.expect(add_fund_model)  # Define this model with required fields such as userID, currencyID, amount, and notes (optional)
#     def post(self):
#         try:
#             request_data = request.json

#             # Retrieve the user and their budget
#             user = Users.query.get_or_404(request_data["userID"])
#             budget = UserBudget.query.filter_by(userID=user.userID).first()

#             # If no existing budget, create a new one
#             if not budget:
#                 budget = UserBudget(
#                     userID=user.userID,
#                     currencyID=request_data["currencyID"]
#                 )
#                 budget.save()

#             # Add funds to the budget
#             budget.add_fund(request_data["amount"])

#             # Create a transaction record
#             transaction = UserBudgetTransaction(
#                 fromBudgetID=None,
#                 toBudgetID=budget.budgetId,
#                 transferAmount=request_data["amount"],
#                 transferType="Top-up",
#                 currencyID=request_data["currencyID"],
#                 notes=request_data.get("notes", "")
#             )
#             transaction.save()

#             return {
#                 "message": "Fund added successfully.",
#                 "budget_details": budget.get_fund_balance(),
#             }, HTTPStatus.OK

#         except Exception as e:
#             current_app.logger.error(f"Error adding fund: {str(e)}")
#             return {
#                 "message": f"Error adding fund: {str(e)}"
#             }, HTTPStatus.INTERNAL_SERVER_ERROR

use_fund_model = user_budget_namespace.model("UseFundModel", {
    "userID": fields.Integer(required=True, description="ID of the user whose budget will be deducted"),
    "amount": fields.Float(required=True, description="Amount to be used from the user's budget"),
    "notes": fields.String(required=False, description="Optional notes for the transaction"),
})
@user_budget_namespace.route("/withdrawal_fund_from_user")
class WithdrawalFundFromUser(Resource):
    @jwt_required()
    @finance_namespace.expect(use_fund_model)  # Define this model with required fields such as userID, amount, and notes (optional)
    def post(self):
        try:
            request_data = request.json

            # Retrieve the user's budget
            user = Users.query.get_or_404(request_data["userID"])
            budget = UserBudget.query.filter_by(userID=user.userID).first()

            if not budget:
                return {
                    "message": "User budget not found."
                }, HTTPStatus.NOT_FOUND

            # Use funds from the budget
            budget.use_fund(request_data["amount"])

            # Create a transaction record
            transaction = UserBudgetTransaction(
                fromBudgetID=budget.budgetId,
                toBudgetID=None,
                transferAmount=request_data["amount"],
                transferType="Withdrawal",
                currencyID=budget.currencyID,
                notes=request_data.get("notes", ""),
                transactionScope=TransactionScope.USER,
                status="COMPLETED",
            )
            transaction.save()

            return {
                "message": "Fund used successfully.",
                "budget_details": budget.get_fund_balance(),
            }, HTTPStatus.OK

        except ValueError as e:
            return {
                "message": str(e)
            }, HTTPStatus.BAD_REQUEST
        except Exception as e:
            current_app.logger.error(f"Error using fund: {str(e)}")
            return {
                "message": f"Error using fund: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@user_budget_namespace.route("/user_budget_transaction_history/<int:user_id>")
class UserBudgetTransactionHistory(Resource):
    @jwt_required()
    def get(self, user_id):
        try:
            # Retrieve the user and their budget
            user = Users.query.get_or_404(user_id)
            budget = UserBudget.query.filter_by(userID=user.userID).first()

            if not budget:
                return {
                    "message": "User budget not found."
                }, HTTPStatus.NOT_FOUND

            # Retrieve transaction history for the budget
            transactions = UserBudgetTransaction.query.filter(
                (UserBudgetTransaction.fromBudgetID == budget.budgetId) |
                (UserBudgetTransaction.toBudgetID == budget.budgetId)
            ).all()

            # Helper function to retrieve user details by budget ID
            def get_user_by_budget_id(budget_id):
                if budget_id is None:
                    return None
                budget = UserBudget.query.get(budget_id)
                if budget:
                    user = Users.query.get(budget.userID)
                    return {"userID": user.userID, "username": user.username} if user else None
                return None

            # Format the transaction history
            transaction_history = [
                {
                    "transactionID": txn.transactionID,
                    "fromUser": get_user_by_budget_id(txn.fromBudgetID),  # User details for fromBudgetID
                    "toUser": get_user_by_budget_id(txn.toBudgetID),      # User details for toBudgetID
                    "transferAmount": txn.transferAmount,
                    "transferType": txn.transferType,
                    "currencyID": txn.currencyID,
                    "notes": txn.notes,
                    "transferDate": txn.transferDate.isoformat()
                }
                for txn in transactions
            ]

            return {
                "message": "Transaction history retrieved successfully.",
                "transaction_history": transaction_history
            }, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error retrieving transaction history: {str(e)}")
            return {
                "message": f"Error retrieving transaction history: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


@user_budget_namespace.route("/get_all_users_budget")
class GetAllUsersBudget(Resource):
    @jwt_required()
    def get(self):
        try:
            users = Users.query.all()
            users_budget = []
            for user in users:
                user_budget = UserBudget.query.filter_by(userID=user.userID).first()
                if user_budget:
                    user_data = {
                        "userID": user.userID,
                        "userFullName": f"{user.firstName} {user.lastName}",
                        "username": user.username,
                        "budget": user_budget.get_fund_balance(),
                    }
                    users_budget.append(user_data)
            return {"users_budget": users_budget}, HTTPStatus.OK

        except Exception as e:
            current_app.logger.error(f"Error getting users budget: {str(e)}")
            return {
                "message": f"Error getting users budget: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR
