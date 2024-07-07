from api.models.projects import ProjectTask, TaskStatus


class ProjectRequirementProcessor:
    
    def __init__(self, project, user_id):
        self.user_id = user_id
        self.project = project
    
    def requirement_1(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Images',
           description= 'Upload a link for images taken as evidence for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate  
       )
       task.save()
    
    def requirement_2(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Videos',
           description= 'Upload a link for videos taken as evidence for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_3(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Stories',
           description= 'Upload a link for stories recorded as evidence for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_4(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Media/Press Reports',
           description= 'Upload a link for media/press reports about this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_5(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Recorded Video Interview',
           description= 'Upload a link for a recorded video interview as evidence for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_6(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Live Video Interview',
           description= 'Make arrangements to have a live video interview.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_7(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Photo Thank You Letter',
           description= 'Upload a link for a photo Thank You letter taken as evidence for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_8(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Written Thank You Letter',
           description= 'Upload a document or upload text of the Thank You Letter.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_9(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Live Broadcast',
           description= 'Make arrangements to have a live broadcast showcasing the project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_10(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Media Requirement - Promotional Video',
           description= 'Upload a link for images taken as evidence for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_11(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Financial Requirement - Invoices',
           description= 'Upload all invoices for transactions involving this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_12(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Financial Requirement - Bank Notices (transfer/receipt)',
           description= 'Upload all bank notices for transactions involving this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_13(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Financial Requirement - Securities',
           description= 'Upload all securities involving this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_14(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Financial Requirement - Receipts (receipt/disbursement)',
           description= 'Upload all receipts for transactions involving this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_15(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Implementation Requirement - Memorandum of Understanding',
           description= 'Upload an memorandum of understanding file for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=1,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_16(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Implementation Requirement - Implementation Agreement',
           description= 'Upload an implementation agreement file for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=1,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_17(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Implementation Requirement - Signed Beneficiary Lists',
           description= 'Upload specific excel sheet with specific beneficiary details for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate   
       )
       task.save()
    
    def requirement_18(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Implementation Requirement - Receipts Records',
           description= 'Upload receipts record files for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate  
       )
       task.save()
    
    def requirement_19(self):
       task =  ProjectTask(
           projectID = self.project.projectID,
           title= 'Implementation Requirement - Completion Records',
           description= 'Upload completion records files for this project.',
           assignedTo = [],
           cc = [],
           createdBy= self.user_id,
           attachedFiles= 'N/A',
           status= TaskStatus.TODO,
           stageID=3,
           startDate = self.project.startDate,
           deadline= self.project.dueDate  
       )
       task.save()
    
    def default_case(self):
        pass