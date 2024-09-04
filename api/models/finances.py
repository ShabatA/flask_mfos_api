from api.models.cases import CasesData
from api.models.projects import ProjectsData
from api.models.users import Users
from ..utils.db import db
from enum import Enum
from datetime import datetime
from flask import jsonify
from http import HTTPStatus
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from sqlalchemy import desc


class Currencies(db.Model):
    __tablename__ = "currencies"

    currencyID = db.Column(db.Integer, primary_key=True)
    currencyCode = db.Column(
        db.String(3), unique=True, nullable=False
    )  # e.g., 'USD', 'EUR'
    currencyName = db.Column(db.String(50), nullable=False)  # e.g., 'US Dollar', 'Euro'
    exchangeRateToUSD = db.Column(db.Float, nullable=False)  # Exchange rate to USD
    lastUpdated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Ensure USD is always present as the default currency
    @staticmethod
    def initialize_defaults():
        if not Currencies.query.filter_by(currencyCode="USD").first():
            usd_currency = Currencies(
                currencyCode="USD",
                currencyName="US Dollar",
                exchangeRateToUSD=1.0,
                lastUpdated=datetime.utcnow(),
            )
            db.session.add(usd_currency)
            db.session.commit()

    def convert_to_default(self, amount, default_currency_id=1):
        if self.currencyID == default_currency_id:
            return amount
        default_currency = Currencies.query.get(default_currency_id)
        if default_currency:
            amount_in_usd = amount / self.dollarRate
            return amount_in_usd * default_currency.dollarRate
        return amount

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


def add_currency(currencyCode, currencyName, exchangeRateToUSD):
    existing_currency = Currencies.query.filter_by(currencyCode=currencyCode).first()
    if existing_currency:
        existing_currency.currencyName = currencyName
        existing_currency.exchangeRateToUSD = exchangeRateToUSD
        existing_currency.lastUpdated = datetime.utcnow()
    else:
        new_currency = Currencies(
            currencyCode=currencyCode,
            currencyName=currencyName,
            exchangeRateToUSD=exchangeRateToUSD,
            lastUpdated=datetime.utcnow(),
        )
        db.session.add(new_currency)

    db.session.commit()


# Example usage to update the exchange rate of an existing currency
def update_currency_exchange_rate(currencyCode, newExchangeRateToUSD):
    currency = Currencies.query.filter_by(currencyCode=currencyCode).first()
    if currency:
        currency.exchangeRateToUSD = newExchangeRateToUSD
        currency.lastUpdated = datetime.utcnow()
        db.session.commit()
    else:
        raise ValueError(f"Currency with code {currencyCode} does not exist.")


# The category_names mapping
category_names = {
    "health": "Healthcare",
    "education": "Education Support",
    "relief": "Relief Aid",
    "shelter": "Housing",
    "sponsorship": "Sponsorship",
    "general": "General"
}


class RegionAccount(db.Model):
    __tablename__ = "region_account"

    accountID = db.Column(db.Integer, primary_key=True)
    accountName = db.Column(db.String(255), nullable=False)
    defaultCurrencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        default=1,
    )
    totalFund = db.Column(
        db.Numeric(10, 2), nullable=False, default=0
    )  # Total across all currencies
    usedFund = db.Column(
        db.Numeric(10, 2), nullable=False, default=0
    )  # Total across all currencies
    availableFund = db.Column(
        db.Numeric(10, 2), nullable=False, default=0
    )  # Total across all currencies
    lastUpdate = db.Column(
        db.DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    health_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    education_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    general_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    shelter_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    sponsorship_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    regionID = db.Column(
        db.Integer, db.ForeignKey("regions.regionID", ondelete="CASCADE")
    )

    projectsFunds = db.relationship("ProjectFunds", backref="projects_data", lazy=True)
    casesFunds = db.relationship("CaseFunds", backref="cases_data", lazy=True)
    donations = db.relationship("Donations", backref="region_account", lazy=True)
    currency_balances = db.relationship(
        "RegionAccountCurrencyBalance", backref="region_account_bal", lazy=True
    )
    transactions = db.relationship(
        "RegionAccountTransaction", backref="region_account_tran", lazy=True
    )

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def add_fund(
        self,
        amount,
        currencyID=None,
        transaction_subtype=None,
        projectID=None,
        caseID=None,
        payment_number=None,
        category=None,
    ):
        if currencyID is None:
            currencyID = self.defaultCurrencyID

        currency = Currencies.query.get(currencyID)
        if not currency:
            raise ValueError("Invalid currencyID")
        
        amount_decimal = Decimal(amount)

        amount_in_default_currency = currency.convert_to_default(
            amount, self.defaultCurrencyID
        )

        balance = RegionAccountCurrencyBalance.query.filter_by(
            accountID=self.accountID, currencyID=currencyID
        ).first()
        if not balance:
            balance = RegionAccountCurrencyBalance(
                accountID=self.accountID,
                currencyID=currencyID,
                totalFund=0,
                availableFund=0,
                usedFund=0,
            )

        balance.totalFund += amount_decimal
        balance.availableFund += amount_decimal
        balance.save()

        self.totalFund += Decimal(amount_in_default_currency)
        self.availableFund += Decimal(amount_in_default_currency)

        # Reverse the category_names dictionary to map from human-readable names to short names
        category_short_names = {v.lower(): k for k, v in category_names.items()}

        # Convert the human-readable category name to its corresponding short name
        category_key = category_short_names.get(category.lower(), None)

        if category_key:
            category_fund = CategoryFund.query.filter_by(
                accountID=self.accountID, category=category_key
            ).first()
            if not category_fund:
                category_fund = CategoryFund(
                    accountID=self.accountID, category=category_key, amount=0
                )
            category_fund.amount += Decimal(amount_in_default_currency)
            category_fund.save()

        self.save()

        transaction = RegionAccountTransaction(
            accountID=self.accountID,
            currencyID=currencyID,
            amount=amount,
            transactionType="add",
            transactionSubtype=transaction_subtype,
            projectID=projectID,
            caseID=caseID,
            paymentNumber=payment_number,
            timestamp=func.now(),
            category=category_key,
        )
        transaction.save()

    def use_fund(
        self,
        amount,
        currencyID=None,
        transaction_subtype=None,
        projectID=None,
        caseID=None,
        payment_number=None,
        category=None,
    ):
        if currencyID is None:
            currencyID = self.defaultCurrencyID

        currency = Currencies.query.get(currencyID)
        if not currency:
            raise ValueError("Invalid currencyID")

        amount_decimal = Decimal(amount)

        amount_in_default_currency = currency.convert_to_default(
            amount, self.defaultCurrencyID
        )
        amount_in_default_currency = Decimal(amount_in_default_currency)

        balance = RegionAccountCurrencyBalance.query.filter_by(
            accountID=self.accountID, currencyID=currencyID
        ).first()
        if not balance or balance.availableFund < amount:
            raise ValueError("Insufficient funds in the specified currency")

        balance.usedFund += amount_decimal
        balance.availableFund -= amount_decimal
        balance.save()

        self.usedFund += amount_in_default_currency
        self.availableFund -= amount_in_default_currency

        # Reverse the category_names dictionary to map from human-readable names to short names
        category_short_names = {v.lower(): k for k, v in category_names.items()}

        # Convert the human-readable category name to its corresponding short name
        category_key = None
        if category is not None:
            category_key = category_short_names.get(category.lower(), None)

            if category_key:
                category_fund = CategoryFund.query.filter_by(
                    accountID=self.accountID, category=category_key
                ).first()
                if (
                    not category_fund
                    or category_fund.amount < amount_in_default_currency
                ):
                    raise ValueError("Insufficient funds in the specified category")
                category_fund.amount -= amount_in_default_currency
                category_fund.save()

            self.save()

        transaction = RegionAccountTransaction(
            accountID=self.accountID,
            currencyID=currencyID,
            amount=amount,
            transactionType="use",
            transactionSubtype=transaction_subtype,
            projectID=projectID,
            caseID=caseID,
            paymentNumber=payment_number,
            timestamp=func.now(),
            category=category_key,
        )
        transaction.save()

    def get_fund_balance(self, currencyID=None):
        if currencyID is None:
            return {
                "totalFund": self.totalFund,
                "usedFund": self.usedFund,
                "availableFund": self.availableFund,
            }

        balance = RegionAccountCurrencyBalance.query.filter_by(
            accountID=self.accountID, currencyID=currencyID
        ).first()
        if balance:
            return {
                "totalFund": float(balance.totalFund),
                "usedFund": float(balance.usedFund),
                "availableFund": float(balance.availableFund),
            }

        return {"totalFund": 0, "usedFund": 0, "availableFund": 0}

    def get_scope_percentages(self):
        if self.usedFund == 0:
            # Avoid division by zero
            return {
                "Healthcare": 0,
                "Education Support": 0,
                "Relief Aid": 0,
                "Housing": 0,
                "Sponsorship": 0,
                "General": 0
            }

        # Mapping from category code name to official name
        category_names = {
            "health": "Healthcare",
            "education": "Education Support",
            "relief": "Relief Aid",
            "shelter": "Housing",
            "sponsorship": "Sponsorship",
            "general": "General"
        }

        categories = ["health", "education", "relief", "shelter", "sponsorship", "general"]
        percentages = {}

        for category in categories:
            # Sum all transactions for this category and account
            total_for_category = sum(
                transaction.amount
                for transaction in self.transactions
                if transaction.category == category
                and transaction.transactionType == "use"
            )
            # Calculate percentage
            percentage = (total_for_category / self.usedFund) * 100
            # Use the official name for the category
            official_name = category_names[category]
            rounded_perc = round(percentage, 2)
            percentages[official_name] = float(rounded_perc)  # rounding to 2 decimal places for better readability

        return percentages

    def get_available_currencies(self):
        return [
            {
                "currencyID": balance.currencyID,
                "currencyCode": balance.currency.currencyCode,
                "currencyName": balance.currency.currencyName,
            }
            for balance in self.currency_balances
        ]

    def get_account_transactions(self):
        transactions = self.transactions
        transaction_list = []
        for transaction in transactions:
            if transaction.projectID is not None:
                project = ProjectsData.query.get(transaction.projectID)
            else:
                project = None
            if transaction.caseID is not None:
                case = CasesData.query.get(transaction.caseID)
            else:
                case = None
            
            transaction_dict = {
                "transactionID": transaction.transactionID,
                "accountID": transaction.accountID,
                "currencyID": transaction.currencyID,
                "amount": float(transaction.amount),
                "transactionType": transaction.transactionType,
                "transactionSubtype": transaction.transactionSubtype,
                "projectID": transaction.projectID,
                "project": project.serialize() if project else None,
                "caseID": transaction.caseID,
                "case": case.serialize() if case else None,
                "paymentNumber": transaction.paymentNumber,
                "timestamp": transaction.timestamp.isoformat(),
            }
            transaction_list.append(transaction_dict)
        return transaction_list

    def get_category_balances(self):
        categories = CategoryFund.query.filter_by(accountID=self.accountID).all()
        category_balances = {}
        
        # Mapping from category code name to official name
        category_names = {
            "health": "Healthcare",
            "education": "Education Support",
            "relief": "Relief Aid",
            "shelter": "Housing",
            "sponsorship": "Sponsorship",
            "general": "General",
        }
        
        standard_budget_perc = {
            "health": 0.3,
            "education": 0.2,
            "relief": 0.2,
            "shelter": 0.15,
            "sponsorship": 0.1,
            "general": 0.2,
        }
        
        if len(categories) == 0:
            categories = ["health", "education", "relief", "shelter", "sponsorship", "general"]
            for category in categories:
                # Convert category code to official name
                official_name = category_names.get(category, "Unknown Category")
                category_balances[official_name] = {
                "availableFund": 0,
                "totalFund": 0,
                "usedFund": 0,
                "latestDonation": "None",
                "standard_budget": float(self.totalFund) * standard_budget_perc[category]
            }
            return category_balances


        for category_fund in categories:
            category_code = category_fund.category
            # Convert category code to official name
            official_name = category_names.get(category_code, "Unknown Category")

            # Initialize default values
            category_balances[official_name] = {
                "availableFund": float(category_fund.amount),
                "totalFund": 0,
                "usedFund": 0,
                "latestDonation": "None",
                "standard_budget": float(self.totalFund) * standard_budget_perc[category_code]
            }

            # Transactions of type 'add' for this category
            add_transactions = RegionAccountTransaction.query.filter_by(
                accountID=self.accountID, category=category_code, transactionType="add"
            ).all()
            
            use_transactions = RegionAccountTransaction.query.filter_by(
                accountID=self.accountID, category=category_code, transactionType="use"
            ).all()

            if add_transactions:
                total_fund = sum(transaction.amount for transaction in add_transactions)
                used_fund = sum(transaction.amount for transaction in use_transactions)
                latest_donation = max(
                    transaction.timestamp for transaction in add_transactions
                )
                latest_donation_formatted = latest_donation.strftime("%d %b %Y")

                category_balances[official_name].update(
                    {
                        "totalFund": float(total_fund),
                        "usedFund": float(
                            used_fund
                        ),  # Assuming usedFund is the same as totalFund for 'add' transactions
                        "latestDonation": latest_donation_formatted,
                    }
                )

        return category_balances
    
    def get_all_donations(self):
        donations = self.donations
        donation_list = []
        for donation in donations:
            if donation.projectID is not None:
                project = ProjectsData.query.get(donation.projectID)
            else:
                project = None
            if donation.caseID is not None:
                case = CasesData.query.get(donation.caseID)
            else:
                case = None
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
                "project": project.serialize() if project else None,
                "case": case.serialize() if case else None,
            }
            donation_list.append(donation_dict)
        return donation_list

class UserBudget(db.Model):
    __tablename__ = "user_budget"

    budgetId = db.Column(db.Integer, primary_key=True)
    userID = db.Column(
        db.Integer,
        db.ForeignKey("users.userID", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=False, default=0)
    availableFund = db.Column(db.Float, nullable=False, default=0)

    currency = db.relationship("Currencies")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def add_fund(self, amount):
        self.totalFund += amount
        self.availableFund += amount
        db.session.commit()

    def use_fund(self, amount):
        if self.availableFund < amount:
            raise ValueError("Insufficient funds")
        self.usedFund += amount
        self.availableFund -= amount
        db.session.commit()

    def get_fund_balance(self):
        return {
            "totalFund": self.totalFund,
            "usedFund": self.usedFund,
            "availableFund": self.availableFund,
            "currencyCode": self.currency.currencyCode,
        }

    def get_available_currencies(self):
        return {
            "currencyID": self.currencyID,
            "currencyCode": self.currency.currencyCode,
            "currencyName": self.currency.currencyName,
        }

class RegionAccountCurrencyBalance(db.Model):
    __tablename__ = "region_account_currency_balances"

    balanceID = db.Column(db.Integer, primary_key=True)
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        nullable=False,
    )
    totalFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    availableFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    usedFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    currency = db.relationship("Currencies")

    @declared_attr
    def region_account(cls):
        return db.relationship("RegionAccount", backref="curr_balances")

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


class RegionAccountTransaction(db.Model):
    __tablename__ = "region_account_transactions"

    transactionID = db.Column(db.Integer, primary_key=True)
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        nullable=False,
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transactionType = db.Column(db.String(10), nullable=False)  # 'add' or 'use'
    transactionSubtype = db.Column(
        db.String(50), nullable=True
    )  # e.g., 'project_payment', 'case_payment'
    projectID = db.Column(
        db.Integer,
        db.ForeignKey("projects_data.projectID", ondelete="CASCADE"),
        nullable=True,
    )
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=True,
    )
    paymentNumber = db.Column(db.Integer, nullable=True)  # e.g., 1, 2, 3, etc.
    timestamp = db.Column(db.DateTime, nullable=False, default=func.now())
    category = db.Column(db.String(50), nullable=True)  # 'health', 'education', etc.

    @declared_attr
    def region_account(cls):
        return db.relationship("RegionAccount", backref="account_transactions")

    @declared_attr
    def project(cls):
        return db.relationship("ProjectsData", backref="account_transactions")

    @declared_attr
    def case(cls):
        return db.relationship("CasesData", backref="account_transactions")

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


class CategoryFund(db.Model):
    __tablename__ = "category_funds"

    id = db.Column(db.Integer, primary_key=True)
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    @declared_attr
    def region_account(cls):
        return db.relationship("RegionAccount", backref="category_funds")

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


class SubFundCurrencyBalance(db.Model):
    __tablename__ = "sub_fund_currency_balances"

    id = db.Column(db.Integer, primary_key=True)
    subFundID = db.Column(
        db.Integer,
        db.ForeignKey("sub_funds.subFundID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=False, default=0)
    availableFund = db.Column(db.Float, nullable=False, default=0)

    currency = db.relationship("Currencies")
    sub_fund = db.relationship("SubFunds", back_populates="currency_balances")

    __table_args__ = (
        db.UniqueConstraint("subFundID", "currencyID", name="unique_subfund_currency"),
    )

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e


class FinancialFund(db.Model):
    __tablename__ = "financial_fund"

    fundID = db.Column(db.Integer, primary_key=True)
    fundName = db.Column(db.String(255), nullable=False)
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=True)
    accountType = db.Column(db.String(50))
    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    administrator = db.Column(
        db.Integer, db.ForeignKey("users.userID", ondelete="CASCADE"), nullable=False
    )  # the employee responsible for managing this fund
    availableFund = db.Column(db.Float, default=0)
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        default=1,
        index=True,
    )
    lastUpdate = db.Column(
        db.DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    # Relationships
    currency_balances = db.relationship(
        "FinancialFundCurrencyBalance", back_populates="financial_fund", lazy=True
    )
    donations = db.relationship("Donations", backref="financial_fund", lazy=True)
    subFunds = db.relationship("SubFunds", back_populates="financial_fund", lazy=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def add_fund(self, amount, currencyID):
        try:
            sub_fund_balance = FinancialFundCurrencyBalance.query.filter_by(
                fundID=self.fundID, currencyID=currencyID
            ).first()
            if not sub_fund_balance:
                sub_fund_balance = FinancialFundCurrencyBalance(
                    fundID=self.fundID, currencyID=currencyID
                )
                db.session.add(sub_fund_balance)

            sub_fund_balance.totalFund += amount
            sub_fund_balance.availableFund += amount

            # Convert the amount to the default currency before updating the financial fund's total and available funds
            converted_amount = self._convert_to_default_currency(amount, currencyID)
            self.totalFund += converted_amount
            self.availableFund += converted_amount

            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("An error occurred while adding funds. Please try again.")

    def use_fund(self, amount, currencyID):
        try:
            sub_fund_balance = FinancialFundCurrencyBalance.query.filter_by(
                fundID=self.fundID, currencyID=currencyID
            ).first()
            if not sub_fund_balance or sub_fund_balance.availableFund < amount:
                raise ValueError("Insufficient funds in the specified currency")

            sub_fund_balance.usedFund += amount
            sub_fund_balance.availableFund -= amount

            # Convert the amount to the default currency before updating the financial fund's used and available funds
            converted_amount = self._convert_to_default_currency(amount, currencyID)
            self.usedFund += converted_amount
            self.availableFund -= converted_amount

            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("An error occurred while using funds. Please try again.")

    def get_fund_balance(self, currencyID=None):
        if currencyID is None:
            return {
                "totalFund": self.totalFund,
                "usedFund": self.usedFund,
                "availableFund": self.availableFund,
            }

        sub_fund_balance = FinancialFundCurrencyBalance.query.filter_by(
            fundID=self.fundID, currencyID=currencyID
        ).first()
        if sub_fund_balance:
            return {
                "totalFund": sub_fund_balance.totalFund,
                "usedFund": sub_fund_balance.usedFund,
                "availableFund": sub_fund_balance.availableFund,
            }

        return {"totalFund": 0, "usedFund": 0, "availableFund": 0}

    def _convert_to_default_currency(self, amount, currencyID):
        # Implement the logic to convert amount to default currency using exchange rates
        currency = Currencies.query.get(currencyID)
        if currency:
            return (
                amount / currency.exchangeRateToUSD
            )  # Assuming exchangeRateToUSD is the exchange rate to USD
        return amount

    def get_available_currencies(self):
        return [
            {
                "currencyID": balance.currencyID,
                "currencyCode": balance.currency.currencyCode,
                "currencyName": balance.currency.currencyName,
            }
            for balance in self.currency_balances
        ]

    def get_all_sub_funds(self):
        sub_funds = self.subFunds
        sub_funds_info = []
        for sub_fund in sub_funds:
            sub_fund_info = {
                "subFundID": sub_fund.subFundID,
                "fundID": sub_fund.fundID,
                "subFundName": sub_fund.subFundName,
                "accountType": sub_fund.accountType,
                "totalFund": sub_fund.totalFund,
                "usedFund": sub_fund.usedFund,
                "availableFund": sub_fund.availableFund,
                "notes": sub_fund.notes,
                "createdAt": sub_fund.createdAt.isoformat(),
                "currencyID": sub_fund.currencyID,
            }
            sub_funds_info.append(sub_fund_info)
        return sub_funds_info

    def get_all_donations(self):
        donations = self.donations
        donation_list = []
        for donation in donations:
            if donation.projectID is not None:
                project = ProjectsData.query.get(donation.projectID)
            else:
                project = None
            if donation.caseID is not None:
                case = CasesData.query.get(donation.caseID)
            else:
                case = None
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
                "project": project.serialize() if project else None,
                "case": case.serialize() if case else None,
            }
            donation_list.append(donation_dict)
        return donation_list


class FinancialFundCurrencyBalance(db.Model):
    __tablename__ = "financial_fund_currency_balances"

    id = db.Column(db.Integer, primary_key=True)
    fundID = db.Column(
        db.Integer,
        db.ForeignKey("financial_fund.fundID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=False, default=0)
    availableFund = db.Column(db.Float, nullable=False, default=0)

    currency = db.relationship("Currencies")
    financial_fund = db.relationship(
        "FinancialFund", back_populates="currency_balances"
    )

    __table_args__ = (
        db.UniqueConstraint("fundID", "currencyID", name="unique_fund_currency"),
    )

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SubFunds(db.Model):
    __tablename__ = "sub_funds"

    subFundID = db.Column(db.Integer, primary_key=True)
    fundID = db.Column(
        db.Integer,
        db.ForeignKey("financial_fund.fundID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subFundName = db.Column(db.String(255), nullable=False)
    accountType = db.Column(db.String(50))
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=False, default=0)
    availableFund = db.Column(db.Float, nullable=False, default=0)
    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        default=1,
        index=True,
    )

    # Relationships
    currency_balances = db.relationship(
        "SubFundCurrencyBalance", back_populates="sub_fund", lazy=True
    )
    financial_fund = db.relationship("FinancialFund", back_populates="subFunds")

    def add_fund(self, amount, currencyID):
        try:
            balance = SubFundCurrencyBalance.query.filter_by(
                subFundID=self.subFundID, currencyID=currencyID
            ).first()
            if not balance:
                balance = SubFundCurrencyBalance(
                    subFundID=self.subFundID, currencyID=currencyID
                )
                db.session.add(balance)

            balance.totalFund += amount
            balance.availableFund += amount
            db.session.commit()

            # Convert the amount to the default currency before updating the subfund's total and available funds
            converted_amount = self._convert_to_default_currency(amount, currencyID)
            self.totalFund += converted_amount
            self.availableFund += converted_amount
            db.session.commit()

            # Update the parent financial fund's balances
            self.financial_fund.add_fund(amount, currencyID)
        except IntegrityError:
            db.session.rollback()
            raise ValueError("An error occurred while adding funds. Please try again.")

    def use_fund(self, amount, currencyID):
        try:
            balance = SubFundCurrencyBalance.query.filter_by(
                subFundID=self.subFundID, currencyID=currencyID
            ).first()
            if not balance or balance.availableFund < amount:
                raise ValueError("Insufficient funds in the specified currency")

            balance.usedFund += amount
            balance.availableFund -= amount
            db.session.commit()

            # Convert the amount to the default currency before updating the subfund's used and available funds
            converted_amount = self._convert_to_default_currency(amount, currencyID)
            self.usedFund += converted_amount
            self.availableFund -= converted_amount
            db.session.commit()

            # Update the parent financial fund's balances
            self.financial_fund.use_fund(amount, currencyID)
        except IntegrityError:
            db.session.rollback()
            raise ValueError("An error occurred while using funds. Please try again.")

    def get_fund_balance(self, currencyID=None):
        if currencyID is None:
            return {
                "totalFund": self.totalFund,
                "usedFund": self.usedFund,
                "availableFund": self.availableFund,
            }

        balance = SubFundCurrencyBalance.query.filter_by(
            subFundID=self.subFundID, currencyID=currencyID
        ).first()
        if balance:
            return {
                "totalFund": balance.totalFund,
                "usedFund": balance.usedFund,
                "availableFund": balance.availableFund,
            }

        return {"totalFund": 0, "usedFund": 0, "availableFund": 0}

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def _convert_to_default_currency(self, amount, currencyID):
        # Implement the logic to convert amount to default currency using exchange rates
        currency = Currencies.query.get(currencyID)
        if currency:
            return (
                amount / currency.exchangeRateToUSD
            )  # Assuming exchangeRateToUSD is the exchange rate to USD
        return amount

    def get_available_currencies(self):
        return [
            {
                "currencyID": balance.currencyID,
                "currencyCode": balance.currency.currencyCode,
                "currencyName": balance.currency.currencyName,
            }
            for balance in self.currency_balances
        ]


# Hold amounts after Project Approval, all payments must spend from this amount
class ProjectFunds(db.Model):
    __tablename__ = "project_funds"

    fundID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(
        db.Integer,
        db.ForeignKey("projects_data.projectID", ondelete="CASCADE"),
        nullable=False,
    )
    fundsAllocated = db.Column(db.Float, nullable=True)
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


# Hold amounts after Case Approval, all payments must spend from this amount
class CaseFunds(db.Model):
    __tablename__ = "case_funds"

    fundID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=False,
    )
    fundsAllocated = db.Column(db.Float, nullable=True)
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class DonorTypes(Enum):
    INDIVIDUAL = "Individual"
    ORGANIZATION = "Organization"
    COMPANY = "Company"
    GOVERNMENT = "Government"


class Donor(db.Model):
    __tablename__ = "donors"

    donorID = db.Column(db.Integer, primary_key=True)
    donorName = db.Column(db.String(255), nullable=False)
    donorType = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'individual' or 'institution'
    placeOfResidence = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    startOfRelationship = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    imageLink = db.Column(db.String, nullable=True)

    # Relationships
    representatives = db.relationship(
        "Representative",
        back_populates="donors",
        lazy=True,
        cascade="all, delete-orphan",
    )
    donations = db.relationship("Donations", backref="donors", lazy=True)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def get_donor_info(self):

        representatives = [
            {
                "name": rep.name,
                "jobPosition": rep.jobPosition,
                "email": rep.email,
                "phoneNumber": rep.phoneNumber,
            }
            for rep in self.representatives
        ]
        return {
            "donorID": self.donorID,
            "donorName": self.donorName,
            "donorType": self.donorType,
            "placeOfResidence": self.placeOfResidence,
            "phoneNumber": self.phoneNumber,
            "email": self.email,
            "startOfRelationship": self.startOfRelationship.isoformat(),
            "notes": self.notes,
            "representatives": representatives,
        }

    def serialize(self):
        donations = (
            Donations.query.filter_by(donorID=self.donorID)
            .order_by(desc(Donations.createdAt))
            .all()
        )
        donations_data = []
        total_donation_amount = 0
        latest_donation = None  # Initialize latest_donation variable
        for donation in donations:
            fund = FinancialFund.query.get(donation.fundID)
            fund_details = {
                "fundID": fund.fundID,
                "fundName": fund.fundName,
                "totalFund": fund.totalFund,
            }
            account = RegionAccount.query.get(donation.accountID)
            account_details = {
                "accountID": account.accountID,
                "accountName": account.accountName,
                "totalFund": float(account.totalFund),
            }
           
            if donation.projectID is not None:
                project = ProjectsData.query.get(donation.projectID)
            else:
                project = None
            if donation.caseID is not None:
                case = CasesData.query.get(donation.caseID)
            else:
                case = None
            donations_details = {
                "donationID": donation.id,
                "fund_account_details": fund_details,
                "region_account_details": account_details,
                "details": donation.details,
                "currency": Currencies.query.get(donation.currencyID).currencyCode,
                "projectScope": donation.projectScope.value,
                "project": project.serialize() if project else None,
                "case": case.serialize() if case else None,
                "donationType": donation.donationType.value,
                "amount": donation.amount,
                "allocationTags": donation.allocationTags,
                "createdAt": donation.createdAt.isoformat(),
            }
            donations_data.append(donations_details)
            total_donation_amount += donation.amount
            if latest_donation is None or donation.createdAt > latest_donation:
                latest_donation = donation.createdAt

            # Fetch cases and projects the donor has contributed to
        cases = (
            CasesData.query.join(Donations, CasesData.caseID == Donations.caseID)
            .filter(Donations.donorID == self.donorID, Donations.caseID.isnot(None))
            .all()
        )

        projects = (
            ProjectsData.query.join(
                Donations, ProjectsData.projectID == Donations.projectID
            )
            .filter(Donations.donorID == self.donorID, Donations.projectID.isnot(None))
            .all()
        )
        projects_ = []
        project_statuses = ProjectsData.query.filter_by(projectStatus="APPROVED").all()
        for project_st in project_statuses:
            if project_st.status_data.data.get("donorNames") is None:
                continue
            if self.donorName in project_st.status_data.data.get("donorNames"):
                projects_.append(project_st)

        cases_ = []
        case_statuses = CasesData.query.filter_by(caseStatus="APPROVED").all()
        for case_st in case_statuses:
            if case_st.status_data.data.get("donorNames") is None:
                continue
            if self.donorName in case_st.status_data.data.get("donorNames"):
                cases_.append(case_st)

        all_projects = list(set(projects + projects_))
        all_cases = list(set(cases + cases_))

        donor_info = self.get_donor_info()
        donor_info["totalDonationAmount"] = total_donation_amount
        donor_info["donations"] = donations_data
        donor_info["latestDonation"] = (
            latest_donation.strftime("%d %b %Y") if latest_donation else None
        )  # Format latest_donation as "20 Sept 2023"
        donor_info["cases"] = ([case.serialize() for case in all_cases],)
        donor_info["projects"] = [project.serialize() for project in all_projects]

        return donor_info


class Representative(db.Model):
    __tablename__ = "representatives"

    representativeID = db.Column(db.Integer, primary_key=True)
    donorID = db.Column(
        db.Integer,
        db.ForeignKey("donors.donorID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(255), nullable=False)
    jobPosition = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(50), nullable=True)
    imageLink = db.Column(db.String, nullable=True)

    # Relationships
    donors = db.relationship("Donor", back_populates="representatives")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class ProjectScopes(Enum):
    HEALTH = "Healthcare"
    SHELTER = "Housing"
    EDUCATION = "Education Support"
    GENERAL = "General"
    SPONSORSHIP = "Sponsorship"
    RELIEF = "Relief Aid"


class DonationTypes(Enum):
    PROJECT = "Project"
    CASE = "Case"
    GENERAL = "General"


class Donations(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    donorID = db.Column(
        db.Integer, db.ForeignKey("donors.donorID", ondelete="CASCADE"), nullable=False
    )
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )
    fundID = db.Column(
        db.Integer,
        db.ForeignKey("financial_fund.fundID", ondelete="CASCADE"),
        nullable=False,
    )
    amount = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    details = db.Column(db.Text, nullable=True)  # this is "notes" on the UI
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        default=1,
    )
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=True,
    )
    projectID = db.Column(
        db.Integer,
        db.ForeignKey("projects_data.projectID", ondelete="CASCADE"),
        nullable=True,
    )
    subFundID = db.Column(
        db.Integer,
        db.ForeignKey("sub_funds.subFundID", ondelete="CASCADE"),
        nullable=True,
    )
    projectScope = db.Column(db.Enum(ProjectScopes), default=ProjectScopes.GENERAL)
    allocationTags = db.Column(
        db.String
    )  # used to tag a donation made to a case/project that is not yet added to the database
    donationType = db.Column(db.Enum(DonationTypes), default=DonationTypes.GENERAL)
    closed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String, default="Initiated")

    donor = db.relationship("Donor", backref="donations_donor")
    currency = db.relationship("Currencies", backref="donations_currency")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def track_serialize(self):
        to_fund = FinancialFund.query.get(self.fundID)
        to_account = RegionAccount.query.get(self.accountID)
        balances = to_account.get_fund_balance(1)
        
        if self.projectID is None:
            project = None
        else:
            project = ProjectsData.query.get(self.projectID)

        if self.caseID is None:
            case = None
        else:
            case = CasesData.query.get(self.caseID)

        return {
            "donationID": self.id,
            "from_donor": Donor.query.get(self.donorID).get_donor_info(),
            "donorName": self.donor.donorName,
            "to_fund": {
                "fundID": to_fund.fundID,
                "fundName": to_fund.fundName,
                "balances": to_fund.get_fund_balance(1),
            },
            "to_account": {
                "accountID": to_account.accountID,
                "accountName": to_account.accountName,
                "balance": float(balances['availableFund']),
            },
            "donationType": self.donationType.value,
            "details": self.details,
            "amount": self.amount,
            "currency": self.currency.currencyCode,
            "createdAt": self.createdAt.isoformat(),
            "status": self.status,
            "closed": self.closed,
            "projectScope": self.projectScope.value,
            "case": case.serialize() if case else None,
            "project": project.serialize() if project else None,
        }


class ProjectFundReleaseRequests(db.Model):
    __tablename__ = "project_fund_release_requests"

    requestID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(
        db.Integer,
        db.ForeignKey("projects_data.projectID", ondelete="CASCADE"),
        nullable=False,
    )
    fundsRequested = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=func.now(), nullable=False)
    requestedBy = db.Column(
        db.Integer, db.ForeignKey("users.userID", ondelete="CASCADE"), nullable=False
    )
    approved = db.Column(db.Boolean, default=False)
    approvedAt = db.Column(db.DateTime, nullable=True, onupdate=func.now())
    paymentCount = db.Column(db.Integer, nullable=False)
    approvedAmount = db.Column(db.Float, nullable=False, default=0)
    bulkName = db.Column(db.String, nullable=True)
    paymentMethod = db.Column(db.String, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String, default="Awaiting Release")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CaseFundReleaseRequests(db.Model):
    __tablename__ = "case_fund_release_requests"

    requestID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(
        db.Integer,
        db.ForeignKey("cases_data.caseID", ondelete="CASCADE"),
        nullable=False,
    )
    fundsRequested = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=func.now(), nullable=False)
    requestedBy = db.Column(
        db.Integer, db.ForeignKey("users.userID", ondelete="CASCADE"), nullable=False
    )
    approved = db.Column(db.Boolean, default=False)
    approvedAt = db.Column(db.DateTime, nullable=True, onupdate=func.now())
    paymentCount = db.Column(db.Integer, nullable=False)
    approvedAmount = db.Column(db.Float, nullable=False, default=0)
    bulkName = db.Column(db.String, nullable=True)
    paymentMethod = db.Column(db.String, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String, default="Awaiting Release")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class ProjectFundReleaseApproval(db.Model):
    __tablename__ = "project_fund_release_approval"

    approvalID = db.Column(db.Integer, primary_key=True)
    requestID = db.Column(
        db.Integer,
        db.ForeignKey("project_fund_release_requests.requestID", ondelete="CASCADE"),
        nullable=False,
    )
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )
    fundID = db.Column(
        db.Integer,
        db.ForeignKey("financial_fund.fundID", ondelete="CASCADE"),
        nullable=False,
    )
    approvedBy = db.Column(
        db.Integer, db.ForeignKey("users.userID", ondelete="CASCADE"), nullable=False
    )
    approvedAmount = db.Column(db.Float, nullable=False)
    approvedAt = db.Column(db.DateTime, default=func.now())
    status = db.Column(db.String, default="Awaiting Approval", nullable=False)
    notes = db.Column(db.Text, nullable=True)
    closed = db.Column(db.Boolean, default=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    def fund_serialize(self, currencyID):
        request = ProjectFundReleaseRequests.query.get(self.requestID)
        project = ProjectsData.query.get(request.projectID)
        user = Users.query.get(self.approvedBy)
        user_details = {
            "userID": user.userID,
            "userFullName": f"{user.firstName} {user.lastName}",
            "username": user.username,
        }
        return {
            "approvalID": self.approvalID,
            "issuedBy": user_details["userFullName"],
            "project_details": {
                "projectID": project.projectID,
                "projectName": project.projectName,
                "projectStatus": project.projectStatus.value,
            },
            "approvedAmount": f'{self.approvedAmount}',
            "approvedAt": self.approvedAt.isoformat(),
            "status": self.status,
            "notes": self.notes,
            "closed": self.closed,
            "transactionType": "Credit"
        }


class CaseFundReleaseApproval(db.Model):
    __tablename__ = "case_fund_release_approval"

    approvalID = db.Column(db.Integer, primary_key=True)
    requestID = db.Column(
        db.Integer,
        db.ForeignKey("case_fund_release_requests.requestID", ondelete="CASCADE"),
        nullable=False,
    )
    accountID = db.Column(
        db.Integer,
        db.ForeignKey("region_account.accountID", ondelete="CASCADE"),
        nullable=False,
    )
    fundID = db.Column(
        db.Integer,
        db.ForeignKey("financial_fund.fundID", ondelete="CASCADE"),
        nullable=False,
    )
    approvedBy = db.Column(
        db.Integer, db.ForeignKey("users.userID", ondelete="CASCADE"), nullable=False
    )
    approvedAmount = db.Column(db.Float, nullable=False)
    approvedAt = db.Column(db.DateTime, default=func.now())
    status = db.Column(db.String, default="Awaiting Approval", nullable=False)
    notes = db.Column(db.Text, nullable=True)
    closed = db.Column(db.Boolean, default=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    def fund_serialize(self, currencyID):
        request = CaseFundReleaseRequests.query.get(self.requestID)
        case = CasesData.query.get(request.caseID)
        user = Users.query.get(self.approvedBy)
        user_details = {
            "userID": user.userID,
            "userFullName": f"{user.firstName} {user.lastName}",
            "username": user.username,
        }
        return {
            "approvalID": self.approvalID,
            "issuedBy": user_details["userFullName"],
            "case_details": {
                "caseID": case.caseID,
                "caseName": case.caseName,
                "caseStatus": case.caseStatus.value,
            },
            "approvedAmount": f'${self.approvedAmount}',
            "approvedAt": self.approvedAt.isoformat(),
            "status": self.status,
            "notes": self.notes,
            "closed": self.closed,
            "transactionType": "Credit"
        }


class TransferStage(Enum):
    ASSESSMENT = "Pending Assessment"
    ONGOING = "On Going"
    APPROVED = "Approved"


class TransferType(Enum):
    EFT = "EFT"
    CASH = "CASH"
    CHECK = "CHECK"


class FundTransfers(db.Model):
    __tablename__ = "fund_transfers"

    transferID = db.Column(db.Integer, primary_key=True)
    from_fund = db.Column(
        db.Integer, db.ForeignKey("financial_fund.fundID", ondelete="CASCADE")
    )
    to_fund = db.Column(
        db.Integer, db.ForeignKey("financial_fund.fundID", ondelete="CASCADE")
    )
    transferAmount = db.Column(db.Float, nullable=False)
    createdBy = db.Column(
        db.Integer, db.ForeignKey("users.userID", ondelete="CASCADE"), nullable=False
    )
    createdAt = db.Column(db.DateTime, default=func.now(), nullable=False)
    currencyID = db.Column(
        db.Integer,
        db.ForeignKey("currencies.currencyID", ondelete="CASCADE"),
        default=1,
    )
    notes = db.Column(db.Text)
    transferType = db.Column(db.Enum(TransferType), default=TransferType.EFT)
    closed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String, default="Initiated")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        
    def out_transfer_serialize(self, currencyID):
        to_fund = FinancialFund.query.get(self.to_fund)
        currency = Currencies.query.get(self.currencyID)
        return {
            "transferID": self.transferID,
            "to_fund": {
                "fundID": to_fund.fundID,
                "fundName": to_fund.fundName,
                "balances": to_fund.get_fund_balance(currencyID),
            },
            "transferAmount": self.transferAmount,
            "currencyName": currency.currencyName,
            "transferType": self.transferType.value,
            "notes": self.notes,
            "createdAt": self.createdAt.isoformat(),
            "status": self.status,
            "closed": self.closed,
            "transactionType": "Credit"
        }
    
    def in_transfer_serialize(self, currencyID):
        from_fund = FinancialFund.query.get(self.from_fund)
        currency = Currencies.query.get(self.currencyID)
        return {
            "transferID": self.transferID,
            "from_fund": {
                "fundID": from_fund.fundID,
                "fundName": from_fund.fundName,
                "balances": from_fund.get_fund_balance(currencyID),
            },
            "transferAmount": self.transferAmount,
            "currencyName": currency.currencyName,
            "transferType": self.transferType.value,
            "notes": self.notes,
            "createdAt": self.createdAt.isoformat(),
            "status": self.status,
            "closed": self.closed,
            "transactionType": "Debit"
        }


# class PaymentFor(Enum):
#     CASE = 'Case'
#     PROJECT = 'Project'
#     OTHER = 'Other'

# class Payments(db.Model):
#     __tablename__ = 'payments'

#     paymentID = db.Column(db.Integer, primary_key=True)
#     from_fund = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID', ondelete='CASCADE'))
#     paymentFor = db.Column(db.Enum(PaymentFor), nullable=False, default=PaymentFor.OTHER)
#     paymentName = db.Column(db.String)
#     amount = db.Column(db.Float)
#     notes = db.Column(db.Text)
#     createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
#     currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID', ondelete='CASCADE'), default=1)
#     transferExpenses = db.Column(db.Float)
#     projectScope = db.Column(db.Enum(ProjectScopes), default=ProjectScopes.GENERAL)
#     paymentMethod = db.Column(db.Enum(TransferType), default=TransferType.EFT)
#     subFundID = db.Column(db.Integer, db.ForeignKey('sub_funds.subFundID', ondelete='CASCADE'), nullable=True)

#     currency = db.relationship("Currencies", backref="payment_currency")

#     def save(self):
#         db.session.add(self)
#         db.session.commit()

#     def delete(self):
#         db.session.delete(self)
#         db.session.commit()


class Reports(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    reportTag = db.Column(db.String, nullable=False)
    createdBy = db.Column(db.String, nullable=False)
    dateCreated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    type = db.Column(db.String)
    reportId = db.Column(db.String)
    pdfUrl = db.Column(db.String)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
