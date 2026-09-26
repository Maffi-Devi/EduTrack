from database.db import get_connection

SEMESTERS = ['Semester 1', 'Semester 2', 'Semester 3', 'Semester 4']

class MarksModel:

    @staticmethod
    def clean_subject(subject):
        """Trim and collapse extra spaces so 'DBMS ' and 'DBMS' are the same subject."""
        return ' '.join((subject or '').split())

    @staticmethod
    def validate_subject(subject):
        errors = []
        subject = MarksModel.clean_subject(subject)
        if len(subject) < 2:
            errors.append("Subject name must be at least 2 characters.")
        elif not subject.replace(' ', '').replace('-', '').isalnum():
            errors.append("Subject name can only contain letters, numbers, spaces, hyphens.")
        return errors

    @staticmethod
    def validate_marks(subject, marks, semester='Semester 1'):
        errors = MarksModel.validate_subject(subject)
        if semester not in SEMESTERS:
            errors.append("Please select a valid semester.")
        try:
            m = float(marks)
            if m < 0 or m > 100:
                errors.append("Marks must be between 0 and 100.")
        except (TypeError, ValueError):
            errors.append("Please enter valid numeric marks.")
        return errors

    @staticmethod
    def exists(user_id, subject, semester):
        conn = get_connection()
        row = conn.execute(
            "SELECT 1 FROM marks WHERE user_id = ? AND LOWER(subject) = LOWER(?) AND semester = ?",
            (user_id, MarksModel.clean_subject(subject), semester)
        ).fetchone()
        conn.close()
        return row is not None

    @staticmethod
    def add(user_id, subject, marks, semester="Semester 1"):
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO marks (user_id, subject, marks, semester) VALUES (?, ?, ?, ?)",
                (user_id, MarksModel.clean_subject(subject), float(marks), semester)
            )
            conn.commit()
            return True, "Marks added successfully!"
        except Exception as e:
            return False, "Failed to add marks. Please try again."
        finally:
            conn.close()

    @staticmethod
    def get_by_user(user_id):
        conn = get_connection()
        marks = conn.execute(
            "SELECT * FROM marks WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        conn.close()
        return marks

    @staticmethod
    def delete(mark_id, user_id):
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM marks WHERE id = ? AND user_id = ?",
                (mark_id, user_id)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def calculate_stats(marks_list):
        if not marks_list:
            return {'avg': 0, 'grade': 'N/A', 'gpa': 0.0, 'cgpa': 0.0,
                    'highest': 0, 'lowest': 0, 'passed': 0, 'failed': 0}

        scores = [float(m['marks']) for m in marks_list]
        avg    = round(sum(scores) / len(scores), 2)
        highest= round(max(scores), 2)
        lowest = round(min(scores), 2)
        passed = sum(1 for s in scores if s >= 40)
        failed = len(scores) - passed

        gpas   = [MarksModel.marks_to_gpa(s) for s in scores]
        cgpa   = round(sum(gpas) / len(gpas), 2)
        gpa    = MarksModel.marks_to_gpa(avg)
        grade  = MarksModel.marks_to_grade(avg)

        return {'avg': avg, 'grade': grade, 'gpa': gpa, 'cgpa': cgpa,
                'highest': highest, 'lowest': lowest,
                'passed': passed, 'failed': failed}

    @staticmethod
    def marks_to_grade(marks):
        if marks >= 90: return 'A+'
        elif marks >= 80: return 'A'
        elif marks >= 70: return 'B+'
        elif marks >= 60: return 'B'
        elif marks >= 50: return 'C'
        elif marks >= 40: return 'D'
        else: return 'F'

    @staticmethod
    def marks_to_gpa(marks):
        if marks >= 90: return 10.0
        elif marks >= 80: return 9.0
        elif marks >= 70: return 8.0
        elif marks >= 60: return 7.0
        elif marks >= 50: return 6.0
        elif marks >= 40: return 5.0
        else: return 0.0

    @staticmethod
    def get_badge(avg):
        if avg >= 90: return {'icon':'🥇','name':'Gold Scholar','color':'#FFD700'}
        elif avg >= 80: return {'icon':'🥈','name':'Silver Star','color':'#C0C0C0'}
        elif avg >= 70: return {'icon':'🥉','name':'Bronze Achiever','color':'#CD7F32'}
        elif avg >= 60: return {'icon':'📘','name':'Steady Learner','color':'#4e54c8'}
        elif avg >= 40: return {'icon':'💪','name':'Keep Going','color':'#f39c12'}
        else: return {'icon':'🚨','name':'Needs Attention','color':'#e74c3c'}

    @staticmethod
    def get_recommendation(subject, marks):
        marks = float(marks)
        if marks >= 80: return f"Excellent in {subject}! Keep it up."
        elif marks >= 60: return f"Good in {subject}. Practice more to reach excellence."
        elif marks >= 40: return f"Average in {subject}. Focus on core concepts."
        else: return f"Need improvement in {subject}. Seek teacher help immediately."
