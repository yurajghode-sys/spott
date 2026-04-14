"""
seed.py — Populate MongoDB with sample data for Spott
Usage:  python seed.py
"""
import os, sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from app import create_app, mongo
import bcrypt

def utcnow():
    return datetime.now(timezone.utc)

EVENTS_DATA = [
    {"title":"Sunburn Arena 2025","category":"Music","date":"Dec 28, 2025","time":"6:00 PM","datetime_iso":"2025-12-28T18:00:00","location":"Mumbai, Maharashtra","price":"₹2,499","emoji":"🎵","image_url":"","capacity":5000,"status":"published","badge":"paid","tags":["edm","festival","music"]},
    {"title":"BengaluruTech Summit","category":"Tech","date":"Jan 5, 2026","time":"9:00 AM","datetime_iso":"2026-01-05T09:00:00","location":"Bangalore, Karnataka","price":"Free","emoji":"💻","image_url":"","capacity":2000,"status":"published","badge":"free","tags":["tech","startup","ai"]},
    {"title":"Jaipur Literature Fest","category":"Education","date":"Jan 23, 2026","time":"10:00 AM","datetime_iso":"2026-01-23T10:00:00","location":"Jaipur, Rajasthan","price":"Free","emoji":"📚","image_url":"","capacity":10000,"status":"published","badge":"free","tags":["books","literature","culture"]},
    {"title":"NH7 Weekender Pune","category":"Music","date":"Feb 14, 2026","time":"4:00 PM","datetime_iso":"2026-02-14T16:00:00","location":"Pune, Maharashtra","price":"₹1,799","emoji":"🎸","image_url":"","capacity":3000,"status":"published","badge":"paid","tags":["indie","music","festival"]},
    {"title":"India Startup Conclave","category":"Startup","date":"Mar 8, 2026","time":"10:00 AM","datetime_iso":"2026-03-08T10:00:00","location":"New Delhi, Delhi","price":"₹999","emoji":"🚀","image_url":"","capacity":1500,"status":"published","badge":"paid","tags":["startup","pitch","vc"]},
    {"title":"Art Mumbai 2026","category":"Art","date":"Feb 22, 2026","time":"11:00 AM","datetime_iso":"2026-02-22T11:00:00","location":"Mumbai, Maharashtra","price":"₹500","emoji":"🎨","image_url":"","capacity":800,"status":"published","badge":"paid","tags":["art","culture","exhibition"]},
    {"title":"Food & Film Festival","category":"Food","date":"Jan 18, 2026","time":"5:00 PM","datetime_iso":"2026-01-18T17:00:00","location":"Hyderabad, Telangana","price":"₹350","emoji":"🍕","image_url":"","capacity":600,"status":"published","badge":"paid","tags":["food","film","culture"]},
    {"title":"Yoga & Mindfulness Retreat","category":"Wellness","date":"Feb 7, 2026","time":"7:00 AM","datetime_iso":"2026-02-07T07:00:00","location":"Rishikesh, Uttarakhand","price":"Free","emoji":"🧘","image_url":"","capacity":200,"status":"published","badge":"free","tags":["yoga","wellness","meditation"]},
    {"title":"Comic Con Hyderabad","category":"Art","date":"Mar 15, 2026","time":"10:00 AM","datetime_iso":"2026-03-15T10:00:00","location":"Hyderabad, Telangana","price":"₹499","emoji":"🦸","image_url":"","capacity":5000,"status":"published","badge":"paid","tags":["comics","cosplay","entertainment"]},
    {"title":"Pitch Perfect Night","category":"Startup","date":"Jan 30, 2026","time":"7:00 PM","datetime_iso":"2026-01-30T19:00:00","location":"Bangalore, Karnataka","price":"Free","emoji":"💡","image_url":"","capacity":300,"status":"published","badge":"free","tags":["startup","pitch","networking"]},
    {"title":"Hornbill Festival","category":"Art","date":"Dec 1, 2025","time":"All Day","datetime_iso":"2025-12-01T09:00:00","location":"Kohima, Nagaland","price":"₹200","emoji":"🎭","image_url":"","capacity":20000,"status":"published","badge":"live","tags":["culture","festival","northeast"]},
    {"title":"IPL Fan Fest 2026","category":"Sports","date":"Apr 10, 2026","time":"3:00 PM","datetime_iso":"2026-04-10T15:00:00","location":"Chennai, Tamil Nadu","price":"₹799","emoji":"🏏","image_url":"","capacity":8000,"status":"published","badge":"paid","tags":["cricket","sports","ipl"]},
    {"title":"Stand-Up Comedy Night","category":"Comedy","date":"Feb 1, 2026","time":"8:00 PM","datetime_iso":"2026-02-01T20:00:00","location":"Mumbai, Maharashtra","price":"₹499","emoji":"🎭","image_url":"","capacity":500,"status":"published","badge":"paid","tags":["comedy","standup","entertainment"]},
    {"title":"AI & ML Bootcamp","category":"Tech","date":"Mar 20, 2026","time":"9:00 AM","datetime_iso":"2026-03-20T09:00:00","location":"Hyderabad, Telangana","price":"₹1,200","emoji":"🤖","image_url":"","capacity":150,"status":"published","badge":"paid","tags":["ai","ml","bootcamp","tech"]},
    {"title":"Frontend-Backend Integration Test Event","category":"Tech","date":"Apr 15, 2026","time":"2:00 PM","datetime_iso":"2026-04-15T14:00:00","location":"Online","price":"Free","emoji":"🔗","image_url":"","capacity":1000,"status":"published","badge":"free","tags":["test","integration","frontend","backend"]},
]

def seed():
    app = create_app()
    with app.app_context():
        print("🗑  Clearing existing data...")
        mongo.db.users.delete_many({})
        mongo.db.events.delete_many({})
        mongo.db.bookings.delete_many({})
        mongo.db.reviews.delete_many({})
        mongo.db.newsletter.delete_many({})

        print("👤 Creating users...")
        admin_pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt(12)).decode()
        user_pw  = bcrypt.hashpw(b"User@1234",  bcrypt.gensalt(12)).decode()

        admin_doc = {
            "name":"Spott Admin","email":"admin@spott.app","phone":"",
            "password":admin_pw,"role":"admin","avatar_url":"",
            "bio":"Platform administrator","interests":[],"is_active":True,
            "created_at":utcnow(),"updated_at":utcnow(),"last_login":None,
            "bookings_count":0,"saved_events":[],"points":9999,
        }
        user_doc = {
            "name":"Aryan Verma","email":"user@spott.app","phone":"+91 98765 43210",
            "password":user_pw,"role":"user","avatar_url":"",
            "bio":"Event enthusiast 🎵","interests":["Music","Tech"],
            "is_active":True,"created_at":utcnow(),"updated_at":utcnow(),
            "last_login":None,"bookings_count":0,"saved_events":[],"points":150,
        }
        admin_id = str(mongo.db.users.insert_one(admin_doc).inserted_id)
        user_id  = str(mongo.db.users.insert_one(user_doc).inserted_id)
        print(f"   ✅ Admin: admin@spott.app / Admin@1234")
        print(f"   ✅ User:  user@spott.app  / User@1234")

        print("🎉 Creating events...")
        from app.models import make_event
        for ev_data in EVENTS_DATA:
            doc = make_event(ev_data, organiser_id=admin_id)
            mongo.db.events.insert_one(doc)
        print(f"   ✅ {len(EVENTS_DATA)} events created")

        print("📋 Creating sample bookings...")
        from app.models import make_booking
        from app.utils.helpers import gen_ref, price_to_float
        events = list(mongo.db.events.find({"status":"published"}).limit(3))
        for ev in events:
            ref = gen_ref("SPOTT")
            bk = make_booking(
                user_id=user_id, event_id=str(ev["_id"]),
                booking_ref=ref, ticket_type="general", quantity=1,
                amount_paid=price_to_float(ev.get("price","Free")),
                attendee_name="Aryan Verma", attendee_email="user@spott.app",
            )
            bk["event_title"]    = ev.get("title","")
            bk["event_date"]     = ev.get("date","")
            bk["event_time"]     = ev.get("time","")
            bk["event_location"] = ev.get("location","")
            bk["event_emoji"]    = ev.get("emoji","🎉")
            mongo.db.bookings.insert_one(bk)
            mongo.db.events.update_one({"_id":ev["_id"]},{"$inc":{"booked_count":1}})
        mongo.db.users.update_one({"_id":__import__("bson").ObjectId(user_id)},
                                  {"$set":{"bookings_count":len(events)}})
        print(f"   ✅ {len(events)} sample bookings created")

        print("📬 Seeding newsletter...")
        mongo.db.newsletter.insert_many([
            {"email":"fan1@example.com","created_at":utcnow()},
            {"email":"fan2@example.com","created_at":utcnow()},
        ])

        print("\n╔══════════════════════════════════════════════╗")
        print("║     ✅  Database Seeded Successfully!        ║")
        print("╠══════════════════════════════════════════════╣")
        print("║  Admin:  admin@spott.app  /  Admin@1234      ║")
        print("║  User:   user@spott.app   /  User@1234       ║")
        print(f"║  Events: {len(EVENTS_DATA)} seeded                        ║")
        print("╚══════════════════════════════════════════════╝")

if __name__ == "__main__":
    seed()
