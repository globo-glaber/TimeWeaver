from app import create_app, db
from app.models import TimeSlot, DEFAULT_SLOTS

app = create_app()

def init_db():
    with app.app_context():
        db.create_all()
        if TimeSlot.query.count() != 7:
            TimeSlot.query.delete()
            for slot_data in DEFAULT_SLOTS:
                db.session.add(TimeSlot(**slot_data))
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)