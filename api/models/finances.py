from ..utils.db import db
from enum import Enum
from datetime import datetime
from flask import jsonify
from http import HTTPStatus
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

class Currencies(db.Model):
    __tablename__ = 'currencies'
    
    currencyID = db.Column(db.Integer, primary_key=True)
    currencyCode = db.Column(db.String(3), unique=True, nullable=False)  # e.g., 'USD', 'EUR'
    currencyName = db.Column(db.String(50), nullable=False)  # e.g., 'US Dollar', 'Euro'
    exchangeRateToUSD = db.Column(db.Float, nullable=False)  # Exchange rate to USD
    lastUpdated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Ensure USD is always present as the default currency
    @staticmethod
    def initialize_defaults():
        if not Currencies.query.filter_by(currencyCode='USD').first():
            usd_currency = Currencies(
                currencyCode='USD',
                currencyName='US Dollar',
                exchangeRateToUSD=1.0,
                lastUpdated=datetime.utcnow()
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
            lastUpdated=datetime.utcnow()
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



class RegionAccount(db.Model):
    __tablename__ = 'region_account'
    
    accountID = db.Column(db.Integer, primary_key=True)
    accountName = db.Column(db.String(255), nullable=False)
    defaultCurrencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), default=1)
    totalFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Total across all currencies
    usedFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)   # Total across all currencies
    availableFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Total across all currencies
    lastUpdate = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())
    health_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    education_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    general_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    shelter_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    sponsorship_funds = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    regionID = db.Column(db.Integer, db.ForeignKey('regions.regionID'))
    
    projectsFunds = db.relationship('ProjectFunds', backref='projects_data', lazy=True)
    casesFunds = db.relationship('CaseFunds', backref='cases_data', lazy=True)
    donations = db.relationship('Donations', backref='region_account', lazy=True)
    currency_balances = db.relationship('RegionAccountCurrencyBalance', backref='region_account_bal', lazy=True)
    transactions = db.relationship('RegionAccountTransaction', backref='region_account_tran', lazy=True)
    
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

    def add_fund(self, amount, currencyID=None, transaction_subtype=None, projectID=None, caseID=None, payment_number=None, category=None):
        if currencyID is None:
            currencyID = self.defaultCurrencyID
        
        currency = Currencies.query.get(currencyID)
        if not currency:
            raise ValueError("Invalid currencyID")
        
        amount_in_default_currency = currency.convert_to_default(amount, self.defaultCurrencyID)
        
        balance = RegionAccountCurrencyBalance.query.filter_by(accountID=self.accountID, currencyID=currencyID).first()
        if not balance:
            balance = RegionAccountCurrencyBalance(accountID=self.accountID, currencyID=currencyID, totalFund=0, availableFund=0, usedFund=0)
        
        balance.totalFund += amount
        balance.availableFund += amount
        balance.save()
        
        self.totalFund += amount_in_default_currency
        self.availableFund += amount_in_default_currency
        
        if category:
            category_fund = CategoryFund.query.filter_by(accountID=self.accountID, category=category).first()
            if not category_fund:
                category_fund = CategoryFund(accountID=self.accountID, category=category, amount=0)
            category_fund.amount += amount_in_default_currency
            category_fund.save()
        
        self.save()
        
        transaction = RegionAccountTransaction(
            accountID=self.accountID,
            currencyID=currencyID,
            amount=amount,
            transactionType='add',
            transactionSubtype=transaction_subtype,
            projectID=projectID,
            caseID=caseID,
            paymentNumber=payment_number,
            timestamp=func.now(),
            category=category
        )
        transaction.save()

    def use_fund(self, amount, currencyID=None, transaction_subtype=None, projectID=None, caseID=None, payment_number=None, category=None):
        if currencyID is None:
            currencyID = self.defaultCurrencyID
        
        currency = Currencies.query.get(currencyID)
        if not currency:
            raise ValueError("Invalid currencyID")
        
        amount_in_default_currency = currency.convert_to_default(amount, self.defaultCurrencyID)
        
        balance = RegionAccountCurrencyBalance.query.filter_by(accountID=self.accountID, currencyID=currencyID).first()
        if not balance or balance.availableFund < amount:
            raise ValueError("Insufficient funds in the specified currency")
        
        balance.usedFund += amount
        balance.availableFund -= amount
        balance.save()
        
        self.usedFund += amount_in_default_currency
        self.availableFund -= amount_in_default_currency
        
        if category:
            category_fund = CategoryFund.query.filter_by(accountID=self.accountID, category=category).first()
            if not category_fund or category_fund.amount < amount_in_default_currency:
                raise ValueError("Insufficient funds in the specified category")
            category_fund.amount -= amount_in_default_currency
            category_fund.save()
        
        self.save()
        
        transaction = RegionAccountTransaction(
            accountID=self.accountID,
            currencyID=currencyID,
            amount=amount,
            transactionType='use',
            transactionSubtype=transaction_subtype,
            projectID=projectID,
            caseID=caseID,
            paymentNumber=payment_number,
            timestamp=func.now(),
            category=category
        )
        transaction.save()

    def get_fund_balance(self, currencyID=None):
        if currencyID is None:
            return {
                "totalFund": self.totalFund,
                "usedFund": self.usedFund,
                "availableFund": self.availableFund
            }
        
        balance = RegionAccountCurrencyBalance.query.filter_by(accountID=self.accountID, currencyID=currencyID).first()
        if balance:
            return {
                "totalFund": balance.totalFund,
                "usedFund": balance.usedFund,
                "availableFund": balance.availableFund
            }
        
        return {
            "totalFund": 0,
            "usedFund": 0,
            "availableFund": 0
        }
    
    def get_scope_balances(self, currencyID=None):
        if currencyID is None:
            return {
                "health_funds": self.health_funds,
                "education_funds": self.education_funds,
                "general_funds": self.general_funds,
                "shelter_funds": self.shelter_funds,
                "sponsorship_funds": self.sponsorship_funds
            }
        
        balance = RegionAccountCurrencyBalance.query.filter_by(accountID=self.accountID, currencyID=currencyID).first()
        
        if balance:
            return {
                "health_funds": self.health_funds,
                "education_funds": self.education_funds,
                "general_funds": self.general_funds,
                "shelter_funds": self.shelter_funds,
                "sponsorship_funds": self.sponsorship_funds
            }
        
        return {
            "health_funds": 0,
            "education_funds": 0,
            "general_funds": 0,
            "shelter_funds": 0,
            "sponsorship_funds": 0
        }
        
    def get_available_currencies(self):
        return [{"currencyID": balance.currencyID, "currencyCode": balance.currency.currencyCode, "currencyName": balance.currency.currencyName} for balance in self.currency_balances]
    
    def get_account_transactions(self):
        transactions = self.transactions
        transaction_list = []
        for transaction in transactions:
            transaction_dict = {
                'transactionID': transaction.transactionID,
                'accountID': transaction.accountID,
                'currencyID': transaction.currencyID,
                'amount': transaction.amount,
                'transactionType': transaction.transactionType,
                'transactionSubtype': transaction.transactionSubtype,
                'projectID': transaction.projectID,
                'caseID': transaction.caseID,
                'paymentNumber': transaction.paymentNumber,
                'timestamp': transaction.timestamp
            }
            transaction_list.append(transaction_dict)
        return transaction_list
        


class RegionAccountCurrencyBalance(db.Model):
    __tablename__ = 'region_account_currency_balances'
    
    balanceID = db.Column(db.Integer, primary_key=True)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), nullable=False)
    totalFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    availableFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    usedFund = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    currency = db.relationship('Currencies')
    
    @declared_attr
    def region_account(cls):
        return db.relationship('RegionAccount', backref='curr_balances')
    
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
    __tablename__ = 'region_account_transactions'
    
    transactionID = db.Column(db.Integer, primary_key=True)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transactionType = db.Column(db.String(10), nullable=False)  # 'add' or 'use'
    transactionSubtype = db.Column(db.String(50), nullable=True)  # e.g., 'project_payment', 'case_payment'
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=True)
    paymentNumber = db.Column(db.Integer, nullable=True)  # e.g., 1, 2, 3, etc.
    timestamp = db.Column(db.DateTime, nullable=False, default=func.now())
    category = db.Column(db.String(50), nullable=True)  # 'health', 'education', etc.
    
    @declared_attr
    def region_account(cls):
        return db.relationship('RegionAccount', backref='account_transactions')
    
    @declared_attr
    def project(cls):
        return db.relationship('ProjectsData', backref='account_transactions')
    
    @declared_attr
    def case(cls):
        return db.relationship('CasesData', backref='account_transactions')
    
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
    __tablename__ = 'category_funds'
    
    id = db.Column(db.Integer, primary_key=True)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    @declared_attr
    def region_account(cls):
        return db.relationship('RegionAccount', backref='category_funds')
    
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
    __tablename__ = 'sub_fund_currency_balances'
    
    id = db.Column(db.Integer, primary_key=True)
    subFundID = db.Column(db.Integer, db.ForeignKey('sub_funds.subFundID'), nullable=False, index=True)
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), nullable=False, index=True)
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=False, default=0)
    availableFund = db.Column(db.Float, nullable=False, default=0)

    currency = db.relationship('Currencies')
    sub_fund = db.relationship('SubFunds', back_populates='currency_balances')

    __table_args__ = (db.UniqueConstraint('subFundID', 'currencyID', name='unique_subfund_currency'),)
    
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
    __tablename__ = 'financial_fund'
    
    fundID = db.Column(db.Integer, primary_key=True)
    fundName = db.Column(db.String(255), nullable=False)
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=True)
    accountType = db.Column(db.String(50))
    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    administrator = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False) # the employee responsible for managing this fund
    availableFund = db.Column(db.Float, default=0)
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), default=1, index=True)
    lastUpdate = db.Column(db.DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    currency_balances = db.relationship('FinancialFundCurrencyBalance', back_populates='financial_fund', lazy=True)
    donations = db.relationship('Donations', backref='financial_fund', lazy=True)
    payments = db.relationship('Payments', backref='financial_fund', lazy=True)
    subFunds = db.relationship('SubFunds', back_populates='financial_fund', lazy=True)
    

    def add_fund(self, amount, currencyID):
        try:
            sub_fund_balance = FinancialFundCurrencyBalance.query.filter_by(fundID=self.fundID, currencyID=currencyID).first()
            if not sub_fund_balance:
                sub_fund_balance = FinancialFundCurrencyBalance(fundID=self.fundID, currencyID=currencyID)
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
            sub_fund_balance = FinancialFundCurrencyBalance.query.filter_by(fundID=self.fundID, currencyID=currencyID).first()
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
                "availableFund": self.availableFund
            }

        sub_fund_balance = FinancialFundCurrencyBalance.query.filter_by(fundID=self.fundID, currencyID=currencyID).first()
        if sub_fund_balance:
            return {
                "totalFund": sub_fund_balance.totalFund,
                "usedFund": sub_fund_balance.usedFund,
                "availableFund": sub_fund_balance.availableFund
            }
        
        return {
            "totalFund": 0,
            "usedFund": 0,
            "availableFund": 0
        }

    def _convert_to_default_currency(self, amount, currencyID):
        # Implement the logic to convert amount to default currency using exchange rates
        currency = Currencies.query.get(currencyID)
        if currency:
            return amount / currency.exchangeRateToUSD  # Assuming exchangeRateToUSD is the exchange rate to USD
        return amount
    
    def get_available_currencies(self):
        return [{"currencyID": balance.currencyID, "currencyCode": balance.currency.currencyCode, "currencyName": balance.currency.currencyName} for balance in self.currency_balances]
    
    def get_all_sub_funds(self):
        sub_funds = self.subFunds
        sub_funds_info = []
        for sub_fund in sub_funds:
            sub_fund_info = {
                'subFundID': sub_fund.subFundID,
                'fundID': sub_fund.fundID,
                'subFundName': sub_fund.subFundName,
                'accountType': sub_fund.accountType,
                'totalFund': sub_fund.totalFund,
                'usedFund': sub_fund.usedFund,
                'availableFund': sub_fund.availableFund,
                'notes': sub_fund.notes,
                'createdAt': sub_fund.createdAt,
                'currencyID': sub_fund.currencyID
            }
            sub_funds_info.append(sub_fund_info)
        return sub_funds_info
    
    def get_all_donations(self):
        donations = self.donations
        donation_list = []
        for donation in donations:
            donation_dict = {
                'donationID': donation.donationID,
                'donor': {
                    'donorID': donation.donor.donorID,
                    'donorName': donation.donor.donorName,
                    'donorEmail': donation.donor.donorEmail,
                    # Add other donor information as needed
                },
                'amount': donation.amount,
                'currencyName': donation.currency.currencyName,
                'donationType': donation.donationType.value,
                'createdAt': donation.createdAt.isoformat()
            }
            donation_list.append(donation_dict)
        return donation_list
    
    
    def get_all_payments(self):
        payments = self.payments
        payment_list = []
        for payment in payments:
            payment_dict = {
                'paymentID': payment.paymentID,
                'accountID': payment.accountID,
                'currencyID': payment.currency.currencyName,
                'amount': payment.amount,
                'transactionType': payment.transactionType.value,
                'transactionSubtype': payment.transactionSubtype.value,
                'projectID': payment.projectID,
                'caseID': payment.caseID,
                'paymentNumber': payment.paymentNumber,
                'timestamp': payment.timestamp.isoformat()
            }
            payment_list.append(payment_dict)
        return payment_list

class FinancialFundCurrencyBalance(db.Model):
    __tablename__ = 'financial_fund_currency_balances'
    
    id = db.Column(db.Integer, primary_key=True)
    fundID = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'), nullable=False, index=True)
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), nullable=False, index=True)
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=False, default=0)
    availableFund = db.Column(db.Float, nullable=False, default=0)

    currency = db.relationship('Currencies')
    financial_fund = db.relationship('FinancialFund', back_populates='currency_balances')

    __table_args__ = (db.UniqueConstraint('fundID', 'currencyID', name='unique_fund_currency'),)


class SubFunds(db.Model):
    __tablename__ = 'sub_funds'
    
    subFundID = db.Column(db.Integer, primary_key=True)
    fundID = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'), nullable=False, index=True)
    subFundName = db.Column(db.String(255), nullable=False)
    accountType = db.Column(db.String(50))
    totalFund = db.Column(db.Float, nullable=False, default=0)
    usedFund = db.Column(db.Float, nullable=False, default=0)
    availableFund = db.Column(db.Float, nullable=False, default=0)
    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), default=1, index=True)

    # Relationships
    currency_balances = db.relationship('SubFundCurrencyBalance', back_populates='sub_fund', lazy=True)
    financial_fund = db.relationship('FinancialFund', back_populates='subFunds')

    def add_fund(self, amount, currencyID):
        try:
            balance = SubFundCurrencyBalance.query.filter_by(subFundID=self.subFundID, currencyID=currencyID).first()
            if not balance:
                balance = SubFundCurrencyBalance(subFundID=self.subFundID, currencyID=currencyID)
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
            balance = SubFundCurrencyBalance.query.filter_by(subFundID=self.subFundID, currencyID=currencyID).first()
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
                "availableFund": self.availableFund
            }

        balance = SubFundCurrencyBalance.query.filter_by(subFundID=self.subFundID, currencyID=currencyID).first()
        if balance:
            return {
                "totalFund": balance.totalFund,
                "usedFund": balance.usedFund,
                "availableFund": balance.availableFund
            }
        
        return {
            "totalFund": 0,
            "usedFund": 0,
            "availableFund": 0
        }

    def _convert_to_default_currency(self, amount, currencyID):
        # Implement the logic to convert amount to default currency using exchange rates
        currency = Currencies.query.get(currencyID)
        if currency:
            return amount / currency.exchangeRateToUSD  # Assuming exchangeRateToUSD is the exchange rate to USD
        return amount
    
    def get_available_currencies(self):
        return [{"currencyID": balance.currencyID, "currencyCode": balance.currency.currencyCode, "currencyName": balance.currency.currencyName} for balance in self.currency_balances]



# Hold amounts after Project Approval, all payments must spend from this amount
class ProjectFunds(db.Model):
    __tablename__ = 'project_funds'
    
    fundID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=False)
    fundsAllocated = db.Column(db.Float, nullable=True)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

# Hold amounts after Case Approval, all payments must spend from this amount
class CaseFunds(db.Model):
    __tablename__ = 'case_funds'
    
    fundID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=False)
    fundsAllocated = db.Column(db.Float, nullable=True)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class DonorTypes(Enum):
    INDIVIDUAL = 'Individual'
    ORGANIZATION = 'Organization'
    COMPANY = 'Company'
    GOVERNMENT = 'Government'

class Donor(db.Model):
    __tablename__ = 'donors'
    
    donorID = db.Column(db.Integer, primary_key=True)
    donorName = db.Column(db.String(255), nullable=False)
    donorType = db.Column(db.String(50), nullable=False)  # e.g., 'individual' or 'institution'
    placeOfResidence = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    startOfRelationship = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    representatives = db.relationship('Representative', back_populates='donors', lazy=True, cascade="all, delete-orphan")
    donations = db.relationship('Donations', backref='donors',lazy=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    def get_donor_info(self):
        
        representatives = [{
            'name': rep.name,
            'jobPosition': rep.jobPosition,
            'email': rep.email,
            'phoneNumber': rep.phoneNumber
        } for rep in self.representatives]
        return {
            'donorID': self.donorID,
            'donorName': self.donorName,
            'donorType': self.donorType,
            'placeOfResidence': self.placeOfResidence,
            'phoneNumber': self.phoneNumber,
            'email': self.email,
            'startOfRelationship': self.startOfRelationship,
            'notes': self.notes,
            'representatives': representatives
        }
       

class Representative(db.Model):
    __tablename__ = 'representatives'
    
    representativeID = db.Column(db.Integer, primary_key=True)
    donorID = db.Column(db.Integer, db.ForeignKey('donors.donorID'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    jobPosition = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(50), nullable=True)
    
    # Relationships
    donors = db.relationship('Donor', back_populates='representatives')
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class ProjectScopes(Enum):
    HEALTH = 'Healthcare'
    SHELTER = 'Housing'
    EDUCATION = 'Education Support'
    GENERAL = 'General'
    SPONSORSHIP = 'Sponsorship'
    RELIEF = 'Relief Aid'

class DonationTypes(Enum):
    PROJECT = 'Project'
    CASE = 'Case'
    GENERAL = 'General'
    
class Donations(db.Model):
    __tablename__ = 'donations'
    
    id = db.Column(db.Integer, primary_key=True)
    donorID = db.Column(db.Integer, db.ForeignKey('donors.donorID'), nullable=False)
    accountID = db.Column(db.Integer, db.ForeignKey('region_account.accountID'), nullable=False)
    fundID = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    details = db.Column(db.Text, nullable=True) # this is "notes" on the UI
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), default=1)
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=True)
    subFundID = db.Column(db.Integer, db.ForeignKey('sub_funds.subFundID'), nullable=True)
    projectScope = db.Column(db.Enum(ProjectScopes), default=ProjectScopes.GENERAL)
    allocationTags = db.Column(db.String) # used to tag a donation made to a case/project that is not yet added to the database
    donationType = db.Column(db.Enum(DonationTypes),default=DonationTypes.GENERAL)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class ProjectFundReleaseRequests(db.Model):
    __tablename__ = 'project_fund_release_requests'
    
    requestID = db.Column(db.Integer, primary_key=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=False)
    fundsRequested = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    requestedBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approvedAt = db.Column(db.DateTime, nullable=True)
    paymentCount = db.Column(db.Integer, nullable=False)
    approvedAmount = db.Column(db.Float, nullable=False, default=0)
    bulkName = db.Column(db.String, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class CaseFundReleaseRequests(db.Model):
    __tablename__ = 'case_fund_release_requests'
    
    requestID = db.Column(db.Integer, primary_key=True)
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=False)
    fundsRequested = db.Column(db.Float, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    requestedBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approvedAt = db.Column(db.DateTime, nullable=True)
    paymentCount = db.Column(db.Integer, nullable=False)
    approvedAmount = db.Column(db.Float, nullable=False, default=0)
    bulkName = db.Column(db.String, nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        
class TransferStage(Enum):
    ASSESSMENT = 'Pending Assessment'
    ONGOING = 'On Going'
    APPROVED = 'Approved'
    
class TransferType(Enum):
    EFT = 'EFT'
    CASH = 'Cash'
    CHECK = 'Check'
    

class FundTransferRequests(db.Model):
    __tablename__ = 'fund_transfer_requests'
    
    requestID = db.Column(db.Integer, primary_key=True)
    from_fund = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'))
    to_fund = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'))
    transferAmount = db.Column(db.Float, nullable=False)
    requestedBy = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    stage = db.Column(db.Enum(TransferStage), default=TransferStage.ASSESSMENT)
    notes = db.Column(db.Text)
    approvedAt = db.Column(db.DateTime, nullable=True)
    transferType = db.Column(db.Enum(TransferType), default=TransferType.EFT)

    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class PaymentFor(Enum):
    CASE = 'Case'
    PROJECT = 'Project'
    OTHER = 'Other'

class Payments(db.Model):
    __tablename__ = 'payments'
    
    paymentID = db.Column(db.Integer, primary_key=True)
    from_fund = db.Column(db.Integer, db.ForeignKey('financial_fund.fundID'))
    paymentFor = db.Column(db.Enum(PaymentFor), nullable=False, default=PaymentFor.OTHER)
    paymentName = db.Column(db.String)
    amount = db.Column(db.Float)
    notes = db.Column(db.Text)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    currencyID = db.Column(db.Integer, db.ForeignKey('currencies.currencyID'), default=1)
    transferExpenses = db.Column(db.Float)
    projectScope = db.Column(db.Enum(ProjectScopes), default=ProjectScopes.GENERAL)
    paymentMethod = db.Column(db.Enum(TransferType), default=TransferType.EFT)
    subFundID = db.Column(db.Integer, db.ForeignKey('sub_funds.subFundID'), nullable=True)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Reports(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    reportTag = db.Column(db.String, nullable=False)
    createdBy = db.Column(db.String, nullable=False)
    dateCreated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    pdfBytes = db.Column(db.LargeBinary, nullable=False)
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
     
    
    
    