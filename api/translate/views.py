from flask_restx import Resource, Namespace, fields 
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from http import HTTPStatus
from ..models.translate import Content, TranslationRequest, TranslationContent, RequestStatus
from ..models.cases import CasesData
from ..models.projects import ProjectsData
from ..models.users import Users
from ..utils.db import db
from datetime import datetime

# Define Namespace for Translation
content_namespace = Namespace("Translation", description="Namespace for managing translation requests.")

# Define input model for adding content
add_content_model = content_namespace.model(
    "AddContent",
    {
        "projectID": fields.Integer(required=False, description="Project ID"),
        "caseID": fields.Integer(required=False, description="Case ID"),
        "translator_id": fields.Integer(required=False, description="User ID of the translator (optional)"),
        "fields": fields.List(
            fields.Nested(
                content_namespace.model(
                    "Field",
                    {
                        "field_name": fields.String(required=True, description="Field name, e.g., 'service_description'"),
                        "original": fields.String(required=True, description="Original content"),
                        "translate": fields.Boolean(required=False, default=False, description="Translate this field")
                    }
                )
            ),
            required=True,
            description="List of fields with content and translation flags",
        ),
    },
)

@content_namespace.route("/request_translation")
class RequestTranslationResource(Resource):
    @jwt_required()
    @content_namespace.expect(add_content_model)
    @content_namespace.doc(description="Add new content with optional translation flags.")
    def post(self):
        # Get the current authenticated user
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        if not current_user:
            return {"error": "Authenticated user not found."}, HTTPStatus.UNAUTHORIZED

        data = request.get_json()

        # Extract case or project ID and validate only one is provided
        case_id = data.get("caseID")
        project_id = data.get("projectID")
        if bool(case_id) == bool(project_id):
            return {"error": "Specify either caseID or projectID, not both or neither."}, HTTPStatus.BAD_REQUEST
        
        # Verify case or project existence
        if case_id:
            case = CasesData.query.get(case_id)
            if not case:
                return {"error": f"Case with ID {case_id} does not exist."}, HTTPStatus.NOT_FOUND
        elif project_id:
            project = ProjectsData.query.get(project_id)
            if not project:
                return {"error": f"Project with ID {project_id} does not exist."}, HTTPStatus.NOT_FOUND

        # Create the main Content instance
        new_content = Content(created_by_id=current_user.userID)
        new_content.save()

        # Add translation content fields
        fields = data.get("fields", [])
        for field_data in fields:
            field_name = field_data.get("field_name")
            original = field_data.get("original", "")
            translate = field_data.get("translate", False)
            new_content.add_translation_content(field_name=field_name, original=original, translate=translate)

        # Commit all translation contents at once
        new_content.save_translation_contents()

        # Create TranslationRequest if any field is marked for translation
        if any(field["translate"] for field in fields):
            translation_request = TranslationRequest(
                content=new_content,
                requested_by_id=current_user.userID,
                translator_id=data.get("translator_id"),
                caseID=case_id,
                projectID=project_id,
                status="pending"
            )
            translation_request.save()

        return {"message": "Content added successfully", "content_id": new_content.content_id}, HTTPStatus.CREATED

# Output model for translation request details
request_details_model = content_namespace.model(
    "RequestDetails",
    {
        "request_id": fields.Integer(description="Request ID"),
        "created_by": fields.String(description="Full name of the requester"),
        "translator": fields.String(description="Full name of the translator, if assigned"),
        "status": fields.String(description="Current status of the translation request"),
        "requested_on": fields.DateTime(description="Date and time when the request was created"),
        "project_id": fields.Integer(description="Associated project ID", nullable=True),
        "case_id": fields.Integer(description="Associated case ID", nullable=True),
    }
)

@content_namespace.route("/requests")
class GetRequestsResource(Resource):
    @jwt_required()
    @content_namespace.marshal_with(request_details_model, as_list=True)
    @content_namespace.doc(description="Retrieve all translation requests with details.")
    def get(self):
        # Fetch all translation requests from the database
        translation_requests = TranslationRequest.query.all()

        # Format the data into a list of dictionaries
        request_list = [
            {
                "request_id": req.request_id,
                "created_by": f"{req.requester.username}" if req.requester else "Unknown",
                "translator": f"{req.translator.username}" if req.translator else "Unassigned",
                "status": req.status,
                "requested_on": req.requested_on,
                "project_id": req.projectID,
                "case_id": req.caseID,
            }
            for req in translation_requests
        ]

        return request_list, HTTPStatus.OK


@content_namespace.route("/requests/translator/<int:translator_id>")
class TranslatorRequestsResource(Resource):
    @jwt_required()
    @content_namespace.marshal_with(request_details_model, as_list=True)
    @content_namespace.doc(description="Retrieve translation requests assigned to a specific translator.")
    def get(self, translator_id):
        # Fetch translation requests for the specified translator
        translation_requests = TranslationRequest.query.filter_by(translator_id=translator_id).all()

        # Format the data into a list of dictionaries
        request_list = [
            {
                "request_id": req.request_id,
                "created_by": f"{req.requester.username}" if req.requester else "Unknown",
                "translator": f"{req.translator.username}" if req.translator else "Unassigned",
                "status": req.status,
                "requested_on": req.requested_on,
                "project_id": req.projectID,
                "case_id": req.caseID,
            }
            for req in translation_requests
        ]

        return request_list, HTTPStatus.OK


# Output model for translation content details
content_details_model = content_namespace.model(
    "ContentDetails",
    {
        "field_name": fields.String(description="Field name, e.g., 'service_description'"),
        "original": fields.String(description="Original content"),
        "translated": fields.String(description="Translated content, if any"),
        "translate": fields.Boolean(description="Whether this field needs translation"),
    }
)

# Output model for a single translation request with its contents
translator_request_model = content_namespace.model(
    "TranslatorRequest",
    {
        "request_id": fields.Integer(description="Request ID"),
        "status": fields.String(description="Status of the translation request"),
        "requested_on": fields.DateTime(description="Date and time when the request was created"),
        "project_id": fields.Integer(description="Associated project ID", nullable=True),
        "case_id": fields.Integer(description="Associated case ID", nullable=True),
        "content_fields": fields.List(fields.Nested(content_details_model), description="Fields to be translated"),
    }
)

@content_namespace.route("/requests/<int:request_id>/content")
class TranslatorContentResource(Resource):
    @jwt_required()
    @content_namespace.marshal_with(translator_request_model)
    @content_namespace.doc(description="Retrieve the content fields for a specific translation request assigned to the authenticated translator.")
    def get(self, request_id):
        # Get the current authenticated user's ID
        current_user_id = Users.query.filter_by(username=get_jwt_identity()).first().userID

        # Fetch the translation request and check translator assignment
        translation_request = TranslationRequest.query.get(request_id)
        if not translation_request:
            return {"error": "Translation request not found."}, HTTPStatus.NOT_FOUND

        # if translation_request.translator_id != current_user_id:
        #     return {"error": "You are not authorized to view this content."}, HTTPStatus.FORBIDDEN

        # Gather content fields associated with the request
        content_fields = [
            {
                "field_name": field.field_name,
                "original": field.original,
                "translated": field.translated,
                "translate": field.translate
            }
            for field in translation_request.content.translation_contents
        ]

        # Format the response data
        response_data = {
            "request_id": translation_request.request_id,
            "status": translation_request.status,
            "requested_on": translation_request.requested_on,
            "project_id": translation_request.projectID,
            "case_id": translation_request.caseID,
            "content_fields": content_fields
        }

        return response_data, HTTPStatus.OK


# Input model for updating translations
translation_update_model = content_namespace.model(
    "TranslationUpdate",
    {
        "translations": fields.List(
            fields.Nested(
                content_namespace.model(
                    "TranslationField",
                    {
                        "field_name": fields.String(required=True, description="Field name to be translated, e.g., 'service_description'"),
                        "translated": fields.String(required=True, description="Translated content for this field"),
                    }
                )
            ),
            required=True,
            description="List of fields and their translations",
        ),
    }
)


@content_namespace.route("/requests/<int:request_id>/add_translations")
class AddTranslationsResource(Resource):
    @jwt_required()
    @content_namespace.doc(description="Retrieve original content and add/update translations for fields marked for translation.")
    def get(self, request_id):
        # Get the current authenticated user's ID
        current_user_id = Users.query.filter_by(username=get_jwt_identity()).first().userID

        # Fetch the translation request and check translator assignment
        translation_request = TranslationRequest.query.get(request_id)
        if not translation_request:
            return {"error": "Translation request not found."}, HTTPStatus.NOT_FOUND

        # if translation_request.translator_id != current_user_id:
        #     return {"error": "You are not authorized to update this translation."}, HTTPStatus.FORBIDDEN

        # Gather fields marked for translation with their original content
        fields_to_translate = [
            {
                "field_name": field.field_name,
                "original": field.original
            }
            for field in translation_request.content.translation_contents if field.translate
        ]

        return {
            "message": "Fields marked for translation",
            "fields_to_translate": fields_to_translate
        }, HTTPStatus.OK
    
    @jwt_required()
    @content_namespace.expect(translation_update_model)
    def post(self, request_id):
        # Get the current authenticated user's ID
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        if not current_user:
            return {"error": "Authenticated user not found."}, HTTPStatus.UNAUTHORIZED
        current_user_id = current_user.userID

        # Fetch the translation request and check translator assignment
        translation_request = TranslationRequest.query.get(request_id)
        if not translation_request:
            return {"error": "Translation request not found."}, HTTPStatus.NOT_FOUND

        # if translation_request.translator_id != current_user_id:
        #     return {"error": "You are not authorized to update this translation."}, HTTPStatus.FORBIDDEN

        # Get the list of translations from the request
        data = request.get_json()
        translations = data.get("translations", [])

        # Debug: Check received translations
        print(f"Received translations for request {request_id}: {translations}")

        # Update only fields marked for translation
        updated_fields = []
        for field_data in translations:
            field_name = field_data.get("field_name")
            translated_text = field_data.get("translated")

            # Find the corresponding TranslationContent item
            content_field = next(
                (field for field in translation_request.content.translation_contents
                 if field.field_name == field_name and field.translate), None
            )

            # Debug: Check if content_field was found and marked for translation
            if content_field:
                print(f"Updating field '{field_name}' with translation '{translated_text}'")
                content_field.translated = translated_text  # Update translated content
                db.session.add(content_field)  # Explicitly add the updated object to the session
                updated_fields.append(field_name)
            else:
                print(f"Field '{field_name}' not found or not marked for translation.")

        # Debug: Before commit
        print("Committing changes to the database...")

        # Save all updates to the database
        try:
            db.session.commit()
            print("Commit successful.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during commit: {e}")
            return {"error": "An error occurred while saving translations."}, HTTPStatus.INTERNAL_SERVER_ERROR

        return {
            "message": "Translations updated successfully",
            "updated_fields": updated_fields
        }, HTTPStatus.OK
    



# Input model for updating the request status
status_update_model = content_namespace.model(
    "StatusUpdate",
    {
        "status": fields.String(required=True, description="New status for the translation request")
    }
)


@content_namespace.route("/requests/<int:request_id>/change_status")
class ChangeRequestStatusResource(Resource):
    @jwt_required()
    @content_namespace.expect(status_update_model)
    @content_namespace.doc(description="Change the status of a translation request.")
    def put(self, request_id):
        # Get the current authenticated user's ID
        current_user_id = Users.query.filter_by(username=get_jwt_identity()).first().userID

        # Fetch the translation request
        translation_request = TranslationRequest.query.get(request_id)
        if not translation_request:
            return {"error": "Translation request not found."}, HTTPStatus.NOT_FOUND

        # Get the new status from the request payload
        data = request.get_json()
        new_status = data.get("status")

        # Ensure the new status is valid
        valid_statuses = [status.value for status in RequestStatus]
        if new_status not in valid_statuses:
            return {
                "error": f"Invalid status. Valid statuses are: {', '.join(valid_statuses)}"
            }, HTTPStatus.BAD_REQUEST

        # Update the status
        translation_request.status = new_status

        # If status is set to completed, update the completion timestamp
        if new_status == RequestStatus.COMPLETED.value:
            translation_request.completed_on = datetime.utcnow()

        # Save changes to the database
        try:
            db.session.commit()
            return {
                "message": "Status updated successfully",
                "request_id": request_id,
                "new_status": new_status
            }, HTTPStatus.OK
        except Exception as e:
            db.session.rollback()
            return {
                "error": f"An error occurred while updating status: {str(e)}"
            }, HTTPStatus.INTERNAL_SERVER_ERROR


# @content_namespace.route("/content/case/<int:case_id>")
# class GetContentByCaseResource(Resource):
#     @jwt_required()
#     @content_namespace.marshal_with(content_details_model, as_list=True)
#     @content_namespace.doc(description="Retrieve content fields associated with a specific case ID.")
#     def get(self, case_id):
#         # Check if the case exists
#         case = CasesData.query.get(case_id)
#         if not case:
#             return {"error": f"Case with ID {case_id} does not exist."}, HTTPStatus.NOT_FOUND

#         # Retrieve translation requests linked to the specified case ID
#         translation_requests = TranslationRequest.query.filter_by(caseID=case_id).all()
#         if not translation_requests:
#             return {"error": "No content found for this case ID."}, HTTPStatus.NOT_FOUND

#         # Compile content details from each translation request's linked content
#         content_list = []
#         for request in translation_requests:
#             content = request.content  # Access the Content associated with each TranslationRequest
#             if content:
#                 # Gather fields for each piece of content
#                 for field in content.translation_contents:
#                     content_list.append({
#                         "field_name": field.field_name,
#                         "original": field.original,
#                         "translated": field.translated,
#                         "translate": field.translate
#                     })

#         return content_list, HTTPStatus.OK

@content_namespace.route("/content/case/<int:case_id>")
class GetContentByCaseResource(Resource):
    @jwt_required()
    @content_namespace.marshal_with(translator_request_model, as_list=True)
    @content_namespace.doc(description="Retrieve content fields associated with a specific case ID, along with request details.")
    def get(self, case_id):
        # Check if the case exists
        case = CasesData.query.get(case_id)
        if not case:
            return {"error": f"Case with ID {case_id} does not exist."}, HTTPStatus.NOT_FOUND

        # Retrieve translation requests linked to the specified case ID
        translation_requests = TranslationRequest.query.filter_by(caseID=case_id).all()
        if not translation_requests:
            return {"error": "No content found for this case ID."}, HTTPStatus.NOT_FOUND

        # Compile request and content details
        response_data = []
        for request in translation_requests:
            content = request.content  # Access the Content associated with each TranslationRequest
            if content:
                # Gather fields for each piece of content
                content_fields = [
                    {
                        "field_name": field.field_name,
                        "original": field.original,
                        "translated": field.translated,
                        "translate": field.translate
                    }
                    for field in content.translation_contents
                ]

                # Append detailed request information to the response
                response_data.append({
                    "request_id": request.request_id,
                    "status": request.status,
                    "requested_on": request.requested_on,
                    "completed_on": request.completed_on,
                    "requested_by": {
                        "user_id": request.requester.userID,
                        "username": request.requester.username
                    },
                    "translator": {
                        "user_id": request.translator.userID,
                        "username": request.translator.username
                    } if request.translator else None,
                    "project_id": request.projectID,
                    "case_id": request.caseID,
                    "content_fields": content_fields
                })

        return response_data, HTTPStatus.OK



# @content_namespace.route("/content/project/<int:project_id>")
# class GetContentByProjectResource(Resource):
#     @jwt_required()
#     @content_namespace.marshal_with(content_details_model, as_list=True)
#     @content_namespace.doc(description="Retrieve content fields associated with a specific project ID.")
#     def get(self, project_id):
#         # Check if the project exists
#         project = ProjectsData.query.get(project_id)
#         if not project:
#             return {"error": f"Project with ID {project_id} does not exist."}, HTTPStatus.NOT_FOUND

#         # Retrieve translation requests linked to the specified project ID
#         translation_requests = TranslationRequest.query.filter_by(projectID=project_id).all()
#         if not translation_requests:
#             return {"error": "No content found for this project ID."}, HTTPStatus.NOT_FOUND

#         # Compile content details from each translation request's linked content
#         content_list = []
#         for request in translation_requests:
#             content = request.content  # Access the Content associated with each TranslationRequest
#             if content:
#                 # Gather fields for each piece of content
#                 for field in content.translation_contents:
#                     content_list.append({
#                         "field_name": field.field_name,
#                         "original": field.original,
#                         "translated": field.translated,
#                         "translate": field.translate
#                     })

#         return content_list, HTTPStatus.OK

@content_namespace.route("/content/project/<int:project_id>")
class GetContentByProjectResource(Resource):
    @jwt_required()
    @content_namespace.marshal_with(translator_request_model, as_list=True)
    @content_namespace.doc(description="Retrieve content fields associated with a specific project ID, along with request details.")
    def get(self, project_id):
        # Check if the project exists
        project = ProjectsData.query.get(project_id)
        if not project:
            return {"error": f"Project with ID {project_id} does not exist."}, HTTPStatus.NOT_FOUND

        # Retrieve translation requests linked to the specified project ID
        translation_requests = TranslationRequest.query.filter_by(projectID=project_id).all()
        if not translation_requests:
            return {"error": "No content found for this project ID."}, HTTPStatus.NOT_FOUND

        # Compile request and content details
        response_data = []
        for request in translation_requests:
            content = request.content  # Access the Content associated with each TranslationRequest
            if content:
                # Gather fields for each piece of content
                content_fields = [
                    {
                        "field_name": field.field_name,
                        "original": field.original,
                        "translated": field.translated,
                        "translate": field.translate
                    }
                    for field in content.translation_contents
                ]

                # Append detailed request information to the response
                response_data.append({
                    "request_id": request.request_id,
                    "status": request.status,
                    "requested_on": request.requested_on,
                    "completed_on": request.completed_on,
                    "requested_by": {
                        "user_id": request.requester.userID,
                        "username": request.requester.username
                    },
                    "translator": {
                        "user_id": request.translator.userID,
                        "username": request.translator.username
                    } if request.translator else None,
                    "project_id": request.projectID,
                    "case_id": request.caseID,
                    "content_fields": content_fields
                })

        return response_data, HTTPStatus.OK


@content_namespace.route("/requests/translator/current")
class CurrentTranslatorRequestsResource(Resource):
    @jwt_required()
    @content_namespace.marshal_with(request_details_model, as_list=True)
    @content_namespace.doc(description="Retrieve translation requests assigned to the current authenticated translator.")
    def get(self):
        # Get the current authenticated user's ID
        current_user = Users.query.filter_by(username=get_jwt_identity()).first()
        if not current_user:
            return {"error": "Authenticated user not found."}, HTTPStatus.UNAUTHORIZED

        # Fetch translation requests assigned to the current user (translator)
        translation_requests = TranslationRequest.query.filter_by(translator_id=current_user.userID).all()

        # Format the data into a list of dictionaries
        request_list = [
            {
                "request_id": req.request_id,
                "created_by": f"{req.requester.username}" if req.requester else "Unknown",
                "translator": f"{req.translator.username}" if req.translator else "Unassigned",
                "status": req.status.value,
                "requested_on": req.requested_on,
                "project_id": req.projectID,
                "case_id": req.caseID,
            }
            for req in translation_requests
        ]

        return request_list, HTTPStatus.OK
