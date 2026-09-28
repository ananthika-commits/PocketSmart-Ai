import json
import sqlite3
from typing import Any, Dict, List, Optional

# Compatibility fix for passlib with bcrypt >= 4.1.0
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        class _BcryptAbout:
            __version__ = getattr(bcrypt, "__version__", "4.1.2")
        bcrypt.__about__ = _BcryptAbout()
except ImportError:
    pass

from app.config import BASE_DIR

DB_PATH = BASE_DIR / "pocketsmart.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                input_payload TEXT NOT NULL,
                result_payload TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()

    # Seed demo user and initial sample plan if database is freshly initialized
    _seed_demo_data_if_empty()


def _seed_demo_data_if_empty() -> None:
    try:
        user = get_user_by_username("demo_user")
        if not user:
            from passlib.context import CryptContext
            pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            new_user = create_user("demo_user", "demo@pocketsmart.ai", pwd_ctx.hash("demo1234"))
            
            # Seed a sample home interior plan
            sample_input = {
                "budget": 35000,
                "rooms": "Living Room, Dining Area",
                "items": "LED ceiling lights, dining table, area rug",
                "style": "Modern Minimalist",
            }
            sample_result = {
                "category": "Home Interior",
                "summary": "Balanced Modern Minimalist setup for Living Room & Dining Area.",
                "budget_note": "Allocated 45% furniture (₹15,750), 25% lighting (₹8,750), 20% decor (₹7,000), 10% reserve (₹3,500).",
                "total_estimated_spend": "₹31,500",
                "estimated_savings": "₹6,300",
                "budget_allocation": [
                    {"label": "Furniture & Main Pieces", "percentage": 45, "amount": "₹15,750"},
                    {"label": "Lighting & Fixtures", "percentage": 25, "amount": "₹8,750"},
                    {"label": "Decor & Soft Furnishings", "percentage": 20, "amount": "₹7,000"},
                    {"label": "Reserve & Delivery Buffer", "percentage": 10, "amount": "₹3,500"},
                ],
                "tips": [
                    "Pair 2700K warm white LED lights with neutral wall paint.",
                    "Measure door clearances before ordering modular tables.",
                ],
                "recommendations": [
                    {
                        "name": "Smart Dimmable LED Ambient Light System",
                        "category": "Lighting & Electricals",
                        "platform": "Amazon",
                        "price": "₹8,750",
                        "savings_tip": "Buy multipack bundle with smart app control to save ~18%.",
                        "reason": "Brightens the living room with warm dimmable tones and energy efficiency.",
                        "search_query": "smart led ceiling accent lighting",
                        "url": "https://www.amazon.in/s?k=smart+led+ceiling+accent+lighting",
                    },
                    {
                        "name": "Minimalist Modular Wooden Dining Table",
                        "category": "Furniture",
                        "platform": "IKEA",
                        "price": "₹15,750",
                        "savings_tip": "IKEA flat-pack delivery saves on heavy assembly surcharges.",
                        "reason": "Durable solid pine table designed for compact apartment dining spaces.",
                        "search_query": "modular wooden dining table ikea",
                        "url": "https://www.ikea.com/in/en/search/?q=dining+table",
                    },
                    {
                        "name": "Handwoven Geometric Area Rug & Cushions",
                        "category": "Soft Furnishings & Decor",
                        "platform": "Flipkart",
                        "price": "₹7,000",
                        "savings_tip": "Check festive sale coupons for extra 10% instant discount.",
                        "reason": "Provides acoustic dampening, cozy floor texture, and ties room colors together.",
                        "search_query": "handwoven geometric area rug",
                        "url": "https://www.flipkart.com/search?q=handwoven+geometric+area+rug",
                    },
                ],
            }
            save_recommendation(new_user["id"], "Home Interior", sample_input, sample_result)
    except Exception:
        pass


def create_user(username: str, email: str, password_hash: str) -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), password_hash),
        )
        user_id = cursor.lastrowid
        conn.commit()
        return {"id": user_id, "username": username.strip(), "email": email.strip().lower()}


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
            (username.strip(),),
        ).fetchone()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
            (email.strip(),),
        ).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def save_recommendation(
    user_id: int, category: str, input_payload: Dict[str, Any], result_payload: Dict[str, Any]
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO recommendations (user_id, category, input_payload, result_payload) VALUES (?, ?, ?, ?)",
            (
                user_id,
                category,
                json.dumps(input_payload),
                json.dumps(result_payload),
            ),
        )
        rec_id = cursor.lastrowid
        conn.commit()
        return rec_id


def get_recent_recommendations(
    user_id: int, limit: int = 10, category: Optional[str] = None
) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                """
                SELECT id, category, input_payload, result_payload, created_at
                FROM recommendations
                WHERE user_id = ? AND LOWER(category) = LOWER(?)
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, category, input_payload, result_payload, created_at
                FROM recommendations
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

    response: List[Dict[str, Any]] = []
    for row in rows:
        try:
            inp = json.loads(row["input_payload"])
        except Exception:
            inp = {}
        try:
            res = json.loads(row["result_payload"])
        except Exception:
            res = {}
        response.append(
            {
                "id": row["id"],
                "category": row["category"],
                "input_payload": inp,
                "result_payload": res,
                "created_at": row["created_at"],
            }
        )
    return response


def get_recommendation_by_id(rec_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        if user_id is not None:
            row = conn.execute(
                "SELECT * FROM recommendations WHERE id = ? AND user_id = ?",
                (rec_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM recommendations WHERE id = ?",
                (rec_id,),
            ).fetchone()

    if not row:
        return None

    try:
        inp = json.loads(row["input_payload"])
    except Exception:
        inp = {}
    try:
        res = json.loads(row["result_payload"])
    except Exception:
        res = {}

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "category": row["category"],
        "input_payload": inp,
        "result_payload": res,
        "created_at": row["created_at"],
    }


def delete_recommendation(rec_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM recommendations WHERE id = ? AND user_id = ?",
            (rec_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_dashboard_stats(user_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        total_plans = conn.execute(
            "SELECT COUNT(*) as count FROM recommendations WHERE user_id = ?",
            (user_id,),
        ).fetchone()["count"]

        recent_rows = conn.execute(
            "SELECT category, input_payload, result_payload FROM recommendations WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    total_budget_analyzed = 0.0
    category_counts: Dict[str, int] = {}

    for row in recent_rows:
        cat = row["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        try:
            inp = json.loads(row["input_payload"])
            budget = float(inp.get("budget", 0))
            total_budget_analyzed += budget
        except Exception:
            pass

    top_category = max(category_counts, key=category_counts.get) if category_counts else "Home Interior"
    # Estimated savings estimated as ~18% across platform comparisons
    estimated_savings = total_budget_analyzed * 0.18

    return {
        "total_plans": total_plans,
        "total_budget_analyzed": round(total_budget_analyzed, 2),
        "estimated_savings": round(estimated_savings, 2),
        "top_category": top_category,
    }
