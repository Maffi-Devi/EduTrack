from flask import Blueprint, render_template, redirect, session
from models.user_model import UserModel
from models.marks_model import MarksModel

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
    for s in students:
        marks = MarksModel.get_by_user(s['id'])
        stats = MarksModel.calculate_stats(marks)
        student_data.append({
            'name': s['name'],
            'username': s['username'],
            'email': s['email'],
            'subjects': len(marks),
            'avg': stats['avg'],
            'grade': stats['grade'],
            'cgpa': stats['cgpa'],
            'joined': s['created_at']
        })
    return render_template('admin.html',
                           students=student_data,
                           total=len(student_data),
                           name=session['name'])
