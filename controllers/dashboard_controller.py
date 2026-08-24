from flask import Blueprint, render_template, request, redirect, session, jsonify, make_response
from models.user_model import UserModel
from models.marks_model import MarksModel
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

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', 'local-secret-key')
dashboard = Blueprint('dashboard', __name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ── AI Chatbot ────────────────────────────────────────────────────────────────
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

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 600
    }
    try:
        res  = req.post(GROQ_URL, headers=headers, json=payload, timeout=15)
        data = res.json()
        return data['choices'][0]['message']['content']
    except:
        return "Sorry, I'm having trouble connecting. Please try again!"

# ── Dashboard ─────────────────────────────────────────────────────────────────
@dashboard.route('/dashboard')
@login_required
def index():
    user_id  = session['user_id']
    marks    = MarksModel.get_by_user(user_id)
    targets  = TargetModel.get_by_user(user_id)
    notes    = NoteModel.get_by_user(user_id)
    timetable= TimetableModel.get_by_user(user_id)
    stats    = MarksModel.calculate_stats(marks)
    badge    = MarksModel.get_badge(stats['avg']) if marks else None

    alerts = []
    for m in marks:
        if float(m['marks']) < 40:
            alerts.append(f"⚠️ FAIL ALERT: {m['subject']} — {m['marks']}/100. Immediate attention required!")
        elif float(m['marks']) < 50:
            alerts.append(f"🔔 WARNING: {m['subject']} — {m['marks']}/100 is below average.")

    recommendations = []
    subjects = []
    scores   = []
    target_scores = []
    for m in marks:
        t = targets.get(m['subject'], None)
        recommendations.append({
            'subject': m['subject'], 'marks': m['marks'],
            'target': t,
            'gap': round(t - float(m['marks']), 1) if t else None,
            'tip': MarksModel.get_recommendation(m['subject'], m['marks'])
        })
        subjects.append(m['subject'])
        scores.append(float(m['marks']))
        target_scores.append(float(t) if t else None)

    pwd_error   = request.args.get('pwd_error')
    pwd_success = request.args.get('pwd_success')

    return render_template('dashboard.html',
        name=session['name'], marks=marks, stats=stats,
        badge=badge, alerts=alerts, recommendations=recommendations,
        subjects=json.dumps(subjects), scores=json.dumps(scores),
        target_scores=json.dumps(target_scores), targets=targets,
        notes=notes, timetable=timetable,
        pwd_error=pwd_error, pwd_success=pwd_success)

# ── Marks ─────────────────────────────────────────────────────────────────────
@dashboard.route('/add_marks', methods=['POST'])
@login_required
def add_marks():
    subject  = request.form.get('subject', '')
    marks    = request.form.get('marks', '')
    semester = request.form.get('semester', 'Semester 1')
    errors   = MarksModel.validate_marks(subject, marks)
    if errors:
        return redirect(f'/dashboard?error={errors[0]}')
    MarksModel.add(session['user_id'], subject, marks, semester)
    return redirect('/dashboard')

@dashboard.route('/delete_mark/<int:mark_id>')
@login_required
def delete_mark(mark_id):
    MarksModel.delete(mark_id, session['user_id'])
    return redirect('/dashboard')

# ── Targets ───────────────────────────────────────────────────────────────────
@dashboard.route('/set_target', methods=['POST'])
@login_required
def set_target():
    subject = request.form.get('subject', '')
    target  = request.form.get('target', '')
    try:
        t = float(target)
        if 0 <= t <= 100:
            TargetModel.set(session['user_id'], subject, t)
    except:
        pass
    return redirect('/dashboard')

# ── Notes ─────────────────────────────────────────────────────────────────────
@dashboard.route('/add_note', methods=['POST'])
@login_required
def add_note():
    subject = request.form.get('subject', '')
    note    = request.form.get('note', '')
    NoteModel.add(session['user_id'], subject, note)
    return redirect('/dashboard')

@dashboard.route('/delete_note/<int:note_id>')
@login_required
def delete_note(note_id):
    NoteModel.delete(note_id, session['user_id'])
    return redirect('/dashboard')

# ── Timetable ─────────────────────────────────────────────────────────────────
@dashboard.route('/add_exam', methods=['POST'])
@login_required
def add_exam():
    subject   = request.form.get('subject', '')
    exam_date = request.form.get('exam_date', '')
    exam_time = request.form.get('exam_time', '')
    venue     = request.form.get('venue', '')
    TimetableModel.add(session['user_id'], subject, exam_date, exam_time, venue)
    return redirect('/dashboard')

@dashboard.route('/delete_exam/<int:exam_id>')
@login_required
def delete_exam(exam_id):
    TimetableModel.delete(exam_id, session['user_id'])
    return redirect('/dashboard')

# ── Chat ──────────────────────────────────────────────────────────────────────
@dashboard.route('/chat', methods=['POST'])
@login_required
def chat():
    data    = request.get_json()
    message = data.get('message', '').strip()
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
    user_id = session['user_id']
    marks   = MarksModel.get_by_user(user_id)
    if not marks:
        return redirect('/dashboard')

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

    story.append(Paragraph("📚 EduTrack", title_style))
    story.append(Paragraph("Student Performance Report", sub_style))
    story.append(Spacer(1, 10))

    info_data = [
        ['Student Name', session['name']],
        ['Username',     session['username']],
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

    marks_data = [['Subject','Marks','Grade','GPA','Status']]
    for m in marks:
        mv = float(m['marks'])
        marks_data.append([
            m['subject'], f"{m['marks']}/100",
            MarksModel.marks_to_grade(mv),
            str(MarksModel.marks_to_gpa(mv)),
            '✅ Pass' if mv >= 40 else '❌ Fail'
        ])

    marks_table = Table(marks_data, colWidths=[2.2*inch,1.2*inch,1*inch,1*inch,1.2*inch])
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
    response.headers['Content-Disposition'] = f'attachment; filename=EduTrack_Report_{session["username"]}.pdf'
    return response
