from api.models.projects import Category


class ProjectCategoryCalculator:

    def __init__(self, project, assessment_answers):
        self.project = project
        self.assessment_answers = assessment_answers
        self.points_for_cat_a = 0
        self.points_for_c = 0

    def scopeforA(self, scope_str):
        importantScopes = ["0", "3", "11"]
        if scope_str in importantScopes:
            self.points_for_cat_a += 10
        else:
            self.points_for_cat_a += 0

    def budgetforA(self, budget_str):
        if budget_str.lower() == "available/full amount committed":
            self.points_for_cat_a += 10
        else:
            self.points_for_cat_a += 0

    def natureforA(self, nature_str):
        important_nature = ["0", "1", "11"]
        if nature_str in important_nature:
            self.points_for_cat_a += 10
        else:
            self.points_for_cat_a += 0

    def engagementforA(self, engagement):
        important_engagement = ["from one of the gotg's offices", "important donor"]
        if engagement.lower() in important_engagement:
            self.points_for_cat_a += 10
        else:
            self.points_for_cat_a += 0

    def controlforA(self, control_str):
        if control_str.lower() == "i have full control":
            self.points_for_cat_a += 10
        else:
            self.points_for_cat_a += 0

    def legalforA(self, legal_str):
        if legal_str.lower() == "registered":
            self.points_for_cat_a += 10
        else:
            self.points_for_cat_a += 0

    def budgetforC(self, budget):
        if budget.lower() == "no budget/commitment":
            self.points_for_c += 10
        else:
            self.points_for_c += 0

    def legalforC(self, legal):
        if legal.lower() == "not registered":
            self.points_for_c += 10
        else:
            self.points_for_c += 0

    def calculateCategory(self):
        # 1. Budget
        budget_dict = {
            "budgetAvailability": {
                "Available/full amount committed": 3,
                "Partially available/commitment of more than 50%": 2,
                "Partially available/commitment of less than 50%": 1,
                "No budget/commitment": 0,
            },
            "budgetSize": {
                "Less than 10 thousand": 3,
                "Between 10 thousand and 20 thousand": 2,
                "20 to 50 thousand": 1,
                "Above 50 thousand": 0,
            },
        }

        # 2. Project priority for the institution
        project_priority_dict = {
            "projectScope": {
                "0": 3,
                "1": 2,
                "2": 1,
                "3": 3,
                "4": -1,
                "5": 3,
                "6": 1,
                "7": 2,
                "8": 1,
                "9": 2,
                "10": 1,
                "11": 3,
                "12": -1,
            },
            "projectNature": {"0": 4, "1": 4, "2": 3, "3": 2, "4": 1},
            "projectEngagements": {
                "From one of the GOTG's offices": 3,
                "Important donor": 3,
                "International entity": 1,
                "Strategic partner": 1,
                "The project is landmark and has added value for the institution": 1,
            },
        }

        # 3. The importance of the project to the region
        importance_dict = {
            "beneficiaryCategory": {"0": 3, "1": 3, "2": 2, "3": 2, "4": 1, "5": 1},
            "projectRecommendation": {
                "Strong recommendation": 2,
                "Moderate recommendation": 1,
                "None": 0,
            },
            "areaConditions": {
                "No similar or alternative service exists": 1,
                "Similar or alternative service exists": -1,
            },
            "projectImpact": {
                "Represents a creative idea or achieves a distinguished impact": 3,
                "Not a creative idea and does not achieve a distinguished impact": 0,
            },
        }

        # 4. Implementation and procedures
        implementation_dict = {
            "controlAndCommand": {
                "I have full control": 2,
                "Participatory": 1,
                "Out of my administration": -1,
            },
            "licenses": {"Easy": 1, "Difficult": -1},
            "duration": {"Short": 1, "Long": 0},
            "projectLegality": {"Registered": 0, "Not Registered": -3},
        }

        # 5. Marketing project opportunities
        marketing_dict = {
            "marketing": {
                "Self-marketing": 3,
                "Potential donor exists": 2,
                "Requires marketing plan": 1,
                "Difficult to market": -1,
            }
        }

        total_points = 0

        # look at each answer on the string list
        for answer in self.assessment_answers:
            # Convert the answer to lowercase for case-insensitive matching
            answer_lower = answer.lower()
            self.budgetforA(answer_lower)
            self.engagementforA(answer_lower)
            self.legalforA(answer_lower)
            self.controlforA(answer_lower)

            # Check each dictionary for points
            for category_dict in [
                budget_dict,
                project_priority_dict,
                importance_dict,
                implementation_dict,
                marketing_dict,
            ]:
                for section, options in category_dict.items():
                    # Convert each option key to lowercase for case-insensitive matching
                    options_lower = {
                        key.lower(): value for key, value in options.items()
                    }

                    # Check if the lowercase answer is in the lowercase options
                    if answer_lower in options_lower:
                        points = options_lower.get(answer_lower, 0)
                        total_points += points
                        break  # Exit the inner loop once the answer is found in the current section's options

        # now let's process the project data
        points = importance_dict["beneficiaryCategory"].get(
            str(self.project.beneficiaryCategory), 0
        )
        total_points += points
        points = project_priority_dict["projectNature"].get(
            str(self.project.projectNature), 0
        )
        total_points += points
        points = project_priority_dict["projectScope"].get(
            str(self.project.projectScope), 0
        )
        total_points += points

        self.scopeforA(str(self.project.projectScope))
        self.natureforA(str(self.project.projectNature))

        self.project.totalPoints = total_points

        print(f"Total points {total_points}")
        print(f"A points {self.points_for_cat_a}")
        print(f"C points {self.points_for_c}")

        # use the combined answers to check for the logic of which category to assign

        if total_points <= 10 or self.points_for_c == 20:
            self.project.category = Category.C
            self.project.save()
            print(f"Category {self.project.category.value}")
            return
        elif self.points_for_cat_a >= 40:
            self.project.category = Category.A
            self.project.save()
            print(f"Category {self.project.category.value}")
            return
        else:
            self.project.category = Category.B
            self.project.save()
            print(f"Category {self.project.category.value}")
            return
