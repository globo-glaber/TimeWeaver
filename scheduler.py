from app import db
from app.models import Group, Teacher, Classroom, TimeSlot, Subject, TeacherPreference, ScheduleEntry, DAYS_OF_WEEK

def generate_full_schedule():
    """
    Generates an optimized conflict-free schedule considering:
    1. Hard constraints: No teacher, group, or classroom double booking; no scheduling during teacher's 'unavailable' slots.
    2. Soft constraints: Maximize 'preferred' teacher slots, match room types, compact group schedules.
    """
    try:
        ScheduleEntry.query.delete()
        db.session.commit()

        subjects = Subject.query.all()
        classrooms = Classroom.query.all()
        time_slots = TimeSlot.query.order_by(TimeSlot.slot_number).all()
        groups = {g.id: g for g in Group.query.all()}
        teachers = {t.id: t for t in Teacher.query.all()}

        if not subjects:
            return False, "Немає створених предметів для генерації розкладу!", {}
        if not classrooms:
            return False, "Немає створених аудиторій!", {}

        teacher_prefs = {}
        for pref in TeacherPreference.query.all():
            teacher_prefs[(pref.teacher_id, pref.day_of_week, pref.slot_number)] = pref.status

        sessions = []
        for subj in subjects:
            for session_num in range(subj.hours_per_week):
                sessions.append({
                    'subject_id': subj.id,
                    'subject_name': subj.name,
                    'group_id': subj.group_id,
                    'teacher_id': subj.teacher_id,
                    'room_type_required': subj.room_type_required,
                    'subject_type': subj.subject_type
                })

        random.shuffle(sessions)
        
        teacher_schedule = set()
        group_schedule = set()
        room_schedule = set()
        
        group_day_counts = {g_id: {day: 0 for day in DAYS_OF_WEEK} for g_id in groups.keys()}

        scheduled_entries = []
        unassigned_count = 0

        for session in sessions:
            g_id = session['group_id']
            t_id = session['teacher_id']
            r_req = session['room_type_required']
            student_count = groups[g_id].student_count if g_id in groups else 25

            best_candidate = None
            best_score = -999999

            candidate_options = []

            for day in DAYS_OF_WEEK:
                if group_day_counts[g_id][day] >= 5:
                    continue

                for slot in time_slots:
                    slot_num = slot.slot_number

                    if (t_id, day, slot_num) in teacher_schedule:
                        continue

                    if (g_id, day, slot_num) in group_schedule:
                        continue

                    pref_status = teacher_prefs.get((t_id, day, slot_num), 'neutral')
                    if pref_status == 'unavailable':
                        continue

                    for room in classrooms:
                        if (room.id, day, slot_num) in room_schedule:
                            continue

                        score = 0

                        if pref_status == 'preferred':
                            score += 50
                        elif pref_status == 'neutral':
                            score += 10

                        if r_req != "Будь-яка":
                            if room.room_type == r_req:
                                score += 30
                            else:
                                score -= 15
                        
                        if room.capacity >= student_count:
                            score += 15
                        else:
                            score -= 30

                        current_day_load = group_day_counts[g_id][day]
                        if current_day_load in [1, 2, 3]:
                            score += 15
                        elif current_day_load == 0:
                            score += 5

                        score += random.randint(0, 5)

                        candidate_options.append((score, day, slot_num, room.id))

            if candidate_options:
                candidate_options.sort(key=lambda x: x[0], reverse=True)
                
                _, chosen_day, chosen_slot, chosen_room_id = candidate_options[0]

                teacher_schedule.add((t_id, chosen_day, chosen_slot))
                group_schedule.add((g_id, chosen_day, chosen_slot))
                room_schedule.add((chosen_room_id, chosen_day, chosen_slot))
                group_day_counts[g_id][chosen_day] += 1

                entry = ScheduleEntry(
                    group_id=g_id,
                    subject_id=session['subject_id'],
                    teacher_id=t_id,
                    classroom_id=chosen_room_id,
                    day_of_week=chosen_day,
                    slot_number=chosen_slot
                )
                scheduled_entries.append(entry)
            else:
                unassigned_count += 1

        db.session.add_all(scheduled_entries)
        db.session.commit()

        total_scheduled = len(scheduled_entries)
        pref_matches = 0
        for entry in scheduled_entries:
            p_status = teacher_prefs.get((entry.teacher_id, entry.day_of_week, entry.slot_number), 'neutral')
            if p_status == 'preferred':
                pref_matches += 1

        satisfaction_rate = round((pref_matches / max(total_scheduled, 1)) * 100, 1) if total_scheduled else 100

        stats = {
            'total_scheduled': total_scheduled,
            'unassigned': unassigned_count,
            'pref_matches': pref_matches,
            'satisfaction_rate': satisfaction_rate
        }

        if unassigned_count > 0:
            msg = f"Розклад згенеровано! Успішно заплановано {total_scheduled} пар. Увага: {unassigned_count} пар не вдалося розмістити через дефіцит аудиторій або конфлікти часу."
        else:
            msg = f"Розклад успішно й бездоганно згенеровано! Заплановано всі {total_scheduled} пар."

        return True, msg, stats

    except Exception as e:
        db.session.rollback()
        return False, f"Помилка при генерації розкладу: {str(e)}", {}
