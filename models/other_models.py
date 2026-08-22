from database.db import get_connection

class TargetModel:

    @staticmethod
    def set(user_id, subject, target):
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO targets (user_id, subject, target)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, subject)
                   DO UPDATE SET target = excluded.target""",
                (user_id, subject, float(target))
            )
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

    @staticmethod
    def get_by_user(user_id):
        conn = get_connection()
        targets = conn.execute(
            "SELECT * FROM targets WHERE user_id = ?", (user_id,)
        ).fetchall()
        conn.close()
        return {t['subject']: float(t['target']) for t in targets}


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
        except:
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
        except:
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
        except:
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
        except:
            return False
        finally:
            conn.close()
