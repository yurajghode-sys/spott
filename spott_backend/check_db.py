from app import create_app, mongo

app = create_app()
with app.app_context():
    events = list(mongo.db.events.find({}, {'title': 1, 'category': 1, 'datetime_iso': 1}))
    print(f'Total events in database: {len(events)}')
    for event in events:
        print(f'- {event["title"]} ({event["category"]}) - {event.get("datetime_iso", "N/A")}')