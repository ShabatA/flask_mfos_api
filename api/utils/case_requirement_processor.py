from api.models.cases import CaseTask, CaseTaskStatus


class CaseRequirementProcessor:

    def __init__(self, case, user_id):
        self.case = case
        self.user_id = user_id

    def create_task(self, title, description, stage_id=6):
        """Helper method to create and save a CaseTask."""
        task = CaseTask(
            caseID=self.case.caseID,
            title=title,
            description=description,
            assignedTo=[],
            cc=[],
            createdBy=self.user_id,
            attachedFiles="N/A",
            status=CaseTaskStatus.TODO,
            stageID=stage_id,
            startDate=self.case.startDate,
            deadline=self.case.dueDate,
        )
        task.save()

    def requirement_1(self):
        self.create_task(
            title="Media Requirement - Images",
            description="Upload a link for images taken as evidence for this case."
        )

    def requirement_2(self):
        self.create_task(
            title="Media Requirement - Videos",
            description="Upload a link for videos taken as evidence for this case."
        )

    def requirement_3(self):
        self.create_task(
            title="Media Requirement - Stories",
            description="Upload a link for stories recorded as evidence for this case."
        )

    def requirement_4(self):
        self.create_task(
            title="Media Requirement - Media/Press Reports",
            description="Upload a link for media/press reports about this case."
        )

    def requirement_5(self):
        self.create_task(
            title="Media Requirement - Recorded Video Interview",
            description="Upload a link for a recorded video interview as evidence for this case."
        )

    def requirement_6(self):
        self.create_task(
            title="Media Requirement - Live Video Interview",
            description="Make arrangements to have a live video interview."
        )

    def requirement_7(self):
        self.create_task(
            title="Media Requirement - Photo Thank You Letter",
            description="Upload a link for a photo Thank You letter taken as evidence for this case."
        )

    def requirement_8(self):
        self.create_task(
            title="Media Requirement - Written Thank You Letter",
            description="Upload a document or upload text of the Thank You Letter."
        )

    def requirement_9(self):
        self.create_task(
            title="Media Requirement - Live Broadcast",
            description="Make arrangements to have a live broadcast showcasing the case."
        )

    def requirement_10(self):
        self.create_task(
            title="Media Requirement - Promotional Video",
            description="Upload a link for images taken as evidence for this case."
        )

    def requirement_11(self):
        self.create_task(
            title="Financial Requirement - Invoices",
            description="Upload all invoices for transactions involving this case."
        )

    def requirement_12(self):
        self.create_task(
            title="Financial Requirement - Bank Notices (transfer/receipt)",
            description="Upload all bank notices for transactions involving this case."
        )

    def requirement_13(self):
        self.create_task(
            title="Financial Requirement - Securities",
            description="Upload all securities involving this case."
        )

    def requirement_14(self):
        self.create_task(
            title="Financial Requirement - Receipts (receipt/disbursement)",
            description="Upload all receipts for transactions involving this case."
        )

    def requirement_15(self):
        self.create_task(
            title="Implementation Requirement - Memorandum of Understanding",
            description="Upload a memorandum of understanding file for this case.",
            stage_id=2
        )

    def requirement_16(self):
        self.create_task(
            title="Implementation Requirement - Implementation Agreement",
            description="Upload an implementation agreement file for this case.",
            stage_id=2
        )

    def requirement_17(self):
        self.create_task(
            title="Implementation Requirement - Signed Statements",
            description="Upload signed statement files for this case."
        )

    def requirement_18(self):
        self.create_task(
            title="Implementation Requirement - Receipts Records",
            description="Upload receipts record files for this case."
        )

    def requirement_19(self):
        self.create_task(
            title="Implementation Requirement - Completion Records",
            description="Upload completion records files for this case."
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
