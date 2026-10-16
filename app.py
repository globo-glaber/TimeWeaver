import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'schedule-generator-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- CONSTANTS ---
DAYS_OF_WEEK = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"]

DEFAULT_SLOTS = [
    {"slot_number": 1, "start_time": "08:00", "end_time": "09:20"},
    {"slot_number": 2, "start_time": "09:35", "end_time": "10:55"},
    {"slot_number": 3, "start_time": "11:10", "end_time": "12:30"},
    {"slot_number": 4, "start_time": "13:00", "end_time": "14:20"},
    {"slot_number": 5, "start_time": "14:35", "end_time": "15:55"},
    {"slot_number": 6, "start_time": "16:10", "end_time": "17:30"},
    {"slot_number": 7, "start_time": "17:40", "end_time": "19:00"},
]

# --- MODELS ---
class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    student_count = db.Column(db.Integer, default=25)
    subjects = db.relationship('Subject', backref='group', cascade="all, delete-orphan", lazy=True)
    schedule_entries = db.relationship('ScheduleEntry', backref='group', cascade="all, delete-orphan", lazy=True)

class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(50), default="Викладач")
    color = db.Column(db.String(20), default="#0284c7")
    subjects = db.relationship('Subject', backref='teacher', cascade="all, delete-orphan", lazy=True)
    preferences = db.relationship('TeacherPreference', backref='teacher', cascade="all, delete-orphan", lazy=True)
    schedule_entries = db.relationship('ScheduleEntry', backref='teacher', cascade="all, delete-orphan", lazy=True)

class Classroom(db.Model):
    __tablename__ = 'classrooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    capacity = db.Column(db.Integer, default=30)
    room_type = db.Column(db.String(50), default="Загальна")
    schedule_entries = db.relationship('ScheduleEntry', backref='classroom', cascade="all, delete-orphan", lazy=True)

class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.Integer, nullable=False, unique=True)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    hours_per_week = db.Column(db.Integer, default=2)
    subject_type = db.Column(db.String(50), default="Лекція")
    room_type_required = db.Column(db.String(50), default="Будь-яка")
    schedule_entries = db.relationship('ScheduleEntry', backref='subject', cascade="all, delete-orphan", lazy=True)

class TeacherPreference(db.Model):
    __tablename__ = 'teacher_preferences'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    slot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="neutral")

    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'day_of_week', 'slot_number', name='_teacher_slot_uc'),
    )

class ScheduleEntry(db.Model):
    __tablename__ = 'schedule_entries'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)
    slot_number = db.Column(db.Integer, nullable=False)


@app.context_processor
def inject_constants():
    return dict(DAYS_OF_WEEK=DAYS_OF_WEEK)

# --- ROUTES ---

@app.route('/')
def index():
    groups = Group.query.order_by(Group.name).all()
    teachers = Teacher.query.order_by(Teacher.name).all()
    classrooms = Classroom.query.order_by(Classroom.name).all()
    subjects = Subject.query.all()
    time_slots = TimeSlot.query.order_by(TimeSlot.slot_number).all()
    
    selected_view = request.args.get('view', 'official')
    selected_id = request.args.get('id', type=int)

    if not selected_id and groups and selected_view in ['official', 'group']:
        selected_id = groups[0].id

    schedule_grid = {}
    total_entries = ScheduleEntry.query.count()

    for day in DAYS_OF_WEEK:
        schedule_grid[day] = {slot.slot_number: [] for slot in time_slots}

    entries_query = ScheduleEntry.query
    if selected_view in ['group', 'official'] and selected_id:
        entries_query = entries_query.filter_by(group_id=selected_id)
    elif selected_view == 'teacher' and selected_id:
        entries_query = entries_query.filter_by(teacher_id=selected_id)
    elif selected_view == 'classroom' and selected_id:
        entries_query = entries_query.filter_by(classroom_id=selected_id)

    entries = entries_query.all()
    for entry in entries:
        if entry.day_of_week in schedule_grid and entry.slot_number in schedule_grid[entry.day_of_week]:
            schedule_grid[entry.day_of_week][entry.slot_number].append(entry)

    pref_stats = get_preference_satisfaction_stats()
    selected_group = db.session.get(Group, selected_id) if selected_id and selected_view in ['official', 'group'] else None

    return render_template('index.html',
                           groups=groups,
                           teachers=teachers,
                           classrooms=classrooms,
                           subjects=subjects,
                           time_slots=time_slots,
                           schedule_grid=schedule_grid,
                           selected_view=selected_view,
                           selected_id=selected_id,
                           selected_group=selected_group,
                           total_entries=total_entries,
                           pref_stats=pref_stats)


@app.route('/generate', methods=['POST'])
def generate_schedule():
    from scheduler import generate_full_schedule
    success, message, stats = generate_full_schedule()
    if success:
        flash(f"✨ {message}! Задоволено {stats.get('satisfaction_rate', 100)}% побажань викладачів.", "success")
    else:
        flash(f"⚠️ {message}", "danger")
    return redirect(url_for('index'))


@app.route('/clear-all', methods=['POST', 'GET'])
def clear_all():
    """Clears all data and initializes exact slots from Photo 1."""
    ScheduleEntry.query.delete()
    Subject.query.delete()
    TeacherPreference.query.delete()
    Teacher.query.delete()
    Group.query.delete()
    Classroom.query.delete()
    TimeSlot.query.delete()
    db.session.commit()

    for s in DEFAULT_SLOTS:
        db.session.add(TimeSlot(slot_number=s['slot_number'], start_time=s['start_time'], end_time=s['end_time']))
    db.session.commit()

    flash("🧹 Усі викладачі, групи, аудиторії та предмети успішно видалені!", "success")
    return redirect(url_for('index'))


@app.route('/seed-data', methods=['POST', 'GET'])
def seed_database():
    from seed import seed_data
    seed_data()
    flash("🌱 Демонстраційні дані завантажено!", "success")
    return redirect(url_for('index'))


# --- GROUPS ---
@app.route('/groups', methods=['GET', 'POST'])
def groups():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        student_count = request.form.get('student_count', type=int, default=25)
        if name:
            existing = Group.query.filter_by(name=name).first()
            if existing:
                flash(f"Група {name} вже існує!", "warning")
            else:
                group = Group(name=name, student_count=student_count)
                db.session.add(group)
                db.session.commit()
                flash(f"Групу '{name}' успішно додано!", "success")
        return redirect(url_for('groups'))
    
    all_groups = Group.query.order_by(Group.name).all()
    return render_template('groups.html', groups=all_groups)

@app.route('/groups/delete/<int:id>', methods=['POST'])
def delete_group(id):
    group = db.session.get(Group, id)
    if group:
        db.session.delete(group)
        db.session.commit()
        flash(f"Групу '{group.name}' видалено!", "info")
    return redirect(url_for('groups'))


# --- TEACHERS ---
@app.route('/teachers', methods=['GET', 'POST'])
def teachers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        title = request.form.get('title', 'Викладач').strip()
        color = request.form.get('color', '#0284c7')
        if name:
            teacher = Teacher(name=name, title=title, color=color)
            db.session.add(teacher)
            db.session.commit()
            flash(f"Викладача '{name}' додано!", "success")
        return redirect(url_for('teachers'))
    
    all_teachers = Teacher.query.order_by(Teacher.name).all()
    return render_template('teachers.html', teachers=all_teachers)

@app.route('/teachers/delete/<int:id>', methods=['POST'])
def delete_teacher(id):
    teacher = db.session.get(Teacher, id)
    if teacher:
        db.session.delete(teacher)
        db.session.commit()
        flash(f"Викладача '{teacher.name}' видалено!", "info")
    return redirect(url_for('teachers'))


# --- TEACHER PREFERENCES ---
@app.route('/teachers/<int:teacher_id>/preferences', methods=['GET', 'POST'])
def teacher_preferences(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        flash("Викладача не знайдено", "warning")
        return redirect(url_for('teachers'))

    time_slots = TimeSlot.query.order_by(TimeSlot.slot_number).all()

    if request.method == 'POST':
        TeacherPreference.query.filter_by(teacher_id=teacher.id).delete()
        db.session.flush()
        
        for day in DAYS_OF_WEEK:
            for slot in time_slots:
                pref_key = f"pref_{day}_{slot.slot_number}"
                status = request.form.get(pref_key, "neutral")
                if status in ["preferred", "unavailable"]:
                    pref = TeacherPreference(
                        teacher_id=teacher.id,
                        day_of_week=day,
                        slot_number=slot.slot_number,
                        status=status
                    )
                    db.session.add(pref)
        db.session.commit()
        flash(f"Побажання для викладача {teacher.name} збережено!", "success")
        return redirect(url_for('teacher_preferences', teacher_id=teacher.id))

    existing_prefs = {}
    prefs = TeacherPreference.query.filter_by(teacher_id=teacher.id).all()
    for p in prefs:
        existing_prefs[(p.day_of_week, p.slot_number)] = p.status

    all_teachers = Teacher.query.order_by(Teacher.name).all()
    return render_template('teacher_preferences.html',
                           teacher=teacher,
                           all_teachers=all_teachers,
                           time_slots=time_slots,
                           existing_prefs=existing_prefs)

@app.route('/api/preferences/update', methods=['POST'])
def api_update_preference():
    data = request.json or {}
    teacher_id = data.get('teacher_id')
    day = data.get('day')
    slot_number = data.get('slot_number')
    status = data.get('status', 'neutral')

    if not teacher_id or not day or not slot_number:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    pref = TeacherPreference.query.filter_by(
        teacher_id=teacher_id,
        day_of_week=day,
        slot_number=slot_number
    ).first()

    if status == 'neutral':
        if pref:
            db.session.delete(pref)
    else:
        if pref:
            pref.status = status
        else:
            pref = TeacherPreference(
                teacher_id=teacher_id,
                day_of_week=day,
                slot_number=slot_number,
                status=status
            )
            db.session.add(pref)

    db.session.commit()
    return jsonify({'success': True, 'status': status})


# --- CLASSROOMS ---
@app.route('/classrooms', methods=['GET', 'POST'])
def classrooms():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        capacity = request.form.get('capacity', type=int, default=30)
        room_type = request.form.get('room_type', 'Загальна').strip()
        if name:
            existing = Classroom.query.filter_by(name=name).first()
            if existing:
                flash(f"Аудиторія '{name}' вже існує!", "warning")
            else:
                classroom = Classroom(name=name, capacity=capacity, room_type=room_type)
                db.session.add(classroom)
                db.session.commit()
                flash(f"Аудиторію '{name}' додано!", "success")
        return redirect(url_for('classrooms'))

    all_rooms = Classroom.query.order_by(Classroom.name).all()
    return render_template('classrooms.html', classrooms=all_rooms)

@app.route('/classrooms/delete/<int:id>', methods=['POST'])
def delete_classroom(id):
    room = db.session.get(Classroom, id)
    if room:
        db.session.delete(room)
        db.session.commit()
        flash(f"Аудиторію '{room.name}' видалено!", "info")
    return redirect(url_for('classrooms'))


# --- SUBJECTS ---
@app.route('/subjects', methods=['GET', 'POST'])
def subjects():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        group_id = request.form.get('group_id', type=int)
        teacher_id = request.form.get('teacher_id', type=int)
        hours = request.form.get('hours_per_week', type=int, default=2)
        subject_type = request.form.get('subject_type', 'Лекція')
        room_type_required = request.form.get('room_type_required', 'Будь-яка')

        if name and group_id and teacher_id:
            subj = Subject(
                name=name,
                group_id=group_id,
                teacher_id=teacher_id,
                hours_per_week=hours,
                subject_type=subject_type,
                room_type_required=room_type_required
            )
            db.session.add(subj)
            db.session.commit()
            flash(f"Предмет '{name}' додано!", "success")
        return redirect(url_for('subjects'))

    all_subjects = Subject.query.order_by(Subject.name).all()
    all_groups = Group.query.order_by(Group.name).all()
    all_teachers = Teacher.query.order_by(Teacher.name).all()
    return render_template('subjects.html',
                           subjects=all_subjects,
                           groups=all_groups,
                           teachers=all_teachers)

@app.route('/subjects/delete/<int:id>', methods=['POST'])
def delete_subject(id):
    subj = db.session.get(Subject, id)
    if subj:
        db.session.delete(subj)
        db.session.commit()
        flash(f"Предмет '{subj.name}' видалено!", "info")
    return redirect(url_for('subjects'))


# --- UTILS ---
def get_preference_satisfaction_stats():
    entries = ScheduleEntry.query.all()
    if not entries:
        return {'total': 0, 'preferred': 0, 'unavailable': 0, 'satisfaction_rate': 100}

    total_classes = len(entries)
    preferred_matches = 0
    unavailable_matches = 0

    for entry in entries:
        pref = TeacherPreference.query.filter_by(
            teacher_id=entry.teacher_id,
            day_of_week=entry.day_of_week,
            slot_number=entry.slot_number
        ).first()
        if pref:
            if pref.status == 'preferred':
                preferred_matches += 1
            elif pref.status == 'unavailable':
                unavailable_matches += 1

    satisfied_rate = round(((total_classes - unavailable_matches) / max(total_classes, 1)) * 100, 1)
    return {
        'total': total_classes,
        'preferred': preferred_matches,
        'unavailable': unavailable_matches,
        'satisfaction_rate': satisfied_rate
    }


def init_db():
    with app.app_context():
        db.create_all()
        if TimeSlot.query.count() != 7:
            TimeSlot.query.delete()
            db.session.commit()
            for s in DEFAULT_SLOTS:
                db.session.add(TimeSlot(**s))
            db.session.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
