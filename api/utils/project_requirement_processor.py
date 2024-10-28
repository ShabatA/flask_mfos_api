from api.models.projects import ProjectTask, TaskStatus

class ProjectRequirementProcessor:

    def __init__(self, project, user_id):
        self.user_id = user_id
        self.project = project

    def create_task(self, title, description, stage_id=3):
        """Helper method to create a task with shared attributes."""
        task = ProjectTask(
            projectID=self.project.projectID,
            title=title,
            description=description,
            assignedTo=[],
            cc=[],
            createdBy=self.user_id,
            attachedFiles="N/A",
            status=TaskStatus.TODO,
            stageID=stage_id,
            startDate=self.project.startDate,
            deadline=self.project.dueDate,
        )
        task.save()

    def requirement_1(self):
        self.create_task(
            "Media Requirement - Images",
            "Upload a link for images taken as evidence for this project."
        )

    def requirement_2(self):
        self.create_task(
            "Media Requirement - Videos",
            "Upload a link for videos taken as evidence for this project."
        )

    def requirement_3(self):
        self.create_task(
            "Media Requirement - Stories",
            "Upload a link for stories recorded as evidence for this project."
        )

    def requirement_4(self):
        self.create_task(
            "Media Requirement - Media/Press Reports",
            "Upload a link for media/press reports about this project."
        )

    def requirement_5(self):
        self.create_task(
            "Media Requirement - Recorded Video Interview",
            "Upload a link for a recorded video interview as evidence for this project."
        )

    def requirement_6(self):
        self.create_task(
            "Media Requirement - Live Video Interview",
            "Make arrangements to have a live video interview."
        )

    def requirement_7(self):
        self.create_task(
            "Media Requirement - Photo Thank You Letter",
            "Upload a link for a photo Thank You letter taken as evidence for this project."
        )

    def requirement_8(self):
        self.create_task(
            "Media Requirement - Written Thank You Letter",
            "Upload a document or upload text of the Thank You Letter."
        )

    def requirement_9(self):
        self.create_task(
            "Media Requirement - Live Broadcast",
            "Make arrangements to have a live broadcast showcasing the project."
        )

    def requirement_10(self):
        self.create_task(
            "Media Requirement - Promotional Video",
            "Upload a link for images taken as evidence for this project."
        )

    def requirement_11(self):
        self.create_task(
            "Financial Requirement - Invoices",
            "Upload all invoices for transactions involving this project."
        )

    def requirement_12(self):
        self.create_task(
            "Financial Requirement - Bank Notices (transfer/receipt)",
            "Upload all bank notices for transactions involving this project."
        )

    def requirement_13(self):
        self.create_task(
            "Financial Requirement - Securities",
            "Upload all securities involving this project."
        )

    def requirement_14(self):
        self.create_task(
            "Financial Requirement - Receipts (receipt/disbursement)",
            "Upload all receipts for transactions involving this project."
        )

    def requirement_15(self):
        self.create_task(
            "Implementation Requirement - Memorandum of Understanding",
            "Upload a memorandum of understanding file for this project.",
            stage_id=1
        )

    def requirement_16(self):
        self.create_task(
            "Implementation Requirement - Implementation Agreement",
            "Upload an implementation agreement file for this project.",
            stage_id=1
        )

    def requirement_17(self):
        self.create_task(
            "Implementation Requirement - Signed Beneficiary Lists",
            "Upload specific excel sheet with specific beneficiary details for this project."
        )

    def requirement_18(self):
        self.create_task(
            "Implementation Requirement - Receipts Records",
            "Upload receipts record files for this project."
        )

    def requirement_19(self):
        self.create_task(
            "Implementation Requirement - Completion Records",
            "Upload completion records files for this project."
        )
    
    def requirement_20(self):
        self.create_task(
            title="Describe the service provided",
            description="Describe the service provided."
        )
    
    def requirement_21(self):
        self.create_task(
            title="Describe the Attached Documents",
            description="Describe the Attached Documents"
        )
    
    def requirement_22(self):
        self.create_task(
            title="Notes & Recommendations",
            description="Notes & Recommendations."
        )
    
    def requirement_23(self):
        self.create_task(
            title="Credit for the Sponsoring party",
            description="Write a Credit for the Sponsoring party."
        )

    def default_case(self):
        pass
