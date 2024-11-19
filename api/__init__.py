from flask import Flask
from flask_restx import Api

from api.utils.json_encoder import CustomJSONEncoder
from .cases.views import (
    case_namespace,
    case_stage_namespace,
    case_task_namespace,
    case_assessment_namespace,
)
from .auth.views import auth_namespace, user_management_namespace, user_task_namespace, user_otp_namespace
from .regions.views import region_namespace
from .accountfield.views import field_namespace
from .projects.views import (
    project_namespace,
    stage_namespace,
    task_namespace,
    assessment_namespace,
    requirements_namespace,
    activity_namespace,
)
from .finances.views import finance_namespace, user_budget_namespace
from .summary.views import summary_ns
from .translate.views import content_namespace

# from .questions.views import questions_namespace
from flask_cors import CORS

from .config.config import config_dict
from .utils.db import db
from .models.users import Users, Role, UserPermissions

# from .models.questions import Questions, CaseQuestionsMappings, AnswerFormats
from flask_jwt_extended import JWTManager


from flask_migrate import Migrate


def create_app(config=config_dict["development"]):
    app = Flask(__name__)
    app.json_encoder = CustomJSONEncoder
    CORS(app)
    app.config.from_object(config)

    authorizations = {
        "Bearer Auth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Add a JWT with ** Bearer &lt;JWT&gt; to authorize",
        }
    }

    db.init_app(app)
    jwt = JWTManager(app)

    migrate = Migrate(app, db)

    api = Api(
        app,
        title="MOFS API",
        version="1.0",
        authorizations=authorizations,
        security="Bearer Auth",
        description="A REST API FOR MFOS",
    )

    api.add_namespace(case_namespace)
    api.add_namespace(region_namespace)
    api.add_namespace(field_namespace)
    api.add_namespace(project_namespace)
    api.add_namespace(stage_namespace)
    api.add_namespace(task_namespace)
    api.add_namespace(auth_namespace, path="/auth")
    api.add_namespace(user_management_namespace)
    api.add_namespace(user_otp_namespace)
    api.add_namespace(user_task_namespace)
    api.add_namespace(assessment_namespace)
    api.add_namespace(case_stage_namespace)
    api.add_namespace(case_task_namespace)
    api.add_namespace(requirements_namespace)
    api.add_namespace(case_assessment_namespace)
    api.add_namespace(finance_namespace)
    api.add_namespace(activity_namespace)
    api.add_namespace(summary_ns)
    api.add_namespace(content_namespace)
    api.add_namespace(user_budget_namespace)

    @app.shell_context_processor
    def make_shell_context():
        return {"db": db, "Users": Users}

    return app
