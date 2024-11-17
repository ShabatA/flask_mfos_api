from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from ..utils.db import db
from .users import Users
from .cases import CasesData
from .projects import ProjectsData
from enum import Enum as PyEnum
from sqlalchemy import Enum

class Content(db.Model):
    __tablename__ = 'contents'

    content_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    translation_contents = relationship("TranslationContent", back_populates="content", cascade="all, delete-orphan")
    translation_request = relationship("TranslationRequest", uselist=False, back_populates="content", cascade="all, delete-orphan")
    creator = relationship("Users")

    def save(self):
        db.session.add(self)
        db.session.commit()

    def add_translation_content(self, field_name, original, translate=False):
        """Adds a new TranslationContent item to this Content instance."""
        translation_content = TranslationContent(
            content_id=self.content_id,
            field_name=field_name,
            original=original,
            translate=translate
        )
        db.session.add(translation_content)

    def save_translation_contents(self):
        """Commit all translation content items for this Content instance at once."""
        db.session.commit()

    def get_fields_to_translate(self):
        """Returns a list of TranslationContent items marked for translation."""
        return [item for item in self.translation_contents if item.translate]
    
    def update_translation_content(self, field_name, original, translate):
        # Locate the specific translation field
        translation_field = next(
            (field for field in self.translation_contents if field.field_name == field_name), 
            None
        )
        if translation_field:
            # Update the existing translation content
            translation_field.original = original
            translation_field.translate = translate
        else:
            # Add new translation content if it does not exist
            self.add_translation_content(field_name=field_name, original=original, translate=translate)


class RequestStatus(PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TranslationRequest(db.Model):
    __tablename__ = 'translation_requests'

    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_id = db.Column(db.Integer, db.ForeignKey('contents.content_id'), nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False)
    translator_id = db.Column(db.Integer, db.ForeignKey('users.userID'))
    caseID = db.Column(db.Integer, db.ForeignKey('cases_data.caseID'), nullable=True)
    projectID = db.Column(db.Integer, db.ForeignKey('projects_data.projectID'), nullable=True)
    status = db.Column(
        Enum(*[status.value for status in RequestStatus], name="request_status_enum"),
        default=RequestStatus.PENDING.value,
        nullable=False
    )
    requested_on = db.Column(db.DateTime, default=datetime.utcnow)
    completed_on = db.Column(db.DateTime)

    # Relationships
    content = relationship("Content", back_populates="translation_request")
    requester = relationship("Users", foreign_keys=[requested_by_id])
    translator = relationship("Users", foreign_keys=[translator_id])
    case = relationship("CasesData", backref="translation_requests")
    project = relationship("ProjectsData", backref="translation_requests")

    # Helper functions
    def save(self):
        if bool(self.caseID) == bool(self.projectID):
            raise ValueError("A translation request must be linked to either a case or a project, not both or neither.")
        db.session.add(self)
        db.session.commit()

    def assign_translator(self, translator):
        """Assign a translator to this request and update status to in-progress."""
        self.translator = translator
        self.status = RequestStatus.IN_PROGRESS
        self.save()

    def complete_translation(self):
        """Mark the translation as completed and set the completion timestamp."""
        self.status = RequestStatus.COMPLETED
        self.completed_on = datetime.utcnow()
        self.save()

    def get_request_details(self):
        """Return a summary of the translation request details."""
        return {
            "request_id": self.request_id,
            "content_id": self.content_id,
            "status": self.status.value,
            "requested_by": self.requester.mini_user_details(),
            "translator": self.translator.mini_user_details() if self.translator else None,
            "requested_on": self.requested_on,
            "completed_on": self.completed_on
        }


class TranslationContent(db.Model):
    __tablename__ = 'translation_contents'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content_id = db.Column(db.Integer, db.ForeignKey('contents.content_id'), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)  # e.g., 'service_description', 'documents'
    original = db.Column(db.Text, nullable=False)
    translated = db.Column(db.Text, nullable=True)  # Leave empty until translation is provided
    translate = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    content = relationship("Content", back_populates="translation_contents")

    def save(self):
        db.session.add(self)
        db.session.commit()
