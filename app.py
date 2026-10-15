"""HostelMatch backend: Flask + SQLite. Run: python app.py"""
import json, sqlite3, os, math, hmac, uuid, random
from flask import Flask, jsonify, request, render_template, g

BASE = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(BASE, "templates")
app = Flask(__name__, template_folder=templates_dir if os.path.isdir(templates_dir) else BASE)

DB = os.environ.get("DB_PATH", "/tmp/hostelmatch.db" if os.environ.get("VERCEL") else os.path.join(BASE, "hostelmatch.db"))
ADMIN_KEY = os.environ.get("ADMIN_KEY", "change-me")
CLAT, CLNG = float(os.environ.get("CAMPUS_LAT", 19.0760)), float(os.environ.get("CAMPUS_LNG", 72.8777))

def haversine_km(lat1, lon1, lat2, lon2):
    """Accurate Haversine distance in kilometers between two geo coordinates."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

ROOMS = ["single", "double", "triple", "dorm"]
AMENITIES = ["wifi", "ac", "meals", "laundry", "gym", "study_room", "power_backup", "security"]
GENDERS = ["coed", "boys", "girls"]
FOODS = ["all", "jain", "pure_veg", "veg_nonveg"]
SORTS = {
    "match": ("match", True),
    "price": ("price", False),
    "rating": ("rating", True),
    "distance": ("distance_km", False),
    "safety": ("safety_score", True)
}

# Major Mumbai College & University Campuses
COLLEGES = [
    {"id": "all", "name": "All Mumbai (City-wide)", "shortName": "All Mumbai", "area": "Greater Mumbai", "lat": 19.0760, "lng": 72.8777},
    {"id": "mithibai_nmims", "name": "Mithibai College / NMIMS Mumbai (Vile Parle West)", "shortName": "Mithibai & NMIMS", "area": "V.M. Road, Vile Parle West", "lat": 19.1028, "lng": 72.8373},
    {"id": "bhavans_spit", "name": "SPIT / SPCE / Bhavan's College (Andheri West)", "shortName": "SPIT & Bhavan's", "area": "Munshi Nagar, Andheri West", "lat": 19.1232, "lng": 72.8360},
    {"id": "djsanghvi", "name": "D.J. Sanghvi College of Engineering (Vile Parle West)", "shortName": "DJ Sanghvi", "area": "JVPD Scheme, Vile Parle West", "lat": 19.1075, "lng": 72.8372},
    {"id": "vjti_ict", "name": "VJTI & ICT Mumbai (Matunga East)", "shortName": "VJTI & ICT Matunga", "area": "H.R. Mahajani Rd, Matunga", "lat": 19.0222, "lng": 72.8561},
    {"id": "vit_wadala", "name": "VIT - Vidyalankar Institute of Technology (Wadala East)", "shortName": "VIT Wadala", "area": "Vidyalankar Educational Campus, Sangam Nagar, Wadala East", "lat": 19.0218, "lng": 72.8710},
    {"id": "somaiya_vidyavihar", "name": "K.J. Somaiya College of Engineering (Vidyavihar)", "shortName": "Somaiya Vidyavihar", "area": "Vidyanagar, Vidyavihar East", "lat": 19.0726, "lng": 72.8996},
    {"id": "mu_kalina", "name": "University of Mumbai (Kalina Campus, Santacruz East)", "shortName": "MU Kalina", "area": "Vidyanagari, Santacruz East", "lat": 19.0748, "lng": 72.8682},
    {"id": "churchgate_fort", "name": "Churchgate & Fort Colleges (HR, KC, Jai Hind, St. Xavier's, GLC)", "shortName": "Churchgate & Fort Colleges", "area": "Churchgate / Fort, South Mumbai", "lat": 18.9320, "lng": 72.8260},
    {"id": "tsec_bandra", "name": "Thadomal Shahani (TSEC) & Rizvi (Bandra West)", "shortName": "TSEC & Rizvi Bandra", "area": "Linking Road, Bandra West", "lat": 19.0645, "lng": 72.8358},
    {"id": "iit_bombay", "name": "IIT Bombay & IIM Mumbai (Powai)", "shortName": "IIT Bombay Powai", "area": "Main Gate, Powai", "lat": 19.1334, "lng": 72.9133},
    {"id": "tiss_chembur", "name": "TISS Mumbai & VESIT (Chembur / Deonar)", "shortName": "TISS & VESIT Chembur", "area": "Deonar Farm Rd, Chembur", "lat": 19.0540, "lng": 72.9150},
    {"id": "sfit_borivali", "name": "SFIT & Thakur College (Borivali / Kandivali)", "shortName": "SFIT & Thakur College", "area": "Borivali West & Kandivali East", "lat": 19.2300, "lng": 72.8550},
    {"id": "south_mumbai_grant_rd", "name": "Wilson & Sophia Colleges (Grant Road / Girgaon)", "shortName": "Wilson & Sophia Colleges", "area": "Grant Road / Chowpatty", "lat": 18.9560, "lng": 72.8120},
    {"id": "saboo_siddik", "name": "M.H. Saboo Siddik College of Engg (Byculla)", "shortName": "Saboo Siddik Byculla", "area": "Byculla, Central Mumbai", "lat": 18.9680, "lng": 72.8295}
]
COLLEGES_MAP = {c["id"]: c for c in COLLEGES}

IMAGES = [
    "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=700&q=80",
    "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=700&q=80",
    "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?auto=format&fit=crop&w=700&q=80",
    "https://images.unsplash.com/photo-1560185893-a55cbc8c57e8?auto=format&fit=crop&w=700&q=80",
    "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=700&q=80"
]

# Real Verified Existing Mumbai Hostels & PGs
SEED = [
    (
        "Shri Mahavira Jaina Vidyalaya",
        "Andheri West",
        19.1205, 72.8402,
        4.6,
        {"dorm": 3200, "triple": 4500, "double": 6000},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "Established community student residence for boys featuring strict Jain vegetarian meals, spacious library & quiet study halls, walking distance to Bhavan's, SPIT, and Mithibai colleges.",
        "boys", True, "022-26250376", IMAGES[0], 4.8,
        "jain", "C.D. Barfiwala Road, Near Bhavan's College, Andheri West, Mumbai 400058",
        "Bhavan's College (0.5 km), SPIT (0.6 km), Mithibai College (1.8 km), NMIMS (1.9 km)",
        "https://smjv.org/"
    ),
    (
        "Matushree Manjulaben Bhailal Shah Girls Hostel",
        "Borivali West",
        19.2312, 72.8524,
        4.5,
        {"triple": 7500, "double": 9500, "single": 14000},
        ["wifi", "ac", "meals", "security", "power_backup", "study_room"],
        "Air-conditioned girls student residence managed by Jain Jagruti Centre. Features resident woman warden, CCTV security, Jain meal arrangements, and peaceful study atmosphere.",
        "girls", True, "022-66956699", IMAGES[1], 4.9,
        "jain", "Shimpoli Road, Near Chikuwadi, Borivali West, Mumbai 400092",
        "SFIT Borivali (1.6 km), Thakur College (3.2 km), Atharva Malad (4.5 km)",
        "https://jainjagruti.com/"
    ),
    (
        "Seth Hirachand Gumanji Boys' Hostel",
        "Grant Road",
        18.9620, 72.8190,
        4.4,
        {"dorm": 2500, "triple": 3500, "double": 4800},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "Historic Digambar Jain charitable student hostel offering heavily subsidized stay and authentic Jain vegetarian dining for male students in South Mumbai.",
        "boys", True, "022-23821247", IMAGES[2], 4.7,
        "jain", "148, Dr. D.B. Marg (Lamington Road), Grant Road East, Mumbai 400007",
        "Wilson College (1.8 km), Jai Hind (3.4 km), HR & KC College (3.5 km), St. Xavier's (3.2 km)",
        "https://www.hirachandgumanji.com/"
    ),
    (
        "R. R. Shravika Ashram",
        "Grant Road",
        18.9645, 72.8182,
        4.3,
        {"dorm": 3500, "triple": 5000, "double": 6800},
        ["wifi", "meals", "security", "power_backup", "study_room"],
        "Safe and secure residential ashram for Jain girls post-Class 10 and working women with pure vegetarian dining, disciplined environment, and proximity to South Mumbai colleges.",
        "girls", True, "022-23862883", IMAGES[3], 4.9,
        "jain", "Jubilee Baug, Dadaji Road, Opposite Navjeevan Society, Lamington Road, Mumbai 400007",
        "Sophia College (2.2 km), Wilson College (1.9 km), St. Xavier's (3.4 km)",
        "https://www.hirachandgumanji.com/"
    ),
    (
        "United Jain Students Home & Scholars Residency",
        "Sion West",
        19.0392, 72.8618,
        4.5,
        {"dorm": 3200, "triple": 4500, "double": 6200},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "Central Mumbai Jain student accommodation in Sion Jain Society with easy train connectivity, pure Jain meals, reading rooms, and proximity to SIES, VJTI, and Somaiya.",
        "coed", True, "022-24071974", IMAGES[4], 4.8,
        "jain", "Plot 22, Jain Society, Road No. 3, Sion West, Mumbai 400022",
        "SIES College (0.6 km), VJTI Matunga (1.5 km), ICT Mumbai (1.6 km), Somaiya Sion (1.4 km)",
        "https://www.jainsamaj.org/"
    ),
    (
        "Rising Star Girls Hostel",
        "JVPD Scheme, Vile Parle West",
        19.1068, 72.8345,
        4.7,
        {"triple": 12500, "double": 16500, "single": 24000},
        ["wifi", "ac", "meals", "laundry", "security", "power_backup"],
        "High-end girls' accommodation in upscale JVPD Scheme walking distance from NMIMS and Mithibai. Fully furnished with AC, daily housekeeping, 3-tier security, and nutritious meals.",
        "girls", True, "+91 78879 93399", IMAGES[0], 4.9,
        "pure_veg", "6th Road, Near Juhu Circle, JVPD Scheme, Vile Parle West, Mumbai 400049",
        "Mithibai College (0.5 km), NMIMS Mumbai (0.6 km), D.J. Sanghvi (0.4 km), UMIT Juhu (1.2 km)",
        ""
    ),
    (
        "Bright Youth Girls Hostel",
        "Vile Parle West",
        19.1025, 72.8378,
        4.4,
        {"triple": 11000, "double": 15000, "single": 21000},
        ["wifi", "ac", "meals", "laundry", "security", "power_backup"],
        "Immediate proximity to Mithibai and NMIMS gates (3-min walk). Features air conditioning, study desks, CCTV security, and home-style pure veg meals with Jain options.",
        "girls", True, "+91 98216 95040", IMAGES[1], 4.8,
        "pure_veg", "V.M. Road, Near Mithibai College, Vile Parle West, Mumbai 400056",
        "Mithibai College (0.1 km), NMIMS (0.2 km), Narsee Monjee (0.1 km), D.J. Sanghvi (0.5 km)",
        ""
    ),
    (
        "Students Suite Scholars Co-Living",
        "JVPD Scheme, Vile Parle West",
        19.1112, 72.8330,
        4.6,
        {"triple": 14000, "double": 18500, "single": 26000},
        ["wifi", "ac", "meals", "gym", "laundry", "study_room", "security", "power_backup"],
        "Modern co-living student suites with dedicated floors for male and female scholars, high-speed fiber internet, fitness center, game room, and fresh meal plans.",
        "coed", True, "+91 90040 82627", IMAGES[2], 4.7,
        "veg_nonveg", "10th Gulmohar Cross Road, JVPD Scheme, Juhu, Vile Parle West, Mumbai 400049",
        "NMIMS (1.0 km), Mithibai (0.9 km), SPIT (1.4 km), Bhavan's (1.3 km), RGIT (2.2 km)",
        ""
    ),
    (
        "Nidhaan Nest Girls Hostel",
        "Govandi East / Chembur",
        19.0542, 72.9158,
        4.5,
        {"triple": 7500, "double": 9800, "single": 14500},
        ["wifi", "ac", "meals", "laundry", "security", "power_backup"],
        "Safe and secure residential haven close to Tata Institute of Social Sciences (TISS) and Chembur tech colleges. Offers furnished rooms, nutritious meals, and 24/7 security.",
        "girls", True, "+91 97022 68908", IMAGES[3], 4.9,
        "pure_veg", "Deonar Farm Road, Near Telecom Colony, Govandi East, Mumbai 400088",
        "TISS Mumbai (0.1 km), SAKEC Chembur (1.2 km), VESIT Chembur (2.6 km)",
        ""
    ),
    (
        "Ganga Niwas Boys Hostel",
        "Vile Parle West",
        19.1040, 72.8415,
        4.2,
        {"dorm": 6500, "triple": 8800, "double": 11500},
        ["wifi", "meals", "security", "laundry", "power_backup"],
        "Budget-friendly, disciplined boys' student hostel within short walking distance of Mithibai and NMIMS with home-cooked pure vegetarian meals and essential amenities.",
        "boys", True, "+91 87790 03845", IMAGES[4], 4.5,
        "pure_veg", "Dadabhai Road, Near Irla Market, Vile Parle West, Mumbai 400056",
        "Mithibai College (0.5 km), NMIMS (0.6 km), Bhavan's College (1.6 km)",
        ""
    ),
    (
        "Telang Memorial Girls Hostel",
        "Churchgate",
        18.9325, 72.8258,
        4.6,
        {"dorm": 4500, "triple": 6200, "double": 8500},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "Historic and prestigious girls' student accommodation in Churchgate South Mumbai, minutes away from premier commerce, arts, and law colleges along Marine Drive.",
        "girls", True, "022-22041792", IMAGES[0], 4.9,
        "pure_veg", "16 C Road, Churchgate, Mumbai 400020",
        "HR College (0.2 km), KC College (0.3 km), Jai Hind College (0.3 km), GLC (0.4 km), MU Fort (0.8 km)",
        ""
    ),
    (
        "YWCA Lady Willingdon Hostel",
        "Fort",
        18.9272, 72.8315,
        4.5,
        {"triple": 8500, "double": 11500, "single": 16000},
        ["wifi", "meals", "security", "power_backup", "study_room"],
        "Renowned institution celebrating over 125 years of service for women students and young professionals in South Mumbai. Exceptional safety, serene courtyard, and wholesome mess.",
        "girls", True, "022-22020122", IMAGES[1], 4.9,
        "veg_nonveg", "18 Madame Cama Road, Near Regal Cinema, Fort, Mumbai 400001",
        "St. Xavier's College (1.8 km), Elphinstone College (0.7 km), GLC (0.8 km), MU Fort (0.9 km)",
        ""
    ),
    (
        "Sheth G. M. Jain Hostel",
        "Prabhadevi",
        19.0162, 72.8300,
        4.5,
        {"dorm": 2800, "triple": 3800, "double": 5000},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "Charitable Jain trust hostel in Prabhadevi offering affordable accommodation and Jain dining for male students pursuing graduation and competitive exams in Dadar/Central Mumbai.",
        "boys", True, "022-24225315", IMAGES[2], 4.8,
        "jain", "Shankar Ghanekar Marg, Near Siddhivinayak Temple, Prabhadevi, Mumbai 400025",
        "Kirti College Dadar (0.8 km), Ruparel College (1.8 km), VJTI (2.8 km), ICT Matunga (3.0 km)",
        ""
    ),
    (
        "Seva Niketan Boys' Hostel",
        "Byculla",
        18.9715, 72.8350,
        4.3,
        {"dorm": 3500, "triple": 4800, "double": 6500},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "Established community hostel catering to male college students in Central Mumbai with quick access to Byculla railway station, Saboo Siddik, and Grant Medical College.",
        "boys", True, "+91 90042 02344", IMAGES[3], 4.6,
        "veg_nonveg", "Sir J.J. Road, Near Byculla Station, Byculla East, Mumbai 400008",
        "Saboo Siddik College of Engg (0.6 km), Grant Medical College (1.1 km), St. Xavier's (3.5 km)",
        ""
    ),
    (
        "Bhavan's Campus Hostels",
        "Andheri West",
        19.1235, 72.8362,
        4.6,
        {"triple": 5500, "double": 7500},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "On-campus collegiate residences for students of SPIT, SPCE, and Bhavan's with sprawling green grounds, library, pure vegetarian mess, and 24/7 security.",
        "coed", True, "022-26232191", IMAGES[4], 4.9,
        "pure_veg", "Bhavan's Campus, Munshi Nagar, Dadabhai Road, Andheri West, Mumbai 400058",
        "SPIT (0.0 km), SPCE (0.0 km), Bhavan's College (0.0 km), Mithibai College (1.8 km)",
        ""
    ),
    (
        "VJTI Student Hostels",
        "Matunga East",
        19.0225, 72.8565,
        4.5,
        {"triple": 3500, "double": 5000, "single": 7000},
        ["wifi", "meals", "gym", "study_room", "security", "power_backup"],
        "Autonomous engineering college hostels with dedicated blocks for male and female scholars in the academic hub of Matunga, adjacent to VJTI and ICT.",
        "coed", True, "022-24198100", IMAGES[0], 4.8,
        "pure_veg", "H.R. Mahajani Marg, Matunga East, Mumbai 400019",
        "VJTI (0.0 km), ICT Mumbai (0.2 km), Khalsa College (0.4 km), Ruia College (0.8 km)",
        ""
    ),
    (
        "MU Kalina Campus Scholars & Student Hostels",
        "Kalina, Santacruz East",
        19.0745, 72.8680,
        4.1,
        {"dorm": 2200, "triple": 3200, "double": 4500},
        ["wifi", "meals", "study_room", "security", "power_backup"],
        "University of Mumbai residential complex inside Vidyanagari campus providing highly subsidized rooms and dining for students and research scholars.",
        "coed", True, "022-26543000", IMAGES[1], 4.7,
        "pure_veg", "Vidyanagari Campus, CST Road, Kalina, Santacruz East, Mumbai 400098",
        "University of Mumbai Kalina (0.0 km), DBIT Kurla (1.8 km), TSEC Bandra (3.8 km)",
        ""
    ),
    (
        "Somaiya Vidyavihar Campus Hostels",
        "Vidyavihar East",
        19.0725, 72.8990,
        4.7,
        {"triple": 9000, "double": 13000, "single": 18500},
        ["wifi", "ac", "meals", "gym", "laundry", "study_room", "security", "power_backup"],
        "Sprawling 65-acre campus living featuring modern rooms (Sandipani & Maitreyi blocks), sports track, 100% pure vegetarian & Jain mess, and 24/7 security.",
        "coed", True, "022-67283000", IMAGES[2], 4.9,
        "pure_veg", "Somaiya Vidyavihar Campus, Vidyavihar East, Mumbai 400077",
        "K.J. Somaiya College of Engineering (0.1 km), Somaiya Arts & Science (0.2 km)",
        ""
    ),
    (
        "Bandra Student Nest & PG",
        "Bandra West",
        19.0620, 72.8340,
        4.6,
        {"triple": 13500, "double": 17500, "single": 25000},
        ["wifi", "ac", "meals", "laundry", "security", "power_backup"],
        "Vibrant student residence off Linking Road minutes from Bandra station, TSEC, and National College. Offers AC rooms, high-speed WiFi, and home-style pure veg meals.",
        "coed", True, "+91 98205 11223", IMAGES[3], 4.8,
        "pure_veg", "Off Linking Road, Near National College, Bandra West, Mumbai 400050",
        "Thadomal Shahani TSEC (0.4 km), National College (0.2 km), Rizvi Engg (1.2 km), Fr. CRCE (2.2 km)",
        ""
    ),
    (
        "Powai Lake View Residency",
        "Powai",
        19.1280, 72.9110,
        4.6,
        {"triple": 11000, "double": 15500, "single": 22000},
        ["wifi", "ac", "meals", "gym", "laundry", "study_room", "security", "power_backup"],
        "Convenient scholar accommodation opposite IIT Bombay Main Gate with scenic lake views, fiber internet, study desks, and hygienic meals.",
        "coed", True, "+91 98331 44556", IMAGES[4], 4.8,
        "veg_nonveg", "JVLR, Near IIT Main Gate, Powai, Mumbai 400076",
        "IIT Bombay (0.7 km), NITIE / IIM Mumbai (2.0 km)",
        ""
    ),
    (
        "Shraddhanand Mahilashram Girls Hostel",
        "Matunga East",
        19.0268, 72.8572,
        4.6,
        {"dorm": 4000, "triple": 5500, "double": 7500},
        ["wifi", "meals", "study_room", "security", "power_backup", "library"],
        "Established in 1928 by Hindu Mahila Sabha, Shraddhanand Mahilashram is a revered, safe women's institution in Matunga East. Provides secure, disciplined hostel accommodation for female college students attending VJTI, ICT, Ruia, Podar, Khalsa, and VIT Wadala with wholesome pure vegetarian dining and quiet study halls.",
        "girls", True, "022-24012552", IMAGES[0], 4.9,
        "pure_veg", "Shraddhanand Road, Near Maheshwari Udyan (King's Circle), Matunga East, Mumbai 400019",
        "Khalsa College (0.3 km), Ruia & Podar (0.5 km), VJTI (0.6 km), ICT (0.7 km), VIT Wadala (1.6 km)",
        "https://shraddhanandmahilashram.org/"
    ),
]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close(_):
    d = g.pop("db", None)
    if d:
        d.close()

def init_db():
    c = sqlite3.connect(DB)
    c.execute("""
        CREATE TABLE IF NOT EXISTS hostels(
            id INTEGER PRIMARY KEY,
            name TEXT,
            area TEXT,
            distance_km REAL,
            rating REAL,
            rooms TEXT,
            amenities TEXT,
            about TEXT,
            lat REAL,
            lng REAL,
            gender TEXT,
            verified INTEGER,
            phone TEXT,
            cover_image TEXT,
            safety_score REAL,
            food TEXT DEFAULT 'pure_veg',
            address TEXT,
            nearby_colleges TEXT,
            website TEXT
        )
    """)
    c.execute("CREATE TABLE IF NOT EXISTS shortlist(client_id TEXT, hostel_id INTEGER, PRIMARY KEY(client_id, hostel_id))")
    c.execute("CREATE TABLE IF NOT EXISTS enquiries(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, hostel_id INTEGER, name TEXT, phone TEXT, move_date TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    cols = [r[1] for r in c.execute("PRAGMA table_info(hostels)")]
    if "food" not in cols:
        c.execute("ALTER TABLE hostels ADD COLUMN food TEXT DEFAULT 'pure_veg'")
    if "address" not in cols:
        c.execute("ALTER TABLE hostels ADD COLUMN address TEXT")
    if "nearby_colleges" not in cols:
        c.execute("ALTER TABLE hostels ADD COLUMN nearby_colleges TEXT")
    if "website" not in cols:
        c.execute("ALTER TABLE hostels ADD COLUMN website TEXT")

    # Check if database has old fictional hostels that need replacing with real Mumbai hostels
    has_fictional = c.execute("SELECT 1 FROM hostels WHERE area = 'Near Campus Gate' OR name LIKE 'Urban Bunk Co.%'").fetchone()
    if has_fictional:
        c.execute("DELETE FROM hostels")
        c.execute("DELETE FROM sqlite_sequence WHERE name='hostels'")

    existing_names = {r[0] for r in c.execute("SELECT name FROM hostels").fetchall()}
    for i, item in enumerate(SEED, 1):
        name, area, lat, lng, rating, rooms, ams, about, gen, ver, phone, img, sft, food, addr, col_list, web = item
        if name not in existing_names:
            initial_dist = haversine_km(CLAT, CLNG, lat, lng)
            c.execute(
                "INSERT INTO hostels(name, area, distance_km, rating, rooms, amenities, about, lat, lng, gender, verified, phone, cover_image, safety_score, food, address, nearby_colleges, website) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (name, area, initial_dist, rating, json.dumps(rooms), json.dumps(ams), about, lat, lng, gen, 1 if ver else 0, phone, img, sft, food, addr, col_list, web)
            )
    c.commit()
    c.close()

def row_to_dict(r):
    h = dict(r)
    h["rooms"] = json.loads(h["rooms"]) if isinstance(h["rooms"], str) else h["rooms"]
    h["amenities"] = json.loads(h["amenities"]) if isinstance(h["amenities"], str) else h["amenities"]
    h["price"] = min(h["rooms"].values())
    h["gender"] = h.get("gender") or "coed"
    h["food"] = h.get("food") or "pure_veg"
    h["address"] = h.get("address") or h.get("area") or ""
    h["nearby_colleges"] = h.get("nearby_colleges") or ""
    h["website"] = h.get("website") or ""
    h["verified"] = bool(h.get("verified", True))
    h["phone"] = h.get("phone") or "022-26250376"
    h["cover_image"] = h.get("cover_image") or IMAGES[(h["id"] - 1) % len(IMAGES)]
    h["safety_score"] = float(h.get("safety_score") or 4.5)
    return h

def score(h, p):
    """Returns (total 0-100, breakdown). Weights: budget 25, distance 25, amenities 30, room 10, rating 10."""
    rooms = [h["rooms"][r] for r in p["rooms"] if r in h["rooms"]] or list(h["rooms"].values())
    price = min(rooms)
    h["price"] = price
    ratio = price / p["budget"]
    
    if ratio <= 0.8:
        budget = 25.0
    else:
        budget = 25.0 - (ratio - 0.8) / 0.2 * 10.0
    budget = max(0.0, min(25.0, budget))
        
    dist = 25.0 * (1.0 - 0.6 * h["distance_km"] / p["max_distance"])
    dist = max(0.0, min(25.0, dist))
    
    am = p["amenities"]
    amen = 30.0 * (len([a for a in am if a in h["amenities"]]) / len(am)) if am else 30.0
    
    room = 10.0
    rating = min(10.0, max(0.0, h["rating"] / 5.0 * 10.0))
    
    parts = {
        "budget": round(budget, 1),
        "distance": round(dist, 1),
        "amenities": round(amen, 1),
        "room": room,
        "rating": round(rating, 1)
    }
    total = min(100, max(0, round(sum(parts.values()))))
    return total, parts

def parse(data):
    try:
        budget = float(data.get("budget", 0))
        maxd = float(data.get("max_distance", 0))
    except (TypeError, ValueError):
        return None, "budget and max_distance must be numbers"
    if budget <= 0 or maxd <= 0:
        return None, "budget and max_distance must be greater than 0"
    rooms = [r for r in data.get("rooms", []) if r in ROOMS]
    ams = [a for a in data.get("amenities", []) if a in AMENITIES]
    gender = str(data.get("gender", "")).lower().strip()
    food = str(data.get("food", "")).lower().strip()
    q = str(data.get("q", "")).strip().lower()
    college_id = str(data.get("college_id", "")).strip()
    
    campus_lat = None
    campus_lng = None
    if "campus_lat" in data and "campus_lng" in data and data["campus_lat"] and data["campus_lng"]:
        try:
            campus_lat = float(data["campus_lat"])
            campus_lng = float(data["campus_lng"])
        except (ValueError, TypeError):
            pass
    elif college_id in COLLEGES_MAP:
        c = COLLEGES_MAP[college_id]
        campus_lat = c["lat"]
        campus_lng = c["lng"]

    return {
        "budget": budget,
        "max_distance": maxd,
        "rooms": rooms,
        "amenities": ams,
        "gender": gender,
        "food": food,
        "q": q,
        "college_id": college_id,
        "campus_lat": campus_lat,
        "campus_lng": campus_lng
    }, None

@app.get("/")
def index():
    return render_template("index.html", rooms=ROOMS, amenities=AMENITIES, genders=GENDERS, foods=FOODS, colleges=COLLEGES)

@app.get("/api/colleges")
def get_colleges():
    return jsonify(results=COLLEGES)

@app.post("/api/recommend")
def recommend():
    data = request.get_json(silent=True) or {}
    p, err = parse(data)
    if err:
        return jsonify(error=err), 400
    key, rev = SORTS.get(data.get("sort", "match"), SORTS["match"])
    
    # Target coordinates for distance calculation
    ref_lat = p["campus_lat"] if p["campus_lat"] is not None else CLAT
    ref_lng = p["campus_lng"] if p["campus_lng"] is not None else CLNG

    out = []
    for r in db().execute("SELECT * FROM hostels"):
        h = row_to_dict(r)
        
        # Real-time Haversine distance calculation to selected campus
        if h["lat"] and h["lng"]:
            h["distance_km"] = haversine_km(ref_lat, ref_lng, h["lat"], h["lng"])
        
        # Gender filter check
        if p["gender"] and p["gender"] != "coed" and h["gender"] != "coed" and h["gender"] != p["gender"]:
            continue

        # Food & Dietary filter check
        if p["food"] and p["food"] != "all":
            if p["food"] == "jain" and h["food"] != "jain":
                continue
            elif p["food"] in ("pure_veg", "veg") and h["food"] not in ("jain", "pure_veg"):
                continue
            
        # Search query check across name, area, address, nearby colleges, and description
        if p["q"]:
            match_str = f"{h['name']} {h['area']} {h['address']} {h['nearby_colleges']} {h['about']}".lower()
            if p["q"] not in match_str:
                continue

        offered = [x for x in p["rooms"] if x in h["rooms"]]
        if p["rooms"] and not offered:
            continue
        h["price"] = min(h["rooms"][x] for x in (offered or h["rooms"]))
        if h["price"] > p["budget"] or h["distance_km"] > p["max_distance"]:
            continue
        h["match"], h["breakdown"] = score(h, p)
        h["missing_amenities"] = [a for a in p["amenities"] if a not in h["amenities"]]
        out.append(h)
        
    out.sort(key=lambda h: (h[key], h["match"]), reverse=rev)
    return jsonify(count=len(out), results=out, ref_location={"lat": ref_lat, "lng": ref_lng})

@app.get("/api/hostels/<int:hid>")
def hostel(hid):
    r = db().execute("SELECT * FROM hostels WHERE id=?", (hid,)).fetchone()
    return (jsonify(row_to_dict(r)) if r else (jsonify(error="not found"), 404))

def cid():
    return request.headers.get("X-Client-Id", "")[:64] or None

@app.get("/api/shortlist")
def get_short():
    c = cid()
    if not c:
        return jsonify(error="X-Client-Id header required"), 400
    rows = db().execute("SELECT h.* FROM hostels h JOIN shortlist s ON s.hostel_id=h.id WHERE s.client_id=?", (c,))
    return jsonify(results=[row_to_dict(r) for r in rows])

@app.route("/api/shortlist/<int:hid>", methods=["POST", "DELETE"])
def toggle_short(hid):
    c = cid()
    if not c:
        return jsonify(error="X-Client-Id header required"), 400
    d = db()
    if not d.execute("SELECT 1 FROM hostels WHERE id=?", (hid,)).fetchone():
        return jsonify(error="not found"), 404
    if request.method == "POST":
        d.execute("INSERT OR IGNORE INTO shortlist VALUES(?,?)", (c, hid))
    else:
        d.execute("DELETE FROM shortlist WHERE client_id=? AND hostel_id=?", (c, hid))
    d.commit()
    return jsonify(ok=True)

@app.post("/api/enquiry")
def booking_enquiry():
    d = request.get_json(silent=True) or {}
    hid = d.get("hostel_id")
    name = str(d.get("name", "")).strip()
    phone = str(d.get("phone", "")).strip()
    move_date = str(d.get("move_date", "")).strip()
    message = str(d.get("message", "")).strip()
    
    if not hid or not name or not phone:
        return jsonify(error="Hostel ID, Name, and Phone are required"), 400
        
    code = f"HM-{random.randint(10000, 99999)}"
    db().execute("INSERT INTO enquiries(code, hostel_id, name, phone, move_date, message) VALUES(?,?,?,?,?,?)",
                 (code, hid, name, phone, move_date, message))
    db().commit()
    return jsonify(ok=True, code=code, message="Booking inquiry submitted successfully! A manager will contact you shortly.")

@app.get("/api/hostels")
def all_hostels():
    college_id = request.args.get("college_id", "").strip()
    ref_lat = CLAT
    ref_lng = CLNG
    if college_id in COLLEGES_MAP:
        ref_lat = COLLEGES_MAP[college_id]["lat"]
        ref_lng = COLLEGES_MAP[college_id]["lng"]
    elif request.args.get("lat") and request.args.get("lng"):
        try:
            ref_lat = float(request.args.get("lat"))
            ref_lng = float(request.args.get("lng"))
        except ValueError:
            pass
            
    items = []
    for r in db().execute("SELECT * FROM hostels ORDER BY id"):
        h = row_to_dict(r)
        if h["lat"] and h["lng"]:
            h["distance_km"] = haversine_km(ref_lat, ref_lng, h["lat"], h["lng"])
        items.append(h)
    return jsonify(results=items, count=len(items))

# ---------- Admin API ----------
def is_admin():
    return hmac.compare_digest(request.headers.get("X-Admin-Key", ""), ADMIN_KEY)

def clean(d):
    """Validate an admin hostel payload. Returns (values, error)."""
    try:
        name = str(d["name"]).strip()
        area = str(d.get("area", "")).strip()
        dist = float(d.get("distance_km", 1.0))
        rating = float(d["rating"])
        rooms = {k: float(v) for k, v in d["rooms"].items() if k in ROOMS and float(v) > 0}
    except (KeyError, TypeError, ValueError, AttributeError):
        return None, "name, distance_km, rating and rooms {type: price} are required"
    if not name or not rooms or dist < 0 or not 0 <= rating <= 5:
        return None, "need a name, at least one room price, distance >= 0 and rating 0-5"
    ams = [a for a in d.get("amenities", []) if a in AMENITIES]
    try:
        lat = float(d["lat"]) if d.get("lat") not in (None, "") else CLAT
        lng = float(d["lng"]) if d.get("lng") not in (None, "") else CLNG
    except (TypeError, ValueError):
        return None, "lat and lng must be numbers"
    
    gender = str(d.get("gender", "coed")).lower()
    if gender not in GENDERS:
        gender = "coed"
    food = str(d.get("food", "pure_veg")).lower()
    if food not in FOODS:
        food = "pure_veg"
    verified = 1 if d.get("verified", True) else 0
    phone = str(d.get("phone", "022-26250376")).strip()
    cover_image = str(d.get("cover_image", IMAGES[0])).strip()
    safety_score = float(d.get("safety_score", 4.5))
    address = str(d.get("address", area)).strip()
    nearby_colleges = str(d.get("nearby_colleges", "")).strip()
    website = str(d.get("website", "")).strip()

    return dict(name=name, area=area, distance_km=dist, rating=rating, rooms=json.dumps(rooms),
                amenities=json.dumps(ams), about=str(d.get("about", ""))[:400], lat=lat, lng=lng,
                gender=gender, verified=verified, phone=phone, cover_image=cover_image, safety_score=safety_score,
                food=food, address=address, nearby_colleges=nearby_colleges, website=website), None

@app.get("/admin")
def admin_page():
    return render_template("admin.html", rooms=ROOMS, amenities=AMENITIES, genders=GENDERS, foods=FOODS, colleges=COLLEGES)

@app.route("/api/admin/hostels", methods=["POST"])
@app.route("/api/admin/hostels/<int:hid>", methods=["PUT", "DELETE"])
def admin_write(hid=None):
    if not is_admin():
        return jsonify(error="invalid admin key"), 401
    d = db()
    if request.method == "DELETE":
        d.execute("DELETE FROM hostels WHERE id=?", (hid,))
        d.execute("DELETE FROM shortlist WHERE hostel_id=?", (hid,))
        d.commit()
        return jsonify(ok=True)
    v, err = clean(request.get_json(silent=True) or {})
    if err:
        return jsonify(error=err), 400
    if request.method == "POST":
        cur = d.execute("INSERT INTO hostels(name,area,distance_km,rating,rooms,amenities,about,lat,lng,gender,verified,phone,cover_image,safety_score,food,address,nearby_colleges,website) VALUES(:name,:area,:distance_km,:rating,:rooms,:amenities,:about,:lat,:lng,:gender,:verified,:phone,:cover_image,:safety_score,:food,:address,:nearby_colleges,:website)", v)
        hid = cur.lastrowid
    else:
        if not d.execute("SELECT 1 FROM hostels WHERE id=?", (hid,)).fetchone():
            return jsonify(error="not found"), 404
        d.execute("UPDATE hostels SET name=:name,area=:area,distance_km=:distance_km,rating=:rating,rooms=:rooms,amenities=:amenities,about=:about,lat=:lat,lng=:lng,gender=:gender,verified=:verified,phone=:phone,cover_image=:cover_image,safety_score=:safety_score,food=:food,address=:address,nearby_colleges=:nearby_colleges,website=:website WHERE id=:id", {**v, "id": hid})
    d.commit()
    return jsonify(ok=True, id=hid), (201 if request.method == "POST" else 200)

init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("DEBUG") == "1", port=int(os.environ.get("PORT", 5000)))
