import io
from fastapi.testclient import TestClient
from PIL import Image

from app.database import init_db
from gemini_utils import generate_platform_url, _generate_dynamic_fallback
from main import app

# Ensure database is initialized with demo user
init_db()

client = TestClient(app)


def test_startup_health_check():
    response = client.get("/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "PocketSmart AI"


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "PocketSmart" in response.text
    assert "Home Interior" in response.text
    assert "Party Budget" in response.text
    assert "Jewelry" in response.text


def test_testimonials_page_loads():
    response = client.get("/testimonials")
    assert response.status_code == 200
    assert "Real Stories" in response.text
    assert "Whitefield" in response.text


def test_login_page_loads():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Welcome Back" in response.text
    assert "demo_user" in response.text


def test_register_page_loads():
    response = client.get("/register")
    assert response.status_code == 200
    assert "Create Your Account" in response.text


def test_user_authentication_flow():
    # Login with the seeded demo user
    response = client.post(
        "/login",
        data={"username": "demo_user", "password": "demo1234"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_user_registration_and_login():
    import uuid
    uid = uuid.uuid4().hex[:6]
    unique_user = f"user_{uid}"
    unique_email = f"user_{uid}@example.com"
    reg_response = client.post(
        "/register",
        data={
            "username": unique_user,
            "email": unique_email,
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    assert reg_response.status_code == 303
    assert reg_response.headers["location"] == "/dashboard"


def test_home_planner_page_loads():
    response = client.get("/home-planner")
    assert response.status_code == 200
    assert "Home Interior Planning" in response.text


def test_generate_home_route_form():
    response = client.post(
        "/generate-home",
        data={
            "budget": "25000",
            "rooms": "Living Room, Kitchen",
            "items": "LED ceiling lights, dining table, area rug",
            "style": "Modern Minimalist",
        },
    )
    assert response.status_code == 200
    assert "Home Interior" in response.text
    assert "Budget Distribution Strategy" in response.text
    assert "Amazon" in response.text or "IKEA" in response.text


def test_party_planner_page_loads():
    response = client.get("/party-planner")
    assert response.status_code == 200
    assert "Party Budget Planner" in response.text


def test_generate_party_route_form():
    response = client.post(
        "/generate-party",
        data={
            "budget": "50000",
            "guest_count": "45",
            "event_type": "Birthday Celebration",
            "venue": "Rooftop Banquet",
            "notes": "Finger food, mocktails, music system",
        },
    )
    assert response.status_code == 200
    assert "Party Planning" in response.text
    assert "Catering" in response.text or "Zomato" in response.text


def test_jewelry_planner_page_loads():
    response = client.get("/jewelry-planner")
    assert response.status_code == 200
    assert "Jewelry Styling" in response.text
    assert "outfit" in response.text.lower()


def test_generate_jewelry_route_form_text():
    response = client.post(
        "/generate-jewelry",
        data={
            "budget": "20000",
            "occasion": "Wedding / Reception Sangeet",
            "style": "Traditional Ethnic / Kundan & Polki",
            "notes": "Red silk saree with gold embroidery",
        },
    )
    assert response.status_code == 200
    assert "Jewelry Styling" in response.text


def test_generate_jewelry_route_with_image_upload():
    # Create small synthetic test image in memory
    img = Image.new("RGB", (100, 100), color=(180, 50, 80))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    response = client.post(
        "/generate-jewelry",
        data={
            "budget": "18000",
            "occasion": "Festive Celebration (Diwali / Eid / Puja)",
            "style": "Contemporary Rose Gold Glam",
            "notes": "Matching rose dress",
        },
        files={"image": ("outfit.png", img_byte_arr, "image/png")},
    )
    assert response.status_code == 200
    assert "Jewelry Styling" in response.text


def test_platform_url_generation():
    assert "amazon.in" in generate_platform_url("Amazon", "led lights")
    assert "ikea.com" in generate_platform_url("IKEA", "dining table")
    assert "flipkart.com" in generate_platform_url("Flipkart", "area rug")
    assert "swiggy.com" in generate_platform_url("Swiggy", "catering")
    assert "zomato.com" in generate_platform_url("Zomato", "party food")
    assert "oyorooms.com" in generate_platform_url("OYO", "townhouse")


def test_dynamic_fallback_engine():
    home_data = _generate_dynamic_fallback("home", {"budget": 40000, "rooms": "Living Room"})
    assert home_data["category"] == "Home Interior"
    assert len(home_data["recommendations"]) >= 3
    assert len(home_data["budget_allocation"]) >= 3

    party_data = _generate_dynamic_fallback("party", {"budget": 60000, "guest_count": 50})
    assert party_data["category"] == "Party Planning"
    assert len(party_data["recommendations"]) >= 3

    jewelry_data = _generate_dynamic_fallback("jewelry", {"budget": 25000, "occasion": "Wedding"})
    assert jewelry_data["category"] == "Jewelry Styling"
    assert len(jewelry_data["recommendations"]) >= 3


def test_session_and_token_endpoints():
    auth_client = TestClient(app)
    # Log in
    login_res = auth_client.post(
        "/login",
        data={"username": "demo_user", "password": "demo1234"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303

    # Token endpoint
    token_res = auth_client.get("/token")
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert token_data["authenticated"] is True
    assert "access_token" in token_data

    # Session info
    info_res = auth_client.get("/session-info")
    assert info_res.status_code == 200
    assert info_res.json()["logged_in"] is True

    # Session data
    data_res = auth_client.get("/session-data")
    assert data_res.status_code == 200
    assert data_res.json()["username"] == "demo_user"

    # Authenticated dashboard
    dash_res = auth_client.get("/dashboard")
    assert dash_res.status_code == 200
    assert "Welcome back, demo_user" in dash_res.text

    # History page
    hist_res = auth_client.get("/history")
    assert hist_res.status_code == 200
    assert "Recommendation History" in hist_res.text

    # Recommendations details page
    det_res = auth_client.get("/recommendations-details")
    assert det_res.status_code == 200
    assert "Recommendations" in det_res.text

    # API recommendations endpoint
    api_recs = auth_client.get("/api/recommendations")
    assert api_recs.status_code == 200
    assert api_recs.json()["authenticated"] is True
