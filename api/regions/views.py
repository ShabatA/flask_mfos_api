from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.regions import Regions
from ..models.users import Users
from http import HTTPStatus
from ..utils.db import db

region_namespace = Namespace('region', description="a namespace for region")

region_model = region_namespace.model(
    'Region', {
        'regionID': fields.Integer(),
        'regionName': fields.String(required=True, description="Region Name")
    }
)

@region_namespace.route('/region')
class Region(Resource):

    def is_admin(self, user):
        """
        Check if the user has the "admin" role.
        """
        return any(role.RoleName == 'admin' for role in user.roles)
    

    @region_namespace.marshal_with(region_model)
    def get(self):
        """
        Get all regions
        """
        regions = Regions.query.all()
        return regions, HTTPStatus.OK

    @region_namespace.expect(region_model)
    @region_namespace.marshal_with(region_model)
    @jwt_required()
    def post(self):
        """
        Create a new region
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin:
            print("Access forbidden. Only administrators can create regions.")
            return {'message': 'Access forbidden. Only administrators can create regions.'}, HTTPStatus.FORBIDDEN
        
        data = region_namespace.payload
        region = Regions(**data)
        region.save()
        return region, HTTPStatus.CREATED

@region_namespace.route('/region/<int:regionID>')
class GetUpdateDelete(Resource):
    @region_namespace.marshal_with(region_model)
    @jwt_required()
    def get(self, regionID):
        """
        Get a region by ID
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin:
            print("Access forbidden. Only administrators can create regions.")
            return {'message': 'Access forbidden. Only administrators can create regions.'}, HTTPStatus.FORBIDDEN
        
        region = Regions.get_by_id(regionID)
        return region, HTTPStatus.OK

    @region_namespace.expect(region_model)
    @region_namespace.marshal_with(region_model)
    @jwt_required()
    def put(self, regionID):
        """
        Update a region by ID
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin:
            print("Access forbidden. Only administrators can update regions.")
            return {'message': 'Access forbidden. Only administrators can update regions.'}, HTTPStatus.FORBIDDEN

        region = Regions.get_by_id(regionID)
        data = region_namespace.payload

        region.regionName = data['regionName']
        db.session.commit()
        return region, HTTPStatus.OK

    @jwt_required()
    def delete(self, regionID):
        """
        Delete a region by ID
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if not current_admin.is_admin:
            print("Access forbidden. Only administrators can delete regions.")
            return {'message': 'Access forbidden. Only administrators can delete regions.'}, HTTPStatus.FORBIDDEN

        region = Regions.get_by_id(regionID)
        region.delete()
        return {}, HTTPStatus.NO_CONTENT