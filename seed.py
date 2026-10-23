from app import db
from app.models import Group, Teacher, Classroom, TimeSlot, Subject, TeacherPreference, ScheduleEntry, DEFAULT_SLOTS

def seed_data():
    """Resets database to completely empty state with 7 Photo 1 time slots."""
    with app.app_context():
        db.create_all()

        ScheduleEntry.query.delete()
        Subject.query.delete()
        TeacherPreference.query.delete()
        Teacher.query.delete()
        Group.query.delete()
        Classroom.query.delete()
        TimeSlot.query.delete()
        db.session.commit()

        for s in DEFAULT_SLOTS:
            ts = TimeSlot(slot_number=s['slot_number'], start_time=s['start_time'], end_time=s['end_time'])
            db.session.add(ts)
        db.session.commit()
        print("Database reset to completely clean state with 7 slots!")

if __name__ == '__main__':
    seed_data()
