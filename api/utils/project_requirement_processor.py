from api.models.projects import ProjectTask, Projects
from datetime import datetime, timedelta


class ProjectRequirementProcessor:
    
    def __init__(self, project_id):
        self.project_id = project_id
    
    def requirement_1(self):
       task =  ProjectTask(
           
       )