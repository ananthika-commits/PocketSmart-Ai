import json
import re
import urllib.parse
from io import BytesIO
from typing import Any, Dict, List, Optional

from PIL import Image

from app.config import settings

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None


def generate_platform_url(platform: str, query: str) -> str:
    """Generates authentic search / product discovery URLs for major e-commerce platforms."""
    encoded_query = urllib.parse.quote_plus(query.strip())
    p_lower = platform.lower().strip()

    if "amazon" in p_lower:
        return f"https://www.amazon.in/s?k={encoded_query}"
    elif "ikea" in p_lower:
        return f"https://www.ikea.com/in/en/search/?q={encoded_query}"
    elif "flipkart" in p_lower:
        return f"https://www.flipkart.com/search?q={encoded_query}"
    elif "swiggy" in p_lower:
        return f"https://www.swiggy.com/search?query={encoded_query}"
    elif "zomato" in p_lower:
        return f"https://www.zomato.com/search?q={encoded_query}"
    elif "oyo" in p_lower:
        return f"https://www.oyorooms.com/"
    elif "pepperfry" in p_lower:
        return f"https://www.pepperfry.com/site_product/search?q={encoded_query}"
    elif "myntra" in p_lower:
        return f"https://www.myntra.com/{encoded_query}"
    elif "caratlane" in p_lower or "tanishq" in p_lower:
        return f"https://www.caratlane.com/search/{encoded_query}"
    else:
        return f"https://www.google.com/search?q={urllib.parse.quote_plus(platform + ' ' + query)}"


def _clean_json(text: str) -> str:
    """Strips Markdown backticks and extraneous text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def _extract_json(text: str) -> Dict[str, Any]:
    """Finds and parses the first JSON object from LLM response."""
    cleaned = _clean_json(text)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(cleaned)


def _enrich_recommendations(data: Dict[str, Any]) -> Dict[str, Any]:
    """Enriches recommendation items with direct platform search links and verified badges."""
    recommendations = data.get("recommendations", [])
    for item in recommendations:
        name = item.get("name", "Product")
        platform = item.get("platform", "Amazon")
        if not item.get("url"):
            search_term = item.get("search_query") or f"{name} {platform}"
            item["url"] = generate_platform_url(platform, search_term)
        if not item.get("savings_tip"):
            item["savings_tip"] = "Compare prices across platforms to save up to 15-20%."
    return data


def _generate_dynamic_fallback(category: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intelligent, context-sensitive fallback engine when Gemini API key is missing or unavailable.
    Accurately computes budget percentages and provides curated platform options.
    """
    budget = float(user_input.get("budget", 20000))
    currency = "₹"

    if category == "home":
        rooms = user_input.get("rooms", "Living Room, Bedroom")
        items_req = user_input.get("items", "LED ambient lights, center table, decorative rug")
        style = user_input.get("style", "Modern Minimalist").capitalize()

        alloc_furniture = round(budget * 0.45)
        alloc_lighting = round(budget * 0.25)
        alloc_decor = round(budget * 0.20)
        alloc_buffer = round(budget * 0.10)

        recommendations = [
            {
                "name": f"Smart Dimmable LED Ambient Light System",
                "category": "Lighting & Electricals",
                "platform": "Amazon",
                "price": f"{currency}{alloc_lighting:,}",
                "savings_tip": "Buy multi-pack bundle with smart app control to save ~18%.",
                "reason": f"Essential for brightening up {rooms.split(',')[0].strip()} with low power consumption and warm tones.",
                "search_query": "smart led ceiling accent lighting home",
                "url": generate_platform_url("Amazon", "smart led ceiling accent lighting"),
            },
            {
                "name": f"Minimalist Modular Coffee & Dining Table",
                "category": "Furniture",
                "platform": "IKEA",
                "price": f"{currency}{alloc_furniture:,}",
                "savings_tip": "Check IKEA flat-pack deals for easy self-assembly discounts.",
                "reason": f"Space-efficient solid wood finish perfectly complementing a {style} interior style.",
                "search_query": "modular wooden coffee dining table ikea",
                "url": generate_platform_url("IKEA", "coffee table dining furniture"),
            },
            {
                "name": f"Handwoven Geometric Area Rug & Cushions Set",
                "category": "Soft Furnishings & Decor",
                "platform": "Flipkart",
                "price": f"{currency}{alloc_decor:,}",
                "savings_tip": "Use bank discount offers during festive e-commerce sales.",
                "reason": f"Ties the color palette together, providing acoustic warmth and visual texture for {rooms}.",
                "search_query": "handwoven geometric floor rug home decor",
                "url": generate_platform_url("Flipkart", "handwoven geometric area rug"),
            },
        ]

        total_est = alloc_furniture + alloc_lighting + alloc_decor

        return {
            "category": "Home Interior",
            "summary": f"Tailored {style} interior setup for {rooms}, optimizing comfort and aesthetics within {currency}{budget:,.0f}.",
            "budget_note": f"Balanced allocation: 45% Furniture ({currency}{alloc_furniture:,}), 25% Lighting ({currency}{alloc_lighting:,}), 20% Decor ({currency}{alloc_decor:,}), 10% Reserve buffer ({currency}{alloc_buffer:,}).",
            "total_estimated_spend": f"{currency}{total_est:,}",
            "estimated_savings": f"{currency}{round(budget * 0.18):,}",
            "budget_allocation": [
                {"label": "Furniture & Main Pieces", "percentage": 45, "amount": f"{currency}{alloc_furniture:,}"},
                {"label": "Lighting & Fixtures", "percentage": 25, "amount": f"{currency}{alloc_lighting:,}"},
                {"label": "Decor & Soft Furnishings", "percentage": 20, "amount": f"{currency}{alloc_decor:,}"},
                {"label": "Reserve & Delivery Buffer", "percentage": 10, "amount": f"{currency}{alloc_buffer:,}"},
            ],
            "tips": [
                "Measure your doorframes and hallway clearance before placing large furniture orders.",
                "Pair 2700K warm white LED lights with neutral wall paint for a cozy, spacious ambience.",
                "Mix high-impact low-cost items like indoor plants and mirrors to amplify natural light.",
            ],
            "recommendations": recommendations,
        }

    elif category == "party":
        guest_count = int(user_input.get("guest_count", 30))
        event_type = user_input.get("event_type", "Birthday Celebration").capitalize()
        venue = user_input.get("venue", "Banquet / Rooftop")

        alloc_catering = round(budget * 0.45)
        alloc_venue = round(budget * 0.30)
        alloc_decor = round(budget * 0.20)
        alloc_buffer = round(budget * 0.05)

        per_head = round(budget / max(guest_count, 1))

        recommendations = [
            {
                "name": f"Custom Party Meal & Beverage Catering (For {guest_count} guests)",
                "category": "Food & Catering",
                "platform": "Zomato",
                "price": f"{currency}{alloc_catering:,}",
                "savings_tip": "Order pre-set bulk party combos rather than à la carte items.",
                "reason": f"Covers starters, mocktails, main course and dessert at ~{currency}{round(alloc_catering/max(guest_count, 1))} per person.",
                "search_query": "bulk catering party food boxes",
                "url": generate_platform_url("Zomato", "party catering food delivery"),
            },
            {
                "name": f"Event Space / Guest Accommodation Booking",
                "category": "Venue & Stays",
                "platform": "OYO",
                "price": f"{currency}{alloc_venue:,}",
                "savings_tip": "Book townhouse spaces with combined hall & stay facilities.",
                "reason": f"Provides comfortable space, guest resting rooms, and centralized gathering area for {venue}.",
                "search_query": "OYO townhouse banquet party hall",
                "url": generate_platform_url("OYO", "townhouse banquet party hall"),
            },
            {
                "name": f"Theme Decoration Kit & Wireless Party Sound System",
                "category": "Decoration & Entertainment",
                "platform": "Amazon",
                "price": f"{currency}{alloc_decor:,}",
                "savings_tip": "Reusable metallic balloon arch and LED string lights save over single-use florists.",
                "reason": f"Instantly sets the celebratory tone and provides party music without expensive DJ fees.",
                "search_query": f"{event_type.lower()} party decoration lights bluetooth speaker",
                "url": generate_platform_url("Amazon", f"{event_type.lower()} party decoration kit"),
            },
        ]

        total_est = alloc_catering + alloc_venue + alloc_decor

        return {
            "category": "Party Planning",
            "summary": f"Smart {event_type} event plan for {guest_count} guests with an effective per-guest spend of {currency}{per_head:,}.",
            "budget_note": f"Strategic split: 45% Catering ({currency}{alloc_catering:,}), 30% Venue/Stay ({currency}{alloc_venue:,}), 20% Decor/Sound ({currency}{alloc_decor:,}), 5% Buffer ({currency}{alloc_buffer:,}).",
            "total_estimated_spend": f"{currency}{total_est:,}",
            "estimated_savings": f"{currency}{round(budget * 0.15):,}",
            "budget_allocation": [
                {"label": "Catering & Refreshments", "percentage": 45, "amount": f"{currency}{alloc_catering:,}"},
                {"label": "Venue & Accommodations", "percentage": 30, "amount": f"{currency}{alloc_venue:,}"},
                {"label": "Decor & Sound System", "percentage": 20, "amount": f"{currency}{alloc_decor:,}"},
                {"label": "Miscellaneous Reserve", "percentage": 5, "amount": f"{currency}{alloc_buffer:,}"},
            ],
            "tips": [
                f"Confirm final RSVP count 48 hours in advance to optimize catering portions.",
                "Opt for finger food starters and interactive live food counters to elevate guest experience.",
                "Prepare a curated Spotify playlist in advance for seamless background and dance music.",
            ],
            "recommendations": recommendations,
        }

    else:  # Jewelry
        occasion = user_input.get("occasion", "Wedding / Festive").capitalize()
        style = user_input.get("style", "Elegant Modern").capitalize()
        notes = user_input.get("notes", "Matching outfit")

        alloc_necklace = round(budget * 0.50)
        alloc_earrings = round(budget * 0.30)
        alloc_bracelet = round(budget * 0.20)

        recommendations = [
            {
                "name": f"Handcrafted Statement Choker / Pendant Necklace",
                "category": "Necklace & Pendants",
                "platform": "CaratLane",
                "price": f"{currency}{alloc_necklace:,}",
                "savings_tip": "Look for 14kt/18kt verified hallmark gold or silver filigree pieces.",
                "reason": f"Centerpiece jewelry that frames the neckline beautifully for {occasion}.",
                "search_query": f"{style} necklace jewelry caratlane",
                "url": generate_platform_url("CaratLane", f"{style} necklace jewelry"),
            },
            {
                "name": f"Embossed Chandelier / Pearl Drop Earrings",
                "category": "Earrings",
                "platform": "Amazon",
                "price": f"{currency}{alloc_earrings:,}",
                "savings_tip": "Pick anti-tarnish hypoallergenic alloys with customer-verified reviews.",
                "reason": f"Complements the face profile and balances hair styling without being overly heavy.",
                "search_query": f"{style} drop earrings jewelry",
                "url": generate_platform_url("Amazon", f"{style} drop earrings jewelry"),
            },
            {
                "name": f"Minimalist Stackable Cuff Bracelet & Cocktail Ring",
                "category": "Bracelets & Rings",
                "platform": "Flipkart",
                "price": f"{currency}{alloc_bracelet:,}",
                "savings_tip": "Check combo sets with coordinated metal finishes.",
                "reason": f"Subtle wrist accent that ties together the entire {style} ensemble.",
                "search_query": f"{style} stackable cuff bracelet cocktail ring",
                "url": generate_platform_url("Flipkart", f"{style} cuff bracelet cocktail ring"),
            },
        ]

        total_est = alloc_necklace + alloc_earrings + alloc_bracelet

        return {
            "category": "Jewelry Styling",
            "summary": f"Curated {style} jewelry collection designed for {occasion} with harmonious metal accents and budget control.",
            "budget_note": f"Coordinated split: 50% Statement piece ({currency}{alloc_necklace:,}), 30% Accent earrings ({currency}{alloc_earrings:,}), 20% Rings/Bracelet ({currency}{alloc_bracelet:,}).",
            "total_estimated_spend": f"{currency}{total_est:,}",
            "estimated_savings": f"{currency}{round(budget * 0.20):,}",
            "outfit_analysis": f"Aesthetics matched for {occasion} with {style} silhouette. Recommends contrasting or harmonious metallic undertones.",
            "budget_allocation": [
                {"label": "Statement Neckpiece", "percentage": 50, "amount": f"{currency}{alloc_necklace:,}"},
                {"label": "Coordinated Earrings", "percentage": 30, "amount": f"{currency}{alloc_earrings:,}"},
                {"label": "Bracelets & Ring Set", "percentage": 20, "amount": f"{currency}{alloc_bracelet:,}"},
            ],
            "tips": [
                "If your outfit has heavy neck embroidery, choose statement earrings and skip a chunky necklace.",
                "Store costume and silver jewelry in airtight pouches to prevent moisture tarnishing.",
                "Match jewelry metal warmth (Gold, Silver, Rose Gold) with the undertone of your attire.",
            ],
            "recommendations": recommendations,
        }


def _build_prompt(category: str, payload: Dict[str, Any], has_image: bool = False) -> str:
    """Builds optimized structured prompts requesting strict JSON from Gemini."""
    budget = payload.get("budget", 20000)

    if category == "home":
        return f"""
You are PocketSmart AI, an expert interior designer and smart home budgeting assistant.
Analyze the following user input and return a comprehensive budget allocation and cross-platform product recommendation plan.

User Requirements:
- Total Budget: ₹{budget}
- Rooms to furnish/decorate: {payload.get('rooms')}
- Required items / quantities: {payload.get('items')}
- Style preference: {payload.get('style', 'Modern')}

Instructions:
1. Provide a realistic budget distribution breakdown (percentages and rupee amounts).
2. Recommend 3 to 4 specific, cost-effective products from trusted platforms like Amazon, IKEA, Flipkart, or Pepperfry.
3. Every recommendation MUST strictly include:
   - "name": Detailed product title
   - "category": e.g., Furniture, Lighting, Wall Decor, Rugs
   - "platform": One of "Amazon", "IKEA", "Flipkart", "Pepperfry"
   - "price": Estimated price in ₹ (e.g. "₹4,500")
   - "savings_tip": Actionable smart tip to save money
   - "reason": Why this fits the user's specific room and budget
   - "search_query": Search keyword string to find this on that platform
4. Provide practical styling & interior planning tips.

CRITICAL: Return ONLY valid, raw JSON (no conversational text outside JSON) in this exact schema:
{{
  "category": "Home Interior",
  "summary": "High level plan summary",
  "budget_note": "How the budget was distributed",
  "total_estimated_spend": "₹XX,XXX",
  "estimated_savings": "₹X,XXX",
  "budget_allocation": [
    {{"label": "Category Name", "percentage": 45, "amount": "₹X,XXX"}}
  ],
  "tips": [
    "Tip 1", "Tip 2", "Tip 3"
  ],
  "recommendations": [
    {{
      "name": "Product Name",
      "category": "Subcategory",
      "platform": "Amazon / IKEA / Flipkart",
      "price": "₹X,XXX",
      "savings_tip": "Tip",
      "reason": "Reason",
      "search_query": "search query"
    }}
  ]
}}
"""

    elif category == "party":
        return f"""
You are PocketSmart AI, a professional event planner and budget strategist.
Analyze the following user requirements and generate a structured event budget plan with vendor sourcing recommendations.

User Requirements:
- Total Budget: ₹{budget}
- Guest Count: {payload.get('guest_count')}
- Event Type: {payload.get('event_type')}
- Venue Type: {payload.get('venue')}
- Additional Notes: {payload.get('notes', 'None')}

Instructions:
1. Allocate budget across Catering, Venue/Stay, Decoration, and Music/Entertainment.
2. Recommend 3 to 4 vendor options and supplies from Swiggy, Zomato, OYO, Amazon, Blinkit, or Ferns N Petals.
3. Every recommendation MUST include:
   - "name": Vendor service or package title
   - "category": Food & Catering, Venue & Stay, or Decor & Audio
   - "platform": "Swiggy", "Zomato", "OYO", "Amazon"
   - "price": Estimated cost in ₹
   - "savings_tip": Actionable budget savings tip
   - "reason": Why it suits the event type and guest count
   - "search_query": Search query string
4. Calculate per-guest budget and provide party execution tips.

CRITICAL: Return ONLY valid, raw JSON in this schema:
{{
  "category": "Party Planning",
  "summary": "Plan summary",
  "budget_note": "Budget split explanation",
  "total_estimated_spend": "₹XX,XXX",
  "estimated_savings": "₹X,XXX",
  "budget_allocation": [
    {{"label": "Catering / Food", "percentage": 45, "amount": "₹X,XXX"}}
  ],
  "tips": [
    "Tip 1", "Tip 2"
  ],
  "recommendations": [
    {{
      "name": "Service / Item",
      "category": "Category",
      "platform": "Swiggy / Zomato / OYO / Amazon",
      "price": "₹X,XXX",
      "savings_tip": "Tip",
      "reason": "Reason",
      "search_query": "query"
    }}
  ]
}}
"""

    else:  # Jewelry
        image_guidance = (
            "Analyze the attached outfit image carefully for primary colors, metallic accents (gold/silver/rose-gold), "
            "fabric texture, neckline, and aesthetic vibe."
            if has_image
            else "Use the user's outfit description to determine color coordination and metal pairing."
        )

        return f"""
You are PocketSmart AI, a luxury personal jewelry stylist and budget advisor.
Analyze the following requirements and outfit details to curate a coordinated jewelry collection.

User Requirements:
- Budget: ₹{budget}
- Occasion: {payload.get('occasion')}
- Style Preference: {payload.get('style')}
- Outfit Notes: {payload.get('notes', 'None')}
- Visual input: {image_guidance}

Instructions:
1. Provide an outfit aesthetic analysis (detected colors, neckline recommendation, and metal pairing).
2. Recommend 3 to 4 matching jewelry items (Necklace, Earrings, Bangles/Bracelet, Cocktail Ring) across Amazon, Flipkart, CaratLane, or Myntra.
3. Every recommendation MUST include:
   - "name": Jewelry piece title
   - "category": Necklace / Earrings / Bracelet / Ring
   - "platform": "Amazon", "Flipkart", "CaratLane", "Myntra"
   - "price": Price in ₹
   - "savings_tip": Savings / alloy / hallmark tip
   - "reason": Why it matches the outfit tone, occasion, and neckline
   - "search_query": Search query
4. Provide personalized styling and care tips.

CRITICAL: Return ONLY valid, raw JSON in this schema:
{{
  "category": "Jewelry Styling",
  "summary": "Styling summary",
  "outfit_analysis": "Color scheme & aesthetic analysis",
  "budget_note": "Budget distribution note",
  "total_estimated_spend": "₹XX,XXX",
  "estimated_savings": "₹X,XXX",
  "budget_allocation": [
    {{"label": "Statement Piece", "percentage": 50, "amount": "₹X,XXX"}}
  ],
  "tips": [
    "Tip 1", "Tip 2"
  ],
  "recommendations": [
    {{
      "name": "Jewelry Piece",
      "category": "Category",
      "platform": "Amazon / Flipkart / CaratLane / Myntra",
      "price": "₹X,XXX",
      "savings_tip": "Tip",
      "reason": "Styling reason",
      "search_query": "query"
    }}
  ]
}}
"""


def generate_recommendations(
    category: str, user_input: Dict[str, Any], image_file: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Main recommendation orchestrator.
    Attempts Gemini 1.5 Flash multimodal / text generation.
    Falls back gracefully to intelligent algorithmic recommendations if API key is not configured or fails.
    """
    category_key = category.lower().strip()
    if "home" in category_key:
        cat = "home"
    elif "party" in category_key:
        cat = "party"
    else:
        cat = "jewelry"

    # If Gemini API key is missing or genai not installed, use smart dynamic fallback
    if not settings.GEMINI_API_KEY or genai is None:
        data = _generate_dynamic_fallback(cat, user_input)
        return _enrich_recommendations(data)

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"
        model = genai.GenerativeModel(model_name)

        has_image = False
        pil_image = None

        if image_file is not None and hasattr(image_file, "file"):
            try:
                contents = image_file.file.read()
                if contents:
                    pil_image = Image.open(BytesIO(contents))
                    has_image = True
                image_file.file.seek(0)
            except Exception:
                has_image = False

        prompt = _build_prompt(cat, user_input, has_image=has_image)

        if has_image and pil_image:
            response = model.generate_content([prompt, pil_image])
        else:
            response = model.generate_content(prompt)

        response_text = getattr(response, "text", "") or str(response)
        parsed = _extract_json(response_text)

        if isinstance(parsed, dict) and "recommendations" in parsed:
            return _enrich_recommendations(parsed)

    except Exception as err:
        # Log or keep fallback silent
        pass

    # Seamless fallback if API fails or returns invalid structure
    data = _generate_dynamic_fallback(cat, user_input)
    return _enrich_recommendations(data)
