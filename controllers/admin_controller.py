from flask import Blueprint, render_template, redirect, session, request, flash, url_for, abort
from models.user_model import UserModel
from models.marks_model import MarksModel, SEMESTERS
from models.other_models import TargetModel, NoteModel, TimetableModel
from controllers.dashboard_controller import build_report_pdf, target_status

admin = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@admin.route('/admin')
@admin_required
def admin_panel():
    students = UserModel.get_all_students()
    student_data = []
    all_scores = []
    semester_scores = {s: [] for s in SEMESTERS}
    for s in students:
        marks = MarksModel.get_by_user(s['id'])
        stats = MarksModel.calculate_stats(marks)
        for m in marks:
            all_scores.append(float(m['marks']))
            semester_scores.setdefault(m['semester'], []).append(float(m['marks']))
        student_data.append({
            'id': s['id'],
            'name': s['name'],
            'username': s['username'],
            'email': s['email'],
            'subjects': len(marks),
            'avg': stats['avg'],
            'grade': stats['grade'],
            'cgpa': stats['cgpa'],
            'failed': stats['failed'],
            'joined': s['created_at']
        })

    active = [d for d in student_data if d['subjects']]
    overview = {
        'total': len(student_data),
        'active': len(active),
        'no_marks': len(student_data) - len(active),
        'avg': round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
        'at_risk': sum(1 for d in student_data if d['failed']),
        'entries': len(all_scores),
    }
    semester_summary = [
        {'semester': sem, 'entries': len(sc),
         'avg': round(sum(sc) / len(sc), 2) if sc else None,
         'failed': sum(1 for x in sc if x < 40)}
        for sem, sc in semester_scores.items()
    ]
    top = sorted(active, key=lambda d: d['avg'], reverse=True)[:5]

    return render_template('admin.html',
                           students=student_data,
                           overview=overview,
                           semester_summary=semester_summary,
                           top=top,
                           name=session['name'],
                           pwd_error=request.args.get('pwd_error'),
                           pwd_success=request.args.get('pwd_success'))

@admin.route('/admin/student/<int:user_id>')
@admin_required
def student_detail(user_id):
    student = UserModel.get_student(user_id)
    if not student:
        abort(404)
    marks    = MarksModel.get_by_user(user_id)
    targets  = TargetModel.get_by_user(user_id)
    stats    = MarksModel.calculate_stats(marks)
    target_lookup = TargetModel.as_lookup(targets)

    by_semester = {}
    for m in marks:
        t = target_lookup.get((m['subject'].lower(), m['semester']))
        by_semester.setdefault(m['semester'], []).append({
            'row': m, 'target': t,
            'grade': MarksModel.marks_to_grade(float(m['marks'])),
            'status': target_status(t, float(m['marks'])) if t is not None else None,
        })
    semesters = [(s, by_semester[s]) for s in sorted(by_semester)]

    return render_template('admin_student.html',
                           student=student, stats=stats, semesters=semesters,
                           targets=targets,
                           notes=NoteModel.get_by_user(user_id),
                           timetable=TimetableModel.get_by_user(user_id),
                           name=session['name'])

@admin.route('/admin/student/<int:user_id>/pdf')
@admin_required
def student_pdf(user_id):
    student = UserModel.get_student(user_id)
    if not student:
        abort(404)
    report = build_report_pdf(user_id, student['name'], student['username'])
    if report is None:
        flash(f"{student['name']} has no marks yet, so there is no report.", 'error')
        return redirect(url_for('admin.student_detail', user_id=user_id))
    return report

@admin.route('/admin/student/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_student(user_id):
    student = UserModel.get_student(user_id)
    if student and UserModel.delete_student(user_id):
        flash(f"Student '{student['username']}' and all their data were deleted.", 'success')
    else:
        flash("Could not delete that student.", 'error')
    return redirect(url_for('admin.admin_panel'))
