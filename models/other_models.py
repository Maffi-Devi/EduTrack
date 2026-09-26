from database.db import get_connection
from models.marks_model import MarksModel, SEMESTERS

class TargetModel:

    @staticmethod
    def validate(subject, semester, target):
        errors = MarksModel.validate_subject(subject)
        if semester not in SEMESTERS:
            errors.append("Please select a valid semester.")
        try:
            t = float(target)
            if t < 0 or t > 100:
                errors.append("Target must be between 0 and 100.")
        except (TypeError, ValueError):
            errors.append("Please enter a valid numeric target.")
        return errors

    @staticmethod
    def set(user_id, subject, semester, target):
        """Update the target if this subject (any letter case) already has one
        in the same semester, otherwise insert a new target."""
        subject = MarksModel.clean_subject(subject)
        conn = get_connection()
        try:
            cur = conn.execute(
                """UPDATE targets SET target = ?
                   WHERE user_id = ? AND LOWER(subject) = LOWER(?) AND semester = ?""",
                (float(target), user_id, subject, semester)
            )
            if cur.rowcount == 0:
                conn.execute(
                    "INSERT INTO targets (user_id, subject, semester, target) VALUES (?, ?, ?, ?)",
                    (user_id, subject, semester, float(target))
                )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def get_by_user(user_id):
        conn = get_connection()
        targets = conn.execute(
            "SELECT * FROM targets WHERE user_id = ? ORDER BY semester, subject",
            (user_id,)
        ).fetchall()
        conn.close()
        return targets

    @staticmethod
    def as_lookup(targets):
        """Map (subject, semester) -> target so marks rows can find their target."""
        return {(t['subject'].lower(), t['semester']): float(t['target']) for t in targets}

    @staticmethod
    def delete(target_id, user_id):
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM targets WHERE id = ? AND user_id = ?",
                (target_id, user_id)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()


class NoteModel:

    @staticmethod
    def add(user_id, subject, note):
        errors = []
        if not subject or len(subject.strip()) < 2:
            errors.append("Subject name is required.")
        if not note or len(note.strip()) < 3:
            errors.append("Note content is required.")
        if errors:
            return False, errors[0]
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO notes (user_id, subject, note) VALUES (?, ?, ?)",
                (user_id, subject.strip(), note.strip())
            )
            conn.commit()
            return True, "Note added!"
        except Exception:
            return False, "Failed to add note."
        finally:
            conn.close()

    @staticmethod
    def get_by_user(user_id):
        conn = get_connection()
        notes = conn.execute(
            "SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        conn.close()
        return notes

    @staticmethod
    def delete(note_id, user_id):
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM notes WHERE id = ? AND user_id = ?",
                (note_id, user_id)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()


class TimetableModel:

    @staticmethod
    def add(user_id, subject, exam_date, exam_time, venue):
        errors = []
        if not subject or len(subject.strip()) < 2:
            errors.append("Subject name is required.")
        if not exam_date:
            errors.append("Exam date is required.")
        if errors:
            return False, errors[0]
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO timetable (user_id, subject, exam_date, exam_time, venue) VALUES (?, ?, ?, ?, ?)",
                (user_id, subject.strip(), exam_date, exam_time, venue.strip() if venue else '')
            )
            conn.commit()
            return True, "Exam added to timetable!"
        except Exception:
            return False, "Failed to add exam."
        finally:
            conn.close()

    @staticmethod
    def get_by_user(user_id):
        conn = get_connection()
        exams = conn.execute(
            "SELECT * FROM timetable WHERE user_id = ? ORDER BY exam_date ASC",
            (user_id,)
        ).fetchall()
        conn.close()
        return exams

    @staticmethod
    def delete(exam_id, user_id):
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM timetable WHERE id = ? AND user_id = ?",
                (exam_id, user_id)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
