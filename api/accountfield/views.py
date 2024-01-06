from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.accountfields import AccountFields
from http import HTTPStatus
from ..utils.db import db

field_namespace = Namespace('AccountField', description="a namespace for field")

field_model = field_namespace.model(
    'AccountField', {
        'fieldID': fields.Integer(),
        'fieldName': fields.String(required=True, enum=['Health', 'Education', 'General', 'Shelter', 'Sponsorship'], description="Field Name"),
        'percentage': fields.Float(required=True, description="Percentage of each Field")
    }
)

@field_namespace.route('/field')

class AccountFields(Resource):
    @field_namespace.marshal_with(field_model)
    def get(self):
        """
        Get all fields
        """
        fields = AccountFields.query.all()
        return fields, HTTPStatus.OK

    @field_namespace.expect(field_model)
    @field_namespace.marshal_with(field_model)
    def post(self):
        """
        Create a new field
        """
        data = field_namespace.payload
        field = AccountField(**data)
        field.save()
        return field, HTTPStatus.CREATED

    @field_namespace.expect(field_model)
    @field_namespace.marshal_with(field_model)
    def put(self):
        """
        Update a field
        """
        data = field_namespace.payload
        field_id = data.get('fieldID')

        # Check if the field exists
        existing_field = AccountField.query.get(field_id)
        if not existing_field:
            return {"message": "Field not found"}, HTTPStatus.NOT_FOUND

        # Update the existing field
        existing_field.fieldName = data.get('fieldName')
        existing_field.percentage = data.get('percentage')
        db.session.commit()

        return existing_field, HTTPStatus.OK

    @field_namespace.expect(field_model)
    @field_namespace.marshal_with(field_model)
    def delete(self):
        """
        Delete a field
        """
        data = field_namespace.payload
        field_id = data.get('fieldID')

        # Check if the field exists
        existing_field = AccountField.query.get(field_id)
        if not existing_field:
            return {"message": "Field not found"}, HTTPStatus.NOT_FOUND

        db.session.delete