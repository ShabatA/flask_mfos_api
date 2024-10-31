from api.models.cases import CaseCat

class CaseCategoryCalculator:

    def __init__(self, case) -> None:
        self.case = case

    def main_questions_points(self) -> int:
        """
        Calculate points for main questions (1 to 3).
        """
        points = 0
        priority_nature = [
            "health(direct)",
            "basic and university education",
            "life support",
            "shelter",
            "living support"
        ]
        
        # Question 1
        question1_choice = self.case.question1["questionChoice"].strip().lower()
        # print("Question 1:", question1_choice)
        if question1_choice == "yes":
            points += 10
            # print("Matched priority nature, added 10 points for Question 1")

        # Question 2
        question2_choice = self.case.question2["questionChoice"].strip().lower()
        # print("Question 2:", question2_choice)
        if question2_choice == "yes":
            points += 10
            # print("Question 2 is 'yes', added 10 points")

        # Question 3
        question3_choice = self.case.question3["questionChoice"].strip().lower()

        # Check the condition with priority_nature
        if question3_choice in priority_nature:
            points += 10
            # print("Question 3 matches criteria, added 10 points")

        # print("Total main question points:", points)
        return points

    def sub_questions_points(self) -> int:
        """
        Calculate points for sub-questions (4 to 9).
        """
        points = 0
        for i in range(4, 10):
            attr_name = f"question{i}"
            if hasattr(self.case, attr_name):
                attr_value = getattr(self.case, attr_name)
                if attr_value.get("questionChoice", "").lower() == "yes":
                    points += 5
        print(points)
        return points

    def calculate_category(self) -> str:
        """
        Determines the category of the case based on calculated points:
            - Category A: main_question_points >= 20 and sub_question_points >= 10
            - Category B: main_question_points == 10 and sub_question_points >= 10
            - Category D: total points == 0
            - Category C: Default if none of the above qualify
        """
        main_q_points = self.main_questions_points()
        sub_q_points = self.sub_questions_points()
        total_points = main_q_points + sub_q_points

        # Assign category based on point conditions
        if main_q_points >= 20 and sub_q_points >= 10:
            self.case.category = CaseCat.A
        elif main_q_points == 10 and sub_q_points >= 10:
            self.case.category = CaseCat.B
        elif total_points == 0:
            self.case.category = CaseCat.D
        else:
            self.case.category = CaseCat.C

        # Save the category and total points
        self.case.total_points = total_points
        self.case.save()
        
        # Return the assigned category for confirmation
        return self.case.category
