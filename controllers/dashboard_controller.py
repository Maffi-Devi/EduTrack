from flask import Blueprint, render_template, request, redirect, session, jsonify, make_response, url_for, flash
from models.user_model import UserModel
from models.marks_model import MarksModel, SEMESTERS
from models.other_models import TargetModel, NoteModel, TimetableModel
from datetime import datetime
import requests as req
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import io
import os

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '').strip()
GROQ_MODEL   = os.environ.get('GROQ_MODEL', '').strip() or "qwen/qwen3.8-27b"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
dashboard = Blueprint('dashboard', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        if session.get('role') == 'admin':
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated

def back_to_dashboard(error=None, success=None):
    """Redirect to the dashboard, showing a one-time message there."""
    if error:   flash(error, 'error')
    if success: flash(success, 'success')
    return redirect(url_for('dashboard.index'))

def target_status(target, marks):
    """Compare a target with the marks scored for the same subject & semester."""
    if marks is None:
        return {'label': 'Marks pending', 'css': 'status-pending', 'gap': None}
    gap = round(target - marks, 1)
    if gap <= 0:
        return {'label': 'Achieved', 'css': 'status-good', 'gap': gap}
    return {'label': f'Need +{gap}', 'css': 'status-bad', 'gap': gap}

# ── AI Chatbot ────────────────────────────────────────────────────────────────
def offline_reply(user_message, marks_list):
    message = user_message.lower()
    average = None
    if marks_list:
        average = sum(float(mark['marks']) for mark in marks_list) / len(marks_list)

    if 'python' in message:
        return "Python ke liye pehle variables, conditions, loops aur functions samjho. Har concept ka ek chhota program likho, phir usme input validation aur error handling add karo."
    if 'database' in message or 'sql' in message:
        return "Database padhte waqt tables, primary key, foreign key aur SQL CRUD queries se shuru karo. Practice ke liye students aur marks ki do tables bana kar JOIN query try karo."
    if 'algorithm' in message or 'dsa' in message:
        return "DSA mein pehle problem ko input, output aur constraints mein tod do. Phir brute-force solution likho, uski time complexity nikalo, aur uske baad better approach dhoondo."
    if 'study' in message or 'exam' in message or 'padh' in message:
        return "Aaj ke liye 25-minute study session rakho: 15 minutes concept, 5 minutes bina notes recall, aur 5 minutes practice question. Har session ke end mein ek short summary likho."
    if 'marks' in message or 'score' in message or 'result' in message:
        if average is not None:
            return f"Aapka current average {average:.1f}% hai. Sabse kam marks wale subject ko priority do, uske weak topics ki list banao aur roz kam se kam 30 minutes targeted practice karo."
        return "Marks ka personalized advice dene ke liye pehle dashboard par apne subjects aur marks add kijiye."
    return "Main abhi offline mode mein hoon. Aap Python, SQL, DSA, study plan, exam preparation ya marks ke baare mein pooch sakte hain."

def ask_ai(user_message, marks_list):
    marks_summary = ""
    if marks_list:
        marks_summary = "Student's marks: " + ", ".join(
            [f"{m['subject']}: {m['marks']}/100" for m in marks_list])

    system_prompt = f"""You are EduBot, a friendly and strict academic assistant for MCA students.
{marks_summary}

Your rules:
1. Help students understand concepts, study strategies, exam tips, subject doubts.
2. Give personalized advice based on their actual marks.
3. If student asks to complete assignment/project/homework — REFUSE politely and say: "I can guide you step by step, but completing work for you won't help you learn!"
4. Keep responses clear, concise, encouraging.
5. For low marks subjects, proactively suggest improvement tips."""
    if not GROQ_API_KEY:
        return offline_reply(user_message, marks_list)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 600
    }
    try:
        res  = req.post(GROQ_URL, headers=headers, json=payload, timeout=15)
        if not res.ok:
            print(f"Groq API error {res.status_code}: {res.text[:200]}")
            return offline_reply(user_message, marks_list)
        data = res.json()
        return data['choices'][0]['message']['content']
    except (req.RequestException, KeyError, ValueError):
        return offline_reply(user_message, marks_list)

# ── Dashboard ─────────────────────────────────────────────────────────────────
@dashboard.route('/dashboard')
@login_required
def index():
    user_id  = session['user_id']
    marks    = MarksModel.get_by_user(user_id)
    targets  = TargetModel.get_by_user(user_id)
    target_lookup = TargetModel.as_lookup(targets)
    notes    = NoteModel.get_by_user(user_id)
    timetable= TimetableModel.get_by_user(user_id)
    stats    = MarksModel.calculate_stats(marks)
    badge    = MarksModel.get_badge(stats['avg']) if marks else None

    alerts = []
    for m in marks:
        if float(m['marks']) < 40:
            alerts.append(f"⚠️ FAIL ALERT: {m['subject']} ({m['semester']}) — {m['marks']}/100. Immediate attention required!")
        elif float(m['marks']) < 50:
            alerts.append(f"🔔 WARNING: {m['subject']} ({m['semester']}) — {m['marks']}/100 is below average.")

    # One row per marks entry, joined with the target of the same subject + semester
    marks_rows = []
    recommendations = []
    subjects = []
    scores   = []
    target_scores = []
    for m in marks:
        t = target_lookup.get((m['subject'].lower(), m['semester']))
        status = target_status(t, float(m['marks'])) if t is not None else None
        marks_rows.append({'row': m, 'target': t, 'status': status,
                           'grade': MarksModel.marks_to_grade(float(m['marks'])),
                           'gpa': MarksModel.marks_to_gpa(float(m['marks']))})
        recommendations.append({
            'subject': m['subject'], 'semester': m['semester'], 'marks': m['marks'],
            'target': t,
            'tip': MarksModel.get_recommendation(m['subject'], m['marks'])
        })
        subjects.append(f"{m['subject']} ({m['semester'].replace('Semester ', 'Sem ')})")
        scores.append(float(m['marks']))
        target_scores.append(t)

    # Every target, including ones whose marks are not added yet
    marks_lookup = {(m['subject'].lower(), m['semester']): float(m['marks']) for m in marks}
    target_rows = []
    for t in targets:
        scored = marks_lookup.get((t['subject'].lower(), t['semester']))
        target_rows.append({'row': t, 'marks': scored,
                            'status': target_status(float(t['target']), scored)})
    achieved = sum(1 for r in target_rows if r['status']['css'] == 'status-good')

    # Suggestions for the subject box: every subject already used in marks or targets
    known_subjects = sorted({m['subject'] for m in marks} | {t['subject'] for t in targets}, key=str.lower)

    pwd_error   = request.args.get('pwd_error')
    pwd_success = request.args.get('pwd_success')

    return render_template('dashboard.html',
        name=session['name'], marks=marks, stats=stats,
        badge=badge, alerts=alerts, recommendations=recommendations,
        subjects=json.dumps(subjects), scores=json.dumps(scores),
        target_scores=json.dumps(target_scores),
        marks_rows=marks_rows, target_rows=target_rows, achieved=achieved,
        semesters=SEMESTERS, known_subjects=known_subjects,
        notes=notes, timetable=timetable,
        pwd_error=pwd_error, pwd_success=pwd_success)

# ── Marks ─────────────────────────────────────────────────────────────────────
@dashboard.route('/add_marks', methods=['POST'])
@login_required
def add_marks():
    subject  = request.form.get('subject', '')
    marks    = request.form.get('marks', '')
    semester = request.form.get('semester', 'Semester 1')
    errors   = MarksModel.validate_marks(subject, marks, semester)
    if errors:
        return back_to_dashboard(error=errors[0])
    if MarksModel.exists(session['user_id'], subject, semester):
        return back_to_dashboard(error=f"Marks for {MarksModel.clean_subject(subject)} in {semester} are already added. Delete the old entry to change them.")
    MarksModel.add(session['user_id'], subject, marks, semester)
    return back_to_dashboard(success="Marks added successfully!")

@dashboard.route('/delete_mark/<int:mark_id>', methods=['POST'])
@login_required
def delete_mark(mark_id):
    MarksModel.delete(mark_id, session['user_id'])
    return back_to_dashboard(success="Marks entry deleted.")

# ── Targets ───────────────────────────────────────────────────────────────────
@dashboard.route('/set_target', methods=['POST'])
@login_required
def set_target():
    subject  = request.form.get('subject', '')
    semester = request.form.get('semester', '')
    target   = request.form.get('target', '')
    errors   = TargetModel.validate(subject, semester, target)
    if errors:
        return back_to_dashboard(error=errors[0])
    if not TargetModel.set(session['user_id'], subject, semester, target):
        return back_to_dashboard(error="Failed to save target. Please try again.")
    return back_to_dashboard(success=f"Target saved for {MarksModel.clean_subject(subject)} ({semester}).")

@dashboard.route('/delete_target/<int:target_id>', methods=['POST'])
@login_required
def delete_target(target_id):
    TargetModel.delete(target_id, session['user_id'])
    return back_to_dashboard(success="Target deleted.")

# ── Notes ─────────────────────────────────────────────────────────────────────
@dashboard.route('/add_note', methods=['POST'])
@login_required
def add_note():
    subject = request.form.get('subject', '')
    note    = request.form.get('note', '')
    ok, message = NoteModel.add(session['user_id'], subject, note)
    return back_to_dashboard(success=message) if ok else back_to_dashboard(error=message)

@dashboard.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    NoteModel.delete(note_id, session['user_id'])
    return back_to_dashboard(success="Note deleted.")

# ── Timetable ─────────────────────────────────────────────────────────────────
@dashboard.route('/add_exam', methods=['POST'])
@login_required
def add_exam():
    subject   = request.form.get('subject', '')
    exam_date = request.form.get('exam_date', '')
    exam_time = request.form.get('exam_time', '')
    venue     = request.form.get('venue', '')
    ok, message = TimetableModel.add(session['user_id'], subject, exam_date, exam_time, venue)
    return back_to_dashboard(success=message) if ok else back_to_dashboard(error=message)

@dashboard.route('/delete_exam/<int:exam_id>', methods=['POST'])
@login_required
def delete_exam(exam_id):
    TimetableModel.delete(exam_id, session['user_id'])
    return back_to_dashboard(success="Exam removed from timetable.")

# ── Chat ──────────────────────────────────────────────────────────────────────
@dashboard.route('/chat', methods=['POST'])
@login_required
def chat():
    data    = request.get_json(silent=True) or {}
    message = str(data.get('message', '')).strip()
    if not message:
        return jsonify({'reply': 'Please type a message!'})
    if len(message) > 500:
        return jsonify({'reply': 'Message too long. Please keep it under 500 characters.'})
    marks = MarksModel.get_by_user(session['user_id'])
    reply = ask_ai(message, marks)
    return jsonify({'reply': reply})

# ── PDF ───────────────────────────────────────────────────────────────────────
@dashboard.route('/download_pdf')
@login_required
def download_pdf():
    report = build_report_pdf(session['user_id'], session['name'], session['username'])
    if report is None:
        return back_to_dashboard(error="Add some marks first to download a report.")
    return report

def build_report_pdf(user_id, student_name, username):
    """PDF performance report for one student, or None when they have no marks.
    Shared by the student dashboard and the admin panel."""
    marks   = MarksModel.get_by_user(user_id)
    if not marks:
        return None

    stats = MarksModel.calculate_stats(marks)
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=40, leftMargin=40,
                                topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story  = []

    title_style = ParagraphStyle('title', fontSize=22, fontName='Helvetica-Bold',
                                    textColor=colors.HexColor('#1a1a2e'), alignment=1, spaceAfter=6)
    sub_style   = ParagraphStyle('sub', fontSize=12,
                                    textColor=colors.HexColor('#4e54c8'), alignment=1, spaceAfter=20)
    head_style  = ParagraphStyle('head', fontSize=13, fontName='Helvetica-Bold',
                                    textColor=colors.HexColor('#1a1a2e'), spaceAfter=8, spaceBefore=12)

    story.append(Paragraph("EduTrack", title_style))
    story.append(Paragraph("Student Performance Report", sub_style))
    story.append(Spacer(1, 10))

    info_data = [
        ['Student Name', student_name],
        ['Username',     username],
        ['Report Date',  datetime.now().strftime('%d %B %Y')],
        ['Overall Grade',stats['grade']],
        ['Average Score',f"{stats['avg']}%"],
        ['CGPA',         f"{stats['cgpa']} / 10"],
        ['Subjects Passed', str(stats['passed'])],
        ['Subjects Failed', str(stats['failed'])],
    ]
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),11),
        ('PADDING',(0,0),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#dddddd')),
    ]))
    story.append(info_table)
    story.append(Spacer(1,15))
    story.append(Paragraph("Subject-wise Performance", head_style))

    target_lookup = TargetModel.as_lookup(TargetModel.get_by_user(user_id))
    marks_data = [['Subject','Semester','Marks','Target','Grade','GPA','Status']]
    for m in marks:
        mv = float(m['marks'])
        t  = target_lookup.get((m['subject'].lower(), m['semester']))
        marks_data.append([
            m['subject'], m['semester'], f"{m['marks']}/100",
            f"{t:g}" if t is not None else '-',
            MarksModel.marks_to_grade(mv),
            str(MarksModel.marks_to_gpa(mv)),
            'Pass' if mv >= 40 else 'Fail'
        ])

    marks_table = Table(marks_data, colWidths=[1.7*inch,1*inch,0.9*inch,0.7*inch,0.7*inch,0.6*inch,0.9*inch])
    marks_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#4e54c8')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),10),
        ('PADDING',(0,0),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#dddddd')),
        ('ALIGN',(1,0),(-1,-1),'CENTER'),
    ]))
    story.append(marks_table)
    story.append(Spacer(1,15))
    story.append(Paragraph("AI Study Recommendations", head_style))
    for m in marks:
        tip = MarksModel.get_recommendation(m['subject'], m['marks'])
        story.append(Paragraph(f"• <b>{m['subject']}:</b> {tip}", styles['Normal']))
        story.append(Spacer(1,4))

    story.append(Spacer(1,20))
    story.append(Paragraph(
        f"Generated by EduTrack on {datetime.now().strftime('%d %B %Y %I:%M %p')}",
        ParagraphStyle('footer', fontSize=9, textColor=colors.grey, alignment=1)
    ))
    doc.build(story)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=EduTrack_Report_{username}.pdf'
    return response
