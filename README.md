# HostelMatch – Smart Student Hostel Recommendation System

HostelMatch helps college and university students find hostels and PGs that match their monthly budget, max commute distance, preferred room types, and required amenities.

## Key Features
- 🎯 **Transparent Scoring Algorithm (0-100%)**: Calculates match score based on budget (25%), commute distance (25%), amenities matched (30%), room type match (10%), and rating (10%).
- 📊 **Detailed Match Breakdown**: Interactive modal shows exactly why each hostel received its score.
- 🗺️ **Interactive Leaflet Map**: View hostels placed geographically around your campus with distance popups.
- 🔖 **Shortlisting & Saved Hostels**: Bookmark your favorite hostels per browser without registering (using anonymous `X-Client-Id`).
- 🛠️ **Admin Dashboard**: Full CRUD interface (`/admin`) for adding, editing, and deleting hostel listings.
- 📱 **Mobile-First Responsive UI**: Styled with Bricolage Grotesque, dark ink & teal palette, accessible keyboard navigation, and light background.

## Project Structure
```
hostelmatch/
├── app.py                 # Flask server, SQLite DB manager, scoring & recommendation API
├── requirements.txt       # Project dependencies
├── test_app.py            # Unit and API integration tests
├── Procfile               # Gunicorn execution rule for cloud deployment
├── render.yaml            # Render deployment manifest
├── docs/
│   └── DEPLOYMENT.md      # Deployment and environment guide
└── templates/
    ├── index.html         # Main user recommendation portal & map UI
    └── admin.html         # Admin hostel management portal
```

## Quick Start
```bash
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Run the application
python app.py

# 3. Access web application
# Main App:  http://127.0.0.1:5000
# Admin UI:  http://127.0.0.1:5000/admin (Default Key: change-me)
```

## API Reference
- `POST /api/recommend` - Query hostels by budget, commute distance, rooms, amenities, sort order.
- `GET /api/hostels/<id>` - Fetch hostel details.
- `GET /api/shortlist` - Retrieve saved hostels for client ID.
- `POST /api/shortlist/<id>` - Save hostel to shortlist.
- `DELETE /api/shortlist/<id>` - Remove hostel from shortlist.
- `POST /api/admin/hostels` - Create new hostel (requires `X-Admin-Key`).
- `PUT /api/admin/hostels/<id>` - Update hostel details (requires `X-Admin-Key`).
- `DELETE /api/admin/hostels/<id>` - Delete hostel (requires `X-Admin-Key`).
