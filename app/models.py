from app import db

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