from api.models.cases import CaseCat


class CaseCategoryCalculator:

    def __init__(self, case) -> None:
        self.case = case

    def main_questions_points(self) -> int:
        points = 0
        priority_nature = [
            "health(direct)",
            "basic and university education",
            "life support",
            "shelter",
        ]

        if self.case.question1["questionChoice"].lower() in priority_nature:
            points += 10

        if self.case.question2["questionChoice"].lower() == "yes":
            points += 10

        if self.case.question3["questionChoice"].lower() == "yes":
            points += 10

        return points

    def sub_questions_points(self) -> int:
        """
        Go through the sub questions (4 to 9) and check how many are "yes"
        """
        points = 0
        for i in range(4, 10):
            attr_name = f"question{i}"
            if hasattr(self.case, attr_name):
                attr_value = getattr(self.case, attr_name)
                if attr_value["questionChoice"].lower() == "yes":
                    points += 5
                else:
                    pass

        return points

    def calculate_category(self) -> None:
        """
        Calculates the final category as follows:
            - Category = A if main_question_points >= 20 and sub_question_yes_points >= 10
            - Category = B if main_question_points = 10 and sub_question_yes_points >= 10
            - Category = D if all_questions points = 0
            - Category = C if none of the above qualify

        """
        main_q_points = self.main_questions_points()
        print(f"Main Q points: {main_q_points}")
        sub_q_points = self.sub_questions_points()
        print(f"Sub Q points: {sub_q_points}")
        # save the total points (we only interested in the positive answers)
        self.case.total_points = main_q_points + sub_q_points
        print(f"Total Q points: {self.case.total_points}")
        if main_q_points >= 20 and sub_q_points >= 10:
            self.case.category = CaseCat.A
            self.case.save()
            return
        elif main_q_points == 10 and sub_q_points >= 10:
            self.case.category = CaseCat.B
            self.case.save()
            return
        elif self.case.total_points == 0:
            self.case.category = CaseCat.D
            self.case.save()
            return
        else:
            self.case.category = CaseCat.C
            self.case.save()
            return
