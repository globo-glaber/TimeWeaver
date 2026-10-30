from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Group, Teacher, Classroom, TimeSlot, Subject, TeacherPreference, ScheduleEntry, DAYS_OF_WEEK

bp = Blueprint('main', __name__)

@bp.app_context_processor
def inject_constants():
    return dict(DAYS_OF_WEEK=DAYS_OF_WEEK)

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

@bp.route('/')
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

    schedule_grid = {day: {slot.slot_number: [] for slot in time_slots} for day in DAYS_OF_WEEK}
    total_entries = ScheduleEntry.query.count()

    entries_query = ScheduleEntry.query
    if selected_view in ['group', 'official'] and selected_id:
        entries_query = entries_query.filter_by(group_id=selected_id)
    elif selected_view == 'teacher' and selected_id:
        entries_query = entries_query.filter_by(teacher_id=selected_id)
    elif selected_view == 'classroom' and selected_id:
        entries_query = entries_query.filter_by(classroom_id=selected_id)

    for entry in entries_query.all():
        if entry.day_of_week in schedule_grid and entry.slot_number in schedule_grid[entry.day_of_week]:
            schedule_grid[entry.day_of_week][entry.slot_number].append(entry)

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
                           pref_stats=get_preference_satisfaction_stats())

@bp.route('/generate', methods=['POST'])
def generate_schedule():
    from scheduler import generate_full_schedule
    success, message, stats = generate_full_schedule()
    if success:
        rate = stats.get('satisfaction_rate', 100)
        flash(f"✨ {message}! Задоволено {rate}% побажань викладачів.", "success")
    else:
        flash(f"⚠️ {message}", "danger")
    return redirect(url_for('main.index'))

@bp.route('/clear-all', methods=['POST', 'GET'])
def clear_all():
    from app.models import DEFAULT_SLOTS
    ScheduleEntry.query.delete()
    Subject.query.delete()
    TeacherPreference.query.delete()
    Teacher.query.delete()
    Group.query.delete()
    Classroom.query.delete()
    TimeSlot.query.delete()
    
    for s in DEFAULT_SLOTS:
        db.session.add(TimeSlot(**s))
    db.session.commit()

    flash("🧹 Усі дані успішно видалені!", "success")
    return redirect(url_for('main.index'))

@bp.route('/seed-data', methods=['POST', 'GET'])
def seed_database():
    from seed import seed_data
    seed_data()
    flash("🌱 Демонстраційні дані завантажено!", "success")
    return redirect(url_for('main.index'))

@bp.route('/groups', methods=['GET', 'POST'])
def groups():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        student_count = request.form.get('student_count', type=int, default=25)
        if name:
            if Group.query.filter_by(name=name).first():
                flash(f"Група {name} вже існує!", "warning")
            else:
                db.session.add(Group(name=name, student_count=student_count))
                db.session.commit()
                flash(f"Групу '{name}' успішно додано!", "success")
        return redirect(url_for('main.groups'))

    return render_template('groups.html', groups=Group.query.order_by(Group.name).all())

@bp.route('/groups/delete/<int:id>', methods=['POST'])
def delete_group(id):
    group = db.session.get(Group, id)
    if group:
        db.session.delete(group)
        db.session.commit()
        flash(f"Групу '{group.name}' видалено!", "info")
    return redirect(url_for('main.groups'))

@bp.route('/teachers', methods=['GET', 'POST'])
def teachers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        title = request.form.get('title', 'Викладач').strip()
        color = request.form.get('color', '#0284c7')
        if name:
            db.session.add(Teacher(name=name, title=title, color=color))
            db.session.commit()
            flash(f"Викладача '{name}' додано!", "success")
        return redirect(url_for('main.teachers'))

    return render_template('teachers.html', teachers=Teacher.query.order_by(Teacher.name).all())

@bp.route('/teachers/delete/<int:id>', methods=['POST'])
def delete_teacher(id):
    teacher = db.session.get(Teacher, id)
    if teacher:
        db.session.delete(teacher)
        db.session.commit()
        flash(f"Викладача '{teacher.name}' видалено!", "info")
    return redirect(url_for('main.teachers'))

@bp.route('/teachers/<int:teacher_id>/preferences', methods=['GET', 'POST'])
def teacher_preferences(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    if not teacher:
        flash("Викладача не знайдено", "warning")
        return redirect(url_for('main.teachers'))

    time_slots = TimeSlot.query.order_by(TimeSlot.slot_number).all()

    if request.method == 'POST':
        TeacherPreference.query.filter_by(teacher_id=teacher.id).delete()
        db.session.flush()

        for day in DAYS_OF_WEEK:
            for slot in time_slots:
                pref_key = f"pref_{day}_{slot.slot_number}"
                status = request.form.get(pref_key, "neutral")
                if status in ["preferred", "unavailable"]:
                    db.session.add(TeacherPreference(
                        teacher_id=teacher.id, day_of_week=day,
                        slot_number=slot.slot_number, status=status
                    ))
        db.session.commit()
        flash(f"Побажання для {teacher.name} збережено!", "success")
        return redirect(url_for('main.teacher_preferences', teacher_id=teacher.id))

    existing_prefs = {(p.day_of_week, p.slot_number): p.status for p in teacher.preferences}
    return render_template('teacher_preferences.html',
                           teacher=teacher,
                           all_teachers=Teacher.query.order_by(Teacher.name).all(),
                           time_slots=time_slots,
                           existing_prefs=existing_prefs)

@bp.route('/api/preferences/update', methods=['POST'])
def api_update_preference():
    data = request.json or {}
    teacher_id = data.get('teacher_id')
    day = data.get('day')
    slot_number = data.get('slot_number')
    status = data.get('status', 'neutral')

    if not all([teacher_id, day, slot_number]):
        return jsonify({'success': False, 'error': 'Missing fields'}), 400

    pref = TeacherPreference.query.filter_by(teacher_id=teacher_id, day_of_week=day, slot_number=slot_number).first()

    if status == 'neutral':
        if pref: db.session.delete(pref)
    else:
        if pref:
            pref.status = status
        else:
            db.session.add(TeacherPreference(teacher_id=teacher_id, day_of_week=day, slot_number=slot_number, status=status))

    db.session.commit()
    return jsonify({'success': True, 'status': status})

@bp.route('/classrooms', methods=['GET', 'POST'])
def classrooms():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        capacity = request.form.get('capacity', type=int, default=30)
        room_type = request.form.get('room_type', 'Загальна').strip()
        if name:
            if Classroom.query.filter_by(name=name).first():
                flash(f"Аудиторія '{name}' вже існує!", "warning")
            else:
                db.session.add(Classroom(name=name, capacity=capacity, room_type=room_type))
                db.session.commit()
                flash(f"Аудиторію '{name}' додано!", "success")
        return redirect(url_for('main.classrooms'))

    return render_template('classrooms.html', classrooms=Classroom.query.order_by(Classroom.name).all())

@bp.route('/classrooms/delete/<int:id>', methods=['POST'])
def delete_classroom(id):
    room = db.session.get(Classroom, id)
    if room:
        db.session.delete(room)
        db.session.commit()
        flash(f"Аудиторію '{room.name}' видалено!", "info")
    return redirect(url_for('main.classrooms'))

@bp.route('/subjects', methods=['GET', 'POST'])
def subjects():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        group_id = request.form.get('group_id', type=int)
        teacher_id = request.form.get('teacher_id', type=int)
        hours = request.form.get('hours_per_week', type=int, default=2)
        subject_type = request.form.get('subject_type', 'Лекція')
        room_type_required = request.form.get('room_type_required', 'Будь-яка')

        if name and group_id and teacher_id:
            db.session.add(Subject(
                name=name, group_id=group_id, teacher_id=teacher_id,
                hours_per_week=hours, subject_type=subject_type,
                room_type_required=room_type_required
            ))
            db.session.commit()
            flash(f"Предмет '{name}' додано!", "success")
        return redirect(url_for('main.subjects'))

    return render_template('subjects.html',
                           subjects=Subject.query.order_by(Subject.name).all(),
                           groups=Group.query.order_by(Group.name).all(),
                           teachers=Teacher.query.order_by(Teacher.name).all())

@bp.route('/subjects/delete/<int:id>', methods=['POST'])
def delete_subject(id):
    subj = db.session.get(Subject, id)
    if subj:
        db.session.delete(subj)
        db.session.commit()
        flash(f"Предмет '{subj.name}' видалено!", "info")
    return redirect(url_for('main.subjects'))