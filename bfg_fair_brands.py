# ============================================================
# BFG GM MODE — FAIR BRAND ENGINE UPGRADE
# Keeps original Python UI, but fixes brand bias and adds:
# - Equal starting brand ratings
# - Story + continuity show rating
# - In-ring storytelling + wrestling ability match rating
# - Brand color shift
# - Balanced sponsor perks
# ============================================================

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ----------------------------
# Helpers
# ----------------------------

def clamp(value, low, high):
    return max(low, min(high, value))


def money(value):
    value = round(value)
    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000_000:
        return f"{sign}${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.0f}K"
    return f"{sign}${value}"


def slug(text):
    return (
        text.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace(".", "")
        .replace("/", "-")
    )


# ----------------------------
# Equal Brand Settings
# ----------------------------

EQUAL_STARTING_VALUES = {
    "starting_bank": 150_000_000,
    "starting_viewership": 2_000_000,
    "brand_rating": 75,
    "fan_interest": 75,
    "story_score": 75,
    "continuity_score": 75,
    "sponsor_confidence": 75,
    "gm_trust": 75,
    "locker_room_chemistry": 75,
}


BRAND_THEMES = {
    "NXT": {
        "primary": "#b026ff",
        "secondary": "#d4af37",
        "background": "#100014",
        "card": "#1b1024",
        "text": "#f5f0ff",
        "accent_name": "Purple / Gold",
    },
    "SmackDown": {
        "primary": "#1e88ff",
        "secondary": "#e10600",
        "background": "#061427",
        "card": "#0d1d35",
        "text": "#f4f8ff",
        "accent_name": "Blue / Red",
    },
    "WCW": {
        "primary": "#d4af37",
        "secondary": "#8b0000",
        "background": "#140909",
        "card": "#201010",
        "text": "#fff5df",
        "accent_name": "Gold / Dark Red",
    },
}


BALANCED_SPONSOR_PERKS = {
    "NXT": {
        "perk": "Delta / Netflix Premium Media",
        "description": "Delta covers 50% travel costs OR Netflix/Apple gives premium media bonus for strong story shows.",
        "travel_discount": 0.50,
        "hotel_discount": 0.00,
        "media_bonus_multiplier": 1.10,
    },
    "SmackDown": {
        "perk": "Marriott Culture Travel",
        "description": "Marriott covers hotel costs and boosts celebrity/culture event presentation.",
        "travel_discount": 0.00,
        "hotel_discount": 1.00,
        "media_bonus_multiplier": 1.05,
    },
    "WCW": {
        "perk": "Mercedes / Tesla Sports Travel",
        "description": "Mercedes/Tesla covers transportation and boosts sports-business presentation.",
        "travel_discount": 1.00,
        "hotel_discount": 0.00,
        "media_bonus_multiplier": 1.05,
    },
}


# ----------------------------
# Wrestler Model
# ----------------------------

@dataclass
class Wrestler:
    name: str
    brand: str
    division: str = "Main Event"
    alignment: str = "N"  # F, H, N

    overall: int = 75
    popularity: int = 75
    momentum: int = 50
    morale: int = 75
    stamina: int = 80

    # New ability stats
    wrestling_ability: int = 75
    mic_skill: int = 75
    charisma: int = 75
    storytelling: int = 75
    psychology: int = 75

    wins: int = 0
    losses: int = 0
    champion: bool = False
    current_storyline: Optional[str] = None

    wrestler_id: str = field(init=False)

    def __post_init__(self):
        self.wrestler_id = slug(f"{self.brand}-{self.name}")


# ----------------------------
# Brand Model
# ----------------------------

@dataclass
class BrandState:
    name: str
    roster: List[Wrestler] = field(default_factory=list)

    bank: int = EQUAL_STARTING_VALUES["starting_bank"]
    viewership: int = EQUAL_STARTING_VALUES["starting_viewership"]
    brand_rating: int = EQUAL_STARTING_VALUES["brand_rating"]
    fan_interest: int = EQUAL_STARTING_VALUES["fan_interest"]
    story_score: int = EQUAL_STARTING_VALUES["story_score"]
    continuity_score: int = EQUAL_STARTING_VALUES["continuity_score"]
    sponsor_confidence: int = EQUAL_STARTING_VALUES["sponsor_confidence"]
    gm_trust: int = EQUAL_STARTING_VALUES["gm_trust"]
    locker_room_chemistry: int = EQUAL_STARTING_VALUES["locker_room_chemistry"]

    weekly_rating_history: List[float] = field(default_factory=list)
    viewership_history: List[int] = field(default_factory=list)
    money_history: List[int] = field(default_factory=list)
    storyline_history: List[Dict] = field(default_factory=list)


# ----------------------------
# Create Fair Brand State
# ----------------------------

def create_equal_brand_state(brand_name: str, roster: Optional[List[Wrestler]] = None) -> BrandState:
    """
    Creates a brand with equal starting values.
    This removes the old bias where one brand started with higher viewership or better core stats.
    """
    return BrandState(
        name=brand_name,
        roster=roster or [],
        bank=EQUAL_STARTING_VALUES["starting_bank"],
        viewership=EQUAL_STARTING_VALUES["starting_viewership"],
        brand_rating=EQUAL_STARTING_VALUES["brand_rating"],
        fan_interest=EQUAL_STARTING_VALUES["fan_interest"],
        story_score=EQUAL_STARTING_VALUES["story_score"],
        continuity_score=EQUAL_STARTING_VALUES["continuity_score"],
        sponsor_confidence=EQUAL_STARTING_VALUES["sponsor_confidence"],
        gm_trust=EQUAL_STARTING_VALUES["gm_trust"],
        locker_room_chemistry=EQUAL_STARTING_VALUES["locker_room_chemistry"],
    )


# ----------------------------
# Roster Dict Adapters
# (BFG stores wrestlers as dicts — derive ability stats when missing)
# ----------------------------

def ability_stats_for(w: Dict) -> Dict[str, int]:
    """Derive the new ability stats for a BFG roster dict, honoring explicit values when present."""
    overall = int(w.get("overall", 75))
    popularity = int(w.get("popularity", overall))
    return {
        "wrestling_ability": int(w.get("wrestling_ability", overall)),
        "mic_skill": int(w.get("mic_skill", popularity)),
        "charisma": int(w.get("charisma", popularity)),
        "storytelling": int(w.get("storytelling", round((overall + popularity) / 2))),
        "psychology": int(w.get("psychology", clamp(overall - 3, 40, 100))),
    }


def wrestler_from_dict(w: Dict) -> Wrestler:
    stats = ability_stats_for(w)
    return Wrestler(
        name=w.get("name", "Unknown"),
        brand=w.get("company", "NXT"),
        division=w.get("division", "Main Event"),
        alignment=w.get("alignment", "N"),
        overall=int(w.get("overall", 75)),
        popularity=int(w.get("popularity", 75)),
        momentum=int(w.get("momentum", 50)),
        morale=int(w.get("morale", 75)),
        stamina=int(w.get("stamina", 80)),
        wins=int(w.get("wins", 0)),
        losses=int(w.get("losses", 0)),
        **stats,
    )


# ----------------------------
# Match Rating Engine
# ----------------------------

def calculate_match_rating(
    wrestler_a: Wrestler,
    wrestler_b: Wrestler,
    story_told_in_ring: int,
    rivalry_heat: int,
    chemistry: int,
    stipulation_fit: int,
    crowd_interest: int,
):
    """
    Match rating is no longer just popularity or overall.
    It is now based on story told in the ring + wrestling ability.
    """

    avg_wrestling_ability = (wrestler_a.wrestling_ability + wrestler_b.wrestling_ability) / 2
    avg_psychology = (wrestler_a.psychology + wrestler_b.psychology) / 2
    avg_storytelling = (wrestler_a.storytelling + wrestler_b.storytelling) / 2

    in_ring_story_score = (
        story_told_in_ring * 0.50
        + avg_psychology * 0.25
        + avg_storytelling * 0.25
    )

    rating_100 = (
        in_ring_story_score * 0.35
        + avg_wrestling_ability * 0.30
        + rivalry_heat * 0.15
        + chemistry * 0.10
        + stipulation_fit * 0.05
        + crowd_interest * 0.05
    )

    rating_10 = round(clamp(rating_100 / 10, 1, 10), 1)

    return {
        "rating_100": round(clamp(rating_100, 1, 100), 1),
        "rating_10": rating_10,
        "summary": explain_match_rating(rating_10),
    }


def explain_match_rating(rating):
    if rating >= 9:
        return "Classic match. The in-ring story, ability, and emotion all connected."
    if rating >= 8:
        return "Great match. Strong story and strong wrestling performance."
    if rating >= 7:
        return "Good match. Solid work, but it needed a stronger emotional hook."
    if rating >= 6:
        return "Average match. The wrestling was fine, but the story was not strong enough."
    if rating >= 5:
        return "Weak match. The crowd needed more reason to care."
    return "Bad match. Poor story connection and weak in-ring execution."


# ----------------------------
# Show Rating Engine
# ----------------------------

def calculate_show_rating(
    story_continuity: int,
    story_emotion: int,
    avg_match_quality: int,
    character_accuracy: int,
    champion_usage: int,
    sponsor_brand_fit: int,
    crowd_presentation: int,
):
    """
    Show rating is mostly story and continuity.
    Money does not decide show quality.
    Big stars help, but story matters most.
    """

    rating_100 = (
        story_continuity * 0.30
        + story_emotion * 0.20
        + avg_match_quality * 0.20
        + character_accuracy * 0.10
        + champion_usage * 0.10
        + sponsor_brand_fit * 0.05
        + crowd_presentation * 0.05
    )

    rating_10 = round(clamp(rating_100 / 10, 1, 10), 1)

    return {
        "rating_100": round(clamp(rating_100, 1, 100), 1),
        "rating_10": rating_10,
        "letter_grade": convert_rating_to_letter(rating_100),
        "summary": explain_show_rating(rating_10),
    }


def convert_rating_to_letter(score):
    if score >= 93:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 80:
        return "A-"
    if score >= 75:
        return "B+"
    if score >= 70:
        return "B"
    if score >= 65:
        return "B-"
    if score >= 60:
        return "C+"
    if score >= 55:
        return "C"
    if score >= 50:
        return "C-"
    if score >= 40:
        return "D"
    return "F"


def explain_show_rating(rating):
    if rating >= 9:
        return "Legendary show. Story, continuity, emotion, and match quality all delivered."
    if rating >= 8:
        return "Strong show. The stories connected and the matches had purpose."
    if rating >= 7:
        return "Good show. Solid booking, but one or two stories needed stronger follow-up."
    if rating >= 6:
        return "Average show. Some good moments, but continuity or emotion was missing."
    if rating >= 5:
        return "Weak show. The matches happened, but the story did not fully connect."
    return "Bad show. Poor continuity, weak emotional logic, and low fan investment."


# ----------------------------
# Viewership Update
# ----------------------------

def update_viewership(current_viewership: int, show_rating: float, continuity_score: int, fan_interest: int):
    """
    Viewership grows from good booking, not from brand bias.
    """

    rating_bonus = (show_rating - 6.5) * 0.025
    continuity_bonus = (continuity_score - 75) * 0.0015
    fan_bonus = (fan_interest - 75) * 0.001

    growth_rate = rating_bonus + continuity_bonus + fan_bonus
    growth_rate = clamp(growth_rate, -0.08, 0.10)

    new_viewership = round(current_viewership * (1 + growth_rate))
    return clamp(new_viewership, 500_000, 5_000_000)


# ----------------------------
# Season Score / Win Condition
# ----------------------------

def calculate_season_score(
    story_quality: int,
    continuity: int,
    ple_payoff: int,
    sponsor_objectives: int,
    fan_investment: int,
    audience_growth: int,
    profit_score: int,
):
    """
    Richest brand should not automatically win.
    Best story and continuity matter most.
    """

    score = (
        story_quality * 0.30
        + continuity * 0.25
        + ple_payoff * 0.15
        + sponsor_objectives * 0.10
        + fan_investment * 0.10
        + audience_growth * 0.05
        + profit_score * 0.05
    )

    return round(clamp(score, 0, 100), 1)


# ----------------------------
# Brand Color Shift CSS
# ----------------------------

def get_brand_theme_css(brand_name: str):
    theme = BRAND_THEMES.get(brand_name, BRAND_THEMES["NXT"])

    return f"""
    <style>
        .stApp {{
            background: linear-gradient(135deg, {theme["background"]}, #050505 70%);
            color: {theme["text"]};
        }}

        .bfg-header {{
            background: linear-gradient(135deg, {theme["card"]}, #080808);
            border: 1px solid {theme["primary"]};
            box-shadow: 0 0 18px {theme["primary"]}44;
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 18px;
        }}

        .bfg-card {{
            background: {theme["card"]};
            border: 1px solid {theme["primary"]}99;
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 14px;
            box-shadow: 0 0 14px {theme["primary"]}33;
        }}

        .bfg-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            background: {theme["primary"]};
            color: white;
            font-weight: 700;
            margin-right: 8px;
        }}

        .bfg-number {{
            color: {theme["secondary"]};
            font-size: 28px;
            font-weight: 800;
        }}

        div.stButton > button {{
            border-radius: 12px;
            border: 1px solid {theme["primary"]};
            background: linear-gradient(135deg, {theme["primary"]}, {theme["secondary"]});
            color: white;
            font-weight: 700;
        }}
    </style>
    """


def render_brand_header(st, brand: BrandState, current_week: int):
    """
    Use this inside your original UI where your page header is.
    """

    st.markdown(get_brand_theme_css(brand.name), unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="bfg-header">
            <h1>BOUND FOR GLORY GM MODE</h1>
            <span class="bfg-badge">{brand.name}</span>
            <span class="bfg-badge">Week {current_week}</span>
            <p>
                Bank: <span class="bfg-number">{money(brand.bank)}</span> |
                Viewership: <span class="bfg-number">{brand.viewership:,}</span>
            </p>
            <p>
                Story: {brand.story_score} |
                Continuity: {brand.continuity_score} |
                Fan Interest: {brand.fan_interest} |
                GM Trust: {brand.gm_trust}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------
# Simple Example Integration
# ----------------------------

def initialize_fair_brands_if_missing(st):
    """
    Call this once near the start of app.py.
    This creates equal NXT, SmackDown, and WCW states if missing.
    """

    if "brands" not in st.session_state:
        st.session_state.brands = {
            "NXT": create_equal_brand_state("NXT"),
            "SmackDown": create_equal_brand_state("SmackDown"),
            "WCW": create_equal_brand_state("WCW"),
        }

    if "selected_brand" not in st.session_state:
        st.session_state.selected_brand = "NXT"

    if "current_week" not in st.session_state:
        st.session_state.current_week = 1


def apply_weekly_show_result(st, brand_name: str, show_result: dict):
    """
    Call this after the user submits a show.
    """

    brand = st.session_state.brands[brand_name]

    show_rating = show_result["rating_10"]
    brand.weekly_rating_history.append(show_rating)

    brand.viewership = update_viewership(
        current_viewership=brand.viewership,
        show_rating=show_rating,
        continuity_score=brand.continuity_score,
        fan_interest=brand.fan_interest,
    )

    brand.viewership_history.append(brand.viewership)

    if show_rating >= 8:
        brand.story_score = clamp(brand.story_score + 2, 0, 100)
        brand.continuity_score = clamp(brand.continuity_score + 2, 0, 100)
        brand.fan_interest = clamp(brand.fan_interest + 2, 0, 100)
        brand.gm_trust = clamp(brand.gm_trust + 1, 0, 100)
    elif show_rating < 6:
        brand.story_score = clamp(brand.story_score - 2, 0, 100)
        brand.continuity_score = clamp(brand.continuity_score - 2, 0, 100)
        brand.fan_interest = clamp(brand.fan_interest - 2, 0, 100)
        brand.gm_trust = clamp(brand.gm_trust - 1, 0, 100)

    st.session_state.brands[brand_name] = brand
