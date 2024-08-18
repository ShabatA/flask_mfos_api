from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from http import HTTPStatus
from ..models.questions import Questions, CaseQuestionsMappings, AnswerFormats

# from ..models.casequestionsmapping import CaseQuestionsMappings
# from ..models.answerformat import AnswerFormats
from ..models.users import Users
from ..models.cases import Cases
from ..utils.db import db

questions_namespace = Namespace("questions", description="A namespace for questions")

answer_format_model = questions_namespace.model(
    "AnswerFormat",
    {
        "formatID": fields.Integer(),
        "formatName": fields.String(required=True, description="Answer Format Name"),
    },
)

question_model = questions_namespace.model(
    "Question",
    {
        "questionID": fields.Integer(),
        "questionText": fields.String(required=True, description="Question Text"),
        "points": fields.Integer(required=True, description="Question Points"),
        "formatID": fields.Integer(required=True, description="Answer Format ID"),
        "questionType": fields.String(required=True, description="Question Type"),
    },
)

case_questions_mapping_model = questions_namespace.model(
    "CaseQuestionsMapping",
    {
        "mappingID": fields.Integer(),
        # 'caseID': fields.Integer(required=True, description="Case ID"),
        "questionID": fields.Integer(required=True, description="Question ID"),
    },
)


@questions_namespace.route("/questions")
class QuestionsResource(Resource):

    def is_admin(self, user):
        """
        Check if the user has the "admin" role.
        """
        return any(role.RoleName == "admin" for role in user.roles)

    @questions_namespace.marshal_with(question_model)
    def get(self):
        """
        Get all questions
        """
        questions = Questions.query.all()
        return questions, HTTPStatus.OK

    @questions_namespace.expect(question_model)
    @questions_namespace.marshal_with(question_model)
    @jwt_required()
    def post(self):
        """
        Create a new question
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if self.is_admin(current_admin):
            return {
                "message": "Access forbidden. Only administrators can create questions."
            }, HTTPStatus.FORBIDDEN

        data = questions_namespace.payload
        question = Questions(**data)
        question.save()
        return question, HTTPStatus.CREATED


@questions_namespace.route("/questions/<int:questionID>")
class QuestionResource(Resource):

    def is_admin(self, user):
        """
        Check if the user has the "admin" role.
        """
        return any(role.RoleName == "admin" for role in user.roles)

    @questions_namespace.marshal_with(question_model)
    @jwt_required()
    def get(self, questionID):
        """
        Get a question by ID
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if self.is_admin(current_admin):
            return {
                "message": "Access forbidden. Only administrators can access questions."
            }, HTTPStatus.FORBIDDEN

        question = Questions.get_by_id(questionID)
        return question, HTTPStatus.OK

    @questions_namespace.expect(question_model)
    @questions_namespace.marshal_with(question_model)
    @jwt_required()
    def put(self, questionID):
        """
        Update a question by ID
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if self.is_admin(current_admin):
            return {
                "message": "Access forbidden. Only administrators can update questions."
            }, HTTPStatus.FORBIDDEN

        question = Questions.get_by_id(questionID)
        data = questions_namespace.payload

        question.questionText = data["questionText"]
        question.points = data["points"]
        question.formatID = data["formatID"]
        question.questionType = data["questionType"]

        db.session.commit()
        return question, HTTPStatus.OK

    @jwt_required()
    def delete(self, questionID):
        """
        Delete a question by ID
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if self.is_admin(current_admin):
            return {
                "message": "Access forbidden. Only administrators can delete questions."
            }, HTTPStatus.FORBIDDEN

        question = Questions.get_by_id(questionID)
        question.delete()
        return {}, HTTPStatus.NO_CONTENT


@questions_namespace.route("/questions/<int:questionID>/case-mapping")
class CaseQuestionMappingResource(Resource):

    def is_admin(self, user):
        """
        Check if the user has the "admin" role.
        """
        return any(role.RoleName == "admin" for role in user.roles)

    @questions_namespace.expect(case_questions_mapping_model)
    @questions_namespace.marshal_with(case_questions_mapping_model)
    @jwt_required()
    def post(self, questionID):
        """
        Map a question to a case
        """
        current_admin = Users.query.filter_by(username=get_jwt_identity()).first()

        if self.is_admin(current_admin):
            return {
                "message": "Access forbidden. Only administrators can map questions to cases."
            }, HTTPStatus.FORBIDDEN

        question = Questions.get_by_id(questionID)
        data = questions_namespace.payload

        case_mapping = CaseQuestionsMappings(
            caseID=data["caseID"], questionID=questionID
        )

        db.session.add(case_mapping)
        db.session.commit()

        return case_mapping, HTTPStatus.CREATED
