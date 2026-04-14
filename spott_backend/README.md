# 🎉 Spott Event Platform — Backend API

**Production-ready Flask + MongoDB backend** that connects seamlessly to the Spott frontend (index.html). No frontend changes required — just drop in one `<script>` tag.

---

## 📁 Project Structure

```
spott_backend/
├── app/
│   ├── __init__.py          # Flask factory (JWT, CORS, MongoDB, rate limiting)
│   ├── routes/
│   │   ├── auth.py          # Register, login, profile, newsletter
│   │   ├── events.py        # Full CRUD, filters, pagination, reviews
│   │   ├── bookings.py      # Book tickets, cancel, QR tickets
│   │   ├── admin.py         # Dashboard, user/event/booking management
│   │   ├── search.py        # Full-text event search
│   │   ├── upload.py        # Image upload (admin)
│   │   └── users.py         # User stats, saved events
│   ├── models/
│   │   └── __init__.py      # MongoDB document schemas
│   ├── middleware/
│   │   └── auth.py          # JWT decorators (login_required, admin_required)
│   └── utils/
│       ├── responses.py     # JSON response helpers
│       └── helpers.py       # Shared utilities
├── static/
│   ├── js/api.js            # ⭐ Frontend integration layer
│   └── uploads/             # Uploaded images
├── run.py                   # Dev server entry point
├── wsgi.py                  # Production (Gunicorn) entry point
├── seed.py                  # Database seeder with sample data
├── Dockerfile
├── docker-compose.yml       # API + MongoDB + Mongo-Express
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start (Local Development)

### Step 1 — Prerequisites
- Python 3.11+
- MongoDB running locally on port 27017  
  (Install: https://www.mongodb.com/try/download/community)

### Step 2 — Setup

```bash
cd spott_backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3 — Environment Variables

```bash
cp .env.example .env
# Edit .env — minimum required for local dev:
# MONGO_URI=mongodb://localhost:27017/spott_db
# SECRET_KEY=any-random-string
# JWT_SECRET_KEY=another-random-string
```

### Step 4 — Seed the Database

```bash
python seed.py
```

Output:
```
✅ Admin: admin@spott.app / Admin@1234
✅ User:  user@spott.app  / User@1234
✅ 14 events created
✅ 3 sample bookings created
```

### Step 5 — Run the Server

```bash
python run.py
```

API is live at: **http://localhost:5000**  
Health check: http://localhost:5000/api/health

---

## 🔗 Connect to Frontend (index.html)

Add ONE line before `</body>` in your `index.html`:

```html
<script src="http://localhost:5000/static/js/api.js"></script>
```

That's it! The script automatically:
- ✅ Loads all events from MongoDB (replaces hardcoded EVENTS array)
- ✅ Wires `handleAuth()` → real login/register API
- ✅ Wires `handleRegister()` → real account creation
- ✅ Wires `handleSubscribe()` → newsletter subscription
- ✅ Wires `publishEvent()` → real event creation (admin only)
- ✅ Wires `processPayment()` → real booking creation
- ✅ Wires `submitFeedback()` → real review submission
- ✅ Wires `toggleSave()` → real bookmark save
- ✅ Adds live search with backend suggestions
- ✅ Restores login session from localStorage

---

## 🐳 Docker (Recommended for Production)

```bash
cd spott_backend

# Start everything (API + MongoDB + Mongo-Express UI)
docker-compose up -d

# Seed database
docker-compose exec api python seed.py
```

Services:
| Service      | URL                       |
|-------------|---------------------------|
| Flask API   | http://localhost:5000     |
| MongoDB     | mongodb://localhost:27017  |
| Mongo UI    | http://localhost:8081 (admin/spott123) |

---

## 📋 API Reference

### Auth — `/api/auth`

| Method | Endpoint              | Auth | Description |
|--------|-----------------------|------|-------------|
| POST   | `/register`           | ❌   | Create account |
| POST   | `/login`              | ❌   | Get JWT token |
| POST   | `/logout`             | ❌   | Clear session |
| GET    | `/me`                 | ✅   | Current user profile |
| PUT    | `/me`                 | ✅   | Update profile |
| POST   | `/me/save-event/<id>` | ✅   | Toggle bookmark |
| POST   | `/newsletter`         | ❌   | Subscribe to newsletter |

### Events — `/api/events`

| Method | Endpoint              | Auth     | Description |
|--------|-----------------------|----------|-------------|
| GET    | `/`                   | ❌       | List events (filterable, paginated) |
| GET    | `/trending`           | ❌       | Top events by bookings |
| GET    | `/categories`         | ❌       | Category list with counts |
| GET    | `/<id>`               | ❌       | Event detail + reviews |
| POST   | `/`                   | 🔑 Admin | Create event |
| PUT    | `/<id>`               | 🔑 Admin | Update event |
| DELETE | `/<id>`               | 🔑 Admin | Delete event |
| POST   | `/<id>/review`        | ✅       | Submit rating + review |

**Filter params:**
```
GET /api/events?category=Music&type=free&location=Mumbai&sort=newest&page=1&per_page=12
```

### Bookings — `/api/bookings`

| Method | Endpoint              | Auth | Description |
|--------|-----------------------|------|-------------|
| POST   | `/`                   | ✅   | Create booking |
| GET    | `/`                   | ✅   | My bookings |
| GET    | `/<id>/ticket`        | ✅   | Ticket / QR data |
| DELETE | `/<id>`               | ✅   | Cancel booking |

**Create booking body:**
```json
{
  "event_id": "event_mongo_id",
  "ticket_type": "general",
  "quantity": 1,
  "notes": ""
}
```

### Search — `/api/search`

```
GET /api/search?q=music+festival
```

### Admin — `/api/admin` (Admin JWT required)

| Method | Endpoint              | Description |
|--------|-----------------------|-------------|
| GET    | `/dashboard`          | Stats + charts data |
| GET    | `/users`              | All users (paginated) |
| PUT    | `/users/<id>`         | Update role / status |
| DELETE | `/users/<id>`         | Delete user |
| GET    | `/bookings`           | All bookings |
| PUT    | `/bookings/<id>`      | Update booking status |
| GET    | `/events`             | All events (incl. drafts) |

---

## 🗄️ MongoDB Collections

### users
```json
{
  "_id": "ObjectId",
  "name": "Aryan Verma",
  "email": "user@spott.app",
  "password": "$2b$12$...",
  "role": "user",
  "phone": "+91 98765 43210",
  "avatar_url": "",
  "bio": "Event enthusiast",
  "interests": ["Music", "Tech"],
  "is_active": true,
  "points": 150,
  "saved_events": ["event_id_1"],
  "bookings_count": 3,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-06-01T12:00:00Z"
}
```

### events
```json
{
  "_id": "ObjectId",
  "title": "Sunburn Arena 2025",
  "slug": "sunburn-arena-2025",
  "category": "Music",
  "date": "Dec 28, 2025",
  "time": "6:00 PM",
  "datetime_iso": "2025-12-28T18:00:00",
  "location": "Mumbai, Maharashtra",
  "price": "₹2,499",
  "price_value": 2499.0,
  "type": "paid",
  "emoji": "🎵",
  "image_url": "/static/uploads/events/abc.jpg",
  "capacity": 5000,
  "booked_count": 342,
  "status": "published",
  "badge": "paid",
  "tags": ["edm", "festival", "music"],
  "organiser_id": "user_object_id",
  "created_at": "...",
  "updated_at": "..."
}
```

### bookings
```json
{
  "_id": "ObjectId",
  "user_id": "user_object_id",
  "event_id": "event_object_id",
  "booking_ref": "SPOTT-AB12CD34",
  "ticket_type": "general",
  "quantity": 1,
  "amount_paid": 2499.0,
  "status": "confirmed",
  "booking_date": "2025-06-01T10:30:00Z",
  "qr_data": "SPOTT|SPOTT-AB12CD34|Sunburn Arena 2025|user@spott.app",
  "event_title": "Sunburn Arena 2025",
  "event_date": "Dec 28, 2025",
  "event_time": "6:00 PM",
  "event_location": "Mumbai, Maharashtra",
  "attendee_name": "Aryan Verma",
  "attendee_email": "user@spott.app"
}
```

---

## 🔐 Default Credentials (after seeding)

| Role  | Email              | Password    |
|-------|--------------------|-------------|
| Admin | admin@spott.app    | Admin@1234  |
| User  | user@spott.app     | User@1234   |

---

## 🏭 Production Deployment

```bash
export FLASK_ENV=production
export MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/spott_db
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:application
```

---

## 🧪 Test the API

```bash
# Health check
curl http://localhost:5000/api/health

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@spott.app","password":"User@1234"}'

# Get events
curl http://localhost:5000/api/events?category=Music&page=1
```
