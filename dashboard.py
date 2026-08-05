import streamlit as st
import yfinance as yf
import statistics
import math
import os
import json
import hashlib
import html
import pandas as pd
import altair as alt
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta, time as _time
from zoneinfo import ZoneInfo
import logging
for _name in ("yfinance", "peewee",
              "streamlit.runtime.scriptrunner.script_run_context",
              "streamlit.runtime.scriptrunner_utils.script_run_context"):
    logging.getLogger(_name).setLevel(logging.CRITICAL)

st.set_page_config(page_title="דשבורד שבבים", page_icon="💹", layout="wide")

# ---------- יישור מימין לשמאל ----------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { direction: rtl; }
.block-container { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
h1, h2, h3, h4, h5, h6 { text-align: right; }
[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] { direction: ltr; }
/* כיתובי st.caption (הסברים מתחת לכותרות) — יישור לימין בכל הדשבורד */
[data-testid="stCaptionContainer"], [data-testid="stCaption"], .stCaption {
    direction: rtl;
    text-align: right;
}
[data-testid="stCaptionContainer"] p, [data-testid="stCaption"] p, .stCaption p {
    text-align: right;
}
/* כפתור ניתוח החדשות — בולט וקשור לאזור החדשות */
div[data-testid="stButton"] button {
    background: rgba(59,130,246,0.18);
    border: 1px solid #3b82f6;
    color: #93c5fd;
    font-weight: 700;
    border-radius: 8px;
}
div[data-testid="stButton"] button:hover {
    background: rgba(59,130,246,0.30);
    border-color: #60a5fa;
    color: #ffffff;
}
/* מתג "פרטים, מניות וחדשות" — עיצוב בולט וברור, כמו כפתור-פס */
div[data-testid="stToggle"] {
    background: rgba(124,58,237,0.10);
    border: 1px solid rgba(124,58,237,0.55);
    border-radius: 10px;
    padding: 8px 14px;
    margin: 4px 0 6px 0;
    transition: background 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stToggle"]:hover {
    background: rgba(124,58,237,0.20);
    border-color: #a78bfa;
}
div[data-testid="stToggle"] label p {
    font-weight: 700 !important;
    font-size: 15px !important;
    color: #c4b5fd !important;
}
/* כפתור "פתח" קטן ואפור בטבלת התחומים — דיסקרטי, לא מושך תשומת לב */
div[data-testid="stButton"] button[kind="tertiary"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    color: #9ca3af;
    font-weight: 500;
    padding: 4px 10px;
    min-height: 0;
    transition: background 0.12s ease, color 0.12s ease;
}
div[data-testid="stButton"] button[kind="tertiary"]:hover {
    background: rgba(255,255,255,0.10);
    border-color: rgba(255,255,255,0.30);
    color: #e5e7eb;
}
div[data-testid="stButton"] button[kind="tertiary"] p {
    font-size: 13px !important;
}
/* לשוניות (tabs) — בולטות עם רקע, גבול וצבע פעיל ברור */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: rgba(15,17,26,0.85);
    border-radius: 10px 10px 0 0;
    padding: 6px 8px 0;
    border-bottom: 2px solid rgba(255,255,255,0.10);
}
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.04);
    border-radius: 8px 8px 0 0;
    padding: 10px 22px;
    font-size: 15px;
    font-weight: 600;
    color: rgba(255,255,255,0.45);
    border: 1px solid rgba(255,255,255,0.08);
    border-bottom: none;
    margin-bottom: -2px;
    transition: background 0.15s, color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.09);
    color: rgba(255,255,255,0.80);
}
.stTabs [aria-selected="true"] {
    background: rgba(96,165,250,0.13) !important;
    color: #93c5fd !important;
    border-color: rgba(96,165,250,0.35) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #60a5fa !important;
    height: 3px;
    border-radius: 2px 2px 0 0;
}
.stTabs [data-baseweb="tab-panel"] {
    background: rgba(15,17,26,0.50);
    border: 1px solid rgba(255,255,255,0.08);
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 16px 12px 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------- שרשרת הערך ----------
value_chain = {
    "0. חומרי גלם וּווייפרים (Raw Materials)": ["SHECY", "SUOPY", "ENTG"],
    "1. תכנון ו-IP (EDA & IP)": ["SNPS", "CDNS", "ARM"],
    "2. מעבדים ו-AI — Fabless (Compute & AI)": ["NVDA", "AMD", "QCOM"],
    "3. תקשורת ואופטיקה — Fabless (Networking & Optics)": ["AVGO", "COHR", "LITE", "MRVL"],
    "4. יצרנים משולבים (IDM)": ["INTC", "TXN", "ADI", "NXPI", "STM", "ON", "IFNNY", "RNECY", "MCHP"],
    "5. זיכרון ואחסון (Memory & Storage)": ["MU", "WDC", "SNDK", "STX", "005930.KS", "000660.KS"],
    "6. ציוד ייצור (Wafer Fab Equipment)": ["ASML", "AMAT", "LRCX", "TOELY", "ASMIY"],
    "7. בקרת תהליכים ומדידה (Process Control)": ["KLAC", "ONTO", "NVMI", "CAMT"],
    "8. קבלני ייצור (Foundries)": ["TSM", "GFS", "UMC", "TSEM", "005930.KS"],
    "9. הרכבה, אריזה ובדיקות (Back-End / OSAT)": ["AMKR", "TER", "ATEYY", "BESIY", "AEIS"],
    "10. תשתיות AI וקירור (AI Infrastructure)": ["SMCI", "DELL", "HPE", "VRT", "ETN", "ANET"],
    "11. חשמל ואנרגיה": ["GEV", "VST", "CEG", "TLN", "NRG", "PWR", "BE"],
}

ISRAELI_TICKERS = {"TSEM", "NVMI", "CAMT"}

CHAIN_LOGO_DOMAINS = {
    "NVDA": "nvidia.com", "AMD": "amd.com", 
    "QCOM": "qualcomm.com", "MRVL": "marvell.com",
    "AVGO": "broadcom.com", "COHR": "coherent.com", "LITE": "lumentum.com",
    "ANET": "arista.com",
    "INTC": "intel.com", "TXN": "ti.com", "ADI": "analog.com",
    "NXPI": "nxp.com", "STM": "st.com", "ON": "onsemi.com",
    "IFNNY": "infineon.com", "RNECY": "renesas.com", "MCHP": "microchip.com",
    "MU": "micron.com", "WDC": "westerndigital.com", "SNDK": "sandisk.com",
    "STX": "seagate.com",
    "005930.KS": "samsung.com", "000660.KS": "skhynix.com",
    "ASML": "asml.com", "AMAT": "appliedmaterials.com", "LRCX": "lamresearch.com",
    "TOELY": "tel.com", "ASMIY": "asm.com",
    "KLAC": "kla.com", "ONTO": "ontoinnovation.com",
    "NVMI": "novami.com", "CAMT": "camtek.com",
    "TSM": "tsmc.com", "GFS": "gf.com", "UMC": "umc.com", "TSEM": "towersemi.com",
    "AMKR": "amkor.com", "TER": "teradyne.com",
    "ATEYY": "advantest.com", "BESIY": "besi.com", "AEIS": "aei.com",
    "SMCI": "supermicro.com", "DELL": "dell.com", "HPE": "hpe.com",
    "VRT": "vertiv.com", "ETN": "eaton.com",
    "SNPS": "synopsys.com", "CDNS": "cadence.com", "ARM": "arm.com",
    "SHECY": "shinetsu.co.jp", "SUOPY": "sumcosi.com", "ENTG": "entegris.com",
    "GEV": "gevernova.com", "VST": "vistracorp.com", "CEG": "constellationenergy.com",
    "TLN": "talenenergy.com", "NRG": "nrg.com", "PWR": "quantaservices.com",
    "BE": "bloomenergy.com",
}

SENSITIVITY_LEVELS = {
    "vhigh": {"label": "גבוהה מאוד", "color": "#dc2626", "emoji": "🔴"},
    "high":  {"label": "גבוהה",      "color": "#f97316", "emoji": "🟠"},
    "med":   {"label": "בינונית",    "color": "#eab308", "emoji": "🟡"},
    "low":   {"label": "נמוכה",      "color": "#22c55e", "emoji": "🟢"},
}

CAPEX_SENSITIVITY = {
    "0":  {"level": "med",   "timing": "Q+1 עד Q+2",
           "mechanism": "חומרים מתכלים צמודי-ייצור — הנפח יורד, אך ללא קריסת מחיר"},
    "1":  {"level": "low",   "timing": "כמעט אף פעם",
           "mechanism": 'מנויים רב-שנתיים; תכנון שבבים ומו"פ לא נעצרים גם במיתון'},
    "2":  {"level": "high",  "timing": "Q+1 עד Q+2",
           "mechanism": "החשיפה הגבוהה בשרשרת — ההכנסה היא ה-CAPEX; כוח תמחור ומרווח 70%+ סופגים; סיכון מלאי והתחייבויות ל-TSMC"},
    "3":  {"level": "high",  "timing": "Q+1 עד Q+2",
           "mechanism": "ממומן מאותו תקציב; פוטוניקה = הגנת mix-shift בתוך התקציב, לא הגנה מירידתו"},
    "4":  {"level": "low",   "timing": "מחזור נפרד",
           "mechanism": "פיזור לרכב, תעשייה ואנלוגי — תלות נמוכה ב-AI CAPEX"},
    "5":  {"level": "vhigh", "timing": "ספוט: שבועות · HBM: Q+2",
           "mechanism": "קומודיטי + מנוף תפעולי עצום; ספוט מגיב מיידית, חוזי LTA של HBM דוחים אך לא מבטלים"},
    "6":  {"level": "high",  "timing": "הזמנות Q+2 · הכנסות Q+4",
           "mechanism": "רגישות לנגזרת (קצב השינוי); צבר וזמני אספקה ארוכים "},
    "7":  {"level": "med",   "timing": "Q+2 עד Q+4",
           "mechanism": "אינטנסיביות הבדיקה עולה עם מורכבות השבב — הגנה מבנית חלקית"},
    "8":  {"level": "med",   "timing": "Q+2 עד Q+4",
           "mechanism": "מקדמות וחוזי take-or-pay מגלגלים סיכון ללקוח; בוגר (UMC/TSEM) — מחזור נפרד"},
    "9":  {"level": "vhigh", "timing": "Q+1",
           "mechanism": "עסקי ניצולת ללא צבר, מרווח דק; חריג: אריזה מתקדמת (CoWoS) — צוואר בקבוק מבני"},
    "10": {"level": "med",   "timing": "שרתים Q+1 · קירור Q+4",
           "mechanism": "מפוצל: הרכבת שרתים מגיבה תוך רבעון, קירור ותשתית מוגנים בצבר שנה+"},
    "11": {"level": "med",   "timing": "PPA: שנה+ · ציוד הקמה: Q+2 עד Q+4",
           "mechanism": "הביקוש מדאטה סנטרים אמיתי וחזק, אך עם פיגור כפול: ציוד הקמה (GEV, PWR) מגיב תוך כמה רבעונים; חוזי PPA לייצרניות חשמל (VST, CEG) נסגרים שנה+ לפני שהקיבולת הופכת להכנסה"},
}


def _photonics_tickers():
    """סט חברות הפוטוניקה — נגזר ישירות מ-TECH_GROUPS, מקור אמת יחיד."""
    try:
        grp = TECH_GROUPS["ציר טכנולוגיה"]["פוטוניקה ואופטיקה"]
        return set(grp.get("core", {})) | set(grp.get("env", {}))
    except (KeyError, TypeError):
        return set()


BENCHMARK = "SOXX"

SOXX_HOLDINGS = ["NVDA", "AVGO", "AMD", "TXN", "QCOM", "INTC", "MU", "ADI",
                 "MRVL", "NXPI", "MCHP", "ON", "TSM", "ASML", "AMAT", "LRCX", "KLAC"]

# ======================================================
# פילוח טכנולוגי — ליבה ומעטפת
# ======================================================
# כל תחום = מילון עם שני חלקים:
#   "core" (ליבה)   — חברות שהתחום הוא עיקר העסק שלהן. מכפיל שכבה 1.0.
#   "env"  (מעטפת)  — מעגל שני שנהנה עקיפות מהמגמה. מכפיל שכבה 0.4.
# הערך ליד כל מניה = ציון חשיפה 0.0–1.0: אומדן לחלק מהעסק שקשור לתחום,
# על בסיס דוחות הסגמנטים (למשל NVDA ב-GPU/AI: דאטה סנטר ~90% מההכנסות).
# משקל אפקטיבי = חשיפה × מכפיל שכבה, מנורמל בתוך התחום.
# בהתאם להחלטה המתודולוגית: שווי שוק לא נכנס לחישוב.
# התחומים מחולקים לשני צירים חופפים בכוונה (חברה יכולה להופיע בשניהם):
# ציר טכנולוגיה (מה מוכרים) וציר שוקי קצה (למי מוכרים). אין לסכום בין צירים.

TIER_CORE = 1.0
TIER_ENV = 0.4

# משקל מרכיב הסיגנלים התחומיים בציון המשולב.
# SIG_WEIGHT_MAX = התקרה, מושגת רק כשיש SIG_FULL_COUNT סיגנלים או יותר.
# מתחת לזה המשקל דועך ליניארית: סיגנל בודד לא יזיז את הציון כמו קונצנזוס.
# הסיבה: סולם הסיגנלים דיסקרטי (±1), ולכן ראיה בודדת "צועקת" חזק מדי.
SIG_WEIGHT_MAX = 0.3
SIG_FULL_COUNT = 3

TECH_GROUPS = {
    "ציר טכנולוגיה": {
        "GPU / מאיצי AI": {
            "core": {"NVDA": 0.95, "AMD": 0.30, "AVGO": 0.20},
            "env": {"TSM": 0.40, "000660.KS": 0.50, "MU": 0.40, "MRVL": 0.30,
                    "MPWR": 0.30, "IFNNY": 0.20, "BESIY": 0.30, "CAMT": 0.30,
                    "ALAB": 0.40, "CRDO": 0.40, "COHR": 0.30, "LITE": 0.30, "FN": 0.25},
        },
        "CPU / מחשוב": {
            "core": {"INTC": 0.75, "AMD": 0.60},
            "env": {"QCOM": 0.40, "ARM": 0.50, "2454.TW": 0.20},
        },
        "DRAM": {
            "core": {"MU": 0.55, "000660.KS": 0.45, "005930.KS": 0.13},
            "env": {"RMBS": 0.10},
        },
        "HBM": {
            "core": {"000660.KS": 0.40, "MU": 0.25, "005930.KS": 0.04},
            "env": {"BESIY": 0.30, "CAMT": 0.30, "RMBS": 0.20},
        },
        "NAND": {
            "core": {"SNDK": 0.90, "285A.T": 0.90, "MU": 0.15, "000660.KS": 0.15, "005930.KS": 0.08},
            "env": {},
        },
        "ייצור (Foundry)": {
            "core": {"TSM": 0.95, "GFS": 0.90, "UMC": 0.90, "TSEM": 0.90},
            "env": {"INTC": 0.15, "005930.KS": 0.05},
        },
        "ציוד ייצור (Semicap)": {
            "core": {"ASML": 0.95, "AMAT": 0.90, "LRCX": 0.90, "KLAC": 0.90,
                     "TOELY": 0.90, "TER": 0.70, "BESIY": 0.80, "NVMI": 0.85,
                     "CAMT": 0.85, "ONTO": 0.70},
            "env": {},
        },
        "אריזה מתקדמת": {
            "core": {"BESIY": 0.90, "AMKR": 0.85, "ASX": 0.80, "CAMT": 0.50,
                     "ONTO": 0.40, "TSM": 0.15},
            "env": {"AMAT": 0.15, "KLAC": 0.10, "NVMI": 0.20},
        },
        "פוטוניקה ואופטיקה": {
            "core": {"FN": 0.80, "LITE": 0.70, "COHR": 0.60, "MRVL": 0.25, "TSEM": 0.20},
            "env": {"AVGO": 0.10},
        },
        "אנלוגי וכוח": {
            "core": {"TXN": 0.90, "ADI": 0.90, "NXPI": 0.85, "IFNNY": 0.85,
                     "STM": 0.85, "ON": 0.85, "MCHP": 0.85, "MPWR": 0.70, "RNECY": 0.70},
            "env": {"SWKS": 0.20, "QRVO": 0.20},
        },
        "תקשורת ורשתות": {
            "core": {"ALAB": 0.80, "CRDO": 0.80, "MRVL": 0.60, "QCOM": 0.40, "AVGO": 0.35},
            "env": {},
        },
        "EDA ו-IP": {
            "core": {"SNPS": 0.85, "CDNS": 0.85, "RMBS": 0.60, "ARM": 0.50},
            "env": {},
        },
    },
    "ציר שוקי קצה": {
        "Data Center (דאטה סנטר)": {
            # ליבה: מוכרות רכיבים שהדאטה סנטר הוא שוק הקצה העיקרי שלהן
            "core": {"NVDA": 0.90, "MRVL": 0.70, "000660.KS": 0.55, "MU": 0.50,
                     "AMD": 0.45, "AVGO": 0.40, "ALAB": 0.80, "CRDO": 0.80, "INTC": 0.25},
            # מעטפת: ייצור, כוח, אופטיקה ואחסון שנהנים מביקושי הדאטה סנטר
            "env": {"TSM": 0.45, "COHR": 0.40, "LITE": 0.40, "FN": 0.35,
                    "MPWR": 0.30, "SNDK": 0.25, "285A.T": 0.30, "005930.KS": 0.15},
        },
        "Edge AI (בינה מלאכותית בקצה)": {
            # ליבה: מריצות AI על המכשיר עצמו — טלפון, רכב, מכשור קצה
            "core": {"QCOM": 0.50, "2454.TW": 0.40, "ARM": 0.40,
                     "NXPI": 0.25, "STM": 0.20},
            # מעטפת: AI PC ובקרי קצה — חשיפה חלקית ועקיפה למגמה
            "env": {"AMD": 0.15, "INTC": 0.15, "RNECY": 0.15, "MCHP": 0.15},
        },
        "צרכני מסורתי (PC ומובייל)": {
            # איחוד PC + מובייל: החברות המסורתיות של מחשוב וסלולר צרכני
            "core": {"2454.TW": 0.75, "SWKS": 0.70, "QRVO": 0.70, "QCOM": 0.55,
                     "INTC": 0.50, "005930.KS": 0.35, "AMD": 0.30, "NVDA": 0.07},
            "env": {"ARM": 0.50, "TSM": 0.30, "MU": 0.30, "SNDK": 0.30, "285A.T": 0.30},
        },
        "רכב": {
            "core": {"NXPI": 0.55, "ON": 0.50, "RNECY": 0.50,
                     "IFNNY": 0.45, "STM": 0.40, "TXN": 0.35, "ADI": 0.30, "MCHP": 0.20},
            "env": {"QCOM": 0.10},
        },
        "תעשייה": {
            "core": {"ADI": 0.50, "TXN": 0.40, "MCHP": 0.40, "RNECY": 0.35,
                     "IFNNY": 0.25, "STM": 0.25, "ON": 0.25, "TER": 0.25, "NXPI": 0.20},
            "env": {"AMD": 0.10},
        },
    },
}

PHOTONICS_TICKERS = _photonics_tickers()

# ======================================================
# תיאורי תחומים טכנולוגיים
# ======================================================
# הסבר קצר לכל תחום, מוצג בריחוף על אייקון ⓘ בטבלת הפילוח הטכנולוגי.
# המפתחות זהים תו-בתו לשמות התחומים ב-TECH_GROUPS.
# הטקסט נכנס למאפיין title שעטוף בגרשיים בודדים — אין להשתמש ב-' או ב-".
TECH_DESCRIPTIONS = {
    # --- ציר טכנולוגיה ---
    "GPU / מאיצי AI":
        "מעבדים גרפיים ומאיצים ייעודיים שמריצים אימון והסקה של מודלי בינה מלאכותית "
        "במרכזי נתונים. זהו היעד של רוב תקציבי ההשקעה של ענקיות הענן, ולכן התחום "
        "הרגיש ביותר לשינוי בקצב ההשקעות ההוניות. השוק מרוכז סביב שחקן דומיננטי אחד, "
        "עם מרווחים גבוהים חריגים ששומרים על עצמם כל עוד הביקוש עולה על ההיצע.",
    "CPU / מחשוב":
        "מעבדים לשימוש כללי — שרתים, מחשבים אישיים ותחנות עבודה. שוק בוגר עם צמיחה "
        "מתונה, שנמצא בשנים האחרונות תחת לחץ תקציבי מצד מאיצי הבינה המלאכותית שתופסים "
        "נתח גדל מתקציב מרכזי הנתונים. הדינמיקה המרכזית היא מאבק על נתח שוק בין "
        "ארכיטקטורות מתחרות, ולא הרחבת השוק עצמו.",
    "DRAM":
        "זיכרון עבודה נדיף — הקומודיטי הקלאסי של הסקטור. המחירים נעים במחזורים חדים "
        "של עודף ומחסור, ומנוף תפעולי גבוה הופך כל שינוי מחיר לתנודה מוגברת ברווח. "
        "שלושה יצרנים בלבד שולטים כמעט בכל השוק העולמי, ולכן החלטות הרחבת כושר ייצור "
        "של שחקן בודד משפיעות על התמחור של כולם.",
    "HBM":
        "זיכרון בפס רחב — שכבות DRAM מוערמות זו על זו וארוזות צמוד למאיץ. צוואר בקבוק "
        "אמיתי בשרשרת האספקה של הבינה המלאכותית, ולכן נמכר בחוזי אספקה ארוכים ובמרווח "
        "גבוה משמעותית מ-DRAM רגיל. הביקוש נגזר ישירות מכמות המאיצים שנשלחים, מה שהופך "
        "אותו לפחות מחזורי מהזיכרון המסורתי אך תלוי בלקוח מרוכז.",
    "NAND":
        "זיכרון אחסון לא נדיף — כוננים לשרתים, למחשבים ולמכשירי קצה. מחזורי מחיר דומים "
        "ל-DRAM, אך רגישות נמוכה יותר לביקושי בינה מלאכותית ותלות גבוהה יותר בשוק "
        "הצרכני. ההתאוששות נשענת על שילוב של ריסון בהיצע ועל גידול באחסון במרכזי נתונים.",
    "ייצור (Foundry)":
        "קבלני ייצור שמייצרים שבבים עבור חברות שאין להן מפעל משלהן. עסק עתיר הון "
        "שרווחיותו נשענת על ניצולת גבוהה של המפעלים ועל הובלה טכנולוגית בצמתי הייצור "
        "המתקדמים. הצמתים המתקדמים רווחיים בהרבה מהבוגרים, ולכן המרווח נקבע בעיקר "
        "בתמהיל ולא בנפח. מקדמות וחוזי התחייבות מגלגלים חלק מסיכון המחזור אל הלקוח.",
    "ציוד ייצור (Semicap)":
        "המכונות שמייצרות את השבבים — ליתוגרפיה, חריטה, הפקדה, ניקוי ובדיקה. המכירות "
        "נגזרות מתקציבי ההשקעה של היצרנים, ולכן התחום רגיש לקצב השינוי בהשקעה ולא רק "
        "לרמתה. זמני אספקה ארוכים וצבר הזמנות יוצרים פער של כמה רבעונים בין הזמנה "
        "להכרה בהכנסה, מה שממתן את התנודתיות אך גם מעכב את ההתאוששות.",
    "אריזה מתקדמת":
        "השלב שאחרי ייצור הווייפר — חיבור מספר שבבים למארז אחד בפס רחב. הפך מצעד "
        "טכני שולי לצוואר בקבוק מבני, כי ביצועי מאיצי הבינה המלאכותית תלויים בו לא "
        "פחות מאשר בצומת הייצור עצמו. כושר הייצור מוגבל ומורחב לאט, ולכן הוא אחד "
        "האילוצים האמיתיים על כמות המאיצים שניתן לספק.",
    "פוטוניקה ואופטיקה":
        "העברת נתונים באור במקום בחשמל — משדרים אופטיים, לייזרים ורכיבי חיבור. ככל "
        "שמרכזי הנתונים גדלים, המרחק והצריכה של חיבורי נחושת הופכים למגבלה, והתעבורה "
        "עוברת לאופטיקה. התחום נהנה משינוי תמהיל בתוך תקציב מרכזי הנתונים — הגנה מפני "
        "שחיקת נתח, אך לא מפני ירידה בתקציב כולו.",
    "אנלוגי וכוח":
        "שבבים שמתממשקים לעולם הפיזי — חיישנים, ניהול מתח, בקרת הספק ורכיבי כוח. "
        "מיוצרים בעיקר בצמתים בוגרים וזולים, עם מחזור חיי מוצר ארוך ופיזור לקוחות רחב "
        "בתעשייה וברכב. התוצאה היא מחזור עסקי נפרד מזה של הבינה המלאכותית — מגן בזמן "
        "האטה במרכזי נתונים, אך גם לא משתתף בגאות שלהם.",
    "תקשורת ורשתות":
        "הרכיבים שמזיזים נתונים בתוך מרכז הנתונים ובינו לבין העולם — מתגים, בקרי "
        "ממשק ורכיבי תזמון ושחזור אות. ככל שאשכולות המאיצים גדלים, חלק גדל מהביצועים "
        "נקבע ברשת שמחברת ביניהם ולא במאיץ הבודד. תחום שנהנה ישירות מגידול בקנה המידה "
        "של האשכולות, גם בלי גידול במספר המאיצים הכולל.",
    "EDA ו-IP":
        "תוכנת התכנון שבה מעצבים שבבים, ובלוקי קניין רוחני מוכנים שנרכשים ברישוי. "
        "המודל העסקי מבוסס מנויים רב-שנתיים ותמלוגים, ולכן ההכנסה יציבה וצפויה גם "
        "כשההשקעות ההוניות בסקטור יורדות. פעילות התכנון ממשיכה גם במיתון, מה שהופך "
        "את התחום להגנתי יחסית — במחיר של השתתפות מתונה בגאות.",

    # --- ציר שוקי קצה ---
    "Data Center (דאטה סנטר)":
        "שוק הקצה שמניע כיום את רוב הצמיחה בסקטור. הביקוש נגזר ישירות מתקציבי ההשקעה "
        "של ענקיות הענן ומפעילי תשתיות הבינה המלאכותית, ולכן זהו הציר שהכי כדאי לעקוב "
        "אחריו בעונות הדוחות. הריכוזיות גבוהה — מספר קטן של לקוחות קובע את קצב הביקוש "
        "של שרשרת שלמה.",
    "Edge AI (בינה מלאכותית בקצה)":
        "הרצת מודלים על המכשיר עצמו — טלפון, רכב, מצלמה או בקר תעשייתי — במקום בענן. "
        "המניע הוא השהיה נמוכה, פרטיות ועלות תקשורת, והמגבלה היא צריכת חשמל ועלות "
        "רכיב. מחזור החלפה ארוך יותר מזה של מרכזי הנתונים, ולכן ההשפעה על ההכנסות "
        "מתפרשת על פני תקופה ארוכה יותר.",
    "צרכני מסורתי (PC ומובייל)":
        "מחשבים אישיים וסמארטפונים — השוק שהיה מנוע הצמיחה של הסקטור לפני עידן "
        "מרכזי הנתונים. כיום שוק בוגר ורווי, שנע לפי מחזורי החלפה של מכשירים ולפי "
        "הסנטימנט הצרכני. משמש בעיקר כאינדיקטור לבריאות הביקוש הרחב, לא כמנוע צמיחה.",
    "רכב":
        "שבבים לרכב — ניהול מתח, חיישנים, בקרים ומערכות עזר לנהג. תכולת השבבים לרכב "
        "עולה בהתמדה, אך מספר כלי הרכב הנמכרים צומח לאט, ולכן הצמיחה מגיעה מהתוכן ולא "
        "מהנפח. מחזורי הסמכה ארוכים יוצרים יציבות בהכנסות, אך גם התאוששות איטית אחרי "
        "תקופת התאמת מלאי.",
    "תעשייה":
        "אוטומציה, ציוד ייצור, תשתיות אנרגיה ומכשור מדידה. שוק מפוזר מאוד עם אלפי "
        "לקוחות ומחזורי חיי מוצר ארוכים, מה שיוצר יציבות בזמנים רגילים אך גם התאוששות "
        "איטית אחרי מיתון. נחשב לאינדיקטור מקדים לבריאות הכלכלה הריאלית.",
}

# ======================================================
# CapEx — ענקיות הענן
# ======================================================
# ההשקעות ההוניות של ענקיות הענן הן מנוע הביקוש של סקטור השבבים.
CAPEX_COMPANIES = {
    "MSFT": "מיקרוסופט",
    "GOOGL": "אלפאבית (גוגל)",
    "AMZN": "אמזון",
    "META": "מטא",
}

CAPEX_COLORS = {
    "MSFT": "#60a5fa",
    "GOOGL": "#34d399",
    "AMZN": "#fbbf24",
    "META": "#a78bfa",
}

# תחזית CapEx שנתית לשנה הפיסקלית הנוכחית — מוזן ידנית!
# אין מקור API לתחזיות; הן נאמרות בשיחות הוועידה. מעדכנים פעם ברבעון.
# כל עדכון = (תווית: מתי ניתנה התחזית, ערך במיליארדי דולרים).
# ערך None = טרם הוזן, ולא יוצג. השתמש בכפתור "חפש תחזיות עדכניות"
# בתחתית האזור כדי ש-Gemini ימצא לך את המספרים העדכניים.
# שים לב: מיקרוסופט = שנה פיסקלית עד סוף יוני,
# גוגל/אמזון/מטא = שנה קלנדרית רגילה.
CAPEX_GUIDANCE = {
    "MSFT": {
        "year_label": "FY2026 (יולי 2025 – יוני 2026)",
        "updates": [
            ("תחזית אחרי Q1 FY26", None),
            ("תחזית אחרי Q2 FY26", 154),
            ("תחזית אחרי Q3 FY26", 175),
            ("תחזית אחרי Q4 FY26", 175),          
        ],
    },
    "GOOGL": {
        "year_label": "2026",
        "updates": [
            ("תחזית אחרי Q4 2025", 180),
            ("תחזית אחרי Q1 2026", 185),
            ("תחזית אחרי Q2 2026", 200),
        ],
    },
    "AMZN": {
        "year_label": "2026",
        "updates": [
            ("תחזית אחרי Q4 2025", 200),
            ("תחזית אחרי Q1 2026", 200),
            ("תחזית אחרי Q2 2026", 220),
        ],
    },
    "META": {
        "year_label": "2026",
        "updates": [
            ("תחזית אחרי Q4 2025", 125),
            ("תחזית אחרי Q1 2026", 135),
            ("תחזית אחרי Q2 2026", 138),
        ],
    },
}

# RPO — Remaining Performance Obligations (צבר התחייבויות חוזיות שטרם הוכרו כהכנסה)
# במיליארדי דולרים. מוזן ידנית מדוחות 10-Q/10-K (כמו CAPEX_GUIDANCE — אין מקור API).
# מעדכנים רבעון חדש כשמתפרסם. השתמש בכפתור העזר בגרסת מפתח למציאת המספרים.
# מפתחות הרבעונים הם קלנדריים (YYYYQN) — מקור אמת יחיד, אין לפזר את המספרים במקומות אחרים.
RPO_QUARTERLY = {
    "AMZN": {  # mainly AWS
        "2024Q2": 157, "2024Q3": 164, "2024Q4": 177,
        "2025Q1": 189, "2025Q2": 195, "2025Q3": 200, "2025Q4": 244,
        "2026Q1": 364, "2026Q2": 496,
    },
    "MSFT": {  # Commercial RPO
        "2024Q2": 269, "2024Q3": 259, "2024Q4": 298,
        "2025Q1": 315, "2025Q2": 368, "2025Q3": 392, "2025Q4": 625,
        "2026Q1": 627, "2026Q2": 678,
    },
    "GOOGL": {  # mostly cloud
        "2024Q2": 79, "2024Q3": 87, "2024Q4": 93,
        "2025Q1": 92, "2025Q2": 108, "2025Q3": 158, "2025Q4": 243,
        "2026Q1": 468, "2026Q2": 520,
    },
}

HOT_THRESHOLD = 10
BROAD_THRESHOLD = 0.6
GAP_THRESHOLD = 15
MOVE_ALERT = 2.0
STOCK_VS_SOXX_ALERT = 3.0  # סף מרחק של מניה בודדת מ-SOXX (נקודות %) לחריגה

# ציון אנליסטים — ממוצע משוקלל לפי ANALYST_WEIGHTS, בסולם 3 רמות: קנייה (strongBuy/buy)=5,
# החזקה=3, מכירה (sell/strongSell)=1. strongBuy ו-buy נספרות שתיהן כ-5 (וכנ"ל strongSell/sell כ-1) —
# אין הבחנה בין "חזקה" ל"רגילה" בציון הסופי, רק בין קנייה/החזקה/מכירה.
# דוגמה: (5×41 + 3×10 + 1×0) / 51 = 4.61 (41 קנייה [strongBuy+buy], 10 החזקה, 0 מכירה)
ANALYST_WEIGHTS = {"strongBuy": 5.0, "buy": 5.0, "hold": 3.0, "sell": 1.0, "strongSell": 1.0}
ANALYST_MIN_N = 3      # מתחת לזה — אין ציון
ANALYST_DELTA = 0.15   # מרחק מהחציון לצביעה ירוק/אדום

BETA_WINDOW = "6mo"      # נמשך רחב מכוונת-מדידה (3 חודשים) — תשתית לבטא מתגלגלת עתידית
BETA_MIN_POINTS = 40     # פחות נקודות חופפות — אין ציון
BETA_HIGH = 1.0
BETA_LOW = 0.6
BETA_MIN_R2 = 0.10       # מתחת לזה הבטא רועשת ומסומנת בכוכבית

# מספר הימים שבהם מדווחות מוקדמות (MU ביוני, AVGO בדצמבר) מקדימות
# את תחילת הרבעון הקלנדרי הבא. מזיז את גבול העונה אחורה כדי שכל הגל
# ייפול לאותו דלי. ניתן לכוונון.
SEASON_EARLY_DAYS = 21

# ספי צבע לסנטימנט דוחות (ציון Gemini בטווח -1.0 עד 1.0).
# הסף החיובי גבוה מ-0.2 בכוונה: זו התקרה של מדרגת "עמד בציפיות + שמר על הנחיה"
# בפרומפט, כדי שרבעון ניטרלי לא ייצבע ירוק. הסף השלילי סימטרי לו.
SENTIMENT_POS = 0.25
SENTIMENT_NEG = -0.25
EARNINGS_TEMPERATURE = 0.2  # טמפרטורה נמוכה לניתוח מובנה של דוחות בלבד
# חברות שמדווחות רשמית במטבע מקומי אך מציגות ומדוברות בדולר.
# גובר על get_financial_currency בבחירת מטבע היעד לניתוח.
REPORTING_CURRENCY_OVERRIDE = {"TSM": "USD"}

# סף מרחק מהמדד לכל תקופה — כמה החציון צריך להכות/לפגר אחרי SOXX
# כדי שהתחום ייחשב "חם" או "חלש". מטפס עם אורך התקופה.
RELATIVE_THRESHOLD = {
    "online": 2.0,
    "lastclose": 2.0,
    "5d": 5.0,
    "1mo": 10.0,
    "3mo": 13.0,
    "6mo": 15.0,
    "ytd": 15.0,
    "1y": 20.0,
    "5y": 50.0,
}

AI_CACHE_TTL = {
    "online": 3600,
    "lastclose": 43200,
    "5d": 86400,
    "1mo": 259200,
    "3mo": 432000,
    "6mo": 604800,
    "ytd": 604800,
    "1y": 1209600,
    "5y": 1209600,
}

PERIOD_OPTIONS = {
    "Online": "online",
    "Last close": "lastclose",
    "5D": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "YTD": "ytd",
    "1Y": "1y",
    "5Y": "5y",
}
DAILY_PERIODS = ["online", "lastclose"]

NY_TZ = ZoneInfo("America/New_York")
_MARKET_OPEN = _time(9, 30)
_MARKET_CLOSE = _time(16, 0)

# NYSE / NASDAQ holidays through 2027 (early-close days excluded — handled separately)
_NYSE_HOLIDAYS = {
    datetime(2025, 1, 1).date(), datetime(2025, 1, 20).date(),
    datetime(2025, 2, 17).date(), datetime(2025, 4, 18).date(),
    datetime(2025, 5, 26).date(), datetime(2025, 6, 19).date(),
    datetime(2025, 7, 4).date(), datetime(2025, 9, 1).date(),
    datetime(2025, 11, 27).date(), datetime(2025, 12, 25).date(),
    datetime(2026, 1, 1).date(), datetime(2026, 1, 19).date(),
    datetime(2026, 2, 16).date(), datetime(2026, 4, 3).date(),
    datetime(2026, 5, 25).date(), datetime(2026, 6, 19).date(),
    datetime(2026, 7, 3).date(), datetime(2026, 9, 7).date(),
    datetime(2026, 11, 26).date(), datetime(2026, 12, 25).date(),
    datetime(2027, 1, 1).date(), datetime(2027, 1, 18).date(),
    datetime(2027, 2, 15).date(), datetime(2027, 4, 2).date(),
    datetime(2027, 5, 31).date(), datetime(2027, 6, 18).date(),
    datetime(2027, 7, 5).date(), datetime(2027, 9, 6).date(),
    datetime(2027, 11, 25).date(), datetime(2027, 12, 24).date(),
}


def ny_now():
    return datetime.now(NY_TZ)


def session_is_complete(d):
    """True אם יום מסחר d (datetime.date, שעון NY) כבר נסגר לחלוטין (אחרי 16:00 NY)."""
    if d.weekday() >= 5 or d in _NYSE_HOLIDAYS:
        return False
    now = ny_now()
    if now.date() > d:
        return True
    return now.date() == d and now.time() >= _MARKET_CLOSE


def _period_to_start(period):
    """fetch_start ל-yfinance — תמיד לפחות 8 ימים לפני measure_start כדי שעוגן _anchor_index זמין.

    הפרדה מפורשת:
      fetch_start  = measure_start - 8d  (באפר לסופ"ש + חג רצוף)
      measure_start = התאריך שממנו נגזרת התקופה (= d של close[anchor])
    """
    today = ny_now().date()
    if period == "ytd":
        # measure_start = 01/01; עוגן = 31/12 של השנה הקודמת → מביאים מ-25/12
        return today.replace(year=today.year - 1, month=12, day=25)
    if period == "5d":
        # 10 ימים היה קרוב מדי לגבול: שבוע עם חג בודד (4 ימי מסחר) + הבר האחרון
        # חסר (nan_tail, ראה get_history) יכולים לצמצם את הברים הזמינים מתחת
        # ל-6 הדרושים ל-_anchor_index. 15 יום נותן מרווח לחג אחד-שניים + סופ"שים
        # בלי להרחיב משמעותית את גודל הבקשה (עדיין תקופה קצרה וזולה ל-yfinance).
        return today - timedelta(days=15)
    if period == "lastclose":
        return today - timedelta(days=45)
    _months = {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12, "5y": 60}
    months = _months.get(period, 1)
    measure_start = (pd.Timestamp(today) - pd.DateOffset(months=months)).date()
    return measure_start - timedelta(days=8)


def _close_for_date(daily_close, d):
    """שכבה 1: מחיר סגירה רשמי מהסדרה היומית.
    מחזיר (price, "daily") אם קיים, (None, None) אחרת."""
    if daily_close is None:
        return None, None
    matches = [float(v) for ts, v in daily_close.items() if ts.date() == d]
    return (matches[-1], "daily") if matches else (None, None)


@st.cache_data(ttl=60)
def _get_quote_prev_close(symbol):
    """שכבה 2: fast_info.previous_close — הסגירה הרשמית של הסשן שקדם לנוכחי.
    מטמון TTL=60s; None אם לא זמין."""
    try:
        fi = yf.Ticker(symbol).fast_info
        px = getattr(fi, "previous_close", None)
        return float(px) if px and float(px) > 0 else None
    except Exception:
        return None


@st.cache_data(ttl=60)
def _get_quote_last_close(symbol):
    """שכבה 2 עבור הסשן האחרון: fast_info.last_price — הסגירה הרשמית כשהשוק סגור.
    מטמון TTL=60s; None אם לא זמין."""
    try:
        fi = yf.Ticker(symbol).fast_info
        px = getattr(fi, "last_price", None)
        return float(px) if px and float(px) > 0 else None
    except Exception:
        return None


def _anchor_index(close, period, last_date):
    """מיקום הבר שממנו נמדדת התקופה — הבר האחרון שתאריכו קטן ממש מתחילת התקופה.

    כלל: תשואה = close[-1] / close[anchor] * 100 - 100.
    אם last_date=27/07 ו-period="1mo" → start=27/06 (שבת) → עוגן=26/06 (589.94).
    YTD: start=01/01 → עוגן=31/12 של השנה הקודמת.
    5d: 6 ברים = 5 סשנים → עוגן ב-iloc[-6].
    תקופה חלקית (אין בר לפני start) → 0 (מחזיר True ב-is_partial).
    """
    dates = [ts.date() for ts in close.index]

    if period == "5d":
        # ספירת ברים בסדרה בפועל — חסין לחגים מעצם ההגדרה.
        # 6 ברים = 5 סשנים (close[-1] / close[-6] - 1 = תשואת 5 ימי מסחר).
        return max(0, len(dates) - 6), len(dates) < 6

    if period == "ytd":
        start = last_date.replace(month=1, day=1)
    else:
        _months = {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12, "5y": 60}
        months = _months.get(period, 1)
        start = (pd.Timestamp(last_date) - pd.DateOffset(months=months)).date()

    # ≤ ולא <: אם start הוא יום מסחר — הוא עצמו העוגן. רק סופ"ש/חג → יורדים אחורה.
    #
    # נבדק בפועל מול Yahoo Finance (SOXX): אין הגדרת חלון אחידה שתואמת את Yahoo
    # בכל התקופות. 1mo ו-YTD תואמים ל-d<=start (הכלל הנוכחי). 6mo ו-5Y דווקא
    # תואמים ל-d>start (הבר הראשון *אחרי* start). 1Y לא תואם לאף אחד מהשניים.
    # נבדק במפורש: מעבר גורף ל-d>start משפר 6mo/5Y אך שובר 1mo/YTD
    # (1mo: ‑16.69%→‑20.00% ; YTD: +63.19%→+56.67%, מול Yahoo). לכן d<=start
    # נשמר במכוון — לא באג, וללא כלל יחיד שמיישב את כל הטווחים. אל תשנה תנאי
    # זה כדי "לתקן" פער מול Yahoo בתקופה בודדת בלי לבדוק את ההשפעה על כל השאר.
    before = [i for i, d in enumerate(dates) if d <= start]
    if not before:
        return 0, True  # תקופה חלקית
    return before[-1], False


# ---------- מצב מפתח ----------
# DEV_MODE=True: כלי הזנה ידנית גלויים (ניתוח Gemini, שמירה לקובץ, חיפוש CapEx).
# DEV_MODE=False (ברירת מחדל): מוצג רק תוכן שכבר הוזן — מצב צפייה.
# ניתן להפעיל דרך st.secrets["DEV_MODE"]=true או URL ?dev=1.
def _resolve_dev_mode():
    flag = False
    try:
        flag = bool(st.secrets.get("DEV_MODE", False))
    except Exception:
        pass
    if st.query_params.get("dev") == "1":
        flag = True
    return flag

DEV_MODE = _resolve_dev_mode()

_log = logging.getLogger("chip_dashboard")
_log.setLevel(logging.DEBUG if DEV_MODE else logging.WARNING)
if not _log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _log.addHandler(_h)
_log.propagate = False


# ---------- מפתח Gemini ----------
def get_gemini_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY")


def period_stamp(period_code):
    now = datetime.now(timezone.utc)
    if period_code in ("online",):
        return now.strftime("%Y-%m-%d-%H")
    if period_code in ("lastclose", "5d"):
        return now.strftime("%Y-%m-%d")
    if period_code in ("1mo",):
        return now.strftime("%Y-%W")
    return now.strftime("%Y-%m")


# sentinel להבחנה בין "attrs שרד וערכו None" (אין פער) לבין "attrs לא שרד בכלל"
# (המפתח חסר לגמרי) — propagation של attrs ב-pandas אינו מובטח בין גרסאות/אופרטורים,
# ו-cache_data עשוי להעתיק דרך pickle. צרכני הדגל חייבים להבחין בין שני המצבים,
# ולא להשתמש ב-.get() רגיל שמחזיר None בשניהם.
_ATTRS_MISSING = object()


# ---------- פונקציות נתונים ----------
@st.cache_data(ttl=300)
def get_history(symbol, period):
    """מחזיר את סדרת הסגירות (Close) לתקופה, אחרי dropna.

    גולמי בכוונה (auto_adjust=False) בכל מקום, כולל לחישוב תשואות: זהו price
    return, בהתאמה למה שמוצג ב-Yahoo Finance. הפיצולים כבר משוקללים בסדרה
    הגולמית תמיד ע"י yfinance/Yahoo — auto_adjust שולט רק בדיבידנדים, והתאמתם
    מרחיקה את התשואה מ-Yahoo (לא מקרבת), בפער שגדל עם אורך התקופה. אל תעביר
    ל-auto_adjust=True בלי החלטה מודעת ומאומתת מחדש מול Yahoo.

    close.attrs["nan_tail_date"]: נכתב תמיד (גם כשאין פער — אז הערך None),
    כדי שהיעדרות המפתח עצמו (ולא רק ערכו) תסמן כשל מנגנון ולא מצב תקין.
    אם השורה *האחרונה* שחזרה מיאהו הייתה Close=NaN (הסשן טרם אוחד במקור)
    ונמחקה ע"י ה-dropna — הערך הוא התאריך שלה. נשמר על ה-Series עצמו (attrs)
    ולא כערך חוזר נוסף, כדי לא לשנות את חתימת הפונקציה ולא לשבור קוראים
    קיימים שמצפים לסדרה בלבד. שרד את שכבת ה-cache_data של Streamlit כי זו
    פשוט תכונת dict על אותו אובייקט Series, ומועתקת יחד איתו בכל קריאה —
    אך אינו מובטח (ראה _ATTRS_MISSING לעיל), ולכן צרכנים בודקים sentinel.
    """
    try:
        if period == "online":
            data = yf.Ticker(symbol).history(period="2d", interval="5m", auto_adjust=False)
        else:
            start = _period_to_start(period)
            end_d = ny_now().date() + timedelta(days=1)
            data = yf.Ticker(symbol).history(start=str(start), end=str(end_d), auto_adjust=False)
        raw_close = data["Close"]
        close = raw_close.dropna()
        if len(close) < 2:
            return None
        close.attrs["nan_tail_date"] = (
            raw_close.index[-1].date()
            if len(raw_close) > 0 and pd.isna(raw_close.iloc[-1])
            else None
        )
        return close
    except Exception:
        return None


def market_is_open():
    """True אם שוק ניו-יורק פתוח כרגע (09:30–16:00 ET, ימי מסחר בלבד)."""
    now = ny_now()
    if now.weekday() >= 5 or now.date() in _NYSE_HOLIDAYS:
        return False
    return _MARKET_OPEN <= now.time() <= _MARKET_CLOSE



@st.cache_data(ttl=60)
def get_last_session_intraday(symbol, skip_current_day=True):
    """יום המסחר תוך-יומי (5 דק'), עם נקודת עוגן אלכסונית לפני הפתיחה.
    מוגבל לשעות המסחר הרגילות של ארה"ב (09:30–16:00 America/New_York) בלבד.
    מחזיר (session_series, prev_close, prev_date) או (None, None, None).
    prev_date — תאריך יום המסחר שממנו נלקח prev_close (היום לפני הסשן).

    skip_current_day=True  (ברירת מחדל / lastclose):
        אם היום האחרון הוא היום הנוכחי וסשן לא הסתיים עדיין — מדלג עליו.
    skip_current_day=False (online):
        תמיד לוקח את היום האחרון הזמין, גם אם חלקי."""
    try:
        data = yf.Ticker(symbol).history(period="14d", interval="5m", prepost=False, auto_adjust=False)
        close = data["Close"].dropna()
        if len(close) < 2:
            return None, None, None

        idx = close.index
        if idx.tz is None:
            close.index = idx.tz_localize("UTC").tz_convert("America/New_York")
        else:
            close.index = idx.tz_convert("America/New_York")

        close = close[(close.index.time >= _MARKET_OPEN) & (close.index.time <= _MARKET_CLOSE)]
        if len(close) < 2:
            return None, None, None

        idx = close.index
        dates = sorted({ts.date() for ts in idx})
        if not dates:
            return None, None, None

        now_ny = ny_now()
        last_date = dates[-1]
        if skip_current_day and last_date == now_ny.date() and not session_is_complete(last_date) and len(dates) >= 2:
            last_date = dates[-2]

        session = close[[ts.date() == last_date for ts in idx]]
        if len(session) < 2:
            return None, None, None

        before = close[[ts.date() < last_date for ts in idx]]
        prev_close = float(before.iloc[-1]) if len(before) >= 1 else None
        prev_date = before.index[-1].date() if len(before) >= 1 else None

        if prev_close is not None:
            anchor_ts = session.index[0] - timedelta(minutes=15)
            anchor = pd.Series([prev_close], index=pd.DatetimeIndex([anchor_ts], tz="America/New_York"))
            session = pd.concat([anchor, session])

        return session, prev_close, prev_date
    except Exception:
        return None, None, None


def get_change(symbol, period):
    if period == "online":
        # מקור נתונים אחד: session + prev_close מאותה משיכה — ללא סיכון פיצול בין שני calls
        session, prev_close, _ = get_last_session_intraday(symbol, skip_current_day=False)
        if session is None or prev_close is None or prev_close == 0:
            return None
        # מוודאים שהסשן הוא של היום — מגן מפני מצב "שוק לא פתח עדיין"
        if session.index[-1].date() != ny_now().date():
            return None
        change = float(session.iloc[-1]) / prev_close * 100 - 100
    elif period == "lastclose":
        # תאריכים — מהסדרה התוך-יומית (אמינה גם כשהסדרה היומית מפספסת ימים)
        session, intra_prev_close, prev_date = get_last_session_intraday(symbol, skip_current_day=True)
        if session is None or prev_date is None:
            return None
        session_date = session.index[-1].date()
        intra_last_close = float(session.iloc[-1])

        # מחירים — סדר עדיפויות: שכבה 1 (daily) → שכבה 2 (quote) → שכבה 3 (intraday)
        daily = get_history(symbol, "lastclose")

        # --- session_date: הסשן האחרון — quote.last_price רלוונטי רק כשהשוק סגור והסשן נסגר סופית ---
        last_px, last_src = _close_for_date(daily, session_date)
        if last_px is None and not market_is_open() and session_is_complete(session_date):
            _last_q = _get_quote_last_close(symbol)
            if _last_q is not None and intra_last_close and abs(_last_q - intra_last_close) / intra_last_close < 0.01:
                last_px, last_src = _last_q, "quote"
                _log.warning(f"[DATA_WARN {symbol}] {session_date}: quote בלבד ({last_px:.4f}) — לא ניתן לאמת מול סדרה יומית")
        if last_px is None:
            if intra_last_close == 0:
                return None
            last_px, last_src = intra_last_close, "intraday"
            _log.warning(f"[DATA_WARN {symbol}] {session_date}: תוך-יומי בלבד ({last_px:.4f}) — לא ניתן לאמת מול מקור רשמי")

        # --- prev_date: הסשן הקודם — כאן quote.previous_close רלוונטי ---
        prev_px, prev_src = _close_for_date(daily, prev_date)
        if prev_px is None:
            # שכבה 2: fast_info.previous_close מתייחס לסשן שקדם לנוכחי — בדיוק prev_date
            prev_px_q = _get_quote_prev_close(symbol)
            if prev_px_q is not None:
                prev_px, prev_src = prev_px_q, "quote"
                _log.warning(f"[DATA_WARN {symbol}] {prev_date}: quote בלבד ({prev_px:.4f}) — לא ניתן לאמת מול סדרה יומית")
            elif intra_prev_close and intra_prev_close != 0:
                prev_px, prev_src = intra_prev_close, "intraday"
                _log.warning(f"[DATA_WARN {symbol}] {prev_date}: תוך-יומי בלבד ({prev_px:.4f}) — לא ניתן לאמת מול מקור רשמי")
        elif prev_src == "daily":
            # אימות צולב: daily vs quote — פער >0.1% מעיד על בעיה
            prev_px_q = _get_quote_prev_close(symbol)
            if prev_px_q is not None:
                _diff = abs(prev_px - prev_px_q) / prev_px
                if _diff > 0.001:
                    _log.warning(f"[DATA_WARN {symbol}] {prev_date}: daily={prev_px:.4f} quote={prev_px_q:.4f} פער={_diff*100:.2f}% — אי-התאמה בין מקורות")

        if prev_px is None or prev_px == 0:
            return None
        change = last_px / prev_px * 100 - 100
        _log.debug(f"[lastclose {symbol}] {session_date} ({last_px:.2f}, {last_src}) vs {prev_date} ({prev_px:.2f}, {prev_src}) => {change:.2f}%")
    else:
        close = get_history(symbol, period)
        if close is None:
            return None
        if len(close) < 2:
            return None
        last_date = close.index[-1].date()
        # anchor_i נגזר מ-last_date/close.index המקוריים; אין לשנות את לוגיקת
        # העוגן הזו עבור תקופות שאינן 5d — רק 5d מתוקן בהמשך, ורק כאשר תיקון
        # הפער מטה (quote) הצליח (ראה למטה).
        anchor_i, is_partial = _anchor_index(close, period, last_date)
        anchor_px = float(close.iloc[anchor_i])
        last_px = float(close.iloc[-1])

        # בדיקת פער: הדגל כבר קיים במטמון של get_history (nan_tail_date) — ללא משיכת
        # intraday נוספת. קיים סשן מאוחר יותר שכבר הושלם ולא נכלל בסדרה היומית
        # (הנר האחרון חזר עם Close=NaN ונמחק ע"י dropna() ב-get_history).
        _gc_date = close.attrs.get("nan_tail_date", _ATTRS_MISSING)
        if _gc_date is _ATTRS_MISSING:
            _log.warning(f"[DATA_WARN {symbol}] {last_date}: תכונת attrs (nan_tail_date) לא שרדה על הסדרה — לא ניתן לזהות אם קיים סשן מאוחר יותר שחסר בה")
            _gc_date = None

        if _gc_date is not None and not market_is_open() and session_is_complete(_gc_date):
            _gc_q = _get_quote_last_close(symbol)
            # אימות מול close.iloc[-1] — הסגירה של הסשן הקודם, לא ערך תוך-יומי
            # (בניגוד לענף lastclose, שאין בו כאן משיכת intraday להשוואה מולה).
            # לכן הסף רחב בהרבה (15%): המטרה לפסול ציטוט ששייך לסימבול/סשן שגוי
            # לגמרי, לא לאמת תנועה יומית לגיטימית מול עצמה. אל תצמצם סף זה בהשראת
            # ה-1% של lastclose — שם ההשוואה מול אותו סשן ממש, כאן מול הסשן הקודם.
            # בסקטור השבבים תנועה יומית מעל 15% ביום דוחות אינה נדירה — במקרה כזה
            # האימות הצולב נכשל בכוונה ("else" למטה) והקוד נופל למחיר הישן, מלווה
            # בכיתוב "⚠" ל-UI. זו התנהגות מכוונת: עדיף כשל רועש ביום התנודתי ביותר
            # מאשר קבלה שקטה של ציטוט ששייך אולי לסימבול/סשן שגוי לגמרי.
            if _gc_q is not None and last_px and abs(_gc_q - last_px) / last_px < 0.15:
                last_px = _gc_q
                _log.warning(f"[DATA_WARN {symbol}] {last_date}: קיים סשן מאוחר יותר ({_gc_date}) שחסר בסדרה היומית — הוחלף במחיר quote ({last_px:.4f})")
                # תיקון עוגן ל-5d בלבד: anchor_i נגזר מ-close.index שאינו כולל
                # את הסשן החסר (_gc_date) — ה"עכשיו" האמיתי זז קדימה בסשן אחד
                # ברגע שה-quote מייצג אותו. חלון 5d נשען על ספירת ברים בלבד
                # (לא על תאריך יעד כמו שאר התקופות) ולכן מפגר סשן שלם אם לא
                # מתקנים; מזיזים את העוגן קדימה בבר אחד כדי שהחלון ימשיך לכסות
                # בדיוק 5 סשנים אמיתיים. שאר התקופות (1mo ומעלה) לא מתוקנות —
                # הסטייה שם היא יום בודד מתוך חלון חודשים, זניחה בהשוואה.
                if period == "5d":
                    anchor_i = min(anchor_i + 1, len(close) - 1)
                    anchor_px = float(close.iloc[anchor_i])
                    is_partial = (len(close) + 1) < 6
            else:
                _log.warning(f"[DATA_WARN {symbol}] {last_date}: קיים סשן מאוחר יותר ({_gc_date}) שחסר בסדרה היומית ולא ניתן לאמת מול quote — משתמש במחיר הישן")

        if anchor_px == 0:
            return None
        change = last_px / anchor_px * 100 - 100
        _partial_tag = " [חלקי]" if is_partial else ""
        _log.debug(f"[{period} {symbol}] anchor={close.index[anchor_i].date()} ({anchor_px:.2f}) last={last_date} ({last_px:.2f}) => {change:.2f}%{_partial_tag}")
    if math.isnan(change):
        return None
    return change


def get_changes(stocks, period):
    pairs = []
    for symbol in stocks:
        change = get_change(symbol, period)
        if change is not None:
            pairs.append((symbol, change))
    return pairs


def compute_tech_group_index(group_def, period):
    """מדד תחום טכנולוגי: תשואה משוקללת של ליבה (1.0) ומעטפת (0.4).

    משקל מניה = ציון חשיפה × מכפיל שכבה. מניה בלי נתונים לא נספרת.
    מחזיר גם את המשקל האפקטיבי (המנורמל) של כל מניה בתוך התחום,
    ואת תרומת כל שכבה לתשואה (שתיהן יחד = התשואה הכוללת).
    """
    weighted_sum = 0.0
    weight_total = 0.0
    core_rows = []
    env_rows = []

    for symbol, exposure in group_def.get("core", {}).items():
        change = get_change(symbol, period)
        if change is None:
            continue
        w = exposure * TIER_CORE
        weighted_sum += change * w
        weight_total += w
        core_rows.append([symbol, change, w])

    for symbol, exposure in group_def.get("env", {}).items():
        change = get_change(symbol, period)
        if change is None:
            continue
        w = exposure * TIER_ENV
        weighted_sum += change * w
        weight_total += w
        env_rows.append([symbol, change, w])

    if weight_total == 0:
        return None

    # נרמול המשקלים לתצוגה: חלקה של כל מניה מתוך 100% של התחום
    for row in core_rows:
        row[2] = row[2] / weight_total
    for row in env_rows:
        row[2] = row[2] / weight_total

    core_contrib = sum(c * w for s, c, w in core_rows)
    env_contrib = sum(c * w for s, c, w in env_rows)

    all_changes = [c for s, c, w in core_rows] + [c for s, c, w in env_rows]
    up = len([c for c in all_changes if c > 0])
    down = len([c for c in all_changes if c < 0])

    return {
        "weighted_return": weighted_sum / weight_total,
        "core": sorted(core_rows, key=lambda x: x[1], reverse=True),
        "env": sorted(env_rows, key=lambda x: x[1], reverse=True),
        "core_contrib": core_contrib,
        "env_contrib": env_contrib,
        "core_weight": sum(w for s, c, w in core_rows),
        "env_weight": sum(w for s, c, w in env_rows),
        "up": up,
        "down": down,
    }


@st.cache_data(ttl=1800)
def get_news(symbol, limit=3):
    items = []
    try:
        raw = yf.Ticker(symbol).news
        for entry in raw:
            content = entry.get("content", {})
            title = content.get("title")
            if not title:
                continue
            provider = content.get("provider", {}).get("displayName", "")
            link = ""
            canon = content.get("canonicalUrl")
            if canon:
                link = canon.get("url", "")
            date_str = ""
            pub = content.get("pubDate") or content.get("displayTime")
            if pub:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    date_str = dt.strftime("%d/%m/%Y")
                except Exception:
                    date_str = ""
            items.append({"title": title, "provider": provider, "link": link, "date": date_str})
            if len(items) >= limit:
                break
    except Exception:
        pass
    return items


# ---------- פונקציות Gemini ----------
class GeminiError(Exception):
    pass


def _gemini_call(prompt, temperature=None):
    key = get_gemini_key()
    if not key:
        return None, []
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        tool = types.Tool(google_search=types.GoogleSearch())
        if temperature is not None:
            config = types.GenerateContentConfig(tools=[tool], temperature=temperature)
        else:
            config = types.GenerateContentConfig(tools=[tool])
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt, config=config,
        )
        sources = []
        cand = response.candidates[0]
        if cand.grounding_metadata and cand.grounding_metadata.grounding_chunks:
            for chunk in cand.grounding_metadata.grounding_chunks:
                if chunk.web:
                    sources.append((chunk.web.title, chunk.web.uri))
        return response.text, sources
    except Exception as e:
        raise GeminiError(str(e))


# שלושה buckets של TTL: הדקורטור מפעיל את הפקיעה; max_entries מונע תפיחה.
# bucket קצר (≤1h)  — Online בלבד
# bucket בינוני (≤24h) — Last Close, 5d
# bucket ארוך (>24h)  — 1mo ומעלה + שאילתות CapEx/מגמה
@st.cache_data(ttl=3600, max_entries=50)
def _cached_gemini_sh(cache_key, prompt):
    return _gemini_call(prompt)

@st.cache_data(ttl=86400, max_entries=50)
def _cached_gemini_md(cache_key, prompt):
    return _gemini_call(prompt)

@st.cache_data(ttl=604800, max_entries=50)
def _cached_gemini_lg(cache_key, prompt):
    return _gemini_call(prompt)


def _gemini_cached_safe(cache_key, prompt, ttl):
    try:
        if ttl <= 3600:
            return _cached_gemini_sh(cache_key, prompt)
        elif ttl <= 86400:
            return _cached_gemini_md(cache_key, prompt)
        else:
            return _cached_gemini_lg(cache_key, prompt)
    except GeminiError as e:
        msg = str(e)
        if "503" in msg or "UNAVAILABLE" in msg:
            st.error("⚠️ שרתי Gemini עמוסים כרגע. זו תקלה זמנית — נסי שוב בעוד דקה.")
        else:
            st.error("⚠️ שגיאה בקבלת תשובה מ-Gemini: " + msg)
        return None, []


def gemini_explain_move(change, period_label, period_code, movers_text):
    direction = "עלה" if change >= 0 else "ירד"
    prompt = (
        "מדד SOXX (מדד מניות השבבים) " + direction + " ב-" +
        str(round(abs(change), 2)) + " אחוז ביום המסחר האחרון. "
        "המניות שזזו הכי הרבה במדד היום: " + movers_text + ". "
        "חפש ברשת והסבר בקצרה, בעברית, מה הסיבות העיקריות לתנועה של המדד. "
        "אם מניה אחת או כמה מניות ספציפיות הניעו את התנועה (למשל דוח חזק או חלש), ציין אותן בשמן. "
        "ענה ב-3 עד 5 משפטים."
    )
    ttl = AI_CACHE_TTL.get(period_code, 3600)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "move|" + period_code + "|" + day + "|" + str(round(change, 2))
    return _gemini_cached_safe(cache_key, prompt, ttl)


def gemini_explain_outliers(soxx_change, outliers_text, period_code, period_label):
    direction = "עלה" if soxx_change >= 0 else "ירד"
    prompt = (
        "מדד SOXX " + direction + " ב-" + str(round(abs(soxx_change), 2)) +
        " אחוז ביום המסחר האחרון. "
        "אלו המניות במדד שסטו באופן חריג מתנועת המדד (עלו או ירדו לפחות " +
        str(STOCK_VS_SOXX_ALERT) + " נקודות מעל/מתחת ל-SOXX): " + outliers_text + ". "
        "חפש ברשת והסבר בקצרה, בעברית, את הסיבות הספציפיות לתנועה החריגה של כל מניה בולטת — "
        "כגון דוח רבעוני, שדרוג או הורדת דירוג אנליסטים, חדשות מוצר, רגולציה, או רוטציה סקטוריאלית. "
        "התמקד בסיבות הייחודיות לכל מניה בנפרד, לא בתנועת המדד הכללי. ענה ב-4 עד 6 משפטים."
    )
    ttl = AI_CACHE_TTL.get(period_code, 3600)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = (
        "outliers|" + period_code + "|" + day + "|" +
        str(round(soxx_change, 2)) + "|" +
        hashlib.md5(outliers_text.encode("utf-8")).hexdigest()[:8]
    )
    return _gemini_cached_safe(cache_key, prompt, ttl)


def gemini_trend_summary(period_label, period_code, soxx_change, sector_lines):
    prompt = (
        "מדד SOXX (מניות השבבים) השתנה ב-" + str(round(soxx_change, 1)) +
        " אחוז בתקופה של " + period_label + ". "
        "ביצועי התחומים בשרשרת הערך בתקופה זו: " + sector_lines + ". "
        "חפש ברשת וכתוב בעברית סיכום של המגמה המרכזית שתמכה בתנועה בתקופה הזו. "
        "התייחס לנושאים מובילים (כמו ביקושי AI, דאטה סנטרים, זיכרון, ציוד ייצור) "
        "ואילו תחומים הובילו ואילו פיגרו. ענה ב-4 עד 6 משפטים."
    )
    ttl = AI_CACHE_TTL.get(period_code, 604800)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "trend|" + period_code + "|" + day
    return _gemini_cached_safe(cache_key, prompt, ttl)


def gemini_explain_rating(symbol, firm, action, from_grade, to_grade, grade_date):
    """הסבר AI לשינוי דירוג אנליסטים — 3-5 משפטים בעברית עם חיפוש ברשת."""
    direction = "שדרג" if action == "up" else "הוריד"
    prompt = (
        "בית ההשקעות " + str(firm) + " " + direction + " את " + symbol +
        " מ-" + str(from_grade or "—") + " ל-" + str(to_grade or "—") +
        " בתאריך " + str(grade_date) + ". "
        "חפש ברשת והסבר בעברית את הרקע ואת הנימוקים לשינוי הדירוג הזה: "
        "דוח כספי, מחיר יעד, תחזיות, שינוי הערכת שווי, או אירוע תאגידי. "
        "ענה ב-3 עד 5 משפטים בלבד."
    )
    cache_key = "rating|" + symbol + "|" + str(firm) + "|" + str(grade_date) + "|" + str(to_grade)
    return _gemini_cached_safe(cache_key, prompt, ttl=604800)


@st.cache_data(ttl=43200)
def gemini_analyze_news(sector_name, titles_sig, titles_block):
    key = get_gemini_key()
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        config = types.GenerateContentConfig(response_mime_type="application/json")
        prompt = (
            "אלה כותרות חדשות אחרונות על מניות בתחום '" + sector_name + "' בסקטור השבבים:\n"
            + titles_block + "\n\n"
            "החזר JSON בלבד, בלי טקסט נוסף, במבנה הבא:\n"
            '{ "overall": "positive|negative|neutral", '
            '"overall_note": "משפט אחד בעברית שמסכם את סנטימנט החדשות בתחום", '
            '"items": [ { "title": "הכותרת המקורית", '
            '"sentiment": "positive|negative|neutral", '
            '"summary": "סיכום קצר בעברית, משפט עד שניים" } ] }\n'
            "דרג כל כותרת לפי ההשפעה הצפויה על המניה, וכתוב את הסיכומים בעברית."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt, config=config,
        )
        return json.loads(response.text)
    except Exception:
        return None


# ---------- פונקציות CapEx ----------
@st.cache_data(ttl=86400)
def get_capex_quarterly(symbol):
    """CapEx רבעוני במיליארדי דולרים, מהישן לחדש. None אם אין נתונים."""
    try:
        cf = yf.Ticker(symbol).quarterly_cashflow
        row = None
        for name in ("Capital Expenditure", "Capital Expenditures"):
            if name in cf.index:
                row = cf.loc[name]
                break
        if row is None:
            return None
        row = row.dropna().abs() / 1e9
        row = row.sort_index()
        if len(row) == 0:
            return None
        return row
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_capex_annual(symbol):
    """CapEx שנתי (לפי השנה הפיסקלית של החברה) במיליארדי דולרים, מהישן לחדש.

    משמיט שנים קלנדריות >= השנה הנוכחית: yfinance עשוי להחזיר שורה לשנה
    שטרם הסתיימה קלנדרית (ולכן ה-CapEx בה חלקי, לא "בפועל" אמיתי להשוואה
    שנתית מלאה) — למשל FY מיקרוסופט שנסגר ביוני עדיין שייך לשנה הקלנדרית
    הנוכחית. הסינון לפי השנה הקלנדרית של תאריך הדיווח, לא לפי סטטוס הסגירה
    הפיסקלי. משפיע על כל הצרכנים (גרף חברה בודדת, הגרף המצטבר, וטבלת
    הסיכום) מנקודה אחת — לא נוגע ב-get_capex_quarterly."""
    try:
        cf = yf.Ticker(symbol).cashflow
        row = None
        for name in ("Capital Expenditure", "Capital Expenditures"):
            if name in cf.index:
                row = cf.loc[name]
                break
        if row is None:
            return None
        row = row.dropna().abs() / 1e9
        row = row.sort_index()
        _current_year = ny_now().year
        row = row[[d.year < _current_year for d in row.index]]
        if len(row) == 0:
            return None
        return row
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_earnings_history(symbol):
    """היסטוריית EPS: נסיון חי; fallback מ-earnings_calendar.json."""
    try:
        df = yf.Ticker(symbol).earnings_dates
        if df is not None and not df.empty:
            reported = df[df["Reported EPS"].notna()].copy()
            if not reported.empty:
                return reported.sort_index(ascending=False).head(8)
    except Exception:
        pass
    try:
        _ecal = _load_ecal_data()
        _recs = (_ecal or {}).get("earnings_history", {}).get(symbol, {}).get("eps_history", [])
        _reps = sorted([r for r in _recs if r.get("reported_eps") is not None],
                       key=lambda r: r["date"], reverse=True)[:8]
        if not _reps:
            return None
        return pd.DataFrame(
            {"Reported EPS": [r["reported_eps"] for r in _reps],
             "EPS Estimate": [r.get("eps_estimate") for r in _reps],
             "Surprise(%)":  [r.get("surprise_pct") for r in _reps]},
            index=pd.to_datetime([r["date"] for r in _reps]),
        )
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_quarterly_revenue(symbol):
    """הכנסות רבעוניות: נסיון חי; fallback מ-earnings_calendar.json. מחזיר (Series ב-1e9, שם) או (None, None)."""
    try:
        qf = yf.Ticker(symbol).quarterly_financials
        if qf is not None and not qf.empty:
            for name in ("Total Revenue", "TotalRevenue", "Revenue"):
                if name in qf.index:
                    row = qf.loc[name].dropna() / 1e9
                    return row.sort_index(), name
    except Exception:
        pass
    try:
        _ecal = _load_ecal_data()
        _recs = (_ecal or {}).get("earnings_history", {}).get(symbol, {}).get("quarterly_revenue", [])
        if not _recs:
            return None, None
        _name = _recs[0].get("row_name", "Total Revenue")
        _s = pd.Series(
            [r.get("revenue_b") for r in _recs],
            index=pd.to_datetime([r["date"] for r in _recs]),
        ).sort_index()
        return _s, _name
    except Exception:
        return None, None


@st.cache_data(ttl=86400)
def get_financial_currency(symbol):
    """קוד המטבע הפיננסי (financialCurrency) מ-ticker.info."""
    try:
        return yf.Ticker(symbol).info.get("financialCurrency", "USD") or "USD"
    except Exception:
        return "USD"


CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "KRW": "₩", "TWD": "NT$",
    "JPY": "¥", "GBP": "£", "ILS": "₪",
}


def currency_symbol(code):
    """מחזיר סמל מטבע ($, €, ₩ וכו'). לקוד לא-מוכר — הקוד עצמו + רווח."""
    return CURRENCY_SYMBOLS.get(code, (code or "USD") + " ")


def record_currency(symbol, record):
    """קוד המטבע של רשומה: מהשדה השמור אם קיים, אחרת fallback ל-target_currency."""
    ccy = (record or {}).get("currency")
    if ccy:
        return ccy
    return target_currency(symbol)


def target_currency(symbol):
    """המטבע שבו Gemini יתבקש לדווח עבור חברה זו.
    REPORTING_CURRENCY_OVERRIDE גובר על get_financial_currency."""
    if symbol in REPORTING_CURRENCY_OVERRIDE:
        return REPORTING_CURRENCY_OVERRIDE[symbol]
    return get_financial_currency(symbol) or "USD"


@st.cache_data(ttl=21600)
def get_upgrades_downgrades(symbol, limit=25):
    """DataFrame שדרוגים/הורדות: נסיון חי; fallback מ-earnings_calendar.json."""
    try:
        t = yf.Ticker(symbol)
        df = t.upgrades_downgrades
        if df is not None and not df.empty:
            df = df.copy()
            if "GradeDate" in df.columns:
                df["date"] = pd.to_datetime(df["GradeDate"]).dt.date
            elif df.index.name == "GradeDate" or "GradeDate" in str(df.index.name):
                df = df.reset_index()
                df["date"] = pd.to_datetime(df["GradeDate"]).dt.date
            else:
                df = df.reset_index()
                date_col = df.columns[0]
                df["date"] = pd.to_datetime(df[date_col]).dt.date
            df = df.sort_values("date", ascending=False).head(limit).reset_index(drop=True)
            return df
    except Exception:
        pass
    try:
        _ecal = _load_ecal_data()
        _recs = (_ecal or {}).get("ratings", {}).get(symbol, {}).get("upgrades_downgrades", [])
        if not _recs:
            return None
        _df2 = pd.DataFrame({
            "Action":    [r.get("action", "")     for r in _recs],
            "Firm":      [r.get("firm", "")        for r in _recs],
            "FromGrade": [r.get("from_grade", "")  for r in _recs],
            "ToGrade":   [r.get("to_grade", "")    for r in _recs],
            "date":      [r.get("date")             for r in _recs],
        })
        _df2["date"] = pd.to_datetime(_df2["date"]).dt.date
        _df2 = _df2.sort_values("date", ascending=False).head(limit).reset_index(drop=True)
        return _df2 if not _df2.empty else None
    except Exception:
        return None


@st.cache_data(ttl=21600)
def get_price_targets(symbol):
    """dict price targets: נסיון חי; fallback מ-earnings_calendar.json."""
    try:
        t = yf.Ticker(symbol)
        result = {}
        apt = getattr(t, "analyst_price_targets", None)
        if apt is not None:
            current = apt.get("current")
            low     = apt.get("low")
            mean    = apt.get("mean")
            median  = apt.get("median")
            high    = apt.get("high")
        else:
            info    = t.info or {}
            current = info.get("currentPrice")
            low     = info.get("targetLowPrice")
            mean    = info.get("targetMeanPrice")
            median  = info.get("targetMedianPrice")
            high    = info.get("targetHighPrice")
            result["n_analysts"] = info.get("numberOfAnalystOpinions")
            result["rec_key"]    = info.get("recommendationKey")
            result["currency"]   = info.get("currency", "USD")
        if mean and low and high:
            result.update({"current": current, "low": low, "mean": mean,
                            "median": median, "high": high})
            if "currency" not in result:
                result["currency"] = get_financial_currency(symbol)
            return result
    except Exception:
        pass
    try:
        _ecal = _load_ecal_data()
        _pt = (_ecal or {}).get("ratings", {}).get(symbol, {}).get("price_targets")
        return _pt if _pt else None
    except Exception:
        return None


def _fetch_recommendation_dist_raw(symbol):
    """משיכת התפלגות rec ללא קאש — נקראת מתוך threads בלבד."""
    try:
        t = yf.Ticker(symbol)
        rec = t.recommendations
        if rec is not None and not rec.empty:
            row = rec.iloc[0]
            return {
                "strongBuy":  int(row.get("strongBuy",  0) or 0),
                "buy":        int(row.get("buy",         0) or 0),
                "hold":       int(row.get("hold",        0) or 0),
                "sell":       int(row.get("sell",        0) or 0),
                "strongSell": int(row.get("strongSell",  0) or 0),
            }
    except Exception:
        pass
    try:
        _ecal = _load_ecal_data()
        _rd = (_ecal or {}).get("ratings", {}).get(symbol, {}).get("recommendation_dist")
        return _rd if _rd else None
    except Exception:
        return None


@st.cache_data(ttl=21600)
def get_recommendation_dist(symbol):
    """התפלגות rec: נסיון חי; fallback מ-earnings_calendar.json."""
    return _fetch_recommendation_dist_raw(symbol)


def _fetch_analyst_score_raw(symbol):
    """חישוב ציון ללא קאש — נקראת מתוך threads בלבד."""
    dist = _fetch_recommendation_dist_raw(symbol)
    if dist is None:
        return None
    n = sum(dist.values())
    if n < ANALYST_MIN_N:
        return None
    weighted = (
        dist.get("strongBuy",  0) * ANALYST_WEIGHTS["strongBuy"]  +
        dist.get("buy",        0) * ANALYST_WEIGHTS["buy"]         +
        dist.get("hold",       0) * ANALYST_WEIGHTS["hold"]        +
        dist.get("sell",       0) * ANALYST_WEIGHTS["sell"]        +
        dist.get("strongSell", 0) * ANALYST_WEIGHTS["strongSell"]
    )
    return {
        "score": weighted / n,
        "n":     n,
        "buy":   dist.get("strongBuy", 0) + dist.get("buy", 0),
        "hold":  dist.get("hold", 0),
        "sell":  dist.get("sell", 0) + dist.get("strongSell", 0),
    }


@st.cache_data(ttl=21600)
def get_analyst_score(symbol):
    """ממוצע משוקלל 1–5 לפי ANALYST_WEIGHTS. מחזיר dict{"score","n","buy","hold","sell"} או None."""
    return _fetch_analyst_score_raw(symbol)


@st.cache_data(ttl=21600, show_spinner=False)
def scan_analyst_scores(symbols_tuple):
    """סריקה מקבילה של ציוני אנליסטים. מחזיר {symbol: score_dict} רק למי שיש ציון."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as ex:
        raw = list(ex.map(_fetch_analyst_score_raw, symbols_tuple))
    return {sym: sc for sym, sc in zip(symbols_tuple, raw) if sc is not None}


def analyst_median(scores_map):
    """חציון כל הציונים ב-scores_map. מחזיר float או None."""
    import statistics as _stat
    vals = [v["score"] for v in scores_map.values()]
    return _stat.median(vals) if vals else None


def analyst_group_score(symbols, scores_map):
    """ציון אנליסטים מצרפי לתחום — חציון, עמיד לחריגים ולכיסוי לא-אחיד.
    מחזיר {"score","reported","total"} או None."""
    vals = [scores_map[s]["score"] for s in symbols if s in scores_map]
    if not vals:
        return None
    return {
        "score": statistics.median(vals),
        "reported": len(vals),
        "total": len(symbols),
    }


# ── בטא מול SOXX ────────────────────────────────────────────────────────────

def _daily_returns_raw(symbol):
    """תשואות יומיות ללא קאש — נקראת מתוך threads בלבד.
    נמשכות על פני BETA_WINDOW (6 חודשים) ואז נחתכות ל-3 החודשים האחרונים בלבד
    (לפי תאריך, לא לפי מספר שורות) — המשיכה הרחבה יותר מ-3 החודשים הנמדדים
    היא תשתית לבטא מתגלגלת עתידית."""
    try:
        data = yf.Ticker(symbol).history(period=BETA_WINDOW, auto_adjust=False)
        close = data["Close"].dropna()
        if close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        daily = close.pct_change().dropna()
        if len(daily) == 0:
            return None
        cutoff = daily.index[-1] - pd.DateOffset(months=3)
        daily = daily[daily.index >= cutoff]
        if len(daily) < BETA_MIN_POINTS:
            return None
        return daily
    except Exception:
        return None


def _beta_from_bench(symbol, bench_rets):
    """חישוב בטא מול bench_rets ללא קאש."""
    if symbol == BENCHMARK:
        return {"beta": 1.0, "n": len(bench_rets), "r2": 1.0}
    sym_rets = _daily_returns_raw(symbol)
    if sym_rets is None:
        return None
    combined = pd.concat(
        [sym_rets.rename("sym"), bench_rets.rename("bench")], axis=1
    ).dropna()
    n = len(combined)
    if n < BETA_MIN_POINTS:
        return None
    var_bench = combined["bench"].var()
    if var_bench == 0:
        return None
    beta = combined["sym"].cov(combined["bench"]) / var_bench
    corr = combined["sym"].corr(combined["bench"])
    import math as _math
    r2 = corr ** 2 if not _math.isnan(corr) else 0.0
    return {"beta": round(beta, 4), "n": n, "r2": round(r2, 4)}


@st.cache_data(ttl=86400)
def get_beta(symbol):
    """בטא יומית מול SOXX בחלון של 3 חודשים. מחזיר dict{"beta","n","r2"} או None."""
    bench_rets = _daily_returns_raw(BENCHMARK)
    if bench_rets is None:
        return None
    return _beta_from_bench(symbol, bench_rets)


@st.cache_data(ttl=86400, show_spinner=False)
def scan_betas(symbols_tuple):
    """סריקה מקבילה של בטא מול SOXX. מחזיר {symbol: dict} רק למי שיש ערך."""
    import functools
    from concurrent.futures import ThreadPoolExecutor
    bench_rets = _daily_returns_raw(BENCHMARK)
    if bench_rets is None:
        return {}
    fn = functools.partial(_beta_from_bench, bench_rets=bench_rets)
    with ThreadPoolExecutor(max_workers=10) as ex:
        raw = list(ex.map(fn, symbols_tuple))
    return {sym: b for sym, b in zip(symbols_tuple, raw) if b is not None}


def beta_color(beta):
    """צבע הבטא: מעל 1 = מגבירת תנועה (כתום), 0.6–1 = ממתנת (כחול), עד 0.6 = נמוכה (ירוק)."""
    if beta is None:
        return "#9ca3af"
    if beta > 1.0:
        return "#f97316"
    if beta <= 0.6:
        return "#22c55e"
    return "#60a5fa"


def beta_cell_html(agg, wrapper="span", width="95px"):
    """תא HTML לבטא מול SOXX. חתימה זהה ל-analyst_cell_html.
    agg = תוצאת beta_group_score (מפתח "beta","reported","total")
          או get_beta (מפתח "beta","n","r2"), או None."""
    empty_style = "text-align:center; padding:6px 8px; color:#6b7280; font-size:12px;"
    if agg is None or agg.get("beta") is None:
        if wrapper == "span":
            return "<span style='width:" + width + "; " + empty_style + "'>—</span>"
        return "<td style='" + empty_style + "'>—</td>"
    beta = agg["beta"]
    color = beta_color(beta)
    beta_txt = str(round(beta, 2))
    r2 = agg.get("r2", 1.0)
    noisy_html = ""
    if r2 < BETA_MIN_R2:
        noisy_html = ("<span style='color:#6b7280; font-size:10px;' "
                      "title='R² נמוך — הבטא רועשת'>*</span>")
    inner = ("<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>"
             "<span style='color:" + color + "; font-weight:700;'>" + beta_txt + "</span>"
             + noisy_html + "</span>")
    if wrapper == "span":
        return ("<span style='width:" + width + "; text-align:center; white-space:nowrap; "
                "display:inline-block;'>" + inner + "</span>")
    return "<td style='text-align:center; padding:6px 8px; white-space:nowrap;'>" + inner + "</td>"


def beta_group_score(symbols, beta_map):
    """חציון בטא לקבוצת מניות. מחזיר {"beta","r2","reported","total"} או None."""
    import statistics as _stat
    total = len(symbols)
    if total == 0:
        return None
    scored = [(sym, beta_map[sym]["beta"], beta_map[sym].get("r2", 1.0)) for sym in symbols
              if sym in beta_map and beta_map[sym].get("beta") is not None]
    reported = len(scored)
    if reported == 0:
        return {"beta": None, "r2": None, "reported": 0, "total": total}
    beta = _stat.median(b for _, b, _ in scored)
    r2 = _stat.median(r for _, _, r in scored)
    return {"beta": round(beta, 4), "r2": round(r2, 4), "reported": reported, "total": total}


BETA_ROLL_MONTHS = 3            # חלון גלגול קלנדרי — זהה בדיוק לחתך שמשתמשת בו _daily_returns_raw
                                 # (לא ספירת שורות קבועה: למניה עם לוח מסחר שונה מ-SOXX, כמו .KS,
                                 # 3 חודשים קלנדריים ו-63 שורות חופפות אינם בהכרח אותו דבר — ראה תיעוד
                                 # ב-_rolling_beta_series)
BETA_ROLL_FETCH_PAD_DAYS = 130  # ימי קלנדר להיסטוריה נוספת לפני תחילת התקופה — מבטיח
                                 # מספיק היסטוריה לחלון BETA_ROLL_MONTHS בנקודה הראשונה
                                 # המוצגת, גם עם סופ"שים וחגים בתווך.


@st.cache_data(ttl=300)
def _get_daily_close_for_rolling(symbol, fetch_start):
    """סגירות יומיות גולמיות (auto_adjust=False) מ-fetch_start ועד היום — לחישוב
    בטא מתגלגלת. tz מנוטרל בדיוק כמו ב-_daily_returns_raw, כדי שמיזוג SOXX מול
    מניות מבורסות אחרות (למשל .KS) יתבצע לפי תאריך קלנדרי, לא שעון מקומי."""
    try:
        end_d = ny_now().date() + timedelta(days=1)
        data = yf.Ticker(symbol).history(start=str(fetch_start), end=str(end_d), auto_adjust=False)
        close = data["Close"].dropna()
        if len(close) < 2:
            return None
        if close.index.tz is not None:
            close.index = close.index.tz_localize(None)
        return close
    except Exception:
        return None


def _rolling_beta_series(symbol, bench_close, fetch_start):
    """בטא מתגלגלת יומית מול SOXX: לכל יום מסחר t של SOXX, משחזרת בדיוק את השיטה של
    _daily_returns_raw + _beta_from_bench, כאילו t היה "היום" — לא rolling(N) על סדרה
    ממוזגת מראש.

    למה זה קריטי: _daily_returns_raw חותך כל סדרה (מניה, SOXX) בנפרד לפי 3 החודשים
    האחרונים *של אותה סדרה עצמה*, ורק אז _beta_from_bench מיישר (concat+dropna) בין
    השתיים. אם למניה (בעיקר .KS — לוח מסחר קוריאני) יש יום מסחר אחרון שונה מ-SOXX
    (למשל בגלל פיגור דיווח או הפרשי אזור זמן), שני החיתוכים העצמאיים האלה נותנים
    תוצאה שונה מחיתוך יחיד על הסדרה המיושרת מראש — וגרסה קודמת של הפונקציה הזו
    (rolling על combined אחרי dropna) לא התלכדה עם הבטא הסטטית בדיוק מהסיבה הזו.
    לכן כאן, בכל t: מוצא את היום האחרון של המניה שאינו מאוחר מ-t, חותך את שתי
    הסדרות בנפרד לפי BETA_ROLL_MONTHS חודשים אחורה מנקודת הייחוס של כל אחת, ורק
    אז מיישר את השתי-חלונות (חיתוך תאריכים). ב-t=היום האחרון — זהה מתמטית ובדיוק
    ל-get_beta(symbol).

    symbol == BENCHMARK מחזיר קבוע 1.0 לאורך כל הטווח (הגדרה, לא חישוב).
    מסנן ימים עם פחות מ-BETA_MIN_POINTS ימים חופפים בחלון (כמו הבטא הסטטית).
    מחזיר Series (אינדקס=תאריכים) או None אם אין מספיק היסטוריה."""
    bench_rets = bench_close.pct_change().dropna()
    if symbol == BENCHMARK:
        return pd.Series(1.0, index=bench_rets.index)
    close = _get_daily_close_for_rolling(symbol, fetch_start)
    if close is None:
        return None
    sym_rets = close.pct_change().dropna()
    if sym_rets.empty or bench_rets.empty:
        return None

    sym_idx = sym_rets.index
    bench_idx = bench_rets.index
    betas, valid_dates = [], []

    for j, t in enumerate(bench_idx):
        # יום המסחר האחרון של הסימבול עצמו שאינו מאוחר מ-t — עשוי לפגר יום-יומיים
        # אחרי SOXX (הפרשי לוח מסחר/דיווח), בדיוק כמו ב-daily.index[-1] הסטטי.
        k = sym_idx.searchsorted(t, side="right") - 1
        if k < 0:
            continue
        sym_last = sym_idx[k]

        cutoff_sym = sym_last - pd.DateOffset(months=BETA_ROLL_MONTHS)
        cutoff_bench = t - pd.DateOffset(months=BETA_ROLL_MONTHS)
        lo_s = sym_idx.searchsorted(cutoff_sym, side="left")
        lo_b = bench_idx.searchsorted(cutoff_bench, side="left")

        common = sym_idx[lo_s:k + 1].intersection(bench_idx[lo_b:j + 1])
        if len(common) < BETA_MIN_POINTS:
            continue

        w_sym = sym_rets.reindex(common).to_numpy()
        w_bench = bench_rets.reindex(common).to_numpy()
        var_b = w_bench.var(ddof=1)
        if var_b == 0 or math.isnan(var_b):
            continue
        cov_sb = ((w_sym - w_sym.mean()) * (w_bench - w_bench.mean())).sum() / (len(w_bench) - 1)
        betas.append(cov_sb / var_b)
        valid_dates.append(t)

    if not betas:
        return None
    return pd.Series(betas, index=pd.DatetimeIndex(valid_dates))


@st.cache_data(ttl=86400)
def get_forward_estimates(symbol):
    """תחזיות אנליסטים לרבעון הקרוב: eps_est, revenue_est_b, revenue_growth_pct."""
    try:
        t = yf.Ticker(symbol)
        result = {}
        ee = t.earnings_estimate
        if ee is not None and not ee.empty and "0q" in ee.index:
            avg = ee.loc["0q"].get("avg")
            if avg is not None and not (isinstance(avg, float) and math.isnan(avg)):
                result["eps_est"] = float(avg)
        re_ = t.revenue_estimate
        if re_ is not None and not re_.empty and "0q" in re_.index:
            row = re_.loc["0q"]
            avg = row.get("avg")
            growth = row.get("growth")
            if avg is not None and not (isinstance(avg, float) and math.isnan(avg)):
                result["revenue_est_b"] = float(avg) / 1e9
            if growth is not None and not (isinstance(growth, float) and math.isnan(growth)):
                result["revenue_growth_pct"] = float(growth) * 100
        return result if result else None
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_stock_reaction(symbol, report_date_str):
    """% שינוי של המניה מסגירת יום הדוח לסגירת יום המסחר הבא.
    מחזיר (reaction_pct, next_date) או (None, None) בשגיאה."""
    from datetime import timedelta
    try:
        report_date = datetime.fromisoformat(report_date_str[:10]).date()
        start = report_date - timedelta(days=2)
        end = report_date + timedelta(days=6)
        df = yf.Ticker(symbol).history(start=str(start), end=str(end), auto_adjust=False)["Close"].dropna()
        if len(df) < 2:
            return None, None
        date_prices = [(dt.date(), float(p)) for dt, p in zip(df.index, df.values)]
        after = [(d, p) for d, p in date_prices if d >= report_date]
        if len(after) < 2:
            return None, None
        _, p0 = after[0]
        d1, p1 = after[1]
        if p0 == 0:
            return None, None
        return p1 / p0 * 100 - 100, d1
    except Exception:
        return None, None


def get_symbol_cal_status(sym, d, has_report, sentiment_data):
    """מחזיר 'future' / 'analyzed' / 'unanalyzed' לצביעת לוח השנה.
    רשומה שמורה עם sentiment_score גוברת על is_future של yfinance."""
    today = datetime.now(timezone.utc).date()
    if d > today:
        return "future"
    rec = get_record(sentiment_data, sym, season_from_date(d))
    if rec and rec.get("sentiment_score") is not None:
        return "analyzed"
    if not has_report:
        # has_report=False בגלל פיגור עדכון EPS ב-yfinance (שעות עד יום) לא אמור
        # להשאיר צ'יפ כחול לתאריך שכבר חלף — הצבע נגזר מהזמן, לא מזמינות ה-EPS.
        # d == today נשאר "future" (הדוח עדיין עשוי לצאת היום); רק d < today הופך ל"unanalyzed".
        return "unanalyzed" if d < today else "future"
    return "unanalyzed"


@st.cache_data(ttl=3600)
def get_earnings_calendar(symbols, days_back=120, days_fwd=120):
    """לכל חברה: כל הדוחות בחלון [היום - days_back, היום + days_fwd].
    מחזיר רשימת dicts: date (datetime.date), symbol, eps_est, eps_actual, surprise, is_future.

    מקור 1 — earnings_calendar.json (נכתב ע"י GitHub Action יומי, עמיד ל-rate-limit).
    מקור 2 — yfinance חי (ניסיון; ממוזג; חי גובר על הקובץ לאותו (symbol, date)).
    → מקומית: תמיד חי + קובץ. בענן: בעיקר קובץ + מה שהצליח חי."""
    from datetime import timedelta
    import math
    today = datetime.now(timezone.utc).date()
    lo = today - timedelta(days=days_back)
    hi = today + timedelta(days=days_fwd)

    def _clean(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _parse_date(ds):
        try:
            return datetime.strptime(str(ds)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    # --- שלב 1: טעינה מהקובץ ---
    file_records: dict = {}
    try:
        with open(EARNINGS_CALENDAR_FILE, "r", encoding="utf-8") as _fh:
            _raw_json = json.load(_fh)
            _cal_list = _raw_json.get("earnings_calendar", _raw_json) if isinstance(_raw_json, dict) else _raw_json
            for _r in _cal_list:
                _sym = _r.get("symbol")
                _d = _parse_date(_r.get("date"))
                if _sym and _d and lo <= _d <= hi:
                    file_records[(_sym, _d)] = {
                        "date":       _d,
                        "symbol":     _sym,
                        "eps_est":    _clean(_r.get("eps_est")),
                        "eps_actual": _clean(_r.get("eps_actual")),
                        "surprise":   _clean(_r.get("surprise")),
                        "is_future":  bool(_r.get("is_future", True)),
                    }
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        pass

    # --- שלב 2: משיכה חיה (שגיאות נבלעות) ---
    live_records: dict = {}
    for sym in symbols:
        try:
            df = yf.Ticker(sym).earnings_dates
            if df is None or df.empty:
                continue
            for dt in df.index:
                d = dt.date() if hasattr(dt, "date") else dt
                if not (lo <= d <= hi):
                    continue
                row = df.loc[dt]
                eps_act = _clean(row.get("Reported EPS"))
                eps_est = _clean(row.get("EPS Estimate"))
                surp    = _clean(row.get("Surprise(%)"))
                live_records[(sym, d)] = {
                    "date": d, "symbol": sym,
                    "eps_est": eps_est, "eps_actual": eps_act,
                    "surprise": surp, "is_future": eps_act is None,
                }
        except Exception:
            continue

    # --- שלב 3: מיזוג לפי סוג רשומה ---
    def _cal_quarter(d):
        # רבעון קלנדרי של תאריך (datetime.date) — משמש כמפתח dedup לרשומות עתידיות
        return (d.year, (d.month - 1) // 3 + 1)

    # עבר (is_future=False): עובדות היסטוריות — מיזוג לפי (symbol, date), חי גובר
    file_hist = {k: v for k, v in file_records.items() if not v["is_future"]}
    live_hist = {k: v for k, v in live_records.items() if not v["is_future"]}
    merged_hist = {**file_hist, **live_hist}

    # עתיד (is_future=True): Yahoo מעדכן תאריכים → מיזוג לפי (symbol, רבעון)
    # רשומת קובץ נשמרת רק אם אין רשומה חיה לאותו (symbol, רבעון)
    file_fut  = {k: v for k, v in file_records.items() if v["is_future"]}
    live_fut  = {k: v for k, v in live_records.items() if v["is_future"]}
    live_fut_q = {(sym, _cal_quarter(d)): rec for (sym, d), rec in live_fut.items()}
    merged_fut: dict = {}
    for (sym, d), rec in file_fut.items():
        if (sym, _cal_quarter(d)) not in live_fut_q:
            merged_fut[(sym, d)] = rec
    merged_fut.update(live_fut)

    merged = {**merged_hist, **merged_fut}
    out = []
    for r in merged.values():
        r["is_future"] = r.get("eps_actual") is None
        out.append(r)
    out.sort(key=lambda x: x["date"])
    return out


def gemini_capex_guidance():
    """חיפוש התחזיות השנתיות העדכניות — עוזר למלא את CAPEX_GUIDANCE ידנית."""
    prompt = (
        "חפש ברשת את תחזית ה-CapEx השנתית (Capital Expenditure Guidance) "
        "העדכנית ביותר שכל אחת מהחברות הבאות נתנה בשיחת הוועידה האחרונה שלה: "
        "Microsoft (שנה פיסקלית עד יוני), Alphabet/Google, Amazon, Meta. "
        "כתוב בעברית, לכל חברה שורה אחת: שם החברה, לאיזו שנה פיסקלית התחזית, "
        "מה הסכום במיליארדי דולרים, ומתי התחזית ניתנה (איזה דוח רבעוני). "
        "אם חברה עדכנה את התחזית במהלך השנה, ציין גם את המספר הקודם."
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "capex_guidance|" + day
    return _gemini_cached_safe(cache_key, prompt, 259200)


def gemini_rpo_guidance():
    """חיפוש נתוני ה-RPO הרבעוניים העדכניים — עוזר למלא את RPO_QUARTERLY ידנית."""
    prompt = (
        "חפש ברשת את נתון ה-RPO (Remaining Performance Obligations — צבר ההתחייבויות "
        "החוזיות שטרם הוכרו כהכנסה) הרבעוני העדכני ביותר שכל אחת מהחברות הבאות דיווחה "
        "בדוח הרבעוני (10-Q) או השנתי (10-K) האחרון שלה: Amazon (בעיקר AWS), "
        "Microsoft (Commercial RPO), Alphabet/Google (בעיקר Google Cloud). "
        "כתוב בעברית, לכל חברה שורה אחת: שם החברה, מה הסכום במיליארדי דולרים, "
        "ומאיזה דוח (איזה רבעון קלנדרי) הנתון נלקח."
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "rpo_guidance|" + day
    return _gemini_cached_safe(cache_key, prompt, 259200)


def gemini_capex_combined(quarterly_lines, guidance_lines):
    """סיכום משולב של מגמת CapEx רבעונית ועדכוני תחזית שנתית."""
    parts = []
    if quarterly_lines:
        parts.append(
            "נתוני CapEx רבעוניים בפועל של ענקיות הענן (מיליארדי דולרים, 4 רבעונים אחרונים): "
            + quarterly_lines + "."
        )
    if guidance_lines:
        parts.append(
            "עדכוני תחזית CapEx שנתית של ענקיות הענן (כפי שדווחו בשיחות הוועידה):\n"
            + guidance_lines + "."
        )
    data_block = " ".join(parts) if parts else "אין נתונים זמינים."
    prompt = (
        data_block + "\n\n"
        "חפש ברשת הקשר ועדכונים נוספים, ולאחר מכן כתוב בעברית סיכום של 5-6 משפטים "
        "שעונה על שלוש שאלות: "
        "(א) מה מראה המגמה הרבעונית בפועל — האצה או האטה בהשקעות? "
        "(ב) מה כיוון עדכוני התחזית השנתית (עולות/יורדות/יציבות) ומה אמרו המנכ\"לים "
        "בשיחות הוועידה בהצדקת ההשקעות? "
        "(ג) מה המשמעות המשולבת לספקיות השבבים והציוד (NVDA, ASML, AMAT, TSM)?"
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = "capex_combined|" + day
    return _gemini_cached_safe(cache_key, prompt, 604800)


def gemini_analyze_earnings(symbol, season):
    """מנתח דוח ושיחת ועידה של חברה לפי עונה, עם חיפוש רשת.
    season = מחרוזת כמו '2026Q2'. מחזיר dict מובנה, או None בשגיאה.
    לא ממוטמן — נקרא רק על ידי לחיצת משתמש."""
    # בניית רשימת התחומים הסגורה מ-TECH_GROUPS
    valid_domains = set()
    for axis in TECH_GROUPS.values():
        for gname in axis.keys():
            valid_domains.add(gname)
    domains_list = "\n".join("- " + d for d in sorted(valid_domains))

    # המרת עונה לטקסט קריא
    year, q = season[:4], season[5]
    q_months = {"1": "ינואר–מרץ", "2": "אפריל–יוני", "3": "יולי–ספטמבר", "4": "אוקטובר–דצמבר"}
    season_label = "Q" + q + " " + year + " (" + q_months.get(q, "") + ")"

    _target_ccy = target_currency(symbol)
    prompt = (
        "חפש ברשת שני מקורות לגבי " + symbol + " לתקופת " + season_label + ":\n"
        "1. הדוח הרבעוני (10-Q / press release) — תוצאות EPS, הכנסות, מול ציפיות האנליסטים.\n"
        "2. תמליל או סיכום שיחת הוועידה (earnings call transcript) — הערות ההנהלה, "
        "תחזיות, ושוקי הקצה שהוזכרו (data center, auto, industrial, mobile, PC וכד').\n"
        "שלב את שני המקורות לניתוח אחד מקיף.\n\n"
        "לאחר מכן, החזר JSON בלבד (ללא טקסט נוסף לפניו או אחריו) במבנה הבא:\n"
        "{\n"
        '  "report_date": "YYYY-MM-DD",\n'
        '  "sentiment_score": <מספר בין -1.0 לבין 1.0: שלילי=ציפיות מאכזבות/הנחיה יורדת, '
        'חיובי=תוצאות טובות/הנחיה עולה, 0=ניטרלי>,\n'
        '  "results_vs_expectations": "beat|meet|miss",\n'
        '  "guidance_direction": "raised|maintained|lowered|none",\n'
        '  "summary": "<סיכום קצר בעברית, 2-3 משפטים: תוצאות, מה הפתיע, לאן כיוון ההנחיה>",\n'
        '  "domain_signals": [\n'
        '    {"domain": "<שם מהרשימה הסגורה בלבד>", "direction": "improving|stable|deteriorating", '
        '"note": "<משפט קצר בעברית מה אמרה ההנהלה על שוק הקצה הזה>"}\n'
        "  ],\n"
        '  "revenue_actual_b": <הכנסות בפועל במיליארדי ' + _target_ccy + ', מספר עשרוני, או null>,\n'
        '  "revenue_estimate_b": <קונצנזוס האנליסטים להכנסות לפני הדוח, במיליארדי ' + _target_ccy + ', מספר עשרוני, או null>,\n'
        '  "eps_actual": <EPS בפועל, מספר עשרוני, או null>,\n'
        '  "eps_estimate": <קונצנזוס האנליסטים ל-EPS לפני הדוח, מספר עשרוני, או null>,\n'
        '  "currency": "' + _target_ccy + '",\n'
        '  "next_q_guidance": {\n'
        '    "revenue_b": <אמצע טווח תחזית ההכנסות שהחברה נתנה לרבעון הבא, או null>,\n'
        '    "eps": <אמצע טווח תחזית ה-EPS של החברה לרבעון הבא, או null>,\n'
        '    "analyst_revenue_b": <קונצנזוס האנליסטים להכנסות הרבעון הבא, או null>,\n'
        '    "vs_consensus": "above|inline|below|none"\n'
        "  }\n"
        "}\n\n"
        "חוקי חובה:\n"
        "1. sentiment_score: הציון משקף אך ורק את התוצאות מול הציפיות ואת כיוון ההנחיה — "
        "לא את תגובת המניה בשוק ולא את סנטימנט המשקיעים. "
        "גם אם המניה ירדה אחרי דוח חזק (או עלתה אחרי דוח חלש), התעלם מכך בציון.\n"
        "השתמש בטבלת 12 המדרגות (results_vs_expectations x guidance_direction) לקביעת הטווח:\n"
        "beat+raised: 0.8 עד 1.0 | beat+maintained: 0.5 עד 0.7 | "
        "beat+lowered: -0.2 עד 0.1 | beat+none: 0.4 עד 0.6\n"
        "meet+raised: 0.3 עד 0.5 | meet+maintained: -0.1 עד 0.2 | "
        "meet+lowered: -0.5 עד -0.3 | meet+none: -0.1 עד 0.1\n"
        "miss+raised: 0.1 עד 0.24 | miss+maintained: -0.5 עד -0.3 | "
        "miss+lowered: -1.0 עד -0.8 | miss+none: -0.6 עד -0.4\n"
        "שני צירופים נגד-אינטואיטיביים: beat+lowered = תוצאות טובות בעבר אך הנהלה מזהירה על העתיד "
        "-- ציון שלילי-קל בכוונה. miss+raised = רבעון חלש אך הנהלה מבטיחה שיפור "
        "-- חיובי-זהיר בכוונה, מתחת לסף הירוק.\n"
        "מיקום בתוך הטווח לפי גודל ההפתעה בהכנסות/EPS מול קונצנזוס: "
        "הפתעה <2% -> תחתית הטווח; 2%-10% -> אמצע; >10% -> ראש הטווח. "
        "חששות שההנהלה עצמה ציינה (אילוצי אספקה, רגולציה, הגבלות יצוא) "
        "מורידים מעט בתוך הטווח, אך לעולם לא מעבירים מדרגה.\n"
        "בנוסף, התחשב ב-vs_consensus (הנחיית הרבעון הבא מול קונצנזוס האנליסטים) "
        "כמעדן נוסף בתוך אותה מדרגה: "
        "above (הנחיה מעל הקונצנזוס) -> נטה לראש הטווח; "
        "below (הנחיה מתחת לקונצנזוס) -> נטה לתחתית הטווח; "
        "inline או none -> ללא השפעה. "
        "גם עוגן זה אינו מעביר מדרגה — המדרגה נשלטת אך ורק על ידי results x guidance.\n"
        "2. domain: חובה לבחור אך ורק מהרשימה הסגורה הבאה. אין להמציא שמות:\n"
        + domains_list + "\n"
        "3. כלול ב-domain_signals רק תחומים שהוזכרו בצורה מפורשת בשיחה. אם אין — השאר רשימה ריקה.\n"
        "4. אם לא מצאת דוח לתקופה זו, החזר: {\"error\": \"לא נמצא דוח לתקופה זו\"}\n"
        "5. כל שדה מספרי שלא נמצא במקורות — החזר null, אל תנחש. "
        "vs_consensus = השוואת תחזית ההכנסות של החברה מול קונצנזוס האנליסטים לרבעון הבא.\n"
        "6. מטבע: כל הערכים הכספיים חייבים להיות ב-" + _target_ccy + " בלבד — אין לערבב מטבעות. "
        "אם המקורות מציגים גם מקבילה בדולר (נפוץ בחברות קוריאניות, טייוואניות ויפניות) — התעלם ממנה. "
        "revenue_actual_b / revenue_estimate_b / next_q_guidance.revenue_b / next_q_guidance.analyst_revenue_b — "
        "הם במיליארדים של " + _target_ccy + ". לדוגמה: הכנסות 133.87 טריליון וון → revenue_actual_b: 133870. "
        "eps_actual / eps_estimate / next_q_guidance.eps — ערך למניה ב-" + _target_ccy + " ללא המרת סדר גודל. "
        "currency חייב להיות \"" + _target_ccy + "\"."
    )

    try:
        text, _ = _gemini_call(prompt, temperature=EARNINGS_TEMPERATURE)
    except GeminiError:
        return None
    if not text:
        return None
    # מחלץ JSON מהתשובה (Gemini עלול להוסיף טקסט לפני/אחרי)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


_COMPANY_DESC = {
    "TSEM": "Tower Semiconductor — foundry ישראלי לשבבים אנלוגיים, RF ומיוחדים",
    "NVMI": "Nova — ציוד מדידה ובקרת תהליכים (process control & metrology)",
    "CAMT": "Camtek — ציוד בדיקה ומדידה לאריזה מתקדמת",
    "ASML": "ASML — מונופול ציוד הליתוגרפיה (EUV/DUV); שסתום צוואר הבקבוק של ייצור שבבים מתקדמים",
    "AMAT": "Applied Materials — ציוד הפקדה (deposition) ואיטום; מוביל שוק ה-CVD/PVD",
    "LRCX": "Lam Research — ציוד חריטה (etch) ועיבוד ווייפרים",
    "KLAC": "KLA — ציוד בקרת תהליכים (process control & metrology); מוביל ה-inspection",
    "NVDA": "NVIDIA — מעבדי GPU לאימון והסקה של AI; מוביל שוק מרכזי הנתונים",
    "AMD": "AMD — מעבדי CPU ו-GPU למחשוב ומרכזי נתונים; מתחרה עיקרי של NVDA ו-INTC",
    "TSM": "TSMC — גדולת ה-foundries בעולם; מייצרת שבבים ל-Apple, NVDA, AMD ועוד",
    "INTC": "Intel — יצרן מעבדים משולב (IDM); בתהליך מיצוב מחדש כ-foundry",
    "MU": "Micron — יצרן זיכרון DRAM/NAND/HBM; לקוח גדול של ASML ו-AMAT",
    "TXN": "Texas Instruments — שבבים אנלוגיים ומשובצים; חשיפה לאוטומציה ורכב",
    "ADI": "Analog Devices — שבבים אנלוגיים ומעורב-אות; תעשייה, בריאות ורכב",
    "AVGO": "Broadcom — שבבי תקשורת ו-ASIC מותאמים; הרשתות ו-AI custom chips",
    "QCOM": "Qualcomm — SoC לסמארטפונים ו-IoT; חשיפה גוברת לרכב ו-AI edge",
    "MRVL": "Marvell — שבבי תשתית ורשתות; מנוע AI custom silicon בצמיחה",
    "ARM": "Arm Holdings — ארכיטקטורת CPU מורשת; רוב שבבי הסמארטפון והשרת בנויים על IP שלה",
    "MSFT": "Microsoft — ענקית תוכנה וענן (Azure), לקוחה מרכזית של NVDA ו-AMD לתשתיות AI",
    "META": "Meta Platforms — רשתות חברתיות, משקיעה עצומה בתשתיות AI ומרכזי נתונים",
    "GOOGL": "Alphabet/Google — מנוע חיפוש, ענן (GCP) ו-AI; מפתחת שבבי TPU מקוריים",
    "AMZN": "Amazon — ענן AWS ומסחר אלקטרוני; הלקוחה הגדולה ביותר של תשתיות GPU",
    "ORCL": "Oracle — תוכנה ארגונית ותשתיות ענן (OCI); צומחת מהר בהשכרת תשתיות AI",
    "005930.KS": "Samsung Electronics — יצרן זיכרון DRAM/NAND/HBM וגם מפעילה foundry לייצור לוגיקה",
    "000660.KS": "SK Hynix — יצרן זיכרון DRAM/NAND/HBM; ספק HBM מרכזי ל-NVDA",
}


def gemini_israeli_impact(il_symbol, season, context_text):
    """ניתוח השפעת דוחות שפורסמו בעונה על חברה ישראלית ספציפית."""
    desc = _COMPANY_DESC.get(il_symbol, il_symbol)
    prompt = (
        "עונת הדוחות " + season + ".\n"
        "הדוחות הבאים פורסמו עד כה בסקטור השבבים:\n"
        + context_text + "\n\n"
        "בהתבסס על הסיגנלים שעלו מהדוחות לעיל, וחיפוש ברשת למידע עדכני נוסף, "
        "נתח את ההשפעה הצפויה על " + il_symbol + " (" + desc + ").\n"
        "ענה בעברית, 4-5 משפטים: אילו סיגנלים מהדוחות רלוונטיים ל-" + il_symbol + ", "
        "מה חיובי ומה שלילי, ומה הציפיות לדוח של " + il_symbol + " בעונה זו."
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ctx_hash = hashlib.md5(context_text.encode("utf-8")).hexdigest()[:8]
    cache_key = "il_impact|" + il_symbol + "|" + season + "|" + day + "|" + ctx_hash
    return _gemini_cached_safe(cache_key, prompt, 86400)


def gemini_focused_impact(source_sym, target_sym, season, source_record):
    """ניתוח ממוקד: כיצד דוח חברה אחת משפיע על חברה ספציפית אחרת."""
    src_desc = _COMPANY_DESC.get(source_sym, source_sym)
    tgt_desc = _COMPANY_DESC.get(target_sym, target_sym)
    sc = source_record.get("sentiment_score", 0) or 0
    sc_pct = ("+" if sc >= 0 else "") + str(int(round(sc * 100))) + "%"
    sm = source_record.get("summary", "")
    gd = source_record.get("guidance_direction", "")
    res = source_record.get("results_vs_expectations", "")
    signals = source_record.get("domain_signals", [])
    sig_lines = "\n".join(
        "  • " + s.get("domain", "") + " [" + s.get("direction", "") + "]: " + s.get("note", "")
        for s in signals
    ) if signals else "  אין סיגנלים תחומיים שמורים."
    prompt = (
        "עונת הדוחות " + season + ".\n"
        "להלן סיכום דוח " + source_sym + " (" + src_desc + "):\n"
        "• סנטימנט: " + sc_pct +
        (", תוצאות: " + res if res and res != "none" else "") +
        (", הנחיה: " + gd if gd and gd != "none" else "") + "\n" +
        ("• סיכום: " + sm + "\n" if sm else "") +
        "• סיגנלים תחומיים:\n" + sig_lines + "\n\n"
        "בהתבסס על הדוח לעיל וחיפוש ברשת למידע עדכני, "
        "נתח ספציפית את ההשפעה הצפויה על " + target_sym + " (" + tgt_desc + ").\n"
        "התייחס במפורש לסיגנלים התחומיים שהוזכרו — אילו מהם רלוונטיים ישירות לעסקי " + target_sym + ", "
        "מה מרמז זאת על הביקוש למוצריה ושירותיה, ומה ההשלכה על הדוח הצפוי שלה. "
        "ענה בעברית, 4-5 משפטים."
    )
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rec_hash = hashlib.md5((source_sym + season + str(sc) + sm[:50]).encode("utf-8")).hexdigest()[:8]
    cache_key = "focused|" + source_sym + "|" + target_sym + "|" + season + "|" + day + "|" + rec_hash
    return _gemini_cached_safe(cache_key, prompt, 86400)


# ======================================================
# סנטימנט דוחות ושיחות ועידה — שכבת נתונים
# ======================================================
SENTIMENT_FILE = "earnings_sentiment.json"
EARNINGS_CALENDAR_FILE = "earnings_calendar.json"


def _load_ecal_data():
    """טוען earnings_calendar.json → dict עם מקטעים. תומך בפורמט ישן (רשימה). None בשגיאה."""
    try:
        with open(EARNINGS_CALENDAR_FILE, "r", encoding="utf-8") as _fh:
            _raw = json.load(_fh)
        if isinstance(_raw, list):
            return {"earnings_calendar": _raw, "ratings": {}, "earnings_history": {}}
        return _raw
    except Exception:
        return None


def season_from_date(d):
    """עונת דוחות = הרבעון שעליו מדווחים (לא רבעון הפרסום).
    חלון הדיווח על רבעון N נפתח ~3 שבועות לפני תום רבעון N+1
    ונמשך עד לפתיחת החלון הבא."""
    if isinstance(d, str):
        d = datetime.fromisoformat(d[:10])
    shifted = d + timedelta(days=SEASON_EARLY_DAYS)
    q = (shifted.month - 1) // 3 + 1
    y = shifted.year
    q -= 1                      # התווית = הרבעון המדווח
    if q == 0:
        q, y = 4, y - 1
    return str(y) + "Q" + str(q)


def current_season():
    return season_from_date(datetime.now(timezone.utc))


def latest_season_with_data(sentiment):
    """העונה האחרונה שיש בה לפחות רשומה אחת. אם הקובץ ריק — current_season().
    מיון לקסיקוגרפי עובד כי הפורמט YYYYQN שומר על סדר כרונולוגי."""
    all_seasons = set()
    for sym_data in sentiment.values():
        all_seasons.update(sym_data.keys())
    if not all_seasons:
        return current_season()
    return sorted(all_seasons)[-1]


def _season_lag(sentiment):
    """מחזיר (data_season, cur_season, lagging) לתצוגת תגית מצב עונה.
    lagging=True כשהעונה הקלנדרית מתקדמת מהעונה שיש בה נתונים."""
    data_s = latest_season_with_data(sentiment)
    cur_s = current_season()
    return data_s, cur_s, cur_s > data_s


def load_sentiment():
    """טוען את קובץ הסנטימנט. מבנה: {symbol: {season: record}}. אין קובץ -> {}.
    לא ממוטמן בכוונה, כדי שכתיבה חדשה תשתקף מיד."""
    try:
        with open(SENTIMENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_sentiment_record(sym, season, record):
    """כותב/מעדכן רשומה אחת. עובד מקומית; ב-Streamlit Cloud לא ישרוד restart,
    ואז מעתיקים ידנית ודוחפים ל-git (בדיוק כמו CAPEX_GUIDANCE)."""
    data = load_sentiment()
    data.setdefault(sym, {})[season] = record
    with open(SENTIMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_record(sentiment, sym, season):
    return sentiment.get(sym, {}).get(season)


def aggregate_sentiment(weighted_symbols, season, sentiment=None):
    """סנטימנט משוקלל של תחום בעונה נתונה.
    weighted_symbols = {symbol: weight}. מחזיר ציון משוקלל, כיסוי ופירוט,
    או None אם אף חברה בתחום לא דיווחה בעונה הזו.
    כיסוי = כמה מתוך חברות התחום כבר יש להן רשומה בעונה."""
    if sentiment is None:
        sentiment = load_sentiment()
    rows = []
    wsum = 0.0
    wtot = 0.0
    for sym, w in weighted_symbols.items():
        rec = get_record(sentiment, sym, season)
        if rec is None or rec.get("sentiment_score") is None:
            continue
        score = float(rec["sentiment_score"])
        wsum += score * w
        wtot += w
        rows.append((sym, score, rec.get("guidance_direction"),
                     rec.get("results_vs_expectations")))
    if wtot == 0:
        return None
    return {
        "score": wsum / wtot,
        "reported": len(rows),
        "total": len(weighted_symbols),
        "rows": sorted(rows, key=lambda x: x[1], reverse=True),
    }


def value_chain_sentiment(sector, season, sentiment=None):
    # שרשרת הערך: ממוצע פשוט, כל מניה במשקל שווה
    symbols = {s: 1.0 for s in value_chain[sector]}
    return aggregate_sentiment(symbols, season, sentiment)


def tech_group_sentiment(group_def, season, sentiment=None):
    # פילוח טכנולוגי: אותו משקל כמו התשואה — חשיפה × מכפיל שכבה
    symbols = {}
    for s, exp in group_def.get("core", {}).items():
        symbols[s] = exp * TIER_CORE
    for s, exp in group_def.get("env", {}).items():
        symbols[s] = symbols.get(s, 0.0) + exp * TIER_ENV
    return aggregate_sentiment(symbols, season, sentiment)


def domain_signal_score(group_name, season, sentiment_data):
    """ציון סיגנלים תחומיים: ממוצע improving(+1)/stable(0)/deteriorating(-1)
    מכל החברות שציינו את group_name בעונה. מחזיר (score, count) או (None, 0)."""
    _dir_val = {"improving": 1.0, "stable": 0.0, "deteriorating": -1.0}
    vals = []
    for sym_data in sentiment_data.values():
        rec = sym_data.get(season)
        if not rec:
            continue
        for sig in rec.get("domain_signals", []):
            if sig.get("domain") == group_name:
                vals.append(_dir_val.get(sig.get("direction", "stable"), 0.0))
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


def weighted_tech_score(group_name, group_def, season, sentiment_data):
    """ציון משוקלל סופי לתחום טכנולוגי: סנטימנט חברות + סיגנלים תחומיים.
    משקל הסיגנלים דועך ליניארית: 0% לאפס סיגנלים → SIG_WEIGHT_MAX כשיש ≥ SIG_FULL_COUNT.
    מחזיר dict עם score ורכיביו, או None אם אין נתונים כלל."""
    comp_agg = tech_group_sentiment(group_def, season, sentiment_data)
    sig_score, sig_count = domain_signal_score(group_name, season, sentiment_data)
    if comp_agg is None and sig_score is None:
        return None
    comp_score = comp_agg["score"] if comp_agg else None
    sig_weight = SIG_WEIGHT_MAX * min(sig_count / SIG_FULL_COUNT, 1.0)
    if comp_score is not None and sig_score is not None:
        final = (1 - sig_weight) * comp_score + sig_weight * sig_score
    elif comp_score is not None:
        final = comp_score
        sig_weight = 0.0
    else:
        final = sig_score
        sig_weight = 1.0
    return {
        "score": final,
        "comp_score": comp_score,
        "comp_reported": comp_agg["reported"] if comp_agg else 0,
        "comp_total": comp_agg["total"] if comp_agg else 0,
        "sig_score": sig_score,
        "sig_count": sig_count,
        "sig_weight": sig_weight,
    }


def titles_signature(titles):
    joined = "||".join(titles)
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def build_chart(stocks, period, intraday=False, skip_current_day=True):
    series_list = []
    for symbol in stocks:
        if intraday:
            close, _prev, _ = get_last_session_intraday(symbol, skip_current_day)
        else:
            close = get_history(symbol, period)
            if close is not None and len(close) >= 2:
                _ai, _ = _anchor_index(close, period, close.index[-1].date())
                close = close.iloc[_ai:]
        if close is None:
            continue
        clean = close.dropna()
        if len(clean) < 2:
            continue  # אין מספיק נתונים — לא נכניס עמודה ריקה למקרא
        # נרמול לפי הערך התקין הראשון של אותה מניה
        normalized = clean / clean.iloc[0] * 100
        normalized.name = symbol
        # נרמול timezone ל-UTC: מניות קוריאניות (005930.KS) חוזרות ב-Asia/Seoul,
        # ארה"ב ב-America/New_York — pd.concat על אינדקסים עם tz שונה מייצר object index
        # ושובר את interpolate(method="time"). כל הסדרות מומרות ל-UTC לפני האיחוד.
        if normalized.index.tz is not None:
            normalized.index = normalized.index.tz_convert("UTC")
        series_list.append(normalized)

    if len(series_list) == 0:
        return pd.DataFrame()

    chart_data = pd.concat(series_list, axis=1).sort_index()
    # אינטרפולציה לינארית מבוססת-זמן בין נקודות מסחר אמיתיות.
    # פותר מראה מדורג כשבורסות עם לוח מסחר שונה (קוריאה מול ארה"ב)
    # ממוזגות לאותו ציר — במקום ffill שמקפיא ואז קופץ.
    try:
        chart_data = chart_data.interpolate(method="time", limit_direction="both")
    except Exception:
        return pd.DataFrame()
    chart_data = chart_data.dropna(axis=1, how="all")
    if chart_data.index.tz is not None:
        chart_data.index = chart_data.index.tz_convert("America/New_York")
    return chart_data


def build_spread_chart(stocks, period, intraday=False, skip_current_day=True):
    # גרף פער מצטבר: חציון התחום (מנורמל ל-100) פחות SOXX (מנורמל ל-100), לאורך התקופה
    # אזור צבוע: ירוק כשהתחום מכה את המדד, אדום כשמפגר
    chart_data = build_chart(stocks, period, intraday=intraday, skip_current_day=skip_current_day)
    if chart_data.empty:
        return None
    if intraday:
        soxx_close, _, _ = get_last_session_intraday(BENCHMARK, skip_current_day)
    else:
        soxx_close = get_history(BENCHMARK, period)
        if soxx_close is not None and len(soxx_close) >= 2:
            _ai_s, _ = _anchor_index(soxx_close, period, soxx_close.index[-1].date())
            soxx_close = soxx_close.iloc[_ai_s:]
    if soxx_close is None:
        return None

    median_series = chart_data.median(axis=1)
    soxx_norm = soxx_close / soxx_close.iloc[0] * 100
    if soxx_norm.index.tz is not None:
        soxx_norm.index = soxx_norm.index.tz_convert("UTC")
    # מיישרים את שני האינדקסים לאותם תאריכים
    df = pd.DataFrame({"median": median_series, "soxx": soxx_norm}).dropna()
    if len(df) < 2:
        return None
    df["spread"] = df["median"] - df["soxx"]
    if df.index.tz is not None:
        df.index = df.index.tz_convert("America/New_York")
    df = df.reset_index()
    date_col = df.columns[0]
    df = df.rename(columns={date_col: "תאריך"})

    # --- החדרת נקודות חצייה של האפס ---
    # בכל מקום שבו הפער עובר מחיובי לשלילי (או להפך) בין שתי נקודות,
    # מחשבים את התאריך המדויק שבו הוא שווה 0 ומכניסים שם נקודת ביניים.
    # כך המילוי הירוק/אדום נחתך בדיוק על קו האפס, בלי משולשים בצבע הלא נכון.
    rows = []
    for i in range(len(df)):
        rows.append({"תאריך": df["תאריך"].iloc[i], "spread": df["spread"].iloc[i]})
        if i < len(df) - 1:
            y1 = df["spread"].iloc[i]
            y2 = df["spread"].iloc[i + 1]
            if (y1 > 0 and y2 < 0) or (y1 < 0 and y2 > 0):
                t1 = df["תאריך"].iloc[i]
                t2 = df["תאריך"].iloc[i + 1]
                # אינטרפולציה ליניארית של רגע החצייה
                frac = abs(y1) / (abs(y1) + abs(y2))
                t_cross = t1 + (t2 - t1) * frac
                rows.append({"תאריך": t_cross, "spread": 0.0})
    df = pd.DataFrame(rows)

    # שתי עמודות נפרדות: אחת רק לערכים החיוביים, אחת רק לשליליים.
    # מחוץ לתחום כל אחת מקבלת 0, כך שהמילוי לא "גולש" מעבר לקו האפס.
    df["pos"] = df["spread"].clip(lower=0)
    df["neg"] = df["spread"].clip(upper=0)

    _x_axis_kw = dict(labelFontSize=12, labelPadding=8, tickCount=6)
    if intraday:
        _x_axis_kw["format"] = "%H:%M"
    base = alt.Chart(df).encode(
        x=alt.X("תאריך:T", title=None, axis=alt.Axis(**_x_axis_kw))
    )
    area_pos = base.mark_area(color="rgba(34,197,94,0.35)").encode(
        y=alt.Y("pos:Q", title="פער מ-SOXX (נק')",
                axis=alt.Axis(labelFontSize=12, titleFontSize=13, titlePadding=10)))
    area_neg = base.mark_area(color="rgba(239,68,68,0.35)").encode(y="neg:Q")
    line = base.mark_line(strokeWidth=2.5, color="#e5e7eb").encode(y="spread:Q")
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        strokeDash=[3, 3], color="#888", strokeWidth=1.5
    ).encode(y="y:Q")
    return (area_pos + area_neg + line + zero).properties(
        height=260, padding={"top": 10, "bottom": 10, "left": 10, "right": 20}
    )


CORR_MIN_POINTS = 10   # מינימום נקודות תשואה יומית לחוליה כדי להיכלל במטריצת הקורלציה


@st.cache_data(ttl=300)
def compute_sector_correlation(period):
    """מטריצת קורלציה (Pearson) בין תשואות יומיות של חציון הביצועים של חוליות שרשרת הערך.

    לכל חוליה: חציון הביצועים המנורמלים — אותו build_chart+median המשמש בכל מקום אחר
    באפליקציה (כולל טיפול ה-tz/אינטרפולציה הקיים למניות מבורסות אחרות, כמו .KS), ואז
    pct_change().dropna() לתשואות יומיות. חוליה עם פחות מ-CORR_MIN_POINTS תשואות מושמטת
    לגמרי (לא נכנסת כעמודת NaN שתשבור את הצביעה/הקורלציה).

    מחזיר (corr_df, dropped_sectors). corr_df ריק (columns=[]) אם פחות משתי חוליות
    תקינות — זה גם הסימן לתקופה קצרה מדי (למשל 5d), בלי צורך ברשימת תקופות קשיחה
    נפרדת: אם התקופה קצרה, כל החוליות יינשרו מהסף באופן טבעי.

    כוללת גם את SOXX עצמו כעמודה/שורה נוספת (מפתח BENCHMARK) — נקודת ייחוס,
    לא עוד חוליה: תשואות יומיות ישירות מ-get_history(BENCHMARK, period), אותה
    שיטה (pct_change().dropna()) ואותו סף CORR_MIN_POINTS, כדי שלא "יחייה"
    מטריצה בתקופה שבפועל קצרה מדי לשאר החוליות. נוסף תמיד אחרון ל-returns_map
    (סדר ה-dict נשמר ב-pd.concat) כדי לשבת בקצה המטריצה (שורה/עמודה אחרונה),
    לא משולב בין החוליות. tz של get_history (America/New_York, ישיר מ-yfinance
    למניה אמריקאית בודדת) תואם את ה-tz הסופי של build_chart — נבדק ישירות.

    לא נוגע בגרף הבטא המתגלגלת או בפונקציות הבטא — זו אגרגציה נפרדת לגמרי, לפי מחיר
    (חציון ביצועים), לא בטא מול SOXX."""
    returns_map = {}
    dropped = []
    for sector, tickers in value_chain.items():
        chart = build_chart(tickers, period, intraday=False, skip_current_day=False)
        if chart.empty:
            dropped.append(sector)
            continue
        median_series = chart.median(axis=1)
        rets = median_series.pct_change().dropna()
        if len(rets) < CORR_MIN_POINTS:
            dropped.append(sector)
            continue
        returns_map[sector] = rets

    soxx_close = get_history(BENCHMARK, period)
    if soxx_close is not None:
        soxx_rets = soxx_close.pct_change().dropna()
        if len(soxx_rets) >= CORR_MIN_POINTS:
            returns_map[BENCHMARK] = soxx_rets
        else:
            dropped.append(BENCHMARK)
    else:
        dropped.append(BENCHMARK)

    if len(returns_map) < 2:
        return pd.DataFrame(), dropped
    rets_df = pd.concat(returns_map, axis=1)
    corr_df = rets_df.corr()
    return corr_df, dropped


def clean_name(sector):
    if ". " in sector:
        return sector.split(". ", 1)[1]
    return sector


def rtl_text(s):
    """עוטף מחרוזת בתווי כיווניות Unicode לתצוגה נכונה ב-SVG של Plotly.
    Plotly מרנדר טקסט כ-SVG; CSS direction/unicode-bidi אינו נתמך שם.
    U+202B פותח הטמעת RTL, U+202C סוגר אותה."""
    return "\u202B" + s + "\u202C"


def sentiment_pct(score):
    """ממפה ציון מנוע (-1..+1) לאחוז תצוגה (0..100). 50 = ניטרלי."""
    return int(round((float(score) + 1) / 2 * 100))


def fmt_money_b(value, ccy_symbol=""):
    """מציג ערך כספי: T (טריליון) / B (מיליארד) / M (מיליון)."""
    v = float(value)
    if abs(v) >= 1000:
        return ccy_symbol + f"{v/1000:.2f}T"
    if abs(v) >= 1:
        return ccy_symbol + f"{v:.2f}B"
    return ccy_symbol + f"{v*1000:.1f}M"


def sector_key(sector_name):
    # מזהה יציב וקצר לכל תחום, לפי שמו (לא לפי מיקומו בדירוג).
    # משמש למפתחות widgets ו-session_state כדי שהמצב יישאר צמוד לתחום
    # גם כשהדירוג משתנה בעקבות החלפת תקופה.
    return hashlib.md5(sector_name.encode("utf-8")).hexdigest()[:8]


def ranking_bar_chart(items, chart_key, soxx_marker=None, debug=False):
    """גרף עמודות אופקי לחיץ לדירוג תחומים, בכיוון RTL.

    items = רשימה של (label, value) כבר ממוינת מהגבוה לנמוך.
    value = התשואה של התחום באחוזים.
    soxx_marker = ערך תשואת SOXX; אם ניתן, מצויר קו כתום בולט במיקומו.
    debug = אם True, מדפיס את מבנה אירוע הבחירה (לאבחון קליק).
    לחיצה על עמודה מחזירה את ה-label שלה (או None אם לא נלחץ כלום).

    RTL: לא הופכים את ציר ה-X (שובר on_select). עמודות חיוביות יוצאות
    ימינה, שליליות שמאלה — קו אפס באמצע. שמות בצד ימין עם automargin.
    """
    if not items:
        return None

    def transform(v):
        # שורש מוחלט לדחיסה ויזואלית, עם שמירת הסימן המקורי
        return math.copysign(math.sqrt(abs(v)), v)

    labels = [lbl for lbl, val in items]
    values = [val for lbl, val in items]
    bar_widths = [transform(v) for v in values]
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in values]
    text_labels = [("+" if v >= 0 else "") + str(round(v, 1)) + "%" for v in values]

    # סדר: הגבוה למעלה. Plotly מצייר מלמטה למעלה, אז הופכים.
    labels_r = list(reversed(labels))
    widths_r = list(reversed(bar_widths))
    colors_r = list(reversed(colors))
    texts_r = list(reversed(text_labels))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=widths_r, y=labels_r, orientation="h",
        marker=dict(color=colors_r, line=dict(width=0)),
        text=texts_r, textposition="outside",
        textfont=dict(size=13, color="#e5e7eb"),
        hoverinfo="skip", hovertemplate=None,
        cliponaxis=False,
    ))
    # קו אפס — מפריד אמיתי בין אזור חיובי לשלילי
    fig.add_vline(x=0, line_width=2, line_color="rgba(255,255,255,0.45)")

    # ריפוד נפרד לכל צד לפי הקצה האמיתי שלו —
    # מונע ריק מוגזם כשצד חיובי קצר בהרבה מהשלילי (או להיפך)
    max_pos = max((w for w in widths_r if w > 0), default=0.0)
    max_neg = max((-w for w in widths_r if w < 0), default=0.0)

    # קו SOXX בולט: כתום עבה ומקווקו במיקום תשואת המדד, עם תווית מודגשת בתיבה
    if soxx_marker is not None:
        soxx_x = transform(soxx_marker)
        if soxx_x >= 0:
            max_pos = max(max_pos, soxx_x)
        else:
            max_neg = max(max_neg, -soxx_x)
        fig.add_vline(
            x=soxx_x, line_width=4, line_color="#f59e0b", line_dash="dash",
        )
        fig.add_annotation(
            x=soxx_x, y=1.0, yref="paper", yanchor="bottom",
            text="<b>SOXX " + ("+" if soxx_marker >= 0 else "") + str(round(soxx_marker, 1)) + "%</b>",
            showarrow=False, font=dict(size=15, color="#000000"),
            bgcolor="#f59e0b", bordercolor="#f59e0b", borderpad=4,
            xanchor="center", yshift=6,
        )

    left_pad = max(max_neg, 0.5) * 0.38
    right_pad = max(max_pos, 0.5) * 0.35
    row_h = 40
    top_margin = 34 if soxx_marker is not None else 8
    chart_h = max(len(labels) * row_h + 30 + top_margin, 120)
    fig.update_layout(
        height=chart_h, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=top_margin, b=12, l=20, r=20),
        showlegend=False, bargap=0.42,
        hovermode=False,
        xaxis=dict(visible=False, showgrid=False, zeroline=False,
                   range=[-(max_neg + left_pad), max_pos + right_pad]),
        yaxis=dict(showgrid=False, side="right", automargin=True,
                   tickfont=dict(size=13, color="#d1d5db")),
    )

    event = st.plotly_chart(
        fig, width='stretch', key=chart_key,
        on_select="rerun", selection_mode="points",
    )

    # בלוק דיבאג זמני: מציג את מבנה אירוע הבחירה כדי לאבחן את הקליק
    if debug:
        st.caption("🔧 דיבאג — מבנה אירוע הבחירה (זמני):")
        st.write({"type": str(type(event)), "event": event})

    # חילוץ התחום שנלחץ — חסין למספר מבנים אפשריים של האירוע
    try:
        sel = None
        if isinstance(event, dict):
            sel = event.get("selection")
        else:
            sel = getattr(event, "selection", None)
        if sel is not None:
            points = sel["points"] if isinstance(sel, dict) else getattr(sel, "points", None)
            if points:
                p0 = points[0]
                # התווית יכולה לחזור תחת 'y' (קטגוריה) או 'label'
                if isinstance(p0, dict):
                    return p0.get("y") or p0.get("label")
                return getattr(p0, "y", None)
    except (KeyError, TypeError, IndexError, AttributeError):
        pass
    return None


def section_banner(number, total, icon, title, color, subtitle="", period_dependent=None, period_label=""):
    """באנר גדול ובולט לתחילת אזור ראשי בדשבורד.
    period_dependent=True  → תגית 🕐 מגיב לתקופה
    period_dependent=False → תגית 📌 נתונים עצמאיים
    period_dependent=None  → ללא תגית (תאימות לאחור)"""
    sub_html = ""
    if subtitle:
        sub_html = ("<div style='font-size:14px; color:rgba(255,255,255,0.75); "
                    "margin-top:4px; font-weight:400;'>" + subtitle + "</div>")
    if period_dependent is True:
        period_tag = ("<span style='font-size:11px; color:#fbbf24; font-weight:600; "
                      "background:rgba(251,191,36,0.12); padding:2px 8px; border-radius:20px; "
                      "border:1px solid rgba(251,191,36,0.3);'>"
                      "🕐 מגיב לתקופה: " + period_label + "</span>")
    elif period_dependent is False:
        period_tag = ("<span style='font-size:11px; color:#6b7280; font-weight:600; "
                      "background:rgba(107,114,128,0.12); padding:2px 8px; border-radius:20px; "
                      "border:1px solid rgba(107,114,128,0.3);'>"
                      "📌 נתונים עצמאיים</span>")
    else:
        period_tag = ""
    st.markdown(
        "<div id='zone-" + str(number) + "' style='height:36px;'></div>"
        "<div dir='rtl' style='text-align:right; background:linear-gradient(90deg, " + color + "22, transparent); "
        "border-right:8px solid " + color + "; border-radius:10px; "
        "padding:16px 20px; margin-bottom:18px;'>"
        "<div style='display:flex; align-items:center; justify-content:space-between;'>"
        "<span style='font-size:24px; font-weight:800; color:#ffffff;'>" + icon + "&nbsp; " + title + "</span>"
        "<span style='font-size:13px; color:rgba(255,255,255,0.45); font-weight:600; "
        "background:rgba(255,255,255,0.06); padding:3px 10px; border-radius:20px;'>"
        "אזור " + str(number) + "/" + str(total) + "</span>"
        "</div>"
        + sub_html
        + (("<div style='margin-top:6px;'>" + period_tag + "</div>") if period_tag else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def _fetch_logo_b64_raw(domain):
    """משיכת favicon ללא קאש — נקראת מתוך threads בלבד."""
    import base64, urllib.request
    url = (
        "https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON"
        "&fallback_opts=TYPE,SIZE,URL&url=https://" + domain + "&size=64"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=4).read()
        if not data or len(data) < 80:
            return None
        return base64.b64encode(data).decode()
    except Exception:
        return None


@st.cache_data(ttl=604800, show_spinner=False)
def fetch_logo_b64(domain):
    """מושך favicon דרך Google faviconV2 ומחזיר base64, או None בכישלון."""
    return _fetch_logo_b64_raw(domain)


@st.cache_data(ttl=604800, show_spinner=False)
def warm_all_logos(domains_tuple):
    """מחמם את כל הלוגואים במקביל; תוצאה ממוטמנת שבוע."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(_fetch_logo_b64_raw, domains_tuple))
    return dict(zip(domains_tuple, results))


def chain_logo_html(ticker, logo_cache):
    """מחזיר <img> עם data-URI base64 או מונוגרמה — ללא JS, ללא בקשות חיצוניות."""
    domain = CHAIN_LOGO_DOMAINS.get(ticker)
    b64 = logo_cache.get(domain) if domain else None
    if b64:
        return (
            "<img src='data:image/png;base64," + b64 + "'"
            " style='width:18px;height:18px;border-radius:50%;"
            "object-fit:contain;background:#fff;flex:none;' alt=''/>"
        )
    letter = ticker[0] if ticker and ticker[0].isalpha() else "?"
    return (
        "<span style='display:inline-flex;width:18px;height:18px;"
        "border-radius:50%;background:#374151;color:#e5e7eb;"
        "align-items:center;justify-content:center;font-size:11px;"
        "font-weight:700;flex:none;'>" + letter + "</span>"
    )


def capex_guidance_delta():
    """מחשב שינוי מצרפי בתחזית CAPEX: (prev, last, pct, n) או None."""
    pairs = []
    for sym, data in CAPEX_GUIDANCE.items():
        vals = [v for _, v in data.get("updates", []) if v is not None]
        if len(vals) >= 2:
            pairs.append((vals[-2], vals[-1]))
    if not pairs:
        return None
    total_prev = sum(p for p, _ in pairs)
    total_last = sum(l for _, l in pairs)
    if total_prev == 0:
        return None
    pct = (total_last - total_prev) / total_prev * 100
    return (total_prev, total_last, pct, len(pairs))


def render_chain_map(period, mode="perf"):
    """מפת שרשרת הערך — 3 שורות + פסי חיבור, ביצועים חיים."""
    _logo_cache = warm_all_logos(tuple(sorted(set(CHAIN_LOGO_DOMAINS.values()))))

    # --- ביצועים לכל תחום ---
    perf = {}
    for key, tickers in value_chain.items():
        prefix = key.split(".")[0]
        pairs = get_changes(tickers, period)
        perf[prefix] = statistics.median(v for _, v in pairs) if pairs else None

    _is_sens = (mode == "sensitivity")
    _delta = capex_guidance_delta()
    _warn_capex = bool(_delta and _delta[2] < 0)

    def perf_tag(prefix):
        v = perf.get(prefix)
        if v is None:
            return "<span style='font-size:11px; color:#6b7280; background:rgba(107,114,128,0.15); padding:1px 7px; border-radius:12px;'>—</span>"
        color = "#22c55e" if v >= 0 else "#ef4444"
        bg    = "rgba(34,197,94,0.15)" if v >= 0 else "rgba(239,68,68,0.15)"
        sign  = "+" if v > 0 else ""
        return ("<span style='font-size:11px; color:" + color + "; background:" + bg +
                "; padding:1px 7px; border-radius:12px; font-weight:700;'>"
                + sign + str(round(v, 1)) + "%</span>")

    def card_border(prefix):
        if _is_sens:
            lvl = CAPEX_SENSITIVITY.get(prefix, {}).get("level", "med")
            color = SENSITIVITY_LEVELS[lvl]["color"]
            return "2px solid " + color
        v = perf.get(prefix)
        if v is None:
            return "1px solid rgba(255,255,255,0.08)"
        return ("2.5px solid #22c55e" if v >= 0 else "2.5px solid #ef4444")

    def sens_tag(prefix):
        s = CAPEX_SENSITIVITY.get(prefix, {})
        lvl = s.get("level", "med")
        info = SENSITIVITY_LEVELS[lvl]
        timing = s.get("timing", "")
        mech = s.get("mechanism", "")
        warn_badge = " ⚠️" if (_warn_capex and lvl in ("vhigh", "high")) else ""
        tip = (
            "<div class='sens-tip' dir='rtl'>"
            "<span style='font-weight:700; color:" + info["color"] + ";'>רגישות: " + info["label"] + "</span><br>"
            "⏱ עיתוי פגיעת הרווח: " + timing + "<br>"
            "<span style='color:#9ca3af;'>" + mech + "</span>"
            "</div>"
        )
        return (
            "<span class='sens-tag'>"
            "<span style='font-size:11px; color:" + info["color"] + "; background:rgba(255,255,255,0.08);"
            " padding:1px 7px; border-radius:12px; font-weight:700; cursor:default;'>"
            + info["emoji"] + " " + info["label"] + warn_badge +
            "</span>"
            + tip +
            "</span>"
        )

    def pill_ring(t):
        is_il = t in ISRAELI_TICKERS
        is_ph = t in PHOTONICS_TICKERS
        if is_il and is_ph:
            return " box-shadow:0 0 0 2px #3b82f6, 0 0 0 5px #eab308, 0 0 7px 2px rgba(234,179,8,0.6); border-color:transparent;"
        if is_il:
            return " box-shadow:0 0 0 2px #3b82f6, 0 0 5px 1px rgba(59,130,246,.55); border-color:transparent;"
        if is_ph:
            return " box-shadow:0 0 0 2px #eab308, 0 0 5px 1px rgba(234,179,8,.6); border-color:transparent;"
        return ""

    def build_pills(tickers):
        pills = ""
        for t in tickers:
            logo = chain_logo_html(t, _logo_cache)
            ring = pill_ring(t)
            pills += (
                "<span style='display:inline-flex; align-items:center; gap:3px;"
                " background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.10);"
                " border-radius:20px; padding:2px 7px 2px 4px; font-size:11px; color:#d1d5db;" + ring + "'>"
                + logo + "&nbsp;" + t + "</span>"
            )
        return pills

    def _card_tag(prefix):
        if _is_sens:
            return sens_tag(prefix)
        lvl = CAPEX_SENSITIVITY.get(prefix, {}).get("level", "med")
        warn = ("<span style='font-size:10px;'> ⚠️</span>"
                if (_warn_capex and lvl in ("vhigh", "high")) else "")
        return perf_tag(prefix) + warn

    def card(prefix, subtitle, extra_style="", badge=""):
        key = next((k for k in value_chain if k.startswith(prefix + ".")), None)
        if key is None:
            return ""
        name = clean_name(key)
        bc = card_border(prefix)
        pills = build_pills(value_chain[key])
        return (
            "<div style='background:#141824; border:" + bc + "; border-radius:12px;"
            " padding:12px 14px; overflow:visible; " + extra_style + "'>"
            "<div style='display:flex; align-items:center; gap:6px; margin-bottom:4px; flex-wrap:wrap; overflow:visible;'>"
            "<span style='font-size:13px; font-weight:700; color:#f3f4f6;'>" + name + "</span>"
            + (badge if badge else "")
            + _card_tag(prefix) +
            "</div>"
            "<div style='font-size:11px; color:#6b7280; margin-bottom:8px;'>" + subtitle + "</div>"
            "<div style='display:flex; flex-wrap:wrap; gap:4px; overflow:visible;'>" + pills + "</div>"
            "</div>"
        )

    def connector_v(label):
        return (
            "<div style='display:flex; flex-direction:column; align-items:center;"
            " justify-content:center; color:#9ca3af; font-size:12px; padding:4px 0; gap:2px;'>"
            "<span style='border-right:2px dashed #4b5563; height:20px; width:0;'></span>"
            "<span style='font-size:15px; color:#6b7280;'>▼</span>"
            "<span style='text-align:center; color:#d1d5db; font-size:12px;'>" + label + "</span>"
            "</div>"
        )

    def connector_h(label):
        return (
            "<div style='display:flex; flex-direction:column; align-items:center;"
            " justify-content:center; color:#9ca3af; font-size:11px; padding:0 2px; min-width:40px;'>"
            "<span style='border-bottom:2px dashed #4b5563; width:100%; margin-bottom:4px;'></span>"
            "<span style='font-size:14px; color:#6b7280;'>◀</span>"
            "<span style='white-space:nowrap; color:#d1d5db;'>" + label + "</span>"
            "</div>"
        )

    # --- מקרא (מותנה במצב) ---
    if _is_sens:
        legend = (
            "<div dir='rtl' style='display:flex; flex-wrap:wrap; gap:14px; align-items:center;"
            " font-size:11px; color:#9ca3af; margin-bottom:14px; padding:8px 12px;"
            " background:rgba(255,255,255,0.03); border-radius:8px; border:1px solid rgba(255,255,255,0.07);'>"
            "<span style='font-weight:700; color:#d1d5db;'>רגישות CAPEX:</span>"
        )
        for lvl_key in ("vhigh", "high", "med", "low"):
            info = SENSITIVITY_LEVELS[lvl_key]
            legend += (
                "<span style='display:inline-flex; align-items:center; gap:4px;'>"
                "<span style='font-size:13px;'>" + info["emoji"] + "</span>"
                "<span style='color:" + info["color"] + "; font-weight:700;'>" + info["label"] + "</span>"
                "</span>"
            )
        legend += (
            "<span style='color:#6b7280;'>| ריחוף על הכרטיס לפרטים</span>"
            "<span style='display:block; width:100%; color:#6b7280; margin-top:4px;'>"
            "המניות מגיבות מיד בכל החוליות — העיתוי מתייחס לפגיעה בדוחות</span>"
            "</div>"
        )
    else:
        legend = (
            "<div dir='rtl' style='display:flex; flex-wrap:wrap; gap:14px; align-items:center;"
            " font-size:11px; color:#9ca3af; margin-bottom:14px; padding:8px 12px;"
            " background:rgba(255,255,255,0.03); border-radius:8px; border:1px solid rgba(255,255,255,0.07);'>"
            "<span style='font-weight:700; color:#d1d5db;'>מקרא:</span>"
            "<span style='display:inline-flex; align-items:center; gap:6px;'>"
            "<span style='display:inline-flex; width:14px; height:14px; border-radius:50%; flex-shrink:0;"
            " box-shadow:0 0 0 2px #eab308, 0 0 5px 1px rgba(234,179,8,.6);'></span>"
            "נוגע בציר הפוטוניקה</span>"
            "<span style='display:inline-flex; align-items:center; gap:6px;'>"
            "<span style='display:inline-flex; width:14px; height:14px; border-radius:50%; flex-shrink:0;"
            " box-shadow:0 0 0 2px #3b82f6, 0 0 5px 1px rgba(59,130,246,.55);'></span>"
            "חברה ישראלית</span>"
            "<span>| מסגרת ירוקה = ביצועי יתר · אדומה = ביצועי חסר</span>"
            "</div>"
        )

    warn_banner = ""
    if _delta and _delta[2] < 0:
        x_pct = abs(round(_delta[2], 1))
        n_cos = _delta[3]
        warn_banner = (
            "<div dir='rtl' style='background:rgba(239,68,68,0.10); border:1px solid rgba(239,68,68,0.40);"
            " border-radius:8px; padding:10px 14px; margin-bottom:10px; font-size:12px; color:#fca5a5;'>"
            "⚠️ תחזית ה-CAPEX המצרפית ירדה ב-" + str(x_pct) + "% בעדכון האחרון (" + str(n_cos) + " חברות)"
            " — החוליות בדרגת רגישות גבוהה ומעלה מסומנות"
            "</div>"
        )

    # --- שורה עליונה ---
    row_top = (
        "<div style='display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:0;'>"
        + card("1", "כלי EDA, IP-blocks, ארכיטקטורות")
        + card("6", "מכונות פוטוליתוגרפיה, אצ'ינג, הפקדה")
        + card("7", "מדידה, יישור ובקרת תהליכים")
        + card("0", "ווייפרים, גזים, נוזלי עיבוד")
        + "</div>"
    )

    conn1 = (
        "<div style='display:grid; grid-template-columns:1fr 3fr; gap:10px; margin:8px 0;'>"
        + connector_v("כלי תכנון ורישיונות IP למעצבות")
        + connector_v("מכונות ייצור, מדידה ייעודית, ווייפרים גולמיים — אל קווי הייצור")
        + "</div>"
    )

    # --- שורה אמצעית: מעצבות Fabless (2+3) + foundry + osat ---
    fab2_card = (
        "<div style='background:#141824; border:1px solid rgba(255,255,255,0.08); border-radius:12px;"
        " padding:12px 14px;'>"
        "<div style='font-size:12px; font-weight:700; color:#9ca3af; margin-bottom:8px;'>מעצבות Fabless</div>"
        "<div style='display:grid; grid-template-columns:1fr 1fr; gap:8px;'>"
    )
    for pfx in ["2", "3"]:
        key = next((k for k in value_chain if k.startswith(pfx + ".")), None)
        if key:
            name = clean_name(key)
            bc   = card_border(pfx)
            sub  = "מעבדים ומאיצי AI" if pfx == "2" else "תקשורת ואופטיקה"
            pills = build_pills(value_chain[key])
            fab2_card += (
                "<div style='background:rgba(255,255,255,0.03); border:" + bc + ";"
                " border-radius:8px; padding:8px 10px; overflow:visible;'>"
                "<div style='display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:4px; overflow:visible;'>"
                "<span style='font-size:12px; font-weight:700; color:#f3f4f6;'>" + name + "</span>"
                + _card_tag(pfx) +
                "</div>"
                "<div style='font-size:10px; color:#6b7280; margin-bottom:6px;'>" + sub + "</div>"
                "<div style='display:flex; flex-wrap:wrap; gap:3px; overflow:visible;'>" + pills + "</div>"
                "</div>"
            )
    fab2_card += "</div></div>"

    row_mid = (
        "<div style='display:grid; grid-template-columns:2.05fr 56px 1.1fr 56px 1.25fr; gap:6px; align-items:center; margin-bottom:0;'>"
        + fab2_card
        + connector_h("tape-out")
        + card("8", "קבלני ייצור — הופכים עיצוב לשבב")
        + connector_h("ווייפרים גמורים")
        + card("9", "אריזה, חיבורים ובדיקות אחרי ייצור")
        + "</div>"
    )

    conn2 = (
        "<div style='display:grid; grid-template-columns:2fr 1fr; gap:10px; margin:8px 0;'>"
        + connector_v("IDM וזיכרון מתכננות ומייצרות בעצמן — קונות EDA, ציוד וחומרים ישירות מהשורה העליונה")
        + connector_v("שבבים ארוזים אל השרתים")
        + "</div>"
    )

    row_bot = (
        "<div style='display:grid; grid-template-columns:1.3fr 0.85fr 0.85fr 0.85fr; gap:10px;'>"
        + card("4",  "מתכנן ומייצר בעצמו — לוגיקה, אנלוגי, עוצמה")
        + card("5",  "זיכרון DRAM, NAND ואחסון")
        + card("10", "שרתים, מדפי מחשוב, קירור נוזלי")
        + card("11", "חשמל, ציוד אנרגיה ותשתית לדאטה סנטרים",
               extra_style="border-style:dashed;")
        + "</div>"
    )

    _map_css = (
        "<style>"
        ".sens-tag { position: relative; display: inline-flex; align-items: center; overflow: visible; }"
        ".sens-tip {"
        "  display: none;"
        "  position: absolute;"
        "  top: calc(100% + 4px);"
        "  right: 0;"
        "  background: #1e2533;"
        "  color: #e5e7eb;"
        "  font-size: 11px;"
        "  font-weight: 400;"
        "  line-height: 1.7;"
        "  padding: 8px 12px;"
        "  border-radius: 6px;"
        "  border: 1px solid #374151;"
        "  white-space: normal;"
        "  min-width: 220px;"
        "  max-width: 320px;"
        "  z-index: 9999;"
        "  text-align: right;"
        "  direction: rtl;"
        "  pointer-events: none;"
        "  box-shadow: 0 4px 12px rgba(0,0,0,0.5);"
        "}"
        ".sens-tag:hover > .sens-tip { display: block; }"
        "</style>"
    )
    full_html = (
        _map_css
        + "<div dir='rtl' style='text-align:right; margin-bottom:24px;'>"
        + warn_banner + legend + row_top + conn1 + row_mid + conn2 + row_bot
        + "</div>"
    )
    st.markdown(full_html, unsafe_allow_html=True)
    if _delta:
        _pct_str = str(abs(round(_delta[2], 1)))
        if _delta[2] >= 0:
            st.markdown(
                "<div dir='rtl' style='font-size:13px; color:#22c55e; text-align:right; margin:2px 0 6px;'>"
                "✓ תחזית ה-CAPEX המצרפית עלתה ב-" + _pct_str + "% בעדכון האחרון — אין טריגר רגישות"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div dir='rtl' style='font-size:13px; color:#ef4444; text-align:right; margin:2px 0 6px;'>"
                "⚠️ תחזית ה-CAPEX המצרפית ירדה ב-" + _pct_str + "% בעדכון האחרון — החוליות הרגישות מסומנות"
                "</div>",
                unsafe_allow_html=True,
            )
    st.caption("◆ ציר הפוטוניקה מודגש בטבעת צהובה — חברות שאינן מופיעות במפה (כמו FN) נכללות בציר במלואו באזור הפילוח הטכנולוגי.")
    st.markdown(
        "<div dir='rtl' style='font-size:0.8rem; color:#9ca3af; text-align:right; margin:2px 0 0;'>"
        "חוליה 11 — חשמל ואנרגיה — נוספה כחוליה תומכת: היא מזינה את השרשרת אך אינה חלק ממדד "
        "<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>SOXX</span>"
        " ואינה מתואמת איתו. לכן דירוג המרחק מהמדד עלול להציב אותה בקצוות, והבטא שלה צפויה "
        "להופיע נמוכה ומסומנת בכוכבית בשל "
        "<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>R²</span>"
        " נמוך."
        "</div>",
        unsafe_allow_html=True,
    )


def section_header(title, accent):
    # כותרת אזור מובלטת עם פס צבעוני ורקע עדין, להפרדה ברורה בתוך הכרטיס
    return ("<div dir='rtl' style='text-align:right; font-weight:800; font-size:18px; "
            "background:rgba(120,120,120,0.10); border-right:5px solid " + accent +
            "; border-radius:6px; padding:8px 12px; margin:20px 0 10px 0;'>"
            + title + "</div>")


def col_header(label, active=False, width=None, flex=False):
    """כותרת עמודה בשורת ה-header של טבלאות הדירוג.
    active=True → מודגשת עם חץ ▼ לציון עמודת המיון הפעילה."""
    color = "#e5e7eb" if active else "#9ca3af"
    weight = "700" if active else "600"
    arrow = " ▼" if active else ""
    sizing = "flex:1;" if flex else ("width:" + width + ";" if width else "")
    align = "right" if flex else "center"
    return ("<span style='" + sizing + " text-align:" + align +
            "; color:" + color + "; font-weight:" + weight + ";'>"
            + label + arrow + "</span>")


def render_sentiment_trend(seasons, scores, chart_key, second_series=None):
    """גרף קו של סנטימנט לאורך עונות.
    second_series (אופציונלי): tuple של (seasons2, scores2, label2, color2) לקו שני מקווקו."""
    scores_pct = [sentiment_pct(s) for s in scores]
    colors = ["#22c55e" if s >= SENTIMENT_POS else ("#ef4444" if s <= SENTIMENT_NEG else "#9ca3af") for s in scores]
    labels = [str(p) + "%" for p in scores_pct]

    # ציר Y ב-0–100
    _all_pct = list(scores_pct)
    if second_series:
        _all_pct += [sentiment_pct(s) for s in second_series[1]]
    _s_min = min(_all_pct)
    _s_max = max(_all_pct)
    _pad = max((_s_max - _s_min) * 0.18, 7)
    _y_low  = max(_s_min - _pad, 0)
    _y_high = _s_max + _pad + 4

    _tick_vals  = [t for t in [0, 25, 50, 75, 100] if _y_low - 1 <= t <= _y_high + 1]
    _tick_text  = [str(t) + "%" for t in _tick_vals]

    _has_second = bool(second_series)
    _first_label = "סנטימנט חברות" if _has_second else None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=seasons, y=scores_pct, mode="lines+markers+text",
        name=_first_label,
        line=dict(color="#60a5fa", width=2.5),
        marker=dict(size=14, color=colors, line=dict(color="#1e2533", width=2)),
        text=labels, textposition="top center",
        textfont=dict(size=13, color="#e5e7eb"),
        hovertemplate="<b>%{x}</b><br>ציון: %{y:.0f}%<extra></extra>",
        showlegend=_has_second,
    ))

    if _has_second:
        _s2, _sc2, _lbl2, _col2 = second_series
        _sc2_pct = [sentiment_pct(s) for s in _sc2]
        fig.add_trace(go.Scatter(
            x=_s2, y=_sc2_pct, mode="lines+markers",
            name=_lbl2,
            line=dict(color=_col2, width=2, dash="dash"),
            marker=dict(size=9, color=_col2, line=dict(color="#1e2533", width=1.5)),
            hovertemplate="<b>%{x}</b><br>" + _lbl2 + ": %{y:.0f}%<extra></extra>",
            showlegend=True,
        ))

    fig.add_hline(y=50, line_dash="dot", line_color="rgba(255,255,255,0.25)", line_width=1)
    fig.update_layout(
        height=240, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(14,18,30,0.7)",
        margin=dict(t=28 if not _has_second else 40, b=36, l=60, r=70),
        yaxis=dict(
            range=[_y_low, _y_high],
            gridcolor="rgba(255,255,255,0.08)",
            tickvals=_tick_vals, ticktext=_tick_text,
            tickfont=dict(size=12, color="#9ca3af"),
            showline=True, linecolor="rgba(255,255,255,0.18)", linewidth=1,
            zeroline=False,
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=12, color="#9ca3af"),
            showline=True, linecolor="rgba(255,255,255,0.18)", linewidth=1,
            ticks="outside", ticklen=4, tickcolor="rgba(255,255,255,0.18)",
        ),
        showlegend=_has_second,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11)) if _has_second else {},
    )
    st.plotly_chart(fig, width='stretch', key=chart_key)


def returns_table_html(pairs, descending=True, sentiment_data=None, season=None,
                       outlier_map=None, analyst_scores=None, analyst_med=None,
                       beta_scores=None):
    sortable = [(change, symbol) for symbol, change in pairs]
    sortable.sort(reverse=descending)
    show_sent = sentiment_data is not None and season is not None
    show_analyst = analyst_scores is not None
    show_beta = beta_scores is not None
    rows = ""
    for change, symbol in sortable:
        c = "#22c55e" if change >= 0 else "#ef4444"
        is_outlier = outlier_map is not None and symbol in outlier_map
        row_style = " style='background:rgba(245,158,11,0.12);'" if is_outlier else ""
        if is_outlier:
            rel = outlier_map[symbol]
            rel_col = "#22c55e" if rel >= 0 else "#ef4444"
            rel_label = ("ביצועי יתר " if rel >= 0 else "ביצועי חסר ") + str(round(abs(rel), 1)) + " נק'"
            sym_html = (
                "🎯 " + symbol +
                " <span style='font-size:11px; color:" + rel_col + ";'>" + rel_label + "</span>"
            )
            td_sym = (
                "<td style='text-align:right; padding:4px 10px; border-right:3px solid #f59e0b;'>"
                + sym_html + "</td>"
            )
        else:
            td_sym = "<td style='text-align:right; padding:4px 10px;'>" + symbol + "</td>"
        row = ("<tr" + row_style + ">"
               + td_sym
               + "<td style='text-align:right; padding:4px 10px; color:" + c +
               "; font-weight:600;'>" + str(round(change, 1)) + "%</td>")
        if show_sent:
            rec = get_record(sentiment_data, symbol, season)
            if rec and rec.get("sentiment_score") is not None:
                score = float(rec["sentiment_score"])
                pct = sentiment_pct(score)
                emoji = "🟢" if score >= SENTIMENT_POS else ("🔴" if score <= SENTIMENT_NEG else "⚪")
                col = "#22c55e" if score >= SENTIMENT_POS else ("#ef4444" if score <= SENTIMENT_NEG else "#9ca3af")
                sent_html = (emoji + " <span style='color:" + col +
                             "; font-weight:700;'>" + str(pct) + "%</span>")
                report_date = rec.get("report_date", "—")
            else:
                sent_html = "<span style='color:#6b7280;'>—</span>"
                report_date = "—"
            row += ("<td style='text-align:center; padding:4px 10px; white-space:nowrap;'>"
                    + sent_html + "</td>"
                    "<td style='text-align:center; padding:4px 10px; color:#9ca3af; font-size:12px;'>"
                    + report_date + "</td>")
        if show_analyst:
            sc = analyst_scores.get(symbol)
            row += analyst_cell_html(sc, analyst_med, wrapper="td")
        if show_beta:
            row += beta_cell_html(beta_scores.get(symbol), wrapper="td")
        rows += row + "</tr>"
    hdr = ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
           "<tr>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th>")
    if show_sent:
        hdr += ("<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>סנטימנט הדוח האחרון</th>"
                "<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>תאריך דוח</th>")
    if show_analyst:
        hdr += "<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>ציון אנליסטים</th>"
    if show_beta:
        hdr += "<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>בטא מול SOXX</th>"
    return hdr + "</tr>" + rows + "</table>"


def tech_table_html(rows, sentiment_data=None, season=None):
    # טבלת מניות לתחום טכנולוגי: מניה, תשואה, משקל אפקטיבי, וסנטימנט דוח (אופציונלי)
    # rows = רשימה של [סימבול, תשואה, משקל מנורמל], כבר ממוינת מהגבוה לנמוך
    show_sent = sentiment_data is not None and season is not None
    body = ""
    for symbol, change, weight in rows:
        c = "#22c55e" if change >= 0 else "#ef4444"
        row = ("<tr><td style='text-align:right; padding:4px 10px;'>" + symbol +
               "</td><td style='text-align:right; padding:4px 10px; color:" + c +
               "; font-weight:600;'>" + str(round(change, 1)) + "%</td>"
               "<td style='text-align:right; padding:4px 10px; color:#9ca3af;'>" +
               str(round(weight * 100, 1)) + "%</td>")
        if show_sent:
            rec = get_record(sentiment_data, symbol, season)
            if rec and rec.get("sentiment_score") is not None:
                score = float(rec["sentiment_score"])
                pct = sentiment_pct(score)
                emoji = "🟢" if score >= SENTIMENT_POS else ("🔴" if score <= SENTIMENT_NEG else "⚪")
                col = "#22c55e" if score >= SENTIMENT_POS else ("#ef4444" if score <= SENTIMENT_NEG else "#9ca3af")
                sent_html = (emoji + " <span style='color:" + col +
                             "; font-weight:700;'>" + str(pct) + "%</span>")
            else:
                sent_html = "<span style='color:#6b7280;'>—</span>"
            row += "<td style='text-align:center; padding:4px 10px; white-space:nowrap;'>" + sent_html + "</td>"
        body += row + "</tr>"
    hdr = ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px;'>"
           "<tr><th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>מניה</th>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>תשואה</th>"
           "<th style='text-align:right; padding:4px 10px; border-bottom:1px solid #666;'>משקל בתחום</th>")
    if show_sent:
        hdr += "<th style='text-align:center; padding:4px 10px; border-bottom:1px solid #666;'>סנטימנט הדוח האחרון</th>"
    return hdr + "</tr>" + body + "</table>"


def sentiment_cell_html(agg, wrapper="td", width="110px"):
    """תא HTML לסנטימנט דוחות. agg = תוצאת aggregate_sentiment, או None.
    wrapper='td' לטבלאות HTML, wrapper='span' לשורות flexbox (מפת החום)."""
    if agg is None:
        empty_style = "text-align:center; padding:6px 8px; color:#6b7280; font-size:12px;"
        if wrapper == "span":
            return f"<span style='width:{width}; {empty_style}'>—</span>"
        return f"<td style='{empty_style}'>—</td>"
    score = agg["score"]
    reported = agg["reported"]
    total = agg["total"]
    pct = sentiment_pct(score)
    if score >= SENTIMENT_POS:
        emoji = "🟢"
        color = "#22c55e"
    elif score <= SENTIMENT_NEG:
        emoji = "🔴"
        color = "#ef4444"
    else:
        emoji = "⚪"
        color = "#9ca3af"
    cov_color = "#9ca3af" if reported <= 1 else "#6b7280"
    cov = f"<span style='color:{cov_color}; font-size:10px;'>({reported}/{total})</span>"
    inner = f"{emoji} <span style='color:{color}; font-weight:700;'>{pct}%</span> {cov}"
    if wrapper == "span":
        return (f"<span style='width:{width}; text-align:center; white-space:nowrap; display:inline-block;'>"
                f"{inner}</span>")
    return f"<td style='text-align:center; padding:6px 8px; white-space:nowrap;'>{inner}</td>"


def analyst_color(score, median):
    """צבע לפי המרחק מהחציון. אם median=None → אפור."""
    if median is None or score is None:
        return "#9ca3af"
    if score >= median + ANALYST_DELTA:
        return "#22c55e"
    if score <= median - ANALYST_DELTA:
        return "#ef4444"
    return "#9ca3af"


def analyst_cell_html(agg, median, wrapper="span", width="105px"):
    """תא HTML לציון אנליסטים.
    agg = תוצאת analyst_group_score / get_analyst_score, או None.
    wrapper='span' לשורות flex, wrapper='td' לטבלאות."""
    empty_style = "text-align:center; padding:6px 8px; color:#6b7280; font-size:12px;"
    if agg is None or agg.get("score") is None:
        if wrapper == "span":
            return "<span style='width:" + width + "; " + empty_style + "'>—</span>"
        return "<td style='" + empty_style + "'>—</td>"
    score = agg["score"]
    score_color = analyst_color(score, median)
    score_txt = str(round(score, 2))
    if "reported" in agg:
        cov_txt = "(" + str(agg["reported"]) + "/" + str(agg["total"]) + ")"
    elif "n" in agg:
        cov_txt = "n=" + str(agg["n"])
    else:
        cov_txt = ""
    cov_html = ("<span style='color:#6b7280; font-size:10px;'> " + cov_txt + "</span>"
                if cov_txt else "")
    inner = ("<span style='color:" + score_color + "; font-weight:700;'>" + score_txt + "</span>"
             + cov_html)
    if wrapper == "span":
        return ("<span style='width:" + width + "; text-align:center; white-space:nowrap; "
                "display:inline-block;'>" + inner + "</span>")
    return "<td style='text-align:center; padding:6px 8px; white-space:nowrap;'>" + inner + "</td>"


def weighted_score_html(ws, wrapper="span"):
    """תא/span HTML לציון המשוקלל (weighted_tech_score). wrapper='span' לשורות flex."""
    width = "140px"
    empty_style = "text-align:center; padding:6px 8px; color:#6b7280; font-size:12px;"
    if ws is None:
        if wrapper == "span":
            return "<span style='width:" + width + "; " + empty_style + "'>—</span>"
        return "<td style='" + empty_style + "'>—</td>"
    score = ws["score"]
    pct = sentiment_pct(score)
    if score >= SENTIMENT_POS:
        emoji, color = "🟢", "#22c55e"
    elif score <= SENTIMENT_NEG:
        emoji, color = "🔴", "#ef4444"
    else:
        emoji, color = "⚪", "#9ca3af"
    cov_parts = []
    if ws["comp_reported"]:
        cov_parts.append(str(ws["comp_reported"]) + "/" + str(ws["comp_total"]) + " חב׳")
    if ws["sig_count"]:
        cov_parts.append(str(ws["sig_count"]) + " סיג׳")
    cov = ("<span style='color:#6b7280; font-size:10px;'>" +
           ("(" + " · ".join(cov_parts) + ")" if cov_parts else "") + "</span>")
    inner = (emoji + " <span style='color:" + color + "; font-weight:700;'>" +
             str(pct) + "%</span> " + cov)
    if wrapper == "span":
        return ("<span style='width:" + width + "; text-align:center; "
                "white-space:nowrap; display:inline-block;'>" + inner + "</span>")
    return "<td style='text-align:center; padding:6px 8px; white-space:nowrap;'>" + inner + "</td>"


def capex_guidance_table_html(rows):
    # טבלה מסכמת של התחזיות: חברה, תחזית אחרונה, תחזית קודמת, שינוי ביניהן,
    # ושינוי התחזית מול ה-CapEx בפועל של השנה הקודמת.
    # rows = רשימת מילונים עם המפתחות: name, last, prev, chg_prev, chg_actual
    def pct_cell(v):
        if v is None:
            return "<td style='text-align:center; padding:6px 10px; color:#6b7280;'>—</td>"
        c = "#22c55e" if v >= 0 else "#ef4444"
        sg = "+" if v >= 0 else ""
        return ("<td style='text-align:center; padding:6px 10px; color:" + c +
                "; font-weight:700;'>" + sg + str(round(v, 1)) + "%</td>")

    def usd_cell(v):
        if v is None:
            return "<td style='text-align:center; padding:6px 10px; color:#6b7280;'>—</td>"
        return ("<td style='text-align:center; padding:6px 10px;'>$" +
                str(round(v, 1)) + "B</td>")

    body = ""
    for r in rows:
        body += ("<tr>"
                 "<td style='text-align:right; padding:6px 10px; font-weight:600;'>" + r["name"] + "</td>"
                 + usd_cell(r["last"])
                 + usd_cell(r["prev"])
                 + pct_cell(r["chg_prev"])
                 + usd_cell(r["actual_prev"])
                 + pct_cell(r["chg_actual"])
                 + "</tr>")
    return ("<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:8px; font-size:14px;'>"
            "<tr style='border-bottom:1px solid #666;'>"
            "<th style='text-align:right; padding:6px 10px;'>חברה</th>"
            "<th style='text-align:center; padding:6px 10px;'>תחזית אחרונה</th>"
            "<th style='text-align:center; padding:6px 10px;'>תחזית קודמת</th>"
            "<th style='text-align:center; padding:6px 10px;'>שינוי בתחזית</th>"
            "<th style='text-align:center; padding:6px 10px;'>שנה קודמת בפועל</th>"
            "<th style='text-align:center; padding:6px 10px;'>תחזית מול בפועל</th>"
            "</tr>" + body + "</table>")


def render_ai_alert(soxx_change, holdings_pairs, period, period_label):
    if soxx_change is None:
        return
    if period in DAILY_PERIODS:
        if abs(soxx_change) >= MOVE_ALERT:
            alert_color = "#22c55e" if soxx_change >= 0 else "#ef4444"
            arrow = "▲" if soxx_change >= 0 else "▼"
            pct_html = "<span style='color:" + alert_color + ";'>" + arrow + " " + str(round(soxx_change, 2)) + "%</span>"
            st.markdown(
                "<div dir='rtl' style='background:rgba(120,120,120,0.12); border:2px solid " + alert_color +
                "; border-radius:10px; padding:12px 16px; margin:10px 0; text-align:right; font-size:17px; font-weight:700;'>"
                "🚨 התראת תנועה חריגה — SOXX " + pct_html + " ביום המסחר האחרון</div>",
                unsafe_allow_html=True,
            )
            _move_stamp = period_stamp(period)
            _move_key = "move_" + period + "_" + _move_stamp
            if st.button("🧠 הסבר את תנועת המדד", key="movebtn_" + period):
                movers = []
                for sym, ch in holdings_pairs[:3]:
                    movers.append(sym + " " + str(round(ch, 1)) + "%")
                for sym, ch in holdings_pairs[-3:]:
                    movers.append(sym + " " + str(round(ch, 1)) + "%")
                movers_text = ", ".join(movers)
                with st.spinner("מבקש הסבר מ-Gemini עם חיפוש ברשת..."):
                    text, sources = gemini_explain_move(round(soxx_change, 2), period_label, period, movers_text)
                st.session_state[_move_key] = {"text": text, "sources": sources}
            _saved_move = st.session_state.get(_move_key)
            if _saved_move is not None:
                if _saved_move.get("text"):
                    st.markdown("<div dir='rtl' style='text-align:right; font-weight:700; margin-top:8px;'>🧠 הסבר לתנועה:</div>", unsafe_allow_html=True)
                    st.markdown("<div dir='rtl' style='text-align:right;'>" + html.escape(_saved_move["text"]) + "</div>", unsafe_allow_html=True)
                    if _saved_move.get("sources"):
                        with st.expander("מקורות"):
                            for title, uri in _saved_move["sources"]:
                                st.markdown("• [" + (title or uri) + "](" + uri + ")")
                else:
                    st.caption("הסבר AI לא זמין כרגע (חסר מפתח Gemini).")
    else:
        stamp = period_stamp(period)
        trend_key = "trend_" + period + "_" + stamp
        if st.button("🧠 סכם לי את המגמה בתקופה הזו"):
            lines = []
            for sector in value_chain:
                pr = get_changes(value_chain[sector], period)
                if len(pr) == 0:
                    continue
                nums = [c for s, c in pr]
                med = statistics.median(nums)
                lines.append(clean_name(sector) + " " + str(round(med, 1)) + "%")
            sector_lines = ", ".join(lines)
            with st.spinner("מבקש סיכום מגמה מ-Gemini..."):
                text, sources = gemini_trend_summary(period_label, period, soxx_change, sector_lines)
            st.session_state[trend_key] = {"text": text, "sources": sources}

        saved = st.session_state.get(trend_key)
        if saved and saved.get("text"):
            st.markdown("<div dir='rtl' style='text-align:right; font-weight:700; margin-top:8px;'>🧠 סיכום המגמה:</div>", unsafe_allow_html=True)
            st.markdown("<div dir='rtl' style='text-align:right;'>" + html.escape(saved["text"]) + "</div>", unsafe_allow_html=True)
            if saved.get("sources"):
                with st.expander("מקורות"):
                    for title, uri in saved["sources"]:
                        st.markdown("• [" + (title or uri) + "](" + uri + ")")


# ---------- ממשק ----------
st.title("💹 דשבורד שרשרת הערך של השבבים")
if DEV_MODE:
    st.markdown(
        "<div style='background:rgba(234,179,8,0.15); border:1px solid #ca8a04; "
        "border-radius:8px; padding:6px 14px; margin-bottom:6px; "
        "font-size:13px; font-weight:700; color:#fbbf24; direction:rtl; text-align:right;'>"
        "🔧 מצב מפתח פעיל</div>",
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    "<div dir='rtl' style='text-align:right; margin-bottom:10px;'>"
    "<div style='font-size:12px; font-weight:700; color:#9ca3af; "
    "margin-bottom:8px; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1);'>"
    "📑 ניווט מהיר</div>"
    "<div style='display:flex; flex-direction:column; gap:4px;'>"
    "<a href='#zone-1' style='color:#f59e0b; text-decoration:none; font-size:13px;'>⚡ SOXX — מדד השבבים</a>"
    "<a href='#zone-2' style='color:#8b5cf6; text-decoration:none; font-size:13px;'>🗺️ מפת שרשרת הערך</a>"
    "<a href='#zone-3' style='color:#3b82f6; text-decoration:none; font-size:13px;'>🗺️ מפת חום — דירוג שרשרת הערך</a>"
    "<a href='#zone-4' style='color:#22c55e; text-decoration:none; font-size:13px;'>🔍 צלילה לתחום</a>"
    "<a href='#zone-5' style='color:#a78bfa; text-decoration:none; font-size:13px;'>🧬 פילוח טכנולוגי</a>"
    "<a href='#zone-6' style='color:#22d3ee; text-decoration:none; font-size:13px;'>🏗️ CapEx — ענקיות הענן</a>"
    "<a href='#zone-7' style='color:#f59e0b; text-decoration:none; font-size:13px;'>📋 דוחות — עונת הדוחות</a>"
    "<a href='#zone-il' style='color:#3b82f6; text-decoration:none; font-size:12px; padding-right:16px;'>↳ 🇮🇱 חברות ישראליות</a>"
    "<a href='#zone-8' style='color:#ec4899; text-decoration:none; font-size:13px;'>🎯 דירוגי אנליסטים</a>"
    "</div></div>",
    unsafe_allow_html=True,
)
st.sidebar.divider()

period_label = st.sidebar.selectbox("Period:", list(PERIOD_OPTIONS.keys()), index=3)
period = PERIOD_OPTIONS[period_label]
st.sidebar.caption("משפיע על אזורים 1–5 בלבד")
st.sidebar.caption("התשואה נמדדת מהסגירה האחרונה עד הסגירה שקדמה לתחילת התקופה — ייתכן הבדל קל מול מקורות אחרים בשל הגדרת חלון שונה.")

# ======================================================
# אזור 1 — SOXX
# ======================================================
section_banner(1, 8, "⚡", "מדד סקטור השבבים — SOXX", "#f59e0b",
               subtitle="התנהגות המדד הכללי, עם התראות AI על תנועות חריגות",
               period_dependent=True, period_label=period_label)
soxx_close = get_history(BENCHMARK, period)
_online_closed = (period == "online" and not market_is_open())

if soxx_close is None:
    st.warning("לא הצלחנו למשוך נתוני SOXX כרגע")
    soxx_change = None
    holdings_pairs = []
elif _online_closed:
    st.info("⏸️ מצב Online פעיל רק בשעות המסחר (09:30–16:00 שעון ניו-יורק, ימי מסחר בלבד). עבור ל-Last Close לנתוני יום המסחר האחרון.")
    soxx_change = None
    holdings_pairs = []
else:
    # שלב 1: משוך את הסשן התוך-יומי מראש — מקור אמת יחיד לכותרת, לגרף ולכיתוב
    _session = None
    _mini_prev_close = None
    _mini_prev_date = None
    if period in DAILY_PERIODS:
        _skip = (period == "lastclose")
        _session, _mini_prev_close, _mini_prev_date = get_last_session_intraday(BENCHMARK, skip_current_day=_skip)

    # שלב 1ב: תיקון עוגן — prev_close נפתר פעם אחת (שכבה 1 → 2) ומוזרק לגרף ולכותרת.
    # ללא זה: הכותרת משתמשת ב-quote (רשמי) אך הגרף עוגן ב-intraday (שונה בפחות מ-1%).
    if period == "lastclose" and _session is not None and _mini_prev_date is not None:
        _daily_bm = get_history(BENCHMARK, "lastclose")
        _off_prev, _ = _close_for_date(_daily_bm, _mini_prev_date)
        if _off_prev is None:
            _off_q = _get_quote_prev_close(BENCHMARK)
            if _off_q is not None:
                _off_prev = _off_q
        if _off_prev is not None:
            _session = _session.copy()
            _session.iloc[0] = _off_prev
            _mini_prev_close = _off_prev

        # אותו תיקון עבור הנקודה האחרונה — אחרת הגרף נשאר עוגן בתוך-יומי
        # בזמן שהכותרת (get_change) כבר עברה ל-quote, ונפתח פיצול בין השניים.
        _off_last_date = _session.index[-1].date()
        _off_last, _ = _close_for_date(_daily_bm, _off_last_date)
        if _off_last is None and not market_is_open() and session_is_complete(_off_last_date):
            _off_intra = float(_session.iloc[-1])
            _off_last_q = _get_quote_last_close(BENCHMARK)
            if _off_last_q is not None and _off_intra and abs(_off_last_q - _off_intra) / _off_intra < 0.01:
                _off_last = _off_last_q
        if _off_last is not None:
            _session = _session.copy()
            _session.iloc[-1] = _off_last

    soxx_change = get_change(BENCHMARK, period)
    if soxx_change is not None:
        soxx_color = "#22c55e" if soxx_change >= 0 else "#ef4444"
        _soxx_pct_html = ("+" if soxx_change >= 0 else "") + str(round(soxx_change, 1)) + "%"
    else:
        soxx_color = "#6b7280"
        _soxx_pct_html = "אין נתונים"

    st.markdown(
        "<h3>⚡ SOXX — מדד סקטור השבבים "
        "(<span style='color:" + soxx_color + ";'>" + _soxx_pct_html + "</span>)</h3>",
        unsafe_allow_html=True,
    )
    if period == "lastclose" and _session is not None:
        # כיתוב אזהרה כאשר מחיר כלשהו הגיע משכבה 3 (תוך-יומי — לא סגירה רשמית)
        _bm_daily = get_history(BENCHMARK, "lastclose")
        _ld = _session.index[-1].date()
        _pd = _mini_prev_date
        _, _ls = _close_for_date(_bm_daily, _ld)
        if _ls is None and not market_is_open() and session_is_complete(_ld):
            _ls = "quote" if _get_quote_last_close(BENCHMARK) else None
        _, _ps = _close_for_date(_bm_daily, _pd) if _pd else (None, None)
        if _ps is None and _pd:
            _ps = "quote" if _get_quote_prev_close(BENCHMARK) else None
        if _ls is None or _ps is None:
            _missing = _ld.strftime("%d/%m") if _ls is None else (_pd.strftime("%d/%m") if _pd else "?")
            st.caption("⚠ מחיר SOXX " + _missing + ": הסגירה הרשמית חסרה במקור — מוצג מחיר משוער מנתונים תוך-יומיים")
    elif period == "online" and _session is not None:
        st.caption("Online · " + _session.index[-1].date().strftime("%d/%m/%Y") + " · מסחר פעיל")
    else:
        st.caption("תקופה: " + period_label)
        # כיתוב על מצב הנתונים כאשר קיים סשן מאוחר יותר שכבר הושלם ולא נכלל
        # בסדרה היומית (ראה get_change, ענף התקופות הארוכות) — אותה בדיקה, כאן
        # רק לצורך הכיתוב. משתמש ב-soxx_close שכבר נמשך למעלה — ללא בקשה נוספת.
        _lp_nan_tail = soxx_close.attrs.get("nan_tail_date", _ATTRS_MISSING)
        if _lp_nan_tail is _ATTRS_MISSING:
            _log.warning(f"[DATA_WARN {BENCHMARK}] תכונת attrs (nan_tail_date) לא שרדה על הסדרה — לא ניתן לזהות אם קיים סשן מאוחר יותר שחסר בה")
            _lp_nan_tail = None
        if _lp_nan_tail is not None and not market_is_open() and session_is_complete(_lp_nan_tail):
            _lp_q = _get_quote_last_close(BENCHMARK)
            _lp_last_daily = float(soxx_close.iloc[-1])
            if _lp_q is not None and _lp_last_daily and abs(_lp_q - _lp_last_daily) / _lp_last_daily < 0.15:
                st.caption(
                    "ℹ️ מחיר הסגירה של " + _lp_nan_tail.strftime("%d/%m") +
                    " טרם אוחד במקור — מוצג ציטוט רשמי"
                )
            else:
                st.caption(
                    "⚠ מחיר SOXX " + _lp_nan_tail.strftime("%d/%m") +
                    ": הסגירה הרשמית חסרה במקור — מוצג מחיר הסשן הקודם"
                )

    holdings_pairs = get_changes(SOXX_HOLDINGS, period)
    holdings_pairs.sort(key=lambda x: x[1], reverse=True)

    render_ai_alert(soxx_change, holdings_pairs, period, period_label)

    # שלב 2: בנה את הגרף הקטן — בתקופות יומיות אנחנו כבר מחזיקים את _session
    mini_source = soxx_close
    if period in DAILY_PERIODS and _session is not None:
        mini_source = _session
    elif period in DAILY_PERIODS:
        _mini_prev_close = None
    soxx_price = mini_source.reset_index()
    soxx_price.columns = ["תאריך", "מחיר"]
    base_price = soxx_price["מחיר"].iloc[0]
    soxx_price["תשואה"] = soxx_price["מחיר"] / base_price * 100 - 100
    # תשואה צבועה לבועה: ירוק לחיובי, אדום לשלילי, שתי ספרות
    ret_cells = []
    for v in soxx_price["תשואה"]:
        col = "#22c55e" if v >= 0 else "#ef4444"
        sg = "+" if v >= 0 else ""
        ret_cells.append("<span style='color:" + col + "'>" + sg + format(v, ".2f") + "%</span>")

    # בתקופות יומיות ציר הזמן הוא שעות — אבל רק אם באמת יש מקור תוך-יומי;
    # אם _session חסר, mini_source נפל חזרה לסדרה היומית (תאריכים, לא שעות)
    _mini_is_intraday = period in DAILY_PERIODS and _session is not None
    _mini_xfmt = "%H:%M" if _mini_is_intraday else "%d/%m/%Y"
    # צבע דינמי: ירוק אם התקופה עלתה, אדום אם ירדה.
    # בתקופות יומיות — ייחוס מול סגירה קודמת; בשאר — ייחוס מול נקודת פתיחת הסדרה.
    _mini_ref = _mini_prev_close if _mini_prev_close is not None else base_price
    _mini_last_price = float(soxx_price["מחיר"].iloc[-1])
    if _mini_last_price >= _mini_ref:
        _mini_line_color = "#22c55e"
        _mini_fill_color = "rgba(34,197,94,0.15)"
    else:
        _mini_line_color = "#ef4444"
        _mini_fill_color = "rgba(239,68,68,0.15)"
    mini = go.Figure()
    mini.add_trace(go.Scatter(
        x=soxx_price["תאריך"], y=soxx_price["מחיר"], mode="lines",
        line=dict(color=_mini_line_color, width=2.5), fill="tozeroy",
        fillcolor=_mini_fill_color,
        customdata=ret_cells,
        hovertemplate="%{x|" + _mini_xfmt + "}<br>מחיר: $%{y:.2f}<br>תשואה: %{customdata}<extra></extra>",
    ))
    # ציר Y דינמי: לא מתחילים מאפס, אלא מרווח קטן סביב טווח המחירים בפועל,
    # כדי שתנועת המחיר תיראה נכון (בעיקר בתקופות קצרות). מילוי עדין עד תחתית הציר.
    price_min = float(soxx_price["מחיר"].min())
    price_max = float(soxx_price["מחיר"].max())
    # אם יש קו סגירה קודמת מעל/מתחת לטווח היום — מרחיבים את הטווח שיכלול אותו
    if _mini_prev_close is not None:
        price_min = min(price_min, _mini_prev_close)
        price_max = max(price_max, _mini_prev_close)
    price_pad = (price_max - price_min) * 0.15
    if price_pad == 0:
        price_pad = price_max * 0.01 if price_max else 1.0
    y_low = price_min - price_pad
    y_high = price_max + price_pad
    mini.update_layout(
        height=240, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=30, l=50, r=20),
        yaxis=dict(title="מחיר ($)", gridcolor="rgba(255,255,255,0.08)",
                   range=[y_low, y_high]),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                   tickformat=("%H:%M" if _mini_is_intraday else None)),
        showlegend=False,
    )
    st.plotly_chart(mini, width='stretch')
    if period in DAILY_PERIODS:
        _cap_date = mini_source.index[-1].date()
        st.caption("יום מסחר אחרון שמוצג: " + _cap_date.strftime("%d/%m/%Y"))
    st.markdown(
        "<div style='margin:8px 0 20px; border-top:1px solid rgba(255,255,255,0.08);'></div>",
        unsafe_allow_html=True,
    )

    if len(holdings_pairs) >= 2:
        top5 = holdings_pairs[:5]
        bottom5 = list(reversed(holdings_pairs[-5:]))

        # חריגות — מחושבות לפני הטבלאות (מזינות סימון) ומשמשות גם לכפתור אחרי הטבלאות
        if soxx_change is not None and period in DAILY_PERIODS:
            _outliers = sorted(
                [(sym, ch, ch - soxx_change) for sym, ch in holdings_pairs
                 if abs(ch - soxx_change) >= STOCK_VS_SOXX_ALERT],
                key=lambda x: -abs(x[2]),
            )
        else:
            _outliers = []
        _outlier_map = {sym: rel for sym, ch, rel in _outliers}

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📈 העליות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(top5, descending=True, outlier_map=_outlier_map), unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='text-align:right; font-weight:700; font-size:16px;'>📉 הירידות הגדולות</div>", unsafe_allow_html=True)
            st.markdown(returns_table_html(bottom5, descending=False, outlier_map=_outlier_map), unsafe_allow_html=True)

        if _outliers:
            st.caption(
                "🎯 מניות המסומנות סטו ≥" + str(int(STOCK_VS_SOXX_ALERT)) +
                " נק' מ-SOXX ביום המסחר האחרון — תנועה שאינה מוסברת על ידי המדד הכללי."
            )
            _out_stamp = period_stamp(period)
            _out_key = "outliers_" + period + "_" + _out_stamp
            if st.button("🧠 הסבר את התנועות החריגות", key="outliersbtn_" + period):
                _otxt = ", ".join(
                    sym + " " + ("+" if ch >= 0 else "") + str(round(ch, 1)) + "%" +
                    " (מרחק " + ("+" if rel >= 0 else "") + str(round(rel, 1)) + " נק' מ-SOXX)"
                    for sym, ch, rel in _outliers
                )
                with st.spinner("מבקש הסבר חריגות מ-Gemini עם חיפוש ברשת..."):
                    _out_text, _out_sources = gemini_explain_outliers(
                        soxx_change, _otxt, period, period_label
                    )
                st.session_state[_out_key] = {"text": _out_text, "sources": _out_sources}
            _saved_out = st.session_state.get(_out_key)
            if _saved_out and _saved_out.get("text"):
                st.markdown(
                    "<div dir='rtl' style='text-align:right; font-weight:700; margin-top:8px;'>🧠 הסבר החריגות:</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div dir='rtl' style='text-align:right;'>" + html.escape(_saved_out["text"]) + "</div>",
                    unsafe_allow_html=True,
                )
                if _saved_out.get("sources"):
                    with st.expander("מקורות"):
                        for title, uri in _saved_out["sources"]:
                            st.markdown("• [" + (title or uri) + "](" + uri + ")")


_rating_universe = tuple(sorted({t for lst in value_chain.values() for t in lst}))
_analyst_scores  = scan_analyst_scores(_rating_universe)
_analyst_med     = analyst_median(_analyst_scores)

if not _online_closed:

    # ---------- חישוב הדירוג ----------
    with st.spinner("סורק את כל התחומים..."):
        results = []
        for sector in value_chain:
            pairs = get_changes(value_chain[sector], period)
            if len(pairs) == 0:
                continue
            numbers = []
            for s, c in pairs:
                numbers.append(c)
            median = statistics.median(numbers)
            average = sum(numbers) / len(numbers)
            up = 0
            down = 0
            for c in numbers:
                if c > 0:
                    up = up + 1
                elif c < 0:
                    down = down + 1
            breadth = up / len(numbers)
            results.append((median, average, up, down, len(numbers), breadth, sector, pairs))
        # דירוג לפי המרחק מהמדד: חציון פחות תשואת SOXX, מהגבוה לנמוך
        soxx_ref = soxx_change if soxx_change is not None else 0.0
        results.sort(key=lambda r: r[0] - soxx_ref, reverse=True)


    # ---------- מפת חום ----------
    def render_domain_detail(sector, pairs, period, analyst_scores=None, analyst_med=None,
                             beta_scores=None):
        """מרנדר את תוכן הפרטים של תחום: מניות, גרף מגמת הפער, וחדשות + ניתוח AI.
        משמש גם במפת החום (שרשרת ערך). נקרא רק כשהשורה של התחום פתוחה."""
        # --- אזור טבלת המניות ---
        st.markdown(section_header("📊 מניות בתחום", "#3b82f6"), unsafe_allow_html=True)
        _det_sent = load_sentiment()
        _det_season = latest_season_with_data(_det_sent)
        st.markdown(returns_table_html(pairs, sentiment_data=_det_sent, season=_det_season,
                                       analyst_scores=analyst_scores, analyst_med=analyst_med,
                                       beta_scores=beta_scores),
                    unsafe_allow_html=True)
        _rd_defined = len(value_chain.get(sector, []))
        if period in DAILY_PERIODS and len(pairs) < _rd_defined:
            st.caption(
                "⚠ " + str(len(pairs)) + " מתוך " + str(_rd_defined) + " טיקרים בחוליה נכללו בחישוב. "
                "בתקופות יומיות (Online ו-Last Close) טיקרים מבורסות אסייתיות אינם נכללים בשל הפרשי שעות מסחר."
            )
        if beta_scores is not None:
            st.caption("בטא מול SOXX: מעל 1 = מניה מגבירה את תנועת המדד · מתחת ל-1 = ממתנת · "
                       "חלון: 3 חודשים, יומי · אינה מגיבה לבורר התקופה")

        # --- גרף מגמת הפער מ-SOXX לאורך התקופה ---
        st.markdown(section_header("📈 מגמת הפער מ-SOXX לאורך התקופה", "#22c55e"), unsafe_allow_html=True)
        spread_chart = build_spread_chart(value_chain[sector], period,
                                          intraday=(period in DAILY_PERIODS),
                                          skip_current_day=(period == "lastclose"))
        if spread_chart is not None:
            st.altair_chart(spread_chart, width='stretch')
            st.caption("🟢 מעל הקו = ביצועי יתר מול SOXX · 🔴 מתחת = ביצועי חסר · בתקופות יומיות הגרף נמדד מסגירת היום הקודם — כולל פער הפתיחה · הנקודה האחרונה תואמת את המספר בכותרת")
        else:
            st.caption("אין מספיק נתונים לגרף המגמה")

        # --- מגמת סנטימנט לאורך עונות ---
        _vc_all_s = sorted({s for _sd in _det_sent.values() for s in _sd})
        _vc_tx, _vc_ty = [], []
        for _s in _vc_all_s:
            _agg_vc = value_chain_sentiment(sector, _s, _det_sent)
            if _agg_vc is not None:
                _vc_tx.append(_s)
                _vc_ty.append(_agg_vc["score"])
        if len(_vc_tx) >= 2:
            st.markdown(section_header("📈 מגמת סנטימנט לאורך עונות", "#22d3ee"), unsafe_allow_html=True)
            render_sentiment_trend(_vc_tx, _vc_ty, "trend_vc_" + sector_key(sector))
        elif len(_vc_tx) == 1:
            st.caption("עונה אחת שמורה לתחום זה — הגרף יופיע לאחר עונה נוספת.")

        # --- אזור החדשות ---
        sector_news = {}   # title -> {"item": item, "symbols": [...]}
        for symbol, change in pairs:
            for item in get_news(symbol, limit=2):
                t = item["title"]
                if t in sector_news:
                    if symbol not in sector_news[t]["symbols"]:
                        sector_news[t]["symbols"].append(symbol)
                else:
                    sector_news[t] = {"item": item, "symbols": [symbol]}

        st.markdown(section_header("📰 חדשות אחרונות בתחום", "#a78bfa"), unsafe_allow_html=True)
        if len(sector_news) == 0:
            st.caption("אין חדשות זמינות כרגע לתחום הזה")
            return

        st.caption("לחצי לניתוח סנטימנט החדשות עם AI")
        titles_list = list(sector_news.keys())
        sig = titles_signature(titles_list)
        news_key = "news_analysis_" + sector_key(sector) + "_" + sig
        do_analyze = st.button("🧠 נתח חדשות", key="newsbtn_" + sector_key(sector))

        if do_analyze:
            titles_block = ""
            for t in titles_list:
                titles_block += "- " + t + "\n"
            with st.spinner("מנתח חדשות עם Gemini..."):
                st.session_state[news_key] = gemini_analyze_news(clean_name(sector), sig, titles_block)

        analysis = st.session_state.get(news_key)

        if analysis and "overall" in analysis:
            ov = analysis["overall"]
            ov_color = {"positive": "#22c55e", "negative": "#ef4444"}.get(ov, "#eab308")
            ov_label = {"positive": "🟢 חיובי", "negative": "🔴 שלילי"}.get(ov, "⚪ ניטרלי")
            st.markdown(
                "<div dir='rtl' style='text-align:right; color:" + ov_color +
                "; font-weight:700; margin:8px 0;'>סנטימנט חדשות בתחום: " + ov_label +
                " — " + html.escape(analysis.get("overall_note", "")) + "</div>",
                unsafe_allow_html=True,
            )
            if ov == "negative":
                st.markdown(
                    "<div dir='rtl' style='text-align:right; color:#ef4444; font-weight:700;'>⚠️ הערת אזהרה: יש חדשות שליליות בתחום הזה</div>",
                    unsafe_allow_html=True,
                )

        item_map = {}
        if analysis and "items" in analysis:
            for it in analysis["items"]:
                item_map[it.get("title", "")] = it

        for entry in sector_news.values():
            item = entry["item"]
            syms = entry["symbols"]
            date_part = ""
            if item["date"]:
                date_part = " (" + item["date"] + ")"
            info = item_map.get(item["title"])
            badge = ""
            if info:
                sent = info.get("sentiment", "neutral")
                emoji = {"positive": "🟢", "negative": "🔴"}.get(sent, "⚪")
                risk = " ⚠️ סיכון" if sent == "negative" else ""
                badge = emoji + risk + " "
            if item["link"]:
                title_html = ("<a href='" + html.escape(item["link"]).replace("'", "&#39;") +
                              "' target='_blank'>" + html.escape(item["title"]) + "</a>")
            else:
                title_html = html.escape(item["title"])
            summary_html = ""
            if info and info.get("summary"):
                summary_html = "<div style='color:#aaa; font-size:13px; margin-top:3px;'>" + html.escape(info["summary"]) + "</div>"
            syms_html = " · ".join("<b>" + s + "</b>" for s in syms)
            if len(syms) > 1:
                syms_html += " <span style='color:#6b7280; font-size:11px;'>🔗 משותף</span>"
            st.markdown(
                "<div dir='rtl' style='text-align:right; background:rgba(255,255,255,0.03); "
                "border:1px solid #333; border-radius:8px; padding:8px 10px; margin-top:6px;'>"
                + syms_html + " · " + badge + title_html + date_part + summary_html + "</div>",
                unsafe_allow_html=True,
            )



    st.markdown(
        "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
        "position:relative;'></div>",
        unsafe_allow_html=True,
    )

    # ======================================================
    # אזור 2 — מפת שרשרת הערך
    # ======================================================
    section_banner(2, 8, "🗺️", "מפת שרשרת הערך", "#8b5cf6",
                   subtitle="מי יושב איפה בשרשרת ומה זורם בין השלבים ",
                   period_dependent=True, period_label=period_label)
    _chain_mode_choice = st.radio(
        "תצוגת המפה:",
        ["📈 צבע לפי ביצועים", "⚡ צבע לפי רגישות CAPEX"],
        horizontal=True,
        key="chain_map_mode",
    )
    _chain_mode = "sensitivity" if "רגישות" in _chain_mode_choice else "perf"
    render_chain_map(period, mode=_chain_mode)

    st.markdown(
        "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
        "position:relative;'></div>",
        unsafe_allow_html=True,
    )
    _beta_scores     = scan_betas(_rating_universe)

    section_banner(3, 8, "🗺️", "מפת חום — דירוג שרשרת הערך", "#3b82f6",
                   subtitle="12 חוליות שרשרת הערך, מדורגות לפי המרחק מ-SOXX",
                   period_dependent=True, period_label=period_label)
    st.caption("מדורג לפי המרחק מ-SOXX — מי בביצועי יתר הגבוהים ביותר מול המדד. הגרף מציג את התמונה; לחצי על שורה בטבלה למטה כדי לפתוח פרטים.")

    # גרף עמודות אופקי לתצוגה: כל תחום לפי החציון שלו, ממוין מהגבוה לנמוך,
    # עם קו SOXX בולט. הגרף הוא תצוגה בלבד; האינטראקציה בטבלה שמתחתיו.
    heat_items = [(clean_name(r[6]), r[0]) for r in results]   # (שם נקי, חציון)
    all_sectors = [r[6] for r in results]

    with st.container(border=True):
        _heat_clicked = ranking_bar_chart(heat_items, "heat_bar_" + period, soxx_marker=soxx_change)
    if _heat_clicked:
        _heat_clean_to_sector = {clean_name(r[6]): r[6] for r in results}
        _heat_clicked_sector = _heat_clean_to_sector.get(_heat_clicked)
        if _heat_clicked_sector:
            _heat_open_key = "open_heat_" + sector_key(_heat_clicked_sector)
            if not st.session_state.get(_heat_open_key, False):
                st.session_state[_heat_open_key] = True
                st.rerun()

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # ---------- טבלת התחומים — טבלה צבעונית במסגרת + כפתור "פתח" אפור קטן ----------
    # כל שורה מוצגת כ-HTML צבעוני, ולצידה (משמאל) כפתור "פתח/סגור" אפור קטן.
    # מצב הפתיחה נשמר לפי זהות התחום (sector_key) — יציב בין תקופות.
    soxx_hdr = ""
    if soxx_change is not None:
        soxx_hdr = "SOXX " + ("+" if soxx_change >= 0 else "") + str(round(soxx_change, 1)) + "%"

    _sentiment_data = load_sentiment()
    _sent_season = latest_season_with_data(_sentiment_data)
    _sent_cur_s = current_season()
    if _sent_cur_s > _sent_season:
        st.caption("⚠️ סנטימנט: מציג נתוני " + _sent_season + " · עונת " + _sent_cur_s + " טרם נותחה")
    else:
        st.caption("📊 סנטימנט עונה: " + _sent_season)

    _heat_sort = st.radio(
        "מיין לפי:",
        ["📈 מרחק מ-SOXX", "🧠 סנטימנט דוחות", "📊 ציון אנליסטים", "🎯 בטא"],
        horizontal=True,
        key="heat_sort_mode",
    )
    if _heat_sort == "🧠 סנטימנט דוחות":
        st.caption(
            "ℹ️ תחומים ללא דוחות מנותחים מוצגים בתחתית (—). "
            "שים לב שהכיסוי חלקי: חלק מהתחומים כוללים חברות שאינן ב-CORE_COMPANIES ולעולם לא יקבלו ציון סנטימנט."
        )
        _heat_sent_cache = {
            row[6]: (None if row[6].startswith("11.") else value_chain_sentiment(row[6], _sent_season, _sentiment_data))
            for row in results
        }
        def _heat_sent_key(row):
            agg = _heat_sent_cache[row[6]]
            return (agg is not None, agg["score"] if agg is not None else 0.0)
        _display_results = sorted(results, key=_heat_sent_key, reverse=True)
    elif _heat_sort == "📊 ציון אנליסטים":
        def _heat_analyst_key(row):
            agg = analyst_group_score(value_chain.get(row[6], []), _analyst_scores)
            sc = agg["score"] if agg and agg["score"] is not None else None
            return (sc is not None, sc if sc is not None else 0.0)
        _display_results = sorted(results, key=_heat_analyst_key, reverse=True)
    elif _heat_sort == "🎯 בטא":
        def _heat_beta_key(row):
            agg = beta_group_score(value_chain.get(row[6], []), _beta_scores)
            b = agg["beta"] if agg and agg["beta"] is not None else None
            return (b is not None, b if b is not None else 0.0)
        _display_results = sorted(results, key=_heat_beta_key, reverse=True)
    else:
        _display_results = results

    _chain11_sent_span = (
        "<span style='width:110px; text-align:center; display:inline-block;'"
        " title='חוליה תומכת. אינה נמנית עם מדד SOXX ואינה מתואמת איתו. "
        "תוצאות הדוחות בתחום מונעות מרגולציה, מתמחור אנרגיה ומחוזי אספקה ארוכי טווח, "
        "ולא ממחזור הזמנות השבבים, ולכן ניתוח הפתעות הדוח אינו רלוונטי עבורה ואינו מחושב.'>"
        "<span style='font-size:11px; color:#6b7280;'>חוליה תומכת</span>"
        "</span>"
    )

    with st.container(border=True):
        # כותרת עמודות
        h1, h2 = st.columns([9, 1.3])
        with h1:
            _h_soxx_active   = (_heat_sort == "📈 מרחק מ-SOXX")
            _h_sent_active   = (_heat_sort == "🧠 סנטימנט דוחות")
            _h_analyst_active = (_heat_sort == "📊 ציון אנליסטים")
            _h_beta_active   = (_heat_sort == "🎯 בטא")
            st.markdown(
                "<div dir='rtl' style='display:flex; align-items:center; padding:4px 10px; "
                "font-size:12px; color:#9ca3af; font-weight:600;'>"
                "<span style='width:32px; text-align:right;'>#</span>"
                + col_header("תחום", flex=True)
                + col_header("חציון", width="80px")
                + col_header("מול המדד " + soxx_hdr, active=_h_soxx_active, width="170px")
                + col_header("רוחב", width="90px")
                + col_header("סנטימנט הדוח האחרון", active=_h_sent_active, width="110px")
                + col_header("ציון אנליסטים", active=_h_analyst_active, width="105px")
                + col_header("בטא (3ח')", active=_h_beta_active, width="95px")
                + "</div>",
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)

        rank = 1
        _partial_coverage_seen = False
        for median, average, up, down, total, breadth, sector, pairs in _display_results:
            med_color = "#22c55e" if median >= 0 else "#ef4444"
            med_txt = ("+" if median >= 0 else "") + str(round(median, 1)) + "%"
            if soxx_change is not None:
                rel = median - soxx_change
                if rel >= 0:
                    vs_color = "#22c55e"
                    vs_txt = "▲ ביצועי יתר ב-" + str(round(rel, 1)) + " נק'"
                else:
                    vs_color = "#ef4444"
                    vs_txt = "▼ ביצועי חסר ב-" + str(round(abs(rel), 1)) + " נק'"
            else:
                vs_color = "#9ca3af"
                vs_txt = "—"
            bcolor = "#22c55e" if breadth >= BROAD_THRESHOLD else ("#eab308" if breadth >= 0.4 else "#ef4444")
            _defined = len(value_chain.get(sector, []))
            _partial = period in DAILY_PERIODS and total < _defined
            if _partial:
                _partial_coverage_seen = True

            open_key = "open_heat_" + sector_key(sector)
            is_open = st.session_state.get(open_key, False)
            row_bg = "rgba(96,165,250,0.12)" if is_open else "transparent"

            if sector.startswith("11."):
                _sent_span = _chain11_sent_span
            else:
                _agg = value_chain_sentiment(sector, _sent_season, _sentiment_data)
                _sent_span = sentiment_cell_html(_agg, wrapper="span")
            _analyst_agg  = analyst_group_score(value_chain.get(sector, []), _analyst_scores)
            _analyst_span = analyst_cell_html(_analyst_agg, _analyst_med, wrapper="span")
            _beta_agg     = beta_group_score(value_chain.get(sector, []), _beta_scores)
            _beta_span    = beta_cell_html(_beta_agg, wrapper="span")

            if is_open:
                _row_bg_val = row_bg
                _row_border_r = "none"
            else:
                _row_bg_val = "transparent"
                _row_border_r = "none"

            row_col, btn_col = st.columns([9, 1.3])
            with row_col:
                st.markdown(
                    "<div dir='rtl' style='display:flex; align-items:center; padding:8px 10px; "
                    "background:" + _row_bg_val + "; border-top:1px solid rgba(255,255,255,0.06); "
                    "border-right:" + _row_border_r + "; "
                    "border-radius:6px; min-height:34px;'>"
                    "<span style='width:32px; text-align:right; color:#9ca3af;'>" + str(rank) + "</span>"
                    "<span style='flex:1; text-align:right; font-weight:600;'>" + clean_name(sector) + "</span>"
                    "<span style='width:80px; text-align:center; color:" + med_color + "; font-weight:700;'>" + med_txt + "</span>"
                    "<span style='width:170px; text-align:center; color:" + vs_color + "; font-weight:600; font-size:14px;'>" + vs_txt + "</span>"
                    "<span style='width:90px; text-align:center; color:" + bcolor + "; font-size:14px;'>"
                    + str(up) + "/" + str(total) + " עלו"
                    + ("&nbsp;<span style='font-size:10px; color:#9ca3af;'>(" + str(total) + "/" + str(_defined) + ")</span>" if _partial else "")
                    + "</span>"
                    + _sent_span
                    + _analyst_span
                    + _beta_span +
                    "</div>",
                    unsafe_allow_html=True,
                )
            with btn_col:
                btn_txt = "סגור" if is_open else "פתח"
                if st.button(btn_txt, key="heatrow_" + sector_key(sector),
                             width='stretch', type="tertiary"):
                    st.session_state[open_key] = not is_open
                    st.rerun()

            if is_open:
                with st.container(border=True):
                    if sector.startswith("11."):
                        st.markdown(
                            "<div dir='rtl' style='text-align:right; font-size:12px; color:#9ca3af; "
                            "background:rgba(107,114,128,0.08); border:1px solid rgba(107,114,128,0.20); "
                            "border-radius:6px; padding:8px 12px; margin-bottom:4px;'>"
                            "חוליה תומכת. אינה נמנית עם מדד "
                            "<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>SOXX</span>"
                            " ואינה מתואמת איתו. "
                            "תוצאות הדוחות בתחום מונעות מרגולציה, מתמחור אנרגיה ומחוזי אספקה ארוכי טווח, "
                            "ולא ממחזור הזמנות השבבים, ולכן ניתוח הפתעות הדוח אינו רלוונטי עבורה ואינו מחושב."
                            "</div>",
                            unsafe_allow_html=True,
                        )
                    render_domain_detail(sector, pairs, period,
                                         analyst_scores=_analyst_scores,
                                         analyst_med=_analyst_med,
                                         beta_scores=_beta_scores)

            rank = rank + 1

    if _partial_coverage_seen:
        st.caption(
            "⚠ חוליות שמוצג בהן מספר בסוגריים בעמודת הרוחב (למשל 4/5) נכללו בחלקן בלבד. "
            "בתקופות יומיות (Online ו-Last Close) טיקרים מבורסות אסייתיות אינם נכללים בשל הפרשי שעות מסחר."
        )
    st.caption(
        "ציון אנליסטים 1–5: 5=קנייה חזקה · 4=קנייה · 3=החזקה · 2=מכירה · 1=מכירה חזקה "
        "· ממוצע משוקלל לפי מספר האנליסטים בכל חברה · ירוק/אדום = חריגה מחציון הסקטור ב-±0.15"
    )
    st.caption(
        "בטא (3ח') מול SOXX: >1 = החוליה מגבירה את תנועת המדד, <1 = ממתנת · "
        "חציון החברות בתחום · חלון: 3 חודשים, יומי, ואינו מגיב לבורר התקופה"
    )

    # ---------- מטריצת קורלציה בין חוליות (בלוק ביניים בתוך Zone 3 — לא אזור נפרד) ----------
    st.markdown(
        "<div style='margin:28px 0 20px; border-top:1px solid rgba(255,255,255,0.08); "
        "position:relative;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(section_header("🔗 מטריצת קורלציה בין חוליות שרשרת הערך", "#14b8a6"),
                unsafe_allow_html=True)
    # online/lastclose: לא נתונים יומיים בכלל (סשן תוך-יומי בודד). 5d: נכלל כאן
    # במפורש ולא נשען רק על סף CORR_MIN_POINTS — לחוליות עם מניה מבורסה אחרת
    # (כמו .KS), האינטרפולציה של build_chart על איחוד התאריכים של כמה מניות
    # יכולה "למתוח" את חלון 5d למספר שורות שחוצה את הסף במקרה, ומייצרת מטריצה
    # דלילה כמעט-חסרת-משמעות (1-2 חוליות בלבד) במקום ההודעה הנקייה.
    _corr_excluded_periods = {"online", "lastclose", "5d"}
    if period in _corr_excluded_periods:
        st.caption(
            "ℹ️ מטריצת הקורלציה זמינה רק לתקופות ארוכות מספיק לתשואות יומיות "
            "משמעותיות (לא Online / Last Close / 5D) — נסי 1M ומעלה."
        )
    else:
        _corr_df, _corr_dropped = compute_sector_correlation(period)
        if _corr_df.empty or len(_corr_df.columns) < 2:
            st.caption(
                "ℹ️ התקופה קצרה מדי לחישוב קורלציה משמעותית בין חוליות (נדרשות "
                "לפחות כ-" + str(CORR_MIN_POINTS) + " נקודות תשואה יומית) — "
                "נסי תקופה ארוכה יותר (למשל 1M ומעלה)."
            )
        else:
            _corr_labels = [
                (f"<b>{clean_name(s)}</b>" if s == BENCHMARK else clean_name(s))
                for s in _corr_df.columns
            ]
            _corr_z = _corr_df.values
            _corr_text = [[f"{v:.2f}" for v in row] for row in _corr_z]
            _corr_fig = go.Figure(data=go.Heatmap(
                z=_corr_z,
                x=_corr_labels,
                y=_corr_labels,
                zmin=-1, zmax=1, zmid=0,
                colorscale="RdYlGn",
                text=_corr_text, texttemplate="%{text}",
                textfont=dict(size=11),
                hovertemplate="%{y}<br>%{x}<br>קורלציה: %{z:.2f}<extra></extra>",
                colorbar=dict(title="קורלציה<br>(ירוק=גבוה, אדום=נמוך)", tickfont=dict(size=11)),
            ))
            _corr_fig.update_layout(
                height=max(500, 40 * len(_corr_labels) + 200),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=160, l=170, r=20),
                xaxis=dict(tickangle=-45, automargin=True, side="bottom"),
                yaxis=dict(automargin=True, autorange="reversed"),
            )
            with st.container(border=True):
                st.plotly_chart(
                    _corr_fig, width='stretch',
                    key="zb_corr_" + period,
                )
            st.caption(
                "כל תא = קורלציה (Pearson) בין תשואות יומיות של חציון הביצועים של שתי "
                "החוליות (או מול SOXX עצמו, בשורה/עמודה המודגשות), לאורך התקופה המסוננת · "
                "ירוק/קרוב ל-1 = נעות ביחד · לבן/קרוב ל-0 = עצמאיות · אדום/שלילי = נעות "
                "הפוך. חוליית \"חשמל ואנרגיה\" (אם מופיעה) אינה חלק ממדד SOXX ואינה "
                "מתואמת עם שאר הסקטור — ניתן לראות זאת ישירות בעמודת/שורת SOXX: קורלציה "
                "נמוכה מול שאר החוליות ומול SOXX עצמו צפויה, לא באג."
            )
            if _corr_dropped:
                st.caption(
                    "הושמטו ממטריצת הקורלציה (אין מספיק נתונים בתקופה זו): "
                    + ", ".join(clean_name(s) for s in _corr_dropped)
                )

    # ---------- צלילה לתחום ----------
    st.markdown(
        "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
        "position:relative;'></div>",
        unsafe_allow_html=True,
    )
    section_banner(4, 8, "🔍", "צלילה לתחום — השוואת מניות", "#22c55e",
                   subtitle="בחרי תחום כדי להשוות בין המניות שבו, מול חציון התחום ומול SOXX",
                   period_dependent=True, period_label=period_label)

    sector_names = []
    for r in results:
        sector_names.append(r[6])

    chosen = st.selectbox("בחרי תחום:", sector_names, format_func=clean_name)

    # guard: מונע קריסה כשהתחום לא קיים ב-value_chain (שם ישן, session_state עמיד)
    _z3_tickers = value_chain.get(chosen) if (chosen and chosen in value_chain) else []
    if not sector_names:
        st.warning("לא הצלחנו למשוך נתוני מניות כרגע — נסי לרענן בעוד דקה.")
    elif not _z3_tickers:
        st.info("בחרי תחום מהרשימה.")

    _z3_intraday = period in DAILY_PERIODS
    _z3_skip = period == "lastclose"
    _z3_xfmt = "%H:%M" if _z3_intraday else "%d/%m/%Y"
    chart_data = build_chart(_z3_tickers, period, intraday=_z3_intraday, skip_current_day=_z3_skip)
    if chart_data.empty:
        st.warning("אין מספיק נתונים לתחום הזה")
    else:
        # פלטת צבעים משותפת לשני הטאבים לעקביות ויזואלית
        palette = ["#60a5fa", "#f472b6", "#34d399", "#fbbf24", "#a78bfa",
                   "#fb7185", "#22d3ee", "#a3e635", "#fb923c", "#e879f9",
                   "#4ade80", "#38bdf8", "#facc15", "#f87171", "#c084fc"]

        chosen_pairs = get_changes(_z3_tickers, period)
        _z3_soxx_chg = get_change(BENCHMARK, period)

        if chosen.startswith("11."):
            st.markdown(
                "<div dir='rtl' style='text-align:right; font-size:12px; color:#9ca3af;"
                " background:rgba(107,114,128,0.08); border:1px solid rgba(107,114,128,0.20);"
                " border-radius:6px; padding:8px 12px; margin-bottom:8px;'>"
                "חוליה תומכת. אינה נמנית עם מדד "
                "<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>SOXX</span>"
                " ואינה מתואמת איתו. "
                "תוצאות הדוחות בתחום מונעות מרגולציה, מתמחור אנרגיה ומחוזי אספקה ארוכי טווח, "
                "ולא ממחזור הזמנות השבבים, ולכן ניתוח הפתעות הדוח אינו רלוונטי עבורה ואינו מחושב."
                "</div>",
                unsafe_allow_html=True,
            )

        _z3_tab_perf, _z3_tab_sent, _z3_tab_beta, _z3_tab_roll, _z3_tab_cmproll = st.tabs(
            ["📈 ביצועי מניות", "🧠 סנטימנט התחום", "🎯 בטא מול תשואה", "📉 בטא מתגלגלת",
             "📉 השוואת בטא מתגלגלת"]
        )

        with _z3_tab_perf:
            st.caption("ביצועי המניות מול חציון התחום ומול מדד SOXX — מנורמל ל-100 — בתקופות יומיות מול סגירת היום הקודם, בשאר התקופות מנקודת הפתיחה של התקופה. לחצי על מניה במקרא כדי להסתיר/להציג אותה.")

            date_index = chart_data.index
            median_series = chart_data.median(axis=1)
            if _z3_intraday:
                soxx_close2, _, _ = get_last_session_intraday(BENCHMARK, _z3_skip)
            else:
                soxx_close2 = get_history(BENCHMARK, period)

            def ret_html(ret_series):
                out = []
                for v in ret_series:
                    color = "#22c55e" if v >= 0 else "#ef4444"
                    sign = "+" if v >= 0 else ""
                    out.append("<span style='color:" + color + "'>" + sign + format(v, ".2f") + "%</span>")
                return out

            fig = go.Figure()
            fig.add_hline(y=100, line_dash="dot", line_color="#888", line_width=1)

            for i, symbol in enumerate(chart_data.columns):
                col_color = palette[i % len(palette)]
                series = chart_data[symbol]
                ret = series - 100
                fig.add_trace(go.Scatter(
                    x=date_index, y=series, name=symbol, mode="lines",
                    line=dict(color=col_color, width=1.6), opacity=0.85,
                    customdata=ret_html(ret),
                    hovertemplate="<b>" + symbol + "</b><br>%{x|" + _z3_xfmt + "}<br>"
                                  "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
                ))

            median_ret = median_series - 100
            fig.add_trace(go.Scatter(
                x=date_index, y=median_series, name="חציון התחום", mode="lines",
                line=dict(color="#ffffff", width=4),
                customdata=ret_html(median_ret),
                hovertemplate="<b>חציון התחום</b><br>%{x|" + _z3_xfmt + "}<br>"
                              "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
            ))

            soxx_holdings_chart = build_chart(SOXX_HOLDINGS, period, intraday=_z3_intraday, skip_current_day=_z3_skip)
            if not soxx_holdings_chart.empty:
                soxx_median_series = soxx_holdings_chart.median(axis=1)
                soxx_median_ret = soxx_median_series - 100
                fig.add_trace(go.Scatter(
                    x=soxx_median_series.index, y=soxx_median_series, name="חציון SOXX", mode="lines",
                    line=dict(color="#ef4444", width=4, dash="dot"),
                    customdata=ret_html(soxx_median_ret),
                    hovertemplate="<b>חציון SOXX</b><br>%{x|" + _z3_xfmt + "}<br>"
                                  "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
                ))

            if soxx_close2 is not None:
                soxx_norm2 = soxx_close2 / soxx_close2.iloc[0] * 100
                soxx_ret = soxx_norm2 - 100
                fig.add_trace(go.Scatter(
                    x=soxx_norm2.index, y=soxx_norm2, name="SOXX", mode="lines",
                    line=dict(color="#f59e0b", width=4, dash="dash"),
                    customdata=ret_html(soxx_ret),
                    visible="legendonly",
                    hovertemplate="<b>SOXX</b><br>%{x|" + _z3_xfmt + "}<br>"
                                  "ערך: %{y:.1f}<br>תשואה: %{customdata}<extra></extra>",
                ))

            fig.update_layout(
                height=460,
                hovermode="closest",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=40, l=50, r=40),
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.08,
                            title="מניה", font=dict(size=12),
                            bgcolor="rgba(255,255,255,0.04)",
                            bordercolor="rgba(255,255,255,0.20)", borderwidth=1),
                yaxis=dict(title="מנורמל ל-100", gridcolor="rgba(255,255,255,0.08)"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                           tickformat=(_z3_xfmt if _z3_intraday else None)),
            )
            with st.container(border=True):
                st.plotly_chart(fig, width='stretch')

            st.subheader("טבלת תשואות")
            st.markdown(returns_table_html(chosen_pairs, beta_scores=_beta_scores), unsafe_allow_html=True)
            st.caption("בטא מול SOXX: מעל 1 = מניה מגבירה את תנועת המדד · מתחת ל-1 = ממתנת · "
                       "חלון: 3 חודשים, יומי · אינה מגיבה לבורר התקופה")
            if period in DAILY_PERIODS and len(chosen_pairs) < len(_z3_tickers):
                st.caption(
                    "⚠ " + str(len(chosen_pairs)) + " מתוך " + str(len(_z3_tickers)) + " טיקרים בחוליה נכללו בחישוב. "
                    "בתקופות יומיות (Online ו-Last Close) טיקרים מבורסות אסייתיות אינם נכללים בשל הפרשי שעות מסחר."
                )

            soxx_change2 = _z3_soxx_chg
            if soxx_change2 is not None and len(chosen_pairs) > 0:
                sector_median = statistics.median([c for s, c in chosen_pairs])
                diff = sector_median - soxx_change2
                better = "📈 התחום בביצועי יתר מול המדד" if diff >= 0 else "📉 התחום בביצועי חסר מול המדד"
                st.info("חציון התחום: " + str(round(sector_median, 1)) + "%  |  SOXX: " +
                        str(round(soxx_change2, 1)) + "%  →  " + better + " (" + str(round(diff, 1)) + " נק')")

        with _z3_tab_beta:
            _scatter_pts = [
                (sym, chg, _beta_scores[sym]["beta"], _beta_scores[sym].get("r2", 1.0))
                for sym, chg in chosen_pairs
                if sym in _beta_scores and _beta_scores[sym].get("beta") is not None
            ]
            _no_beta_syms = [sym for sym, _ in chosen_pairs if sym not in _beta_scores]
            if len(_scatter_pts) < 2:
                st.caption("אין מספיק נתוני בטא להציג גרף פיזור לתחום זה.")
            else:
                _sc_syms   = [p[0] for p in _scatter_pts]
                _sc_rets   = [p[1] for p in _scatter_pts]
                _sc_betas  = [p[2] for p in _scatter_pts]
                _sc_r2s    = [p[3] for p in _scatter_pts]
                _sc_colors = [beta_color(b) for b in _sc_betas]
                _sc_labels = [
                    sym + ("*" if r2 < BETA_MIN_R2 else "")
                    for sym, r2 in zip(_sc_syms, _sc_r2s)
                ]
                _sc_warn = [
                    " ⚠️ R² נמוך — הבטא רועשת" if r2 < BETA_MIN_R2 else ""
                    for r2 in _sc_r2s
                ]
                if _z3_soxx_chg is not None:
                    _sc_vs = [round(ret - _z3_soxx_chg, 1) for ret in _sc_rets]
                    _sc_customdata = [
                        [round(r2, 2), warn, vs]
                        for r2, warn, vs in zip(_sc_r2s, _sc_warn, _sc_vs)
                    ]
                    _hover = (
                        "<b>%{text}</b><br>"
                        "בטא: %{x:.2f}<br>"
                        "תשואה: %{y:.1f}%<br>"
                        "מול SOXX: %{customdata[2]:+.1f} נק'<br>"
                        "R²: %{customdata[0]:.2f}%{customdata[1]}"
                        "<extra></extra>"
                    )
                else:
                    _sc_customdata = [
                        [round(r2, 2), warn]
                        for r2, warn in zip(_sc_r2s, _sc_warn)
                    ]
                    _hover = (
                        "<b>%{text}</b><br>"
                        "בטא: %{x:.2f}<br>"
                        "תשואה: %{y:.1f}%<br>"
                        "R²: %{customdata[0]:.2f}%{customdata[1]}"
                        "<extra></extra>"
                    )
                _sc_fig = go.Figure()
                _sc_fig.add_trace(go.Scatter(
                    x=_sc_betas,
                    y=_sc_rets,
                    mode="markers+text",
                    text=_sc_labels,
                    textposition="top center",
                    textfont=dict(size=11, color="#e5e7eb"),
                    marker=dict(size=10, color=_sc_colors, line=dict(width=1, color="#374151")),
                    customdata=_sc_customdata,
                    hovertemplate=_hover,
                    showlegend=False,
                ))
                _sc_fig.add_hline(y=0, line_dash="solid", line_color="rgba(255,255,255,0.45)", line_width=2.5)
                _sc_fig.add_vline(x=1, line_dash="dash", line_color="#f97316", line_width=2)
                if _z3_soxx_chg is not None:
                    _soxx_dir_color = "#22c55e" if _z3_soxx_chg >= 0 else "#ef4444"
                    _sc_fig.add_hline(y=_z3_soxx_chg, line_dash="dash", line_color=_soxx_dir_color, line_width=2)
                    _sc_fig.add_trace(go.Scatter(
                        x=[1.0], y=[_z3_soxx_chg], mode="markers+text",
                        marker=dict(symbol="diamond", size=16, color=_soxx_dir_color,
                                    line=dict(color="#1e2533", width=2)),
                        text=["SOXX"], textposition="bottom center",
                        textfont=dict(size=12, color=_soxx_dir_color),
                        hovertemplate=(
                            "<b>SOXX</b><br>בטא: 1.00 (הגדרה)<br>"
                            "תשואה: %{y:.1f}%<extra></extra>"
                        ),
                        showlegend=False,
                    ))
                _y_vals = list(_sc_rets)
                if _z3_soxx_chg is not None:
                    _y_vals.append(_z3_soxx_chg)
                _y_pad = (max(_y_vals) - min(_y_vals)) * 0.15 + 1.0
                _sc_fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(title=rtl_text("בטא מול SOXX · חלון: 3 חודשים, יומי")),
                    yaxis=dict(
                        title=rtl_text("תשואה בתקופה (%)"),
                        range=[min(_y_vals) - _y_pad, max(_y_vals) + _y_pad],
                    ),
                    margin=dict(l=40, r=20, t=40, b=40),
                )
                st.markdown(
                    "<div dir='rtl' style='text-align:right; font-size:14px; font-weight:600;"
                    " color:#f3f4f6; margin-bottom:4px;'>"
                    "בטא מול תשואה — " + clean_name(chosen) + "</div>",
                    unsafe_allow_html=True,
                )
                st.plotly_chart(_sc_fig, width='stretch', key="z3_beta_" + sector_key(chosen))
                st.caption(
                    "הקו האופקי המקווקו = תשואת SOXX (ירוק = עלה · אדום = ירד) · האנכי = בטא 1 · הצטלבותם היא המדד עצמו · "
                    "מעל הקו = ביצועי יתר מול הסקטור · מימין לקו = מגבירת תנועה · "
                    "הקו האפור הרציף = אפס תשואה · * = R² נמוך, הבטא רועשת"
                )
            if _no_beta_syms:
                st.caption("ללא נתוני בטא: " + ", ".join(_no_beta_syms))

        with _z3_tab_roll:
            _rb_short_periods = {"online", "lastclose", "5d", "1mo"}
            if period in _rb_short_periods:
                st.caption(
                    "ℹ️ התקופה קצרה מחלון הבטא (3 חודשים) — הגרף המתגלגל זמין מ-3M ומעלה."
                )
            else:
                _rb_today = ny_now().date()
                # measure_start — אותה הגדרה בדיוק כמו ב-_anchor_index/_period_to_start
                # (תחילת התקופה המסוננת, ללא הבאפר של שליפת הנתונים)
                _rb_months = {"3mo": 3, "6mo": 6, "1y": 12, "5y": 60}
                if period == "ytd":
                    _rb_measure_start = _rb_today.replace(month=1, day=1)
                else:
                    _rb_measure_start = (
                        pd.Timestamp(_rb_today) - pd.DateOffset(months=_rb_months.get(period, 3))
                    ).date()
                _rb_fetch_start = _rb_measure_start - timedelta(days=BETA_ROLL_FETCH_PAD_DAYS)
                _rb_bench_close = _get_daily_close_for_rolling(BENCHMARK, _rb_fetch_start)

                if _rb_bench_close is None:
                    st.caption("לא הצלחנו למשוך נתוני SOXX לחישוב הבטא המתגלגלת כרגע.")
                else:
                    _rb_start_ts = pd.Timestamp(_rb_measure_start)
                    _rb_series_map = {}
                    _rb_no_data = []
                    for _rb_sym in _z3_tickers:
                        _rb_s = _rolling_beta_series(_rb_sym, _rb_bench_close, _rb_fetch_start)
                        if _rb_s is None:
                            _rb_no_data.append(_rb_sym)
                            continue
                        _rb_s_clip = _rb_s[_rb_s.index >= _rb_start_ts]
                        if len(_rb_s_clip) >= 2:
                            _rb_series_map[_rb_sym] = _rb_s_clip
                        else:
                            _rb_no_data.append(_rb_sym)

                    # התקופה בפועל קצרה מדי (למשל YTD בתחילת ינואר) — נופל לאותה הודעה
                    # כמו התקופות הקצרות המפורשות למעלה, במקום קו כמעט-שטוח ומטעה.
                    if not _rb_series_map:
                        st.caption(
                            "ℹ️ התקופה קצרה מחלון הבטא (3 חודשים) — הגרף המתגלגל זמין מ-3M ומעלה."
                        )
                    else:
                        _rb_df = pd.concat(_rb_series_map, axis=1)
                        _rb_median = _rb_df.median(axis=1, skipna=True)

                        _rb_fig = go.Figure()
                        _rb_fig.add_hline(y=1, line_dash="dash", line_color="#f97316", line_width=2)
                        for _rb_i, (_rb_sym, _rb_s_clip) in enumerate(_rb_series_map.items()):
                            _rb_color = palette[_rb_i % len(palette)]
                            _rb_fig.add_trace(go.Scatter(
                                x=_rb_s_clip.index, y=_rb_s_clip.values, name=_rb_sym, mode="lines",
                                line=dict(color=_rb_color, width=1.5), opacity=0.85,
                                hovertemplate="<b>" + _rb_sym + "</b><br>%{x|%d/%m/%Y}<br>בטא: %{y:.2f}<extra></extra>",
                            ))
                        _rb_fig.add_trace(go.Scatter(
                            x=_rb_median.index, y=_rb_median.values, name="חציון התחום", mode="lines",
                            line=dict(color="#ffffff", width=4),
                            hovertemplate="<b>חציון התחום</b><br>%{x|%d/%m/%Y}<br>בטא: %{y:.2f}<extra></extra>",
                        ))
                        _rb_fig.update_layout(
                            height=420, template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            margin=dict(t=20, b=40, l=50, r=40),
                            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.08,
                                        title="מניה", font=dict(size=12),
                                        bgcolor="rgba(255,255,255,0.04)",
                                        bordercolor="rgba(255,255,255,0.20)", borderwidth=1),
                            yaxis=dict(title="בטא (חלון 3 חודשים)", gridcolor="rgba(255,255,255,0.08)"),
                            xaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickformat="%d/%m/%Y"),
                        )
                        with st.container(border=True):
                            st.plotly_chart(
                                _rb_fig, width='stretch',
                                key="z3_rollbeta_" + sector_key(chosen) + "_" + period,
                            )
                        st.caption(
                            "כל נקודה = בטא מול SOXX בחלון: 3 חודשים, יומי (קלנדרי, ~63 ימי מסחר) שהסתיים "
                            "באותו יום — לא הבטא המצטברת של כל התקופה. קו לבן עבה = חציון התחום · "
                            "קו כתום מקווקו = בטא=1 (SOXX עצמו)."
                        )
                        if _rb_no_data:
                            st.caption("ללא מספיק היסטוריה לבטא מתגלגלת: " + ", ".join(_rb_no_data))

        with _z3_tab_cmproll:
            # השוואת בטא מתגלגלת בין כמה חוליות: החוליה הנבחרת (chosen) למעלה תמיד
            # מוצגת — זה כל הרעיון של "ברירת מחדל = chosen, הבורר רק מוסיף". אותה
            # מתמטיקה בדיוק כמו _z3_tab_roll למעלה ו-_rolling_beta_series/median —
            # לא הגדרת בטא חדשה, רק מקור בחירת החוליות שונה (chosen+multiselect
            # במקום multiselect עצמאי).
            _cmp_short_periods = {"online", "lastclose", "5d", "1mo"}
            if period in _cmp_short_periods:
                st.caption(
                    "ℹ️ התקופה קצרה מחלון הבטא (3 חודשים) — הגרף המתגלגל זמין מ-3M ומעלה."
                )
            else:
                st.caption(
                    "מוצגת החוליה הנבחרת למעלה (" + clean_name(chosen) + ") · אפשר להוסיף עד 5 "
                    "חוליות נוספות להשוואה בבורר שלמטה."
                )
                _cmp_extra = st.multiselect(
                    "הוסיפי חוליות נוספות להשוואה (אופציונלי):",
                    list(value_chain.keys()),
                    default=[],
                    format_func=clean_name,
                    max_selections=5,
                    key="z3_cmproll_extra",
                )
                # chosen תמיד ראשון ותמיד בפנים, גם אם הבורר הנוסף ריק — זו הדרישה
                # המרכזית של המבנה הזה. dict.fromkeys משמר סדר ומסנן כפילות (אם
                # chosen נבחר גם בבורר הנוסף, בטעות או בכוונה).
                _cmp_sectors = list(dict.fromkeys([chosen] + _cmp_extra))

                _cmp_today = ny_now().date()
                _cmp_months = {"3mo": 3, "6mo": 6, "1y": 12, "5y": 60}
                if period == "ytd":
                    _cmp_measure_start = _cmp_today.replace(month=1, day=1)
                else:
                    _cmp_measure_start = (
                        pd.Timestamp(_cmp_today) - pd.DateOffset(months=_cmp_months.get(period, 3))
                    ).date()
                _cmp_fetch_start = _cmp_measure_start - timedelta(days=BETA_ROLL_FETCH_PAD_DAYS)
                _cmp_bench_close = _get_daily_close_for_rolling(BENCHMARK, _cmp_fetch_start)

                if _cmp_bench_close is None:
                    st.caption("לא הצלחנו למשוך נתוני SOXX לחישוב הבטא המתגלגלת כרגע.")
                else:
                    _cmp_start_ts = pd.Timestamp(_cmp_measure_start)
                    _cmp_series_cache = {}

                    def _cmp_get_series(sym):
                        if sym not in _cmp_series_cache:
                            _s = _rolling_beta_series(sym, _cmp_bench_close, _cmp_fetch_start)
                            if _s is not None:
                                _s = _s[_s.index >= _cmp_start_ts]
                            _cmp_series_cache[sym] = _s if (_s is not None and len(_s) >= 2) else None
                        return _cmp_series_cache[sym]

                    _cmp_fig = go.Figure()
                    _cmp_fig.add_hline(y=1, line_dash="dash", line_color="#f97316", line_width=2)
                    _cmp_empty_sectors = []
                    for _cmp_i, _cmp_sector in enumerate(_cmp_sectors):
                        _cmp_sector_series = {}
                        for _cmp_sym in value_chain.get(_cmp_sector, []):
                            _cmp_s = _cmp_get_series(_cmp_sym)
                            if _cmp_s is not None:
                                _cmp_sector_series[_cmp_sym] = _cmp_s
                        if not _cmp_sector_series:
                            _cmp_empty_sectors.append(_cmp_sector)
                            continue
                        # חציון הבטאות המתגלגלות של המניות הזמינות בכל תאריך — בדיוק
                        # כמו beta_group_score (statistics.median) על הבטא הסטטית.
                        _cmp_df = pd.concat(_cmp_sector_series, axis=1)
                        _cmp_median = _cmp_df.median(axis=1, skipna=True).dropna()
                        if len(_cmp_median) < 2:
                            _cmp_empty_sectors.append(_cmp_sector)
                            continue
                        _cmp_color = palette[_cmp_i % len(palette)]
                        _cmp_fig.add_trace(go.Scatter(
                            x=_cmp_median.index, y=_cmp_median.values, name=clean_name(_cmp_sector),
                            mode="lines", line=dict(color=_cmp_color, width=3),
                            hovertemplate="<b>" + clean_name(_cmp_sector) + "</b><br>%{x|%d/%m/%Y}<br>"
                                          "בטא: %{y:.2f}<extra></extra>",
                        ))

                    # add_hline מוסיף shape, לא trace — ==0 ולא <=1: קו חוליה יחיד
                    # לגיטימי (chosen לבד, בלי תוספות) הוא trace בודד ולא אמור להיחסם.
                    if len(_cmp_fig.data) == 0:
                        st.caption(
                            "ℹ️ התקופה קצרה מחלון הבטא (3 חודשים) — הגרף המתגלגל זמין מ-3M ומעלה."
                        )
                    else:
                        _cmp_fig.update_layout(
                            height=440, template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            margin=dict(t=20, b=40, l=50, r=40),
                            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02,
                                        title="חוליה", font=dict(size=12),
                                        bgcolor="rgba(255,255,255,0.04)",
                                        bordercolor="rgba(255,255,255,0.20)", borderwidth=1),
                            yaxis=dict(title="בטא (חלון 3 חודשים)", gridcolor="rgba(255,255,255,0.08)"),
                            xaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickformat="%d/%m/%Y"),
                        )
                        with st.container(border=True):
                            st.plotly_chart(
                                _cmp_fig, width='stretch',
                                key="z3_cmproll_" + period + "_" + "_".join(sector_key(s) for s in _cmp_sectors),
                            )
                        st.caption(
                            "כל קו = חציון הבטא המתגלגלת (מול SOXX) של המניות בחוליה, בחלון: 3 חודשים, יומי, "
                            "לאורך התקופה המסוננת · קו כתום מקווקו = בטא=1 (SOXX עצמו)."
                        )
                        if "11. חשמל ואנרגיה" in _cmp_sectors and "11. חשמל ואנרגיה" not in _cmp_empty_sectors:
                            st.caption(
                                "⚡ חוליית \"חשמל ואנרגיה\" אינה חלק ממדד SOXX ואינה מתואמת איתו — "
                                "בטא נמוכה קרוב לאפס אצלה היא תקינה ותואמת ל-R² נמוך, לא סימן לבעיה בחישוב."
                            )
                        if _cmp_empty_sectors:
                            st.caption(
                                "ללא מספיק נתוני היסטוריה בתקופה זו: "
                                + ", ".join(clean_name(s) for s in _cmp_empty_sectors)
                            )

        with _z3_tab_sent:
            # אגרגט התחום לאורך עונות — value_chain_sentiment (ממוצע פשוט, זהה לכרטיסיות)
            _z3_all_s = sorted({s for sd in _sentiment_data.values() for s in sd})
            _z3_tx, _z3_ty = [], []
            for _s in _z3_all_s:
                _agg = value_chain_sentiment(chosen, _s, _sentiment_data)
                if _agg is not None:
                    _z3_tx.append(_s)
                    _z3_ty.append(_agg["score"])

            # קו לכל מניה בתחום עם ≥2 עונות מנותחות
            _z3_syms = list(_z3_tickers)
            _z3_sym_series: dict[str, tuple[list, list]] = {}
            for _sym in _z3_syms:
                _sx, _sy = [], []
                for _s in _z3_all_s:
                    _r = (_sentiment_data.get(_sym) or {}).get(_s)
                    if _r and _r.get("sentiment_score") is not None:
                        _sx.append(_s)
                        _sy.append(float(_r["sentiment_score"]))
                if len(_sx) >= 2:
                    _z3_sym_series[_sym] = (_sx, _sy)

            if len(_z3_tx) < 2 and not _z3_sym_series:
                st.caption("אין מספיק נתוני סנטימנט להצגת מגמה (נדרשות ≥2 עונות).")
            else:
                # ציר Y ב-0–100
                _z3_all_pct = [sentiment_pct(v) for (_, _sy) in _z3_sym_series.values() for v in _sy] + [sentiment_pct(v) for v in _z3_ty]
                if _z3_all_pct:
                    _z3_s_min = min(_z3_all_pct); _z3_s_max = max(_z3_all_pct)
                    _z3_pad = max((_z3_s_max - _z3_s_min) * 0.18, 7)
                    _z3_y_low = max(_z3_s_min - _z3_pad, 0)
                    _z3_y_high = min(_z3_s_max + _z3_pad + 4, 100)
                else:
                    _z3_y_low, _z3_y_high = 0, 100
                _z3_tick_vals = [t for t in [0, 25, 50, 75, 100] if _z3_y_low - 1 <= t <= _z3_y_high + 1]
                _z3_tick_text = [str(t) + "%" for t in _z3_tick_vals]

                _z3_fig = go.Figure()
                _z3_fig.add_hline(y=50, line_dash="dot", line_color="rgba(255,255,255,0.25)", line_width=1)

                # קווי מניות דקים — אותה פלטה כמו טאב הביצועים
                for _ci, (_sym, (_sx, _sy)) in enumerate(_z3_sym_series.items()):
                    _clr = palette[_ci % len(palette)]
                    _sy_pct = [sentiment_pct(v) for v in _sy]
                    _z3_fig.add_trace(go.Scatter(
                        x=_sx, y=_sy_pct, name=_sym, mode="lines+markers",
                        line=dict(color=_clr, width=1.5),
                        marker=dict(size=7, color=_clr, line=dict(color="#1e2533", width=1)),
                        hovertemplate="<b>" + _sym + "</b><br>%{x}: %{y:.0f}%<extra></extra>",
                    ))

                # קו התחום — לבן ועבה ומקווקו
                if len(_z3_tx) >= 2:
                    _z3_ty_pct = [sentiment_pct(v) for v in _z3_ty]
                    _z3_fig.add_trace(go.Scatter(
                        x=_z3_tx, y=_z3_ty_pct, name=chosen + " (תחום)", mode="lines+markers",
                        line=dict(color="#ffffff", width=3, dash="dash"),
                        marker=dict(size=10, color="#ffffff", line=dict(color="#1e2533", width=2)),
                        hovertemplate="<b>" + chosen + " (אגרגט)</b><br>%{x}: %{y:.0f}%<extra></extra>",
                    ))

                _z3_fig.update_layout(
                    height=380, template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,0.03)",
                    margin=dict(t=20, b=48, l=60, r=10),
                    yaxis=dict(
                        range=[_z3_y_low, _z3_y_high],
                        tickvals=_z3_tick_vals, ticktext=_z3_tick_text,
                        gridcolor="rgba(255,255,255,0.12)",
                        showline=True, linecolor="rgba(255,255,255,0.25)", linewidth=1,
                        tickfont=dict(size=12),
                        zeroline=False,
                    ),
                    xaxis=dict(
                        gridcolor="rgba(255,255,255,0.10)",
                        showline=True, linecolor="rgba(255,255,255,0.25)", linewidth=1,
                        tickfont=dict(size=12),
                        tickangle=0,
                    ),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                font=dict(size=11)),
                )
                st.plotly_chart(_z3_fig, width='stretch', key="z3_sent_" + sector_key(chosen))

    # ======================================================
    # פילוח טכנולוגי — ליבה ומעטפת
    # ======================================================
    st.markdown(
        "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
        "position:relative;'></div>",
        unsafe_allow_html=True,
    )
    section_banner(5, 8, "🧬", "פילוח טכנולוגי — ליבה ומעטפת", "#a78bfa", period_dependent=True, period_label=period_label)
    st.caption("כל תחום מדורג לפי תשואה משוקללת: ליבה (חשיפה × 1.0) ומעטפת (חשיפה × 0.4). "
               "שני צירים חופפים בכוונה — טכנולוגיה (מה מוכרים) ושוקי קצה (למי מוכרים) — אין להשוות ביניהם כסכום.")
    st.markdown(
        "<div dir='rtl' style='text-align:right; color:#6b7280; font-size:12px; margin-top:-10px; margin-bottom:4px;'>"
        "רחף על <span style='color:#a78bfa; background:rgba(167,139,250,0.15); padding:1px 4px; "
        "border-radius:4px; font-size:11px;'>ⓘ</span> לקריאת תיאור כל תחום"
        "</div>",
        unsafe_allow_html=True,
    )


    def render_tech_detail(idx, sentiment_data=None, season=None, group_name=None):
        """מרנדר את פירוק הליבה/מעטפת של תחום טכנולוגי. נקרא כשהשורה פתוחה."""
        wret = idx["weighted_return"]
        sign = "+" if wret >= 0 else ""
        core_sign = "+" if idx["core_contrib"] >= 0 else ""
        env_sign = "+" if idx["env_contrib"] >= 0 else ""
        st.markdown(
            "<div dir='rtl' style='text-align:right; color:#999; font-size:13px; margin-bottom:10px;'>"
            "💡 <b>ליבה</b> = התחום הוא עיקר העסק (מכפיל 1.0) · <b>מעטפת</b> = מעגל שני שנהנה עקיפות (מכפיל 0.4). "
            "המשקל בטבלה = החלק האפקטיבי של המניה בתשואת התחום. "
            "תרומת הליבה: <b>" + core_sign + str(round(idx["core_contrib"], 1)) + " נק'</b> · "
            "תרומת המעטפת: <b>" + env_sign + str(round(idx["env_contrib"], 1)) + " נק'</b> — יחד = התשואה הכוללת.</div>",
            unsafe_allow_html=True,
        )
        right_col, left_col = st.columns(2)
        with right_col:
            st.markdown(
                "<div dir='rtl' style='text-align:center; font-weight:800; color:#22c55e; "
                "border-top:3px solid #22c55e; background:rgba(34,197,94,0.06); "
                "border-radius:6px; padding:6px; margin-bottom:4px;'>🎯 ליבת התחום</div>",
                unsafe_allow_html=True,
            )
            if idx["core"]:
                st.markdown(tech_table_html(idx["core"], sentiment_data=sentiment_data, season=season), unsafe_allow_html=True)
            else:
                st.caption("אין מניות ליבה עם נתונים")
        with left_col:
            st.markdown(
                "<div dir='rtl' style='text-align:center; font-weight:800; color:#f59e0b; "
                "border-top:3px solid #f59e0b; background:rgba(245,158,11,0.06); "
                "border-radius:6px; padding:6px; margin-bottom:4px;'>↪️ מעטפת — נהנות עקיפות</div>",
                unsafe_allow_html=True,
            )
            if idx["env"]:
                st.markdown(tech_table_html(idx["env"], sentiment_data=sentiment_data, season=season), unsafe_allow_html=True)
            else:
                st.caption("אין מניות מעטפת בתחום זה")

        # --- ניתוח סנטימנט בדוחות לתחום זה ---
        if group_name and sentiment_data and season:
            # פירוק הציון המשוקלל — מוצג רק כשיש שני מרכיבים
            _gd_def = None
            for _ax in TECH_GROUPS.values():
                if group_name in _ax:
                    _gd_def = _ax[group_name]
                    break
            if _gd_def is not None:
                _ws_detail = weighted_tech_score(group_name, _gd_def, season, sentiment_data)
                if _ws_detail and _ws_detail["comp_score"] is not None and _ws_detail["sig_score"] is not None:
                    def _fmt(v):
                        p = sentiment_pct(v)
                        c = "#22c55e" if v >= SENTIMENT_POS else ("#ef4444" if v <= SENTIMENT_NEG else "#9ca3af")
                        return "<span style='color:" + c + "; font-weight:700;'>" + str(p) + "%</span>"
                    _sw = _ws_detail["sig_weight"]
                    _sw_pct = round(_sw * 100)
                    _cw_pct = 100 - _sw_pct
                    _sig_diluted = _ws_detail["sig_count"] < SIG_FULL_COUNT
                    _sig_cov = (
                        str(_ws_detail["sig_count"]) + " מתוך " + str(SIG_FULL_COUNT) + " סיג׳"
                        if _sig_diluted else
                        str(_ws_detail["sig_count"]) + " סיג׳"
                    )
                    st.markdown(
                        "<div dir='rtl' style='background:rgba(255,255,255,0.04); border-radius:8px; "
                        "padding:8px 14px; margin:8px 0; font-size:13px; display:flex; gap:20px; flex-wrap:wrap;'>"
                        "<span>ציון משולב: " + _fmt(_ws_detail["score"]) + "</span>"
                        "<span style='color:#9ca3af;'>│</span>"
                        "<span>סנטימנט חברות (" + str(_cw_pct) + "%): " + _fmt(_ws_detail["comp_score"]) +
                        " <span style='color:#6b7280; font-size:11px;'>(" +
                        str(_ws_detail["comp_reported"]) + "/" + str(_ws_detail["comp_total"]) + " חב׳)</span></span>"
                        "<span style='color:#9ca3af;'>│</span>"
                        "<span>סיגנלים (" + str(_sw_pct) + "%): " + _fmt(_ws_detail["sig_score"]) +
                        " <span style='color:#6b7280; font-size:11px;'>(" + _sig_cov + ")</span></span>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        "<div dir='rtl' style='font-size:11px; color:#6b7280; line-height:1.6; "
                        "text-align:right; padding:0 2px; margin-bottom:4px;'>"
                        "💡 <b style='color:#9ca3af;'>ציון משולב</b> = שקלול שני מקורות. "
                        "<b style='color:#9ca3af;'>סנטימנט חברות</b> = ממוצע משוקלל של ציוני הדוחות לפי חשיפה × שכבה "
                        "(רק מי שכבר דיווחה נספרת). "
                        "<b style='color:#9ca3af;'>סיגנלים</b> = ממוצע התייחסויות ההנהלה לתחום בשיחות ועידה "
                        "(🟢 +1 / ⚪ 0 / 🔴 -1), כולל מחברות שאינן בתחום. "
                        "משקל הסיגנלים עולה עם מספרם "
                        "(10% לסיגנל אחד · 20% לשניים · 30% משלושה ומעלה) — ראיה בודדת לא מזיזה כמו קונצנזוס. "
                        "טווחים: 🟢 מ-63% · ⚪ ביניים · 🔴 מתחת ל-38% · 50% = ניטרלי."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    if _ws_detail["comp_reported"] == 1:
                        st.markdown(
                            "<div dir='rtl' style='font-size:11px; color:#fbbf24; line-height:1.5; "
                            "text-align:right; "
                            "background:rgba(251,191,36,0.08); border:1px solid rgba(251,191,36,0.25); "
                            "border-radius:6px; padding:5px 10px; margin-bottom:6px;'>"
                            "⚠️ חברה אחת בלבד דיווחה בתחום — הציון נשען על מקור יחיד ועשוי להשתנות "
                            "משמעותית כשיצטרפו דוחות נוספים."
                            "</div>",
                            unsafe_allow_html=True,
                        )

            # רבעון קלנדרי קודם בדיוק (לא "האחרון שדיווח") — YYYYQN
            _td_prev_q = int(season[5]) - 1
            _td_prev_y = int(season[:4])
            if _td_prev_q == 0:
                _td_prev_q, _td_prev_y = 4, _td_prev_y - 1
            _td_prev_season = f"{_td_prev_y}Q{_td_prev_q}"

            _td_dir_emoji = {"improving": "🟢⬆️", "stable": "⚪➡️", "deteriorating": "🔴⬇️"}
            _td_dir_color = {"improving": "#22c55e", "stable": "#9ca3af", "deteriorating": "#ef4444"}
            _td_dir_order = {"improving": 0, "stable": 1, "deteriorating": 2}
            _td_entries = []
            for _sym, _sym_data in sentiment_data.items():
                _rec = _sym_data.get(season)
                if not _rec:
                    continue
                for _sig in _rec.get("domain_signals", []):
                    if _sig.get("domain") == group_name:
                        _prev_rec = _sym_data.get(_td_prev_season)
                        if _prev_rec is None:
                            # אין רשומה כלל לרבעון הקלנדרי הקודם
                            _prev_dir = None
                        else:
                            _prev_sig = next(
                                (s for s in _prev_rec.get("domain_signals", []) if s.get("domain") == group_name),
                                None,
                            )
                            # False = דיווח קיים אך ללא התייחסות לתחום זה
                            _prev_dir = _prev_sig.get("direction") if _prev_sig else False
                        _td_entries.append({
                            "sym": _sym,
                            "direction": _sig.get("direction", "stable"),
                            "note": _sig.get("note", ""),
                            "prev_dir": _prev_dir,
                        })
            if _td_entries:
                _td_entries.sort(key=lambda e: _td_dir_order.get(e["direction"], 1))
                _td_pos = sum(1 for e in _td_entries if e["direction"] == "improving")
                _td_neg = sum(1 for e in _td_entries if e["direction"] == "deteriorating")
                _td_net = _td_pos - _td_neg
                _td_net_col = "#22c55e" if _td_net > 0 else ("#ef4444" if _td_net < 0 else "#9ca3af")
                _td_net_sign = "+" if _td_net > 0 else ""
                _td_sig_rows = ""
                for e in _td_entries:
                    _cur = e["direction"]
                    _prev = e["prev_dir"]
                    # פיצול להיפוך חיובי/שלילי — מעבר דרך stable אינו היפוך
                    _is_pos_flip = isinstance(_prev, str) and _cur == "improving" and _prev == "deteriorating"
                    _is_neg_flip = isinstance(_prev, str) and _cur == "deteriorating" and _prev == "improving"
                    _is_flip = _is_pos_flip or _is_neg_flip
                    _row_bg = (
                        " background:rgba(34,197,94,0.08);" if _is_pos_flip else
                        " background:rgba(239,68,68,0.10);" if _is_neg_flip else ""
                    )
                    # עמודת "כיוון רבעון קודם"
                    if _prev is None:
                        _prev_dir_cell = "<span style='color:#6b7280;'>—</span>"
                    elif _prev is False:
                        _prev_dir_cell = "<span style='color:#6b7280; font-style:italic;'>לא היתה התייחסות</span>"
                    else:
                        _prev_dir_cell = (
                            "<span style='color:" + _td_dir_color.get(_prev, "#9ca3af") + ";'>"
                            + _td_dir_emoji.get(_prev, "") + "</span>"
                            + " <span style='color:#6b7280; font-size:11px;'>" + _td_prev_season + "</span>"
                        )
                    # עמודת "מגמה" — רלוונטית רק כשיש כיוון קודם ממשי
                    if not isinstance(_prev, str):
                        _trend_cell = "<span style='color:#6b7280;'>—</span>"
                    elif _is_pos_flip:
                        _trend_cell = "<span style='color:#22c55e; font-weight:700;'>✅ שינוי לחיובי</span>"
                    elif _is_neg_flip:
                        _trend_cell = "<span style='color:#ef4444; font-weight:700;'>⚠️ שינוי לשלילי</span>"
                    else:
                        _trend_cell = "<span style='color:#ca8a04;'>ללא שינוי</span>"
                    _td_sig_rows += (
                        "<tr style='border-top:1px solid rgba(255,255,255,0.07);" + _row_bg + "'>"
                        "<td style='text-align:right; padding:6px 10px; font-weight:600; white-space:nowrap;'>" + e["sym"] + "</td>"
                        "<td style='text-align:center; padding:6px 10px;'>"
                        "<span style='color:" + _td_dir_color.get(_cur, "#9ca3af") + "; font-size:16px;'>"
                        + _td_dir_emoji.get(_cur, "") + "</span></td>"
                        "<td style='text-align:right; padding:6px 10px; color:#d1d5db; font-size:12px;'>" + html.escape(e["note"]) + "</td>"
                        "<td style='text-align:center; padding:6px 10px; font-size:12px; white-space:nowrap;'>" + _prev_dir_cell + "</td>"
                        "<td style='text-align:center; padding:6px 10px; font-size:12px; white-space:nowrap;'>" + _trend_cell + "</td>"
                        "</tr>"
                    )
                st.markdown(section_header("📡 ניתוח סנטימנט בדוחות — " + season, "#a78bfa"), unsafe_allow_html=True)
                st.markdown(
                    "<div dir='rtl' style='margin-bottom:6px; font-size:13px; color:#9ca3af;'>"
                    "ציון נטו: <b style='color:" + _td_net_col + ";'>" + _td_net_sign + str(_td_net) + "</b>"
                    " · 📈 " + str(_td_pos) + " · 📉 " + str(_td_neg) + "</div>"
                    "<div dir='rtl' style='overflow-x:auto;'>"
                    "<table dir='rtl' style='width:100%; border-collapse:collapse; font-size:13px;'>"
                    "<tr style='border-bottom:1px solid #444;'>"
                    "<th style='text-align:right; padding:6px 10px; color:#9ca3af;'>חברה</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>כיוון</th>"
                    "<th style='text-align:right; padding:6px 10px; color:#9ca3af;'>מה אמרה ההנהלה</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>כיוון רבעון קודם</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>מגמה</th>"
                    "</tr>" + _td_sig_rows + "</table></div>",
                    unsafe_allow_html=True,
                )

        # --- מגמת סנטימנט לאורך עונות (ברמת התחום) ---
        if group_name and sentiment_data:
            _gd = None
            for _axis in TECH_GROUPS.values():
                if group_name in _axis:
                    _gd = _axis[group_name]
                    break
            if _gd is not None:
                _all_s = sorted({s for sym_d in sentiment_data.values() for s in sym_d})
                _tx, _ty = [], []   # סנטימנט חברות
                _wx, _wy = [], []   # ציון משולב
                for _s in _all_s:
                    _agg = tech_group_sentiment(_gd, _s, sentiment_data)
                    if _agg is not None:
                        _tx.append(_s)
                        _ty.append(_agg["score"])
                    _ws = weighted_tech_score(group_name, _gd, _s, sentiment_data)
                    if _ws is not None:
                        _wx.append(_s)
                        _wy.append(_ws["score"])
                if len(_tx) >= 2:
                    st.markdown(section_header("📈 מגמת סנטימנט לאורך עונות", "#22d3ee"), unsafe_allow_html=True)
                    _second = (_wx, _wy, "ציון משולב", "#f59e0b") if len(_wx) >= 2 else None
                    render_sentiment_trend(_tx, _ty, "trend_tech_" + sector_key(group_name),
                                           second_series=_second)
                    if _second:
                        st.caption("קו מלא = סנטימנט חברות (עקבי בין עונות) · קו מקווקו = ציון משולב "
                                   "(כולל סיגנלים; משקלם משתנה לפי מספרם, ולכן פחות יציב להשוואת מגמה).")
                elif len(_tx) == 1:
                    st.caption("עונה אחת שמורה לתחום זה — הגרף יופיע לאחר עונה נוספת.")


    _tech_sent_data = load_sentiment()
    _tech_sent_season = latest_season_with_data(_tech_sent_data)
    _tech_cur_s = current_season()
    if _tech_cur_s > _tech_sent_season:
        st.caption("⚠️ סנטימנט: מציג נתוני " + _tech_sent_season + " · עונת " + _tech_cur_s + " טרם נותחה")
    else:
        st.caption("📊 סנטימנט עונה: " + _tech_sent_season)

    with st.spinner("מחשב את הפילוח הטכנולוגי..."):
        for axis_name, axis_groups in TECH_GROUPS.items():
            axis_color = "#3b82f6" if axis_name == "ציר טכנולוגיה" else "#a78bfa"
            st.markdown(
                "<div dir='rtl' style='text-align:right; font-weight:800; font-size:22px; "
                "margin:18px 0 8px 0; padding-bottom:4px; border-bottom:2px solid " + axis_color + ";'>"
                + axis_name + "</div>",
                unsafe_allow_html=True,
            )

            axis_results = []
            for group_name, group_def in axis_groups.items():
                idx = compute_tech_group_index(group_def, period)
                if idx is not None:
                    ws = weighted_tech_score(group_name, group_def, _tech_sent_season, _tech_sent_data)
                    axis_results.append((idx["weighted_return"], group_name, idx, ws))

            # דירוג מהתשואה המשוקללת הגבוהה לנמוכה (תמיד — הגרף נשמר לפי תשואה)
            axis_results.sort(key=lambda x: x[0], reverse=True)

            if len(axis_results) == 0:
                st.caption("אין נתונים זמינים לציר זה כרגע")
                continue

            # גרף עמודות תמיד לפי תשואה
            axis_items = [(group_name, wret) for wret, group_name, idx, ws in axis_results]
            axis_chart_key = "tech_bar_" + sector_key(axis_name) + "_" + period
            with st.container(border=True):
                _tech_clicked = ranking_bar_chart(axis_items, axis_chart_key)
            if _tech_clicked:
                _tech_open_key = "open_tech_" + sector_key(_tech_clicked)
                if not st.session_state.get(_tech_open_key, False):
                    st.session_state[_tech_open_key] = True
                    st.rerun()
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

            _tech_sort = st.radio(
                "מיין לפי:",
                ["📈 תשואה משוקללת", "🧠 ציון משולב"],
                horizontal=True,
                key="tech_sort_mode_" + sector_key(axis_name),
            )
            if _tech_sort == "🧠 ציון משולב":
                st.caption(
                    "ℹ️ תחומים ללא דוחות מנותחים מוצגים בתחתית (—). "
                    "שים לב שהכיסוי חלקי: חלק מהתחומים כוללים חברות שאינן ב-CORE_COMPANIES ולעולם לא יקבלו ציון סנטימנט."
                )
                axis_results.sort(
                    key=lambda x: (x[3] is not None, x[3]["score"] if x[3] is not None else 0.0),
                    reverse=True,
                )

            # טבלת התחומים של הציר — במסגרת, עם כפתור "פתח" אפור קטן
            with st.container(border=True):
                th1, th2 = st.columns([9, 1.3])
                with th1:
                    _t_wret_active = (_tech_sort == "📈 תשואה משוקללת")
                    _t_ws_active = (_tech_sort == "🧠 ציון משולב")
                    st.markdown(
                        "<div dir='rtl' style='display:flex; align-items:center; padding:4px 10px; "
                        "font-size:12px; color:#9ca3af; font-weight:600;'>"
                        "<span style='width:32px; text-align:right;'>#</span>"
                        + col_header("תחום", flex=True)
                        + col_header("תשואה", active=_t_wret_active, width="90px")
                        + col_header("ליבה / מעטפת", width="190px")
                        + col_header("ציון משולב", active=_t_ws_active, width="140px")
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                with th2:
                    st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)

                rankn = 1
                for wret, group_name, idx, _ws in axis_results:
                    n_core = len(idx["core"])
                    n_env = len(idx["env"])
                    core_weight_pct = str(round(idx["core_weight"] * 100)) + "%"
                    wret_color = "#22c55e" if wret >= 0 else "#ef4444"
                    wret_txt = ("+" if wret >= 0 else "") + str(round(wret, 1)) + "%"
                    open_key = "open_tech_" + sector_key(group_name)
                    is_open = st.session_state.get(open_key, False)
                    row_bg = "rgba(96,165,250,0.12)" if is_open else "transparent"

                    _tech_sent_span = weighted_score_html(_ws, wrapper="span")

                    _desc = TECH_DESCRIPTIONS.get(group_name)
                    if _desc:
                        _info_icon = ("<span title='" + html.escape(_desc).replace("'", "&#39;") + "' style='color:#a78bfa; "
                                      "font-size:13px; cursor:help; flex-shrink:0; "
                                      "background:rgba(167,139,250,0.15); padding:1px 4px; "
                                      "border-radius:4px; line-height:1;'>ⓘ</span>")
                    else:
                        _info_icon = ""

                    row_col, btn_col = st.columns([9, 1.3])
                    with row_col:
                        st.markdown(
                            "<div dir='rtl' style='display:flex; align-items:center; padding:8px 10px; "
                            "background:" + row_bg + "; border-top:1px solid rgba(255,255,255,0.06); "
                            "border-radius:6px; min-height:34px;'>"
                            "<span style='width:32px; text-align:right; color:#9ca3af;'>" + str(rankn) + "</span>"
                            "<span style='flex:1; display:flex; align-items:center; justify-content:flex-start; gap:6px;'>"
                            "<span style='font-weight:600;'>" + group_name + "</span>"
                            + _info_icon + "</span>"
                            "<span style='width:90px; text-align:center; color:" + wret_color + "; font-weight:700;'>" + wret_txt + "</span>"
                            "<span style='width:190px; text-align:center; color:#9ca3af; font-size:13px;'>"
                            "ליבה " + str(n_core) + " · מעטפת " + str(n_env) + " · משקל " + core_weight_pct + "</span>"
                            + _tech_sent_span +
                            "</div>",
                            unsafe_allow_html=True,
                        )
                    with btn_col:
                        btn_txt = "סגור" if is_open else "פתח"
                        if st.button(btn_txt, key="techrow_" + sector_key(group_name),
                                     width='stretch', type="tertiary"):
                            st.session_state[open_key] = not is_open
                            st.rerun()

                    if is_open:
                        with st.container(border=True):
                            render_tech_detail(idx, sentiment_data=_tech_sent_data,
                                               season=_tech_sent_season, group_name=group_name)
                    rankn = rankn + 1

# ======================================================
# CapEx — השקעות ענקיות הענן
# ======================================================
st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(6, 8, "🏗️", "CapEx — השקעות ענקיות הענן", "#22d3ee",
               subtitle="ההשקעות ההוניות של מיקרוסופט, גוגל, אמזון ומטא — מנוע הביקוש של הסקטור",
               period_dependent=False)
st.caption("נתוני CapEx בפועל מדוחות תזרים המזומנים (yfinance). "
           "תחזיות שנתיות מוזנות ידנית מהשיחות ועידה. "
           "האזור אינו תלוי בתקופה שנבחרה בסרגל הצד.")

with st.spinner("מושך נתוני CapEx..."):
    capex_q = {}
    for sym in CAPEX_COMPANIES:
        s = get_capex_quarterly(sym)
        if s is not None:
            capex_q[sym] = s

if len(capex_q) == 0:
    st.warning("לא הצלחנו למשוך נתוני CapEx כרגע")
else:
    # --- שורת מדדים: הרבעון האחרון + שינוי מהרבעון הקודם ---
    metric_cols = st.columns(len(capex_q))
    for col, (sym, s) in zip(metric_cols, capex_q.items()):
        latest = float(s.iloc[-1])
        delta_txt = None
        if len(s) >= 2 and float(s.iloc[-2]) != 0:
            d = latest / float(s.iloc[-2]) * 100 - 100
            delta_txt = str(round(d, 1)) + "% מרבעון קודם"
        with col:
            st.metric(CAPEX_COMPANIES[sym] + " (" + sym + ")",
                      "$" + str(round(latest, 1)) + "B", delta_txt)

    # --- גרף רבעוני מקובץ: עמודה לכל חברה בכל רבעון ---
    st.markdown(section_header("📊 CapEx רבעוני — חברה מול חברה", "#22d3ee"),
                unsafe_allow_html=True)

    # סופר לכל רבעון כמה חברות מחזירות בו נתון, ומשאיר בציר רק רבעונים שלפחות
    # 2 חברות דיווחו בהם — כך רבעון "יתום" שרק חברה אחת הגיעה אליו (כי לוח
    # הדיווח שלה מוסט מול האחרות, לא כי יש בו נתון אמיתי להשוואה) לא נכנס
    # לגרף כלל. לא נוגע ב-get_capex_quarterly עצמה — הסינון רק בבניית הציר
    # כאן, ומתגלגל אוטומטית בלי קיבוע קשיח: כשחברה תדווח רבעון חדש הוא ייכנס
    # לספירה ברגע שתגיע לסף 2, וכשרבעון ישן ייצא מחלון ה-5-רבעונים של
    # yfinance עבור מספיק חברות הוא ייפול מעצמו.
    quarter_counts = {}
    for s in capex_q.values():
        for d in s.index:
            key = (d.year, d.quarter)
            quarter_counts[key] = quarter_counts.get(key, 0) + 1
    ordered_q = sorted(q for q, cnt in quarter_counts.items() if cnt >= 2)  # כרונולוגי: ישן -> חדש
    q_axis = ["Q" + str(q) + " " + str(y) for (y, q) in ordered_q]

    if not q_axis:
        st.caption("אין מספיק רבעונים חופפים בין החברות להצגת הגרף כרגע.")

    fig_capex = go.Figure()
    for sym, s in capex_q.items():
        # ממפה כל רבעון לערך שלו, כדי ליישר את כל החברות לאותו ציר
        val_by_q = {}
        for d, v in zip(s.index, s.values):
            val_by_q["Q" + str(d.quarter) + " " + str(d.year)] = float(v)
        y_vals = [val_by_q.get(q, None) for q in q_axis]
        fig_capex.add_trace(go.Bar(
            x=q_axis, y=y_vals,
            name=CAPEX_COMPANIES[sym] + " (" + sym + ")",
            marker_color=CAPEX_COLORS.get(sym, "#9ca3af"),
            hovertemplate="<b>" + sym + "</b><br>%{x}<br>CapEx: $%{y:.1f}B<extra></extra>",
        ))
    fig_capex.update_layout(
        barmode="group", height=380, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=40, l=50, r=20),
        yaxis=dict(title="CapEx (מיליארדי $)", gridcolor="rgba(255,255,255,0.08)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                   categoryorder="array", categoryarray=q_axis),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    with st.container(border=True):
        st.plotly_chart(fig_capex, width='stretch')

    # זיהוי דינמי של פער נתונים אמיתי בין חברות: חברה שהרבעון האחרון שיש לה
    # מוקדם מהרבעון האחרון שמופיע בציר (המסונן, ≥2 חברות) — לא שגיאת יישור/
    # מיפוי, ולכן לא "מתקנים" את זה בחיתוך הציר; רק מבהירים אותו בכיתוב כדי
    # שלא ייראה כתקלת תצוגה. הניסוח לא קובע שהחברה "לא פרסמה דוח" — ייתכן
    # שכן, ופשוט נתון ה-CapEx הספציפי מדוח תזרים המזומנים המפורט טרם עודכן
    # אצל ספק הנתונים.
    if ordered_q:
        _capex_q_global_last = ordered_q[-1]
        _capex_lagging_syms = [
            sym for sym, s in capex_q.items()
            if len(s.index) > 0
            and (s.index[-1].year, s.index[-1].quarter) < _capex_q_global_last
        ]
        if _capex_lagging_syms:
            _lag_names = ", ".join(
                CAPEX_COMPANIES[sym] + " (" + sym + ")" for sym in _capex_lagging_syms
            )
            _lag_q_label = "Q" + str(_capex_q_global_last[1]) + " " + str(_capex_q_global_last[0])
            st.caption(
                "ℹ️ נתון ה-CapEx הרבעוני של " + _lag_names + " עבור " + _lag_q_label +
                " טרם זמין במקור הנתונים (yfinance) — לכן חסר בעמודה האחרונה. "
                "ייתכן שהחברה כבר פרסמה תוצאות לרבעון זה; זה עיכוב בעדכון נתון "
                "התזרים המפורט אצל ספק הנתונים, לא שגיאת יישור בגרף."
            )

    # --- סה"כ מצרפי ---
    combined = pd.concat(capex_q.values(), axis=1).dropna()
    if len(combined) >= 2:
        total = combined.sum(axis=1)
        if float(total.iloc[0]) != 0:
            growth = float(total.iloc[-1]) / float(total.iloc[0]) * 100 - 100
            g_color = "#22c55e" if growth >= 0 else "#ef4444"
            st.markdown(
                "<div dir='rtl' style='text-align:right; font-weight:700; margin:4px 0 12px 0;'>"
                "סה\"כ CapEx מצרפי ברבעון האחרון (רבעונים חופפים בלבד): "
                "<span style='color:#22d3ee;'>$" + str(round(float(total.iloc[-1]), 1)) + "B</span>"
                " · צמיחה מתחילת החלון: <span style='color:" + g_color + ";'>"
                + ("+" if growth >= 0 else "") + str(round(growth, 1)) + "%</span></div>",
                unsafe_allow_html=True,
            )

# ==================================================
# תחזית שנתית מול שנים קודמות — טאב לכל חברה + טאב מצטבר
# ==================================================
st.markdown(section_header("📅 CapEx שנתי — בפועל מול התפתחות התחזית", "#f59e0b"),
            unsafe_allow_html=True)
st.caption("עמודות כחולות-ירקרקות = CapEx בפועל בשנים שהסתיימו (לפי השנה הפיסקלית של כל חברה). "
           "עמודות כתומות = עדכוני התחזית לשנה הנוכחית, משמאל לימין לפי סדר העדכונים — "
           "כך רואים אם התחזית מטפסת או נחתכת במהלך השנה. "
           "הטאב האחרון (מצטבר) מציג את סך כל החברות יחד. "
           "התחזיות מוזנות ידנית (CAPEX_GUIDANCE בקוד); השתמש בכפתור למטה כדי למצוא את המספרים העדכניים.")

# שורת טאבים אחת: טאב לכל חברה + טאב "מצטבר" בסוף
tab_labels = [CAPEX_COMPANIES[sym] + " (" + sym + ")" for sym in CAPEX_COMPANIES]
tab_labels.append("📊 מצטבר — כולן יחד")
all_tabs = st.tabs(tab_labels)
company_tabs = all_tabs[:-1]   # טאב לכל חברה
stacked_tab = all_tabs[-1]     # הטאב המצטבר האחרון

for tab, sym in zip(company_tabs, CAPEX_COMPANIES):
    with tab:
        annual = get_capex_annual(sym)
        guid = CAPEX_GUIDANCE.get(sym, {})
        guid_updates = [(lbl, v) for lbl, v in guid.get("updates", []) if v is not None]
        year_label = guid.get("year_label", "השנה הנוכחית")

        if annual is None and len(guid_updates) == 0:
            st.caption("אין נתונים זמינים לחברה זו כרגע")
            continue

        fig_a = go.Figure()

        # עמודות בפועל: שנים פיסקליות שהסתיימו
        if annual is not None:
            a_labels = ["FY" + str(d.year) for d in annual.index]
            a_values = [float(v) for v in annual.values]
            fig_a.add_trace(go.Bar(
                x=a_labels, y=a_values, name="בפועל",
                marker_color="#22d3ee",
                text=["$" + str(round(v, 1)) + "B" for v in a_values],
                textposition="outside", textfont=dict(size=12, color="#e5e7eb"),
                hovertemplate="<b>%{x}</b><br>בפועל: $%{y:.1f}B<extra></extra>",
            ))

        # עמודות תחזית: התפתחות העדכונים לשנה הנוכחית
        if len(guid_updates) > 0:
            g_labels = [lbl for lbl, v in guid_updates]
            g_values = [float(v) for lbl, v in guid_updates]
            fig_a.add_trace(go.Bar(
                x=g_labels, y=g_values, name="תחזית " + year_label,
                marker=dict(color="rgba(245,158,11,0.85)",
                            line=dict(color="#f59e0b", width=1.5)),
                text=["$" + str(round(v, 1)) + "B" for v in g_values],
                textposition="outside", textfont=dict(size=12, color="#fcd34d"),
                hovertemplate="<b>%{x}</b><br>תחזית: $%{y:.1f}B<extra></extra>",
            ))
            # חץ מגמה בין העדכון הראשון לאחרון
            if len(g_values) >= 2:
                diff = g_values[-1] - g_values[0]
                d_color = "#22c55e" if diff >= 0 else "#ef4444"
                d_txt = ("התחזית עלתה ב-" if diff >= 0 else "התחזית ירדה ב-") + \
                        "$" + str(round(abs(diff), 1)) + "B מאז העדכון הראשון"
                st.markdown(
                    "<div dir='rtl' style='text-align:right; color:" + d_color +
                    "; font-weight:700;'>" + ("📈 " if diff >= 0 else "📉 ") + d_txt + "</div>",
                    unsafe_allow_html=True,
                )
        else:
            if DEV_MODE:
                st.markdown(
                    "<div dir='rtl' style='text-align:right; color:#9ca3af; font-size:13px;'>"
                    "⚠️ טרם הוזנו עדכוני תחזית ל-" + year_label +
                    " — עדכן את CAPEX_GUIDANCE בקוד.</div>",
                    unsafe_allow_html=True,
                )

        fig_a.update_layout(
            barmode="group", height=340, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=40, l=50, r=20),
            yaxis=dict(title="CapEx (מיליארדי $)",
                       gridcolor="rgba(255,255,255,0.08)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1),
            showlegend=True,
        )
        st.plotly_chart(fig_a, width='stretch', key="capex_annual_" + sym)
        if guid.get("year_label"):
            st.caption("שנה פיסקלית נוכחית: " + year_label)

# ---------- הטאב המצטבר: סך CapEx שנתי של כל החברות יחד ----------
with stacked_tab:
    st.caption("עמודות מוערמות לכל שנה: כל צבע = חברה. "
               "שים לב — השנה הפיסקלית של מיקרוסופט מסתיימת ביוני, של השאר בדצמבר, "
               "אז זה קירוב לפי שנת הדיווח. "
               "העמודה האחרונה (במסגרת כתומה) = סכום התחזית העדכנית של כל חברה לשנה הבאה. "
               "מעל כל עמודה: הסכום ואחוז הצמיחה מהעמודה הקודמת.")

    annual_by_company = {}
    for sym in CAPEX_COMPANIES:
        a = get_capex_annual(sym)
        if a is not None:
            annual_by_company[sym] = {d.year: float(v) for d, v in zip(a.index, a.values)}

    if len(annual_by_company) == 0:
        st.caption("אין נתונים שנתיים זמינים כרגע")
    else:
        all_years = set()
        for ymap in annual_by_company.values():
            all_years.update(ymap.keys())
        years_sorted = sorted(all_years)
        year_labels = [str(y) for y in years_sorted]

        # --- התחזית המצטברת: העדכון האחרון של כל חברה שהוזן ---
        # לכל חברה לוקחים את הערך האחרון (לא None) מרשימת העדכונים.
        latest_guidance = {}   # sym -> ערך התחזית העדכני
        for sym in CAPEX_COMPANIES:
            guid = CAPEX_GUIDANCE.get(sym, {})
            vals = [v for lbl, v in guid.get("updates", []) if v is not None]
            if vals:
                latest_guidance[sym] = float(vals[-1])
        has_forecast = len(latest_guidance) > 0
        forecast_total = sum(latest_guidance.values()) if has_forecast else 0.0
        # תווית עמודת התחזית (אם חלק מהחברות חסרות — מציינים)
        n_have = len(latest_guidance)
        n_total = len(CAPEX_COMPANIES)
        forecast_label = "תחזית 2026"
        if 0 < n_have < n_total:
            forecast_label = "תחזית (" + str(n_have) + "/" + str(n_total) + " חברות)"

        # ציר ה-X: השנים בפועל + עמודת תחזית מצרפית בסוף (אם קיימת)
        x_axis = list(year_labels)
        if has_forecast:
            x_axis = x_axis + [forecast_label]

        fig_stack = go.Figure()
        for sym in CAPEX_COMPANIES:
            if sym not in annual_by_company:
                continue
            ymap = annual_by_company[sym]
            y_vals = [ymap.get(y, 0.0) for y in years_sorted]
            # ערך התחזית של החברה בעמודה האחרונה (0 אם לא הוזנה)
            if has_forecast:
                y_vals = y_vals + [latest_guidance.get(sym, 0.0)]
            fig_stack.add_trace(go.Bar(
                x=x_axis, y=y_vals,
                name=CAPEX_COMPANIES[sym] + " (" + sym + ")",
                marker_color=CAPEX_COLORS.get(sym, "#9ca3af"),
                hovertemplate="<b>" + sym + "</b><br>%{x}<br>$%{y:.1f}B<extra></extra>",
            ))

        # סכומים לכל עמודה — כולל עמודת התחזית בסוף
        totals = []
        for y in years_sorted:
            t = sum(annual_by_company[sym].get(y, 0.0) for sym in annual_by_company)
            totals.append(t)
        if has_forecast:
            totals.append(forecast_total)

        # תוויות מעל כל עמודה: סכום + אחוז שינוי מהעמודה הקודמת
        growth_texts = []
        for i, t in enumerate(totals):
            if i == 0 or totals[i - 1] == 0:
                growth_texts.append("$" + str(round(t, 1)) + "B")
            else:
                g = t / totals[i - 1] * 100 - 100
                sign = "+" if g >= 0 else ""
                growth_texts.append("$" + str(round(t, 1)) + "B<br>(" + sign + str(round(g, 1)) + "%)")

        # מרווח מעל העמודה הגבוהה ביותר, כדי שהתווית הדו-שורתית (סכום + %)
        # לא תיחתך מלמעלה — במיוחד עמודת התחזית, שבדרך כלל הגבוהה ביותר.
        max_total = max(totals) if totals else 1.0
        y_top = max_total * 1.28

        fig_stack.add_trace(go.Scatter(
            x=x_axis, y=[t * 1.05 for t in totals],
            mode="text", text=growth_texts,
            textposition="top center", textfont=dict(size=13, color="#e5e7eb"),
            showlegend=False, hoverinfo="skip",
        ))

        # מסגרת כתומה סביב עמודת התחזית — כדי שתובחן מהשנים בפועל
        if has_forecast:
            fig_stack.add_shape(
                type="rect", xref="x", yref="paper",
                x0=len(year_labels) - 0.5, x1=len(year_labels) + 0.5,
                y0=0, y1=1,
                line=dict(color="#f59e0b", width=2, dash="dot"),
                fillcolor="rgba(245,158,11,0.05)", layer="below",
            )

        fig_stack.update_layout(
            barmode="stack", height=480, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=40, l=50, r=20),
            yaxis=dict(title="CapEx מצרפי (מיליארדי $)",
                       gridcolor="rgba(255,255,255,0.08)",
                       range=[0, y_top]),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.08,
                        xanchor="right", x=1),
        )
        st.plotly_chart(fig_stack, width='stretch')

        # שורת סיכום: צמיחת ה-CapEx בפועל על פני התקופה
        actual_totals = totals[:-1] if has_forecast else totals
        if len(actual_totals) >= 2 and actual_totals[0] != 0:
            total_growth = actual_totals[-1] / actual_totals[0] * 100 - 100
            tg_color = "#22c55e" if total_growth >= 0 else "#ef4444"
            st.markdown(
                "<div dir='rtl' style='text-align:right; font-weight:700; margin-top:6px;'>"
                "סך ה-CapEx המצרפי בפועל גדל מ-<span style='color:#22d3ee;'>$"
                + str(round(actual_totals[0], 1)) + "B</span> ל-<span style='color:#22d3ee;'>$"
                + str(round(actual_totals[-1], 1)) + "B</span> — צמיחה של <span style='color:"
                + tg_color + ";'>" + ("+" if total_growth >= 0 else "")
                + str(round(total_growth, 1)) + "%</span> על פני התקופה</div>",
                unsafe_allow_html=True,
            )

        # שורת סיכום נוספת: התחזית המצרפית מול השנה האחרונה בפועל
        if has_forecast and len(actual_totals) >= 1 and actual_totals[-1] != 0:
            fc_growth = forecast_total / actual_totals[-1] * 100 - 100
            fc_color = "#22c55e" if fc_growth >= 0 else "#ef4444"
            miss_note = ""
            if n_have < n_total:
                miss_note = " (חלקי — טרם הוזנו תחזיות לכל החברות)"
            st.markdown(
                "<div dir='rtl' style='text-align:right; font-weight:700; margin-top:4px;'>"
                "התחזית המצרפית לשנה הבאה: <span style='color:#f59e0b;'>$"
                + str(round(forecast_total, 1)) + "B</span> — "
                "צמיחה צפויה של <span style='color:" + fc_color + ";'>"
                + ("+" if fc_growth >= 0 else "") + str(round(fc_growth, 1))
                + "%</span> מעל השנה האחרונה בפועל" + miss_note + "</div>",
                unsafe_allow_html=True,
            )
        elif not has_forecast:
            st.caption("💡 עמודת תחזית מצרפית תופיע כאן אחרי שתזין ערכי תחזית ב-CAPEX_GUIDANCE.")

# ==================================================
# טבלה מסכמת: התפתחות התחזיות מול השנה הקודמת בפועל
# ==================================================
st.markdown(section_header("📋 טבלת סיכום — התחזית האחרונה מול הקודמת ומול בפועל", "#f59e0b"),
            unsafe_allow_html=True)

# בונים שורה לכל חברה שיש לה לפחות תחזית אחת שהוזנה
guid_rows = []
for sym in CAPEX_COMPANIES:
    guid = CAPEX_GUIDANCE.get(sym, {})
    vals = [v for lbl, v in guid.get("updates", []) if v is not None]
    if not vals:
        continue  # אין תחזית שהוזנה לחברה זו — לא נציג שורה

    last = float(vals[-1])
    prev = float(vals[-2]) if len(vals) >= 2 else None

    # שינוי התחזית האחרונה מול הקודמת
    chg_prev = None
    if prev is not None and prev != 0:
        chg_prev = last / prev * 100 - 100

    # ה-CapEx בפועל של השנה הפיסקלית האחרונה שהסתיימה
    annual = get_capex_annual(sym)
    actual_prev = None
    if annual is not None and len(annual) > 0:
        actual_prev = float(annual.values[-1])

    # שינוי התחזית מול השנה הקודמת בפועל
    chg_actual = None
    if actual_prev is not None and actual_prev != 0:
        chg_actual = last / actual_prev * 100 - 100

    guid_rows.append({
        "name": CAPEX_COMPANIES[sym] + " (" + sym + ")",
        "last": last,
        "prev": prev,
        "chg_prev": chg_prev,
        "actual_prev": actual_prev,
        "chg_actual": chg_actual,
    })

if len(guid_rows) == 0:
    st.caption("טרם הוזנו תחזיות. הזן ערכים ב-CAPEX_GUIDANCE כדי לראות את הטבלה.")
else:
    st.markdown(capex_guidance_table_html(guid_rows), unsafe_allow_html=True)
    st.caption("«תחזית אחרונה» = העדכון האחרון שהוזן · «תחזית קודמת» = העדכון שלפניו · "
               "«שינוי בתחזית» = כמה השתנתה התחזית בין העדכונים · "
               "«תחזית מול בפועל» = כמה התחזית הנוכחית גבוהה/נמוכה מ-CapEx השנה הקודמת שהסתיימה. "
               "«—» מציין שאין עדיין נתון (למשל רק עדכון תחזית אחד).")

# --- כפתור מאוחד: מגמה רבעונית + עדכוני תחזית — גלוי לכולם ---
if len(capex_q) > 0 or len(guid_rows) > 0:
    _combined_key = "capex_combined_" + datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if st.button("📊 סכם את מגמת ה-CapEx והתחזיות", key="capex_combined_btn"):
        # בניית quarterly_lines
        if capex_q:
            _q_parts = []
            for sym, s in capex_q.items():
                _q_parts.append(sym + ": " + ", ".join(str(round(float(v), 1)) for v in s.values[-4:]))
            _quarterly_lines = " | ".join(_q_parts)
        else:
            _quarterly_lines = ""
        # בניית guidance_lines
        _guid_lines = []
        for sym in CAPEX_COMPANIES:
            guid = CAPEX_GUIDANCE.get(sym, {})
            updates = [(lbl, v) for lbl, v in guid.get("updates", []) if v is not None]
            if updates:
                parts = [lbl + ": $" + str(v) + "B" for lbl, v in updates]
                _guid_lines.append(CAPEX_COMPANIES[sym] + " — " + " → ".join(parts))
        _guidance_lines = "\n".join(_guid_lines)
        with st.spinner("מסכם את מגמת ה-CapEx עם Gemini..."):
            _comb_text, _comb_sources = gemini_capex_combined(_quarterly_lines, _guidance_lines)
        st.session_state[_combined_key] = {"text": _comb_text, "sources": _comb_sources}

    _comb_saved = st.session_state.get(_combined_key)
    if _comb_saved and _comb_saved.get("text"):
        st.markdown("<div dir='rtl' style='text-align:right;'>" + html.escape(_comb_saved["text"]) + "</div>",
                    unsafe_allow_html=True)
        if _comb_saved.get("sources"):
            with st.expander("מקורות"):
                for _t, _u in _comb_saved["sources"]:
                    st.markdown("• [" + (_t or _u) + "](" + _u + ")")

# --- כפתור חיפוש תחזיות עדכניות — מצב מפתח בלבד ---
if DEV_MODE:
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    capex_guid_key = "capex_guid_" + datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if st.button("🔎 חפש את תחזיות ה-CapEx העדכניות (לעדכון ידני של המילון)",
                 key="capex_guid_btn"):
        with st.spinner("מחפש תחזיות עדכניות ברשת..."):
            text, sources = gemini_capex_guidance()
        st.session_state[capex_guid_key] = {"text": text, "sources": sources}

    saved_guid = st.session_state.get(capex_guid_key)
    if saved_guid and saved_guid.get("text"):
        st.markdown("<div dir='rtl' style='text-align:right;'>" + html.escape(saved_guid["text"]) + "</div>",
                    unsafe_allow_html=True)
        if saved_guid.get("sources"):
            with st.expander("מקורות"):
                for title, uri in saved_guid["sources"]:
                    st.markdown("• [" + (title or uri) + "](" + uri + ")")
        st.caption("💡 קח את המספרים מכאן, אמת מול המקורות, והזן אותם ב-CAPEX_GUIDANCE שבראש הקובץ.")

# ==================================================
# Backlog (RPO) — צבר התחייבויות חוזיות שטרם הוכרו כהכנסה
# ==================================================
st.markdown(section_header("📈 Backlog — צבר הזמנות עתידי (RPO)", "#818cf8"),
            unsafe_allow_html=True)
st.caption(
    "Backlog = צבר ההתחייבויות החוזיות שטרם הוכרו כהכנסה (RPO — Remaining Performance "
    "Obligations) — צנרת ההכנסות העתידית מחוזי ענן. נתונים רבעוניים מדוחות 10-Q/10-K, "
    "במיליארדי דולרים. האזור אינו תלוי בתקופה שנבחרה בסרגל הצד. מטא אינה נכללת — RPO הוא "
    "מדד ספציפי לעסקי ענן, ולא רלוונטי לעסקי הפרסום שלה."
)

_rpo_tab_labels = [CAPEX_COMPANIES.get(sym, sym) + " (" + sym + ")" for sym in RPO_QUARTERLY]
_rpo_tab_labels.append("📊 מצטבר — כולן יחד")
_rpo_all_tabs = st.tabs(_rpo_tab_labels)
_rpo_company_tabs = _rpo_all_tabs[:-1]   # טאב לכל חברה
_rpo_stacked_tab = _rpo_all_tabs[-1]     # הטאב המצטבר האחרון

for _rpo_tab, sym in zip(_rpo_company_tabs, RPO_QUARTERLY):
    with _rpo_tab:
        _rpo_series = RPO_QUARTERLY[sym]
        _rpo_sym_qs = sorted(_rpo_series.keys(), key=lambda q: (int(q[:4]), int(q[5])))
        _rpo_sym_x = ["Q" + q[5] + " " + q[:4] for q in _rpo_sym_qs]
        _rpo_sym_y = [_rpo_series[q] for q in _rpo_sym_qs]
        fig_rpo_sym = go.Figure()
        fig_rpo_sym.add_trace(go.Bar(
            x=_rpo_sym_x, y=_rpo_sym_y,
            marker_color=CAPEX_COLORS.get(sym, "#9ca3af"),
            text=["$" + str(round(v)) + "B" for v in _rpo_sym_y],
            textposition="outside", textfont=dict(size=12, color="#e5e7eb"),
            hovertemplate="<b>" + sym + "</b><br>%{x}<br>Backlog: $%{y:.0f}B<extra></extra>",
        ))
        fig_rpo_sym.update_layout(
            height=340, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=40, l=50, r=20),
            yaxis=dict(title="Backlog / RPO (מיליארדי $)", gridcolor="rgba(255,255,255,0.08)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            showlegend=False,
        )
        st.plotly_chart(fig_rpo_sym, width='stretch', key="rpo_bar_" + sym)
        st.caption("צבר ה-Backlog (RPO) הרבעוני של " + CAPEX_COMPANIES.get(sym, sym) + " (" + sym + ") לאורך הזמן.")

# ---------- הטאב המצטבר: סך ה-Backlog של שלוש החברות יחד ----------
with _rpo_stacked_tab:
    st.caption(
        "עמודה מוערמת לכל רבעון = סך צבר ההזמנות (RPO) של שלוש ענקיות הענן יחד באותו רבעון "
        "— כלומר סך צנרת ההכנסות העתידית מחוזי ענן. זהו מלאי (מצב ברגע נתון), לא זרימה "
        "מצטברת כמו CapEx. רבעון שחסר לחברה כלשהי נספר כ-0 בהערמה שלה בלבד, ולא שובר את הגרף — "
        "ציר הרבעונים נבנה מאיחוד הרבעונים של כל שלוש החברות."
    )

    _rpo_all_q = sorted({q for series in RPO_QUARTERLY.values() for q in series},
                         key=lambda q: (int(q[:4]), int(q[5])))
    _rpo_x = ["Q" + q[5] + " " + q[:4] for q in _rpo_all_q]

    fig_rpo_stack = go.Figure()
    for sym, series in RPO_QUARTERLY.items():
        y_vals = [series.get(q, 0.0) for q in _rpo_all_q]
        fig_rpo_stack.add_trace(go.Bar(
            x=_rpo_x, y=y_vals,
            name=CAPEX_COMPANIES.get(sym, sym) + " (" + sym + ")",
            marker_color=CAPEX_COLORS.get(sym, "#9ca3af"),
            hovertemplate="<b>" + sym + "</b><br>%{x}<br>$%{y:.0f}B<extra></extra>",
        ))

    _rpo_totals = [sum(series.get(q, 0.0) for series in RPO_QUARTERLY.values()) for q in _rpo_all_q]
    _rpo_growth_texts = []
    for i, t in enumerate(_rpo_totals):
        if i == 0 or _rpo_totals[i - 1] == 0:
            _rpo_growth_texts.append("$" + str(round(t)) + "B")
        else:
            _rpo_g = t / _rpo_totals[i - 1] * 100 - 100
            _rpo_sign = "+" if _rpo_g >= 0 else ""
            _rpo_growth_texts.append("$" + str(round(t)) + "B<br>(" + _rpo_sign + str(round(_rpo_g, 1)) + "%)")

    _rpo_max_total = max(_rpo_totals) if _rpo_totals else 1.0
    _rpo_y_top = _rpo_max_total * 1.20

    fig_rpo_stack.add_trace(go.Scatter(
        x=_rpo_x, y=[t * 1.03 for t in _rpo_totals],
        mode="text", text=_rpo_growth_texts,
        textposition="top center", textfont=dict(size=12, color="#e5e7eb"),
        showlegend=False, hoverinfo="skip",
    ))

    fig_rpo_stack.update_layout(
        barmode="stack", height=440, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=40, l=50, r=20),
        yaxis=dict(title="Backlog מצרפי (מיליארדי $)", gridcolor="rgba(255,255,255,0.08)",
                   range=[0, _rpo_y_top]),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)",
                   categoryorder="array", categoryarray=_rpo_x),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_rpo_stack, width='stretch', key="rpo_stacked_chart")


def _rpo_prev_q_key(qkey):
    # הרבעון הקלנדרי הקודם ברצף, לפי תיוג YYYYQN — לא לפי מיקום ברשימה
    y, q = int(qkey[:4]), int(qkey[5])
    return (str(y - 1) + "Q4") if q == 1 else (qkey[:4] + "Q" + str(q - 1))


def _rpo_yoy_q_key(qkey):
    # אותו רבעון, שנה קלנדרית קודמת
    return str(int(qkey[:4]) - 1) + "Q" + qkey[5]


def _rpo_pct_html(pct):
    if pct is None:
        return "<span style='color:#6b7280;'>—</span>"
    color = "#22c55e" if pct >= 0 else "#ef4444"
    sign = "+" if pct >= 0 else ""
    return ("<span dir='ltr' style='unicode-bidi:isolate; display:inline-block; color:" + color +
            "; font-weight:700;'>" + sign + str(round(pct, 1)) + "%</span>")


_rpo_table_rows = ""
for sym, series in RPO_QUARTERLY.items():
    _rpo_qs = sorted(series.keys(), key=lambda q: (int(q[:4]), int(q[5])))
    if not _rpo_qs:
        continue
    _rpo_last_q = _rpo_qs[-1]
    _rpo_last_v = series[_rpo_last_q]
    _rpo_prev_v = series.get(_rpo_prev_q_key(_rpo_last_q))
    _rpo_yoy_v = series.get(_rpo_yoy_q_key(_rpo_last_q))
    _rpo_qoq_pct = (_rpo_last_v / _rpo_prev_v * 100 - 100) if _rpo_prev_v else None
    _rpo_yoy_pct = (_rpo_last_v / _rpo_yoy_v * 100 - 100) if _rpo_yoy_v else None
    _rpo_last_q_label = "Q" + _rpo_last_q[5] + " " + _rpo_last_q[:4]
    _rpo_table_rows += (
        "<tr style='border-top:1px solid rgba(255,255,255,0.07);'>"
        "<td style='text-align:right; padding:6px 10px; font-weight:700; color:"
        + CAPEX_COLORS.get(sym, "#9ca3af") + ";'>" + sym + "</td>"
        "<td style='text-align:center; padding:6px 10px; color:#9ca3af;'>" + _rpo_last_q_label + "</td>"
        "<td style='text-align:center; padding:6px 10px;'>"
        "<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>$"
        + str(round(_rpo_last_v)) + "B</span></td>"
        "<td style='text-align:center; padding:6px 10px;'>" + _rpo_pct_html(_rpo_qoq_pct) + "</td>"
        "<td style='text-align:center; padding:6px 10px;'>" + _rpo_pct_html(_rpo_yoy_pct) + "</td>"
        "</tr>"
    )
st.markdown(
    "<div dir='rtl' style='overflow-x:auto; margin-top:8px;'>"
    "<table style='width:100%; border-collapse:collapse; font-size:13px;'>"
    "<tr style='border-bottom:1px solid #666;'>"
    "<th style='text-align:right; padding:6px 10px;'>חברה</th>"
    "<th style='text-align:center; padding:6px 10px;'>רבעון אחרון</th>"
    "<th style='text-align:center; padding:6px 10px;'>RPO נוכחי</th>"
    "<th style='text-align:center; padding:6px 10px;'>מול רבעון קודם (QoQ)</th>"
    "<th style='text-align:center; padding:6px 10px;'>מול רבעון מקביל (YoY)</th>"
    "</tr>" + _rpo_table_rows + "</table></div>",
    unsafe_allow_html=True,
)

if DEV_MODE:
    rpo_guid_key = "rpo_guid_" + datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if st.button("🔎 חפש את נתוני ה-Backlog (RPO) העדכניים (לעדכון ידני של המילון)",
                 key="rpo_guid_btn"):
        with st.spinner("מחפש נתוני RPO עדכניים ברשת..."):
            _rpo_text, _rpo_sources = gemini_rpo_guidance()
        st.session_state[rpo_guid_key] = {"text": _rpo_text, "sources": _rpo_sources}

    saved_rpo_guid = st.session_state.get(rpo_guid_key)
    if saved_rpo_guid and saved_rpo_guid.get("text"):
        st.markdown("<div dir='rtl' style='text-align:right;'>" + html.escape(saved_rpo_guid["text"]) + "</div>",
                    unsafe_allow_html=True)
        if saved_rpo_guid.get("sources"):
            with st.expander("מקורות"):
                for title, uri in saved_rpo_guid["sources"]:
                    st.markdown("• [" + (title or uri) + "](" + uri + ")")
        st.caption("💡 קח את המספרים מכאן, אמת מול המקורות, והזן אותם ב-RPO_QUARTERLY שבראש הקובץ.")

# ======================================================
# אזור 6 — דוחות כספיים וסנטימנט עונת הדוחות
# ======================================================
CORE_COMPANIES = sorted([
    "ASML", "AMAT", "LRCX", "KLAC", "NVDA", "AMD", "TSM", "INTC", "MU",
    "TXN", "ADI", "AVGO", "QCOM", "MRVL", "ARM",
    "TSEM", "NVMI", "CAMT",
    "MSFT", "META", "GOOGL", "AMZN", "ORCL",
    "005930.KS", "000660.KS",
])

st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(7, 8, "📋", "דוחות כספיים — ניתוח עונת הדוחות", "#f59e0b",
               subtitle="ניתוח דוחות ושיחות ועידה עם AI · סנטימנט מצטבר לפי תחום",
               period_dependent=False)

_z6_sent_data = load_sentiment()

_z6_d_season, _z6_c_season, _z6_lag = _season_lag(_z6_sent_data)
if _z6_lag:
    st.markdown(
        "<div dir='rtl' style='background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.4); "
        "border-radius:8px; padding:8px 14px; margin:6px 0 10px; text-align:right; "
        "font-size:14px; color:#fbbf24; font-weight:600;'>"
        + "⚠️ מציג נתוני " + _z6_d_season + " · עונת " + _z6_c_season + " החלה אך טרם נותחו בה דוחות"
        + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div dir='rtl' style='text-align:right; font-size:13px; color:#6b7280; margin:4px 0 8px;'>"
        + "📊 עונה נוכחית: " + _z6_d_season + "</div>",
        unsafe_allow_html=True,
    )


# --- לוח שנה של דוחות ---
st.markdown(section_header("📅 לוח דוחות", "#3b82f6"), unsafe_allow_html=True)

# ניווט חודשי — שמור ב-session_state
_today_nav = datetime.now(timezone.utc)
if "z6_cal_year" not in st.session_state:
    st.session_state["z6_cal_year"] = _today_nav.year
    st.session_state["z6_cal_month"] = _today_nav.month

_month_names_he = ["", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                   "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
_cy = st.session_state["z6_cal_year"]
_cm = st.session_state["z6_cal_month"]

_nav_prev, _nav_title, _nav_next = st.columns([1, 3, 1])
with _nav_prev:
    if st.button("◄ חודש קודם", key="z6_prev_month", width='stretch'):
        _nm, _ny = (_cm - 1, _cy) if _cm > 1 else (12, _cy - 1)
        st.session_state["z6_cal_month"] = _nm
        st.session_state["z6_cal_year"] = _ny
        st.rerun()
with _nav_title:
    st.markdown(
        "<div style='text-align:center; font-size:18px; font-weight:700; padding:6px;'>"
        + _month_names_he[_cm] + " " + str(_cy) + "</div>",
        unsafe_allow_html=True,
    )
with _nav_next:
    if st.button("חודש הבא ►", key="z6_next_month", width='stretch'):
        _nm, _ny = (_cm + 1, _cy) if _cm < 12 else (1, _cy + 1)
        st.session_state["z6_cal_month"] = _nm
        st.session_state["z6_cal_year"] = _ny
        st.rerun()

# טעינת נתוני הלוח (cached, ±120 יום)
with st.spinner("טוען תאריכי דוחות..."):
    _z6_all_entries = get_earnings_calendar(tuple(CORE_COMPANIES))

if not _z6_all_entries:
    st.warning("⚠️ לא הצלחנו למשוך תאריכי דוחות ממקור הנתונים (Yahoo). ייתכן תקלה זמנית או גרסת yfinance ישנה. נסי לרענן.")
    if st.button("🔄 רענן תאריכי דוחות"):
        get_earnings_calendar.clear()
        st.rerun()

# חלון הלוח (±120 יום, זהה ל-get_earnings_calendar)
_z6_today = datetime.now(timezone.utc).date()
_z6_win_lo = _z6_today - timedelta(days=120)
_z6_win_hi = _z6_today + timedelta(days=120)

# שלב א׳: בנה מפת עוגן מרשומות שמורות — (symbol, season) → report_date_str
# משמשת לסינון entries של yfinance שהתאריך שלהם שונה מהתאריך השמור.
_z6_pinned: dict = {}
for _psym, _pss in _z6_sent_data.items():
    for _pseason, _prec in _pss.items():
        _pds = (_prec or {}).get("report_date", "")
        if not _pds or _pds == "—":
            continue
        try:
            datetime.strptime(_pds, "%Y-%m-%d")
            _z6_pinned[(_psym, _pseason)] = _pds
        except ValueError:
            pass

# שלב ב׳: המרה ל-dict {date_str: [entries]}, עם כלל ההעדפה
# entry של yfinance שעבורו קיים עוגן שמור לאותה (symbol, season) אך בתאריך שונה — נדחה.
_z6_cal_dict = {}
for _e in _z6_all_entries:
    _e_pinned = _z6_pinned.get((_e["symbol"], season_from_date(_e["date"])))
    if _e_pinned is not None and _e_pinned != str(_e["date"]):
        continue
    _z6_cal_dict.setdefault(str(_e["date"]), []).append(_e)

# שלב ג׳: הזרק צ'יפים מרשומות שמורות שלא הגיעו כלל מ-yfinance
_z6_present: set = set()
for _pd_str, _pe_list in _z6_cal_dict.items():
    for _pe in _pe_list:
        _z6_present.add((_pe["symbol"], _pd_str))

for _inj_sym, _inj_seasons in _z6_sent_data.items():
    for _inj_season, _inj_rec in _inj_seasons.items():
        _inj_date_str = (_inj_rec or {}).get("report_date", "")
        if not _inj_date_str or _inj_date_str == "—":
            continue
        try:
            _inj_d = datetime.strptime(_inj_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (_z6_win_lo <= _inj_d <= _z6_win_hi):
            continue
        if (_inj_sym, str(_inj_d)) in _z6_present:
            continue  # כבר קיים (yfinance הסכים על אותו תאריך)
        _z6_cal_dict.setdefault(str(_inj_d), []).append({
            "date":       _inj_d,
            "symbol":     _inj_sym,
            "eps_est":    (_inj_rec or {}).get("eps_estimate"),
            "eps_actual": (_inj_rec or {}).get("eps_actual"),
            "surprise":   None,
            "is_future":  False,
        })
        _z6_present.add((_inj_sym, str(_inj_d)))

# אוסף תחזיות לחברות עתידיות בחודש המוצג בלבד — הטולטיפ קיים רק לצ'יפים
# של החודש הזה, אין טעם לסרוק get_forward_estimates על כל חלון ±120 הימים
_z6_fwd_est: dict[str, dict] = {}
for _fe_date, _fe_entries in _z6_cal_dict.items():
    if not (_fe_date[:4] == str(_cy) and _fe_date[5:7] == f"{_cm:02d}"):
        continue
    for _fe in _fe_entries:
        if _fe["is_future"] and _fe["symbol"] not in _z6_fwd_est:
            _fe_data = get_forward_estimates(_fe["symbol"])
            if _fe_data:
                _z6_fwd_est[_fe["symbol"]] = _fe_data

# בניית גריד הלוח
import calendar as _cal_mod
_cal_mod.setfirstweekday(6)   # יום ראשון = תחילת שבוע
_weeks = _cal_mod.monthcalendar(_cy, _cm)
_today_date = datetime.now(timezone.utc).date()

_day_headers_he = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"]
_hdr_html = "<tr>" + "".join(
    "<th style='text-align:center; padding:8px 4px; font-size:13px; font-weight:600; "
    "color:#e5e7eb; background:#1e2533; border-bottom:2px solid #374151; width:14.28%;'>" + _h + "</th>"
    for _h in _day_headers_he
) + "</tr>"

_status_bg_fg = {
    "future":     ("rgba(37,99,235,0.30)",  "#bfdbfe"),
    "analyzed":   ("rgba(22,101,52,0.45)",  "#bbf7d0"),
    "unanalyzed": ("rgba(161,98,7,0.45)",   "#fde68a"),
}
_status_border = {
    "future":     "1px solid rgba(96,165,250,0.5)",
    "analyzed":   "1px solid rgba(74,222,128,0.5)",
    "unanalyzed": "1px solid rgba(253,211,77,0.5)",
}

_rows_html = ""
for _week in _weeks:
    _row = "<tr>"
    for _wday in _week:
        if _wday == 0:
            _row += "<td style='padding:3px; width:14.28%; height:80px; background:#0f1117; border-radius:6px;'></td>"
            continue
        from datetime import date as _date_cls
        _d = _date_cls(_cy, _cm, _wday)
        _dstr = str(_d)
        _is_today = (_d == _today_date)
        _cell_bg = "background:#1a2035;" if _is_today else "background:#141824;"
        _border = "border:2px solid #60a5fa; border-radius:8px;" if _is_today else "border:1px solid #2d3748; border-radius:8px;"
        _num_color = "#60a5fa" if _is_today else "#9ca3af"
        _num_size = "14px" if _is_today else "12px"
        _num_weight = "800" if _is_today else "500"
        _cell = (
            "<td style='padding:6px; width:14.28%; vertical-align:top; height:80px; "
            + _cell_bg + _border + "'>"
            "<div style='font-size:" + _num_size + "; color:" + _num_color + "; "
            "font-weight:" + _num_weight + "; margin-bottom:4px; line-height:1;'>" + str(_wday) + "</div>"
        )
        for _entry in _z6_cal_dict.get(_dstr, []):
            _sym = _entry["symbol"]
            _has_report = not _entry["is_future"]
            _status = get_symbol_cal_status(_sym, _d, _has_report, _z6_sent_data)
            _bg, _fg = _status_bg_fg[_status]
            _bd = _status_border[_status]
            if _status == "future":
                _days_left = (_d - _today_date).days
                _days_txt = (
                    "היום" if _days_left == 0
                    else ("מחר" if _days_left == 1
                    else f"{_days_left} ימים")
                )
                _fwd = _z6_fwd_est.get(_sym, {})
                _tip_lines = [f"📅 {_days_txt}"]
                _eps_e = _fwd.get("eps_est")
                if _eps_e is not None:
                    _tip_lines.append(f"EPS צפי: ${_eps_e:.2f}")
                _rev_e = _fwd.get("revenue_est_b")
                if _rev_e is not None:
                    _tip_lines.append(f"הכנסות: ${_rev_e:.1f}B")
                _grw = _fwd.get("revenue_growth_pct")
                if _grw is not None:
                    _grw_sign = "+" if _grw > 0 else ""
                    _tip_lines.append(f"צמיחה: {_grw_sign}{_grw:.1f}%")
                _tip_html = "<br>".join(_tip_lines)
                _cell += (
                    "<div class='chip-future-wrap'>"
                    "<div class='chip-future' style='background:" + _bg + "; color:" + _fg + "; border:" + _bd + "; "
                    "font-size:11px; font-weight:700; padding:3px 6px; "
                    "border-radius:5px; margin:2px 0; white-space:nowrap; "
                    "text-align:center; position:relative; cursor:default;'>"
                    + _sym +
                    "<div class='chip-tip'>" + _tip_html + "</div>"
                    "</div>"
                    "</div>"
                )
            elif _status == "analyzed":
                _rec = get_record(_z6_sent_data, _sym, season_from_date(_d))
                if not _rec:
                    _cell += (
                        "<div style='background:" + _bg + "; color:" + _fg + "; border:" + _bd + "; "
                        "font-size:11px; font-weight:700; padding:3px 6px; "
                        "border-radius:5px; margin:2px 0; white-space:nowrap; "
                        "text-align:center;'>"
                        + _sym + "</div>"
                    )
                else:
                    _a_tip = []
                    _tip_ccy = currency_symbol(record_currency(_sym, _rec))
                    # סנטימנט
                    _sc = _rec.get("sentiment_score")
                    if _sc is not None:
                        _sc_f = float(_sc)
                        _sc_pct = sentiment_pct(_sc_f)
                        _sc_emoji = "🟢" if _sc_f >= SENTIMENT_POS else ("🔴" if _sc_f <= SENTIMENT_NEG else "⚪")
                        _sc_col = "#22c55e" if _sc_f >= SENTIMENT_POS else ("#ef4444" if _sc_f <= SENTIMENT_NEG else "#9ca3af")
                        _a_tip.append(
                            _sc_emoji + " סנטימנט: <b style='color:" + _sc_col + ";'>"
                            + str(_sc_pct) + "%</b>"
                        )
                    # EPS
                    _ea = _rec.get("eps_actual")
                    _ee = _rec.get("eps_estimate")
                    if _ea is not None and _ee is not None:
                        try:
                            _ea_f = float(_ea); _ee_f = float(_ee)
                            _eps_str = f"EPS: {_tip_ccy}{_ea_f:,.2f} / {_tip_ccy}{_ee_f:,.2f} צפי"
                            if _ee_f != 0:
                                _es = _ea_f / _ee_f * 100 - 100
                                _es_sign = "+" if _es > 0 else ""
                                _es_col = "#22c55e" if _es > 0 else ("#ef4444" if _es < 0 else "#9ca3af")
                                _eps_str += " <span style='color:" + _es_col + ";'>(" + _es_sign + f"{_es:.1f}%)</span>"
                            _a_tip.append(_eps_str)
                        except (TypeError, ValueError):
                            pass
                    # הכנסות
                    _ra = _rec.get("revenue_actual_b")
                    _re = _rec.get("revenue_estimate_b")
                    if _ra is not None and _re is not None:
                        try:
                            _ra_f = float(_ra); _re_f = float(_re)
                            _rev_str = "הכנסות: " + fmt_money_b(_ra_f, _tip_ccy) + " / " + fmt_money_b(_re_f, _tip_ccy) + " צפי"
                            if _re_f != 0:
                                _rs = _ra_f / _re_f * 100 - 100
                                _rs_sign = "+" if _rs > 0 else ""
                                _rs_col = "#22c55e" if _rs > 0 else ("#ef4444" if _rs < 0 else "#9ca3af")
                                _rev_str += " <span style='color:" + _rs_col + ";'>(" + _rs_sign + f"{_rs:.1f}%)</span>"
                            _a_tip.append(_rev_str)
                        except (TypeError, ValueError):
                            pass
                    # תחזית רבעון הבא
                    _nqg = _rec.get("next_q_guidance")
                    if isinstance(_nqg, dict):
                        _nq_rev = _nqg.get("revenue_b")
                        _nq_eps = _nqg.get("eps")
                        _nq_parts = []
                        if _nq_rev is not None:
                            try:
                                _nq_parts.append("הכנסות " + fmt_money_b(float(_nq_rev), _tip_ccy))
                            except (TypeError, ValueError):
                                pass
                        if _nq_eps is not None:
                            try:
                                _nq_parts.append(f"EPS {_tip_ccy}{float(_nq_eps):,.2f}")
                            except (TypeError, ValueError):
                                pass
                        if _nq_parts:
                            _a_tip.append("תחזית רבעון הבא: " + " · ".join(_nq_parts))
                        # מול הקונצנזוס
                        _nq_arv = _nqg.get("analyst_revenue_b")
                        _nq_vs = _nqg.get("vs_consensus", "none")
                        _cons_parts = []
                        if _nq_arv is not None:
                            try:
                                _cons_parts.append(
                                    "<span style='color:#9ca3af; font-size:10px;'>קונצנזוס: "
                                    + fmt_money_b(float(_nq_arv), _tip_ccy) + "</span>"
                                )
                            except (TypeError, ValueError):
                                pass
                        if _nq_vs and _nq_vs != "none":
                            _vs_map = {
                                "above": "🟢 מעל הקונצנזוס",
                                "inline": "⚪ בקו עם הקונצנזוס",
                                "below": "🔴 מתחת לקונצנזוס",
                            }
                            _vs_lbl = _vs_map.get(_nq_vs, "")
                            if _vs_lbl:
                                _cons_parts.append(_vs_lbl)
                        if _cons_parts:
                            _a_tip.append(" · ".join(_cons_parts))
                    # תג מקור
                    _a_tip.append("<span style='color:#a78bfa; font-size:10px;'>🔮 מוערך (Gemini)</span>")
                    _a_tip_html = "<br>".join(_a_tip)
                    _cell += (
                        "<div class='chip-analyzed-wrap'>"
                        "<div class='chip-analyzed' style='background:" + _bg + "; color:" + _fg + "; border:" + _bd + "; "
                        "font-size:11px; font-weight:700; padding:3px 6px; "
                        "border-radius:5px; margin:2px 0; white-space:nowrap; "
                        "text-align:center; position:relative; cursor:default;'>"
                        + _sym +
                        "<div class='chip-tip'>" + _a_tip_html + "</div>"
                        "</div>"
                        "</div>"
                    )
            else:
                _cell += (
                    "<div style='background:" + _bg + "; color:" + _fg + "; border:" + _bd + "; "
                    "font-size:11px; font-weight:700; padding:3px 6px; "
                    "border-radius:5px; margin:2px 0; white-space:nowrap; "
                    "text-align:center;'>"
                    + _sym + "</div>"
                )
        _cell += "</td>"
        _row += _cell
    _rows_html += _row + "</tr>"

st.markdown(
    "<style>"
    ".chip-future-wrap { position: relative; display: block; }"
    ".chip-future { position: relative; cursor: default; }"
    ".chip-tip {"
    "  display: none;"
    "  position: absolute;"
    "  top: calc(100% + 4px);"
    "  left: 50%;"
    "  transform: translateX(-50%);"
    "  background: #1e2533;"
    "  color: #e5e7eb;"
    "  font-size: 11px;"
    "  font-weight: 400;"
    "  line-height: 1.7;"
    "  padding: 6px 10px;"
    "  border-radius: 6px;"
    "  border: 1px solid #374151;"
    "  white-space: nowrap;"
    "  z-index: 9999;"
    "  text-align: right;"
    "  direction: rtl;"
    "  pointer-events: none;"
    "  box-shadow: 0 4px 12px rgba(0,0,0,0.5);"
    "}"
    ".chip-future:hover .chip-tip { display: block; }"
    ".chip-analyzed-wrap { position: relative; display: block; }"
    ".chip-analyzed { position: relative; cursor: default; }"
    ".chip-analyzed:hover .chip-tip { display: block; }"
    "</style>"
    "<div style='overflow:visible; margin-top:8px;'>"
    "<table style='width:100%; border-collapse:separate; border-spacing:3px; table-layout:fixed; overflow:visible;'>"
    + _hdr_html + _rows_html +
    "</table>"
    "<div dir='rtl' style='font-size:12px; color:#9ca3af; margin-top:10px; display:flex; gap:12px; flex-wrap:wrap;'>"
    "<span style='background:rgba(37,99,235,0.30); color:#bfdbfe; padding:2px 8px; border-radius:4px; border:1px solid rgba(96,165,250,0.5);'>🔵 עתידי</span>"
    "<span style='background:rgba(22,101,52,0.45); color:#bbf7d0; padding:2px 8px; border-radius:4px; border:1px solid rgba(74,222,128,0.5);'>🟢 נותח ✓</span>"
    "<span style='background:rgba(161,98,7,0.45); color:#fde68a; padding:2px 8px; border-radius:4px; border:1px solid rgba(253,211,77,0.5);'>🟡 ממתין לניתוח</span>"
    "<span>🇮🇱 ישראלית</span>"
    "<span style='color:#60a5fa; font-weight:700;'>■ היום</span>"
    "</div></div>",
    unsafe_allow_html=True,
)

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# ======================================================
# חברות ישראליות — מעקב צמוד
# ======================================================
st.markdown("<div id='zone-il'></div>", unsafe_allow_html=True)
st.markdown(section_header("🇮🇱 חברות ישראליות — מעקב צמוד", "#3b82f6"), unsafe_allow_html=True)
st.caption("מעקב קבוע אחר שלוש החברות הישראליות בסקטור — דוח אחרון, דוח הבא, וניתוח השפעת עונת הדוחות.")

_il_season = latest_season_with_data(_z6_sent_data)

def _build_il_ctx(season_analyzed):
    """בונה טקסט הקשר לניתוח ישראלי. מחזיר (ctx_text, [syms])."""
    ctx_lines = []
    syms = []
    for _s, _r in season_analyzed.items():
        _sc = _r.get("sentiment_score", 0) or 0
        _sm = _r.get("summary", "")
        _gd = _r.get("guidance_direction", "")
        _sc_pct = ("+" if _sc >= 0 else "") + str(int(round(_sc * 100))) + "%"
        ctx_lines.append(
            "• " + _s + " (סנטימנט: " + _sc_pct +
            (", הנחיה: " + _gd if _gd and _gd != "none" else "") +
            "): " + _sm
        )
        for _sig in _r.get("domain_signals", []):
            ctx_lines.append(
                "  ↳ " + _sig.get("domain", "") + ": " +
                _sig.get("direction", "") + " — " + _sig.get("note", "")
            )
        syms.append(_s)
    ctx_text = "\n".join(ctx_lines) if ctx_lines else "אין ניתוחים שמורים לעונה זו עדיין."
    return ctx_text, syms


# כל הניתוחים השמורים לעונה — יועברו לפונקציית ה-Gemini
_il_season_analyzed = {
    sym: _z6_sent_data[sym][_il_season]
    for sym in _z6_sent_data
    if _il_season in _z6_sent_data.get(sym, {})
}

# מיפוי: חברה → דוח אחרון (is_future=False) ודוח הבא (is_future=True)
_il_last = {}
_il_next = {}
for _e in _z6_all_entries:
    _esym = _e["symbol"]
    if _esym not in ISRAELI_TICKERS:
        continue
    _ed = _e["date"]
    if not _e["is_future"]:
        if _esym not in _il_last or _ed > _il_last[_esym]["date"]:
            _il_last[_esym] = _e
    else:
        if _esym not in _il_next or _ed < _il_next[_esym]["date"]:
            _il_next[_esym] = _e

_il_descriptions = {
    "TSEM": "Tower Semi · Foundry אנלוגי",
    "NVMI": "Nova · Process Control",
    "CAMT": "Camtek · Inspection",
}

_il_display = sorted(ISRAELI_TICKERS)
_il_cols = st.columns(len(_il_display))
for _il_i, _il_sym in enumerate(_il_display):
    with _il_cols[_il_i]:
        with st.container(border=True):
            _il_rec = get_record(_z6_sent_data, _il_sym, _il_season)
            _il_analyzed = bool(_il_rec and _il_rec.get("sentiment_score") is not None)
            _il_dot = "<span>🟢</span>" if _il_analyzed else ""
            st.markdown(
                "<div dir='rtl' style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>"
                "<span><span style='font-size:17px; font-weight:800;'>🇮🇱 " + _il_sym + "</span>"
                " <span style='font-size:12px; color:#9ca3af;'>" + _il_descriptions.get(_il_sym, "") + "</span></span>"
                + _il_dot + "</div>",
                unsafe_allow_html=True,
            )

            # דוח אחרון
            _il_le = _il_last.get(_il_sym)
            if _il_le:
                _il_eps_a = _il_le.get("eps_actual")
                _il_eps_e = _il_le.get("eps_est")
                _il_surp = _il_le.get("surprise")
                _il_eps_html = ""
                if _il_eps_a is not None:
                    _il_eps_html = " · EPS: $" + f"{_il_eps_a:.2f}"
                    if _il_eps_e is not None:
                        _il_eps_html += " (צפוי: $" + f"{_il_eps_e:.2f}" + ")"
                _il_surp_html = ""
                if _il_surp is not None:
                    _il_sc = "#22c55e" if _il_surp > 0 else "#ef4444"
                    _il_ss = "+" if _il_surp > 0 else ""
                    _il_surp_html = (" <span style='color:" + _il_sc + ";'>(" +
                                     _il_ss + f"{_il_surp:.1f}%" + ")</span>")
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; margin:3px 0;'>"
                    "📋 <b>דוח אחרון:</b> " + str(_il_le["date"]) + _il_eps_html + _il_surp_html + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#6b7280; margin:3px 0;'>"
                    "📋 דוח אחרון: לא ידוע בחלון הנוכחי</div>",
                    unsafe_allow_html=True,
                )

            # דוח הבא
            _il_ne = _il_next.get(_il_sym)
            if _il_ne:
                _il_days = (_il_ne["date"] - _today_date).days
                _il_days_txt = " (" + str(_il_days) + " ימים)" if _il_days >= 0 else ""
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; margin:3px 0;'>"
                    "📅 <b>דוח הבא:</b> " + str(_il_ne["date"]) + _il_days_txt + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#6b7280; margin:3px 0;'>"
                    "📅 דוח הבא: לא ידוע בחלון הנוכחי</div>",
                    unsafe_allow_html=True,
                )

            # סנטימנט שמור
            if _il_rec and _il_rec.get("sentiment_score") is not None:
                _il_score = float(_il_rec["sentiment_score"])
                _il_pct = sentiment_pct(_il_score)
                _il_emoji = "🟢" if _il_score >= SENTIMENT_POS else ("🔴" if _il_score <= SENTIMENT_NEG else "⚪")
                _il_col_c = "#22c55e" if _il_score >= SENTIMENT_POS else ("#ef4444" if _il_score <= SENTIMENT_NEG else "#9ca3af")
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; margin:3px 0 10px;'>"
                    "🧠 <b>סנטימנט " + _il_season + ":</b> " + _il_emoji +
                    " <span style='color:" + _il_col_c + "; font-weight:700;'>" +
                    str(_il_pct) + "%</span></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#6b7280; margin:3px 0 10px;'>"
                    "🧠 " + _il_season + ": טרם נותח</div>",
                    unsafe_allow_html=True,
                )

            # כפתור ניתוח השפעה
            _il_impact_key = "il_impact_" + _il_sym + "_" + _il_season
            _il_impact_res = st.session_state.get(_il_impact_key)
            if st.button("🔍 נתח השפעת עונת הדוחות", key="il_impact_btn_" + _il_sym,
                         width='stretch'):
                _il_ctx_text, _il_ctx_syms = _build_il_ctx(_il_season_analyzed)
                with st.spinner("מנתח השפעת הדוחות על " + _il_sym + "..."):
                    _il_txt, _il_srcs = gemini_israeli_impact(_il_sym, _il_season, _il_ctx_text)
                if _il_txt is not None:
                    st.session_state[_il_impact_key] = {
                        "text": _il_txt, "sources": _il_srcs,
                        "count": len(_il_ctx_syms), "companies": _il_ctx_syms,
                    }
                    st.rerun()

            if _il_impact_res:
                _il_saved_count = _il_impact_res.get("count", 0)
                _il_saved_syms = _il_impact_res.get("companies", [])
                st.caption(
                    "מבוסס על " + str(_il_saved_count) + " דוחות שנותחו בעונה " + _il_season +
                    (": " + ", ".join(_il_saved_syms) if _il_saved_syms else "")
                )
                if len(_il_season_analyzed) > _il_saved_count:
                    st.caption("💡 נותחו דוחות נוספים מאז — לחצי שוב לעדכון")
                st.markdown(
                    "<div dir='rtl' style='font-size:13px; color:#d1d5db; line-height:1.6; text-align:right; "
                    "background:rgba(255,255,255,0.04); border-radius:6px; padding:8px 10px; margin-top:4px;'>"
                    + html.escape(_il_impact_res.get("text") or "") + "</div>",
                    unsafe_allow_html=True,
                )
                if _il_impact_res.get("sources"):
                    with st.expander("מקורות"):
                        for _t, _u in _il_impact_res["sources"]:
                            st.markdown("• [" + (_t or _u) + "](" + _u + ")")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# --- ניתוח השפעת עונה לחברות נוספות ---
with st.expander("🔍 ניתוח השפעת עונת הדוחות — חברות נוספות"):
    st.caption("בחרי חברה לניתוח ההשפעה של הדוחות שפורסמו עד כה בעונה " + _il_season + ".")
    _ext_companies = [c for c in CORE_COMPANIES if c not in ISRAELI_TICKERS]
    _ext_chosen = st.selectbox("חברה:", _ext_companies, key="il_ext_sym")
    _ext_impact_key = "il_impact_" + _ext_chosen + "_" + _il_season
    _ext_impact_res = st.session_state.get(_ext_impact_key)

    if st.button("🔍 נתח השפעת עונת הדוחות", key="il_ext_impact_btn", width='stretch'):
        _ext_ctx_text, _ext_ctx_syms = _build_il_ctx(_il_season_analyzed)
        with st.spinner("מנתח השפעת הדוחות על " + _ext_chosen + "..."):
            _ext_txt, _ext_srcs = gemini_israeli_impact(_ext_chosen, _il_season, _ext_ctx_text)
        if _ext_txt is not None:
            st.session_state[_ext_impact_key] = {
                "text": _ext_txt, "sources": _ext_srcs,
                "count": len(_ext_ctx_syms), "companies": _ext_ctx_syms,
            }
            st.rerun()

    if _ext_impact_res:
        _ext_saved_count = _ext_impact_res.get("count", 0)
        _ext_saved_syms = _ext_impact_res.get("companies", [])
        st.caption(
            "מבוסס על " + str(_ext_saved_count) + " דוחות שנותחו בעונה " + _il_season +
            (": " + ", ".join(_ext_saved_syms) if _ext_saved_syms else "")
        )
        if len(_il_season_analyzed) > _ext_saved_count:
            st.caption("💡 נותחו דוחות נוספים מאז — לחצי שוב לעדכון")
        st.markdown(
            "<div dir='rtl' style='font-size:13px; color:#d1d5db; line-height:1.6; text-align:right; "
            "background:rgba(255,255,255,0.04); border-radius:6px; padding:8px 10px; margin-top:4px;'>"
            + html.escape(_ext_impact_res.get("text") or "") + "</div>",
            unsafe_allow_html=True,
        )
        if _ext_impact_res.get("sources"):
            with st.expander("מקורות"):
                for _t, _u in _ext_impact_res["sources"]:
                    st.markdown("• [" + (_t or _u) + "](" + _u + ")")

with st.expander("🎯 ניתוח השפעה ממוקדת — דוח של חברה אחת על חברה אחרת"):
    if not _il_season_analyzed:
        st.caption("אין עדיין דוחות מנותחים בעונה זו")
    else:
        _foc_source_opts = list(_il_season_analyzed.keys())
        _foc_source = st.selectbox("דוח מקור:", _foc_source_opts, key="foc_source_sel")
        _foc_target_opts = [c for c in CORE_COMPANIES if c != _foc_source]
        _foc_target = st.selectbox("חברת יעד:", _foc_target_opts, key="foc_target_sel")
        _foc_key = "focus_impact_" + _foc_source + "_" + _foc_target + "_" + _il_season
        _foc_res = st.session_state.get(_foc_key)
        if st.button("🎯 נתח השפעה", key="foc_impact_btn", width='stretch'):
            _foc_record = _il_season_analyzed[_foc_source]
            with st.spinner("מנתח השפעת " + _foc_source + " על " + _foc_target + "..."):
                _foc_txt, _foc_srcs = gemini_focused_impact(
                    _foc_source, _foc_target, _il_season, _foc_record
                )
            if _foc_txt is not None:
                st.session_state[_foc_key] = {"text": _foc_txt, "sources": _foc_srcs}
                st.rerun()
        if _foc_res:
            st.markdown(
                "<div dir='rtl' style='font-size:13px; color:#d1d5db; line-height:1.6; text-align:right; "
                "background:rgba(255,255,255,0.04); border-radius:6px; padding:8px 10px; margin-top:4px;'>"
                + html.escape(_foc_res.get("text") or "") + "</div>",
                unsafe_allow_html=True,
            )
            if _foc_res.get("sources"):
                with st.expander("מקורות"):
                    for _t, _u in _foc_res["sources"]:
                        st.markdown("• [" + (_t or _u) + "](" + _u + ")")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

st.markdown(section_header("🧠 ניתוח דוח ושיחת ועידה", "#f59e0b"), unsafe_allow_html=True)

_z6_chosen = st.selectbox("בחרי חברה לניתוח הדוח:", CORE_COMPANIES, key="z6_sym_select")

_z6_default_season = latest_season_with_data(_z6_sent_data)
if DEV_MODE:
    # בחירה חופשית — כולל עונות שטרם נותחו; לשימוש מפתח בלבד.
    # מתחיל מ-current_season() (שעצמה עוברת דרך season_from_date) ויורד 4 רבעונים אחורה.
    _cur_s = current_season()
    _q, _y = int(_cur_s[5]), int(_cur_s[:4])
    _season_opts: list[str] = []
    for _ in range(4):
        _season_opts.append(f"{_y}Q{_q}")
        _q -= 1
        if _q == 0:
            _q, _y = 4, _y - 1
    _default_idx = _season_opts.index(_z6_default_season) if _z6_default_season in _season_opts else 0
    _z6_season: str = st.selectbox("עונה:", _season_opts, index=_default_idx, key="z6_season_select")
else:
    _z6_season = _z6_default_season

_z6_result_key = "earnings_result_" + _z6_chosen + "_" + _z6_season
_z6_saved_rec = get_record(_z6_sent_data, _z6_chosen, _z6_season)
_z6_pending = st.session_state.get(_z6_result_key)

if st.session_state.get("z6_save_msg"):
    st.success(st.session_state.pop("z6_save_msg"))


def israeli_exposure_to_signals(domain_signals):
    """מצליב סיגנלים תחומיים של דוח עם חשיפות TSEM/NVMI/CAMT מ-TECH_GROUPS.
    מחזיר {sym: [(domain, direction, eff_exposure), ...]} — רק חברות עם התאמה."""
    ISRAELI_SYMS = {"TSEM", "NVMI", "CAMT"}
    signal_domains = {s.get("domain"): s.get("direction") for s in domain_signals if s.get("domain")}
    result: dict[str, list] = {}
    for axis in TECH_GROUPS.values():
        for domain_name, tiers in axis.items():
            if domain_name not in signal_domains:
                continue
            direction = signal_domains[domain_name]
            for tier_key, tier_mult in (("core", TIER_CORE), ("env", TIER_ENV)):
                for sym, exp in tiers.get(tier_key, {}).items():
                    if sym in ISRAELI_SYMS:
                        result.setdefault(sym, []).append((domain_name, direction, exp * tier_mult))
    for sym in result:
        result[sym].sort(key=lambda x: -x[2])
    return result


def _render_analysis_record(rec, label="", eps_surprise=None, stock_reaction=None, symbol=""):
    """מרנדר רשומת ניתוח (מה-JSON או מ-session_state)."""
    _ccy_sym = currency_symbol(record_currency(symbol, rec))
    score = float(rec.get("sentiment_score") or 0)
    pct = sentiment_pct(score)
    emoji = "🟢" if score >= SENTIMENT_POS else ("🔴" if score <= SENTIMENT_NEG else "⚪")
    col = "#22c55e" if score >= SENTIMENT_POS else ("#ef4444" if score <= SENTIMENT_NEG else "#9ca3af")
    res_map = {"beat": "🟢 הכה ציפיות", "meet": "⚪ עמד בציפיות", "miss": "🔴 פספס ציפיות"}
    guid_map = {"raised": "📈 הועלתה", "maintained": "➡️ נשמרה", "lowered": "📉 הורדה", "none": "—"}
    res_txt = res_map.get(rec.get("results_vs_expectations", ""), "—")
    guid_txt = guid_map.get(rec.get("guidance_direction", ""), "—")
    report_date = rec.get("report_date", "—")
    summary = rec.get("summary", "")
    signals = rec.get("domain_signals", [])

    # שורת תגובת שוק (הפתעת EPS מוצגת ב-rev_row בלבד, כאן רק תגובת השוק)
    mkt_parts = []
    if stock_reaction is not None:
        try:
            rp = float(stock_reaction)
            rp_sign = "+" if rp >= 0 else ""
            rp_col = "#22c55e" if rp > 0 else ("#ef4444" if rp < 0 else "#9ca3af")
            mkt_parts.append(
                "<span>תגובת שוק: <b style='color:" + rp_col + ";'>" + rp_sign + f"{rp:.1f}%" + "</b></span>"
            )
        except (TypeError, ValueError):
            pass
    # אזהרה: הפתעה חיובית + שוק ירד
    alert_html = ""
    if eps_surprise is not None and stock_reaction is not None:
        try:
            if float(eps_surprise) > 0 and float(stock_reaction) < -1:
                alert_html = (
                    "<div dir='rtl' style='background:rgba(234,179,8,0.15); border:1px solid #ca8a04; "
                    "border-radius:6px; padding:5px 10px; font-size:12px; color:#fbbf24; margin-top:4px; text-align:right;'>"
                    "⚠️ הפתעה חיובית אך המניה ירדה</div>"
                )
        except (TypeError, ValueError):
            pass

    mkt_row = ""
    if mkt_parts:
        mkt_row = (
            "<div dir='rtl' style='display:flex; gap:16px; margin:0 0 6px; flex-wrap:wrap; "
            "font-size:13px; background:rgba(30,37,51,0.6); padding:5px 10px; border-radius:6px;'>"
            + " · ".join(mkt_parts) + "</div>"
        )

    _gemini_tag = (
        "<span style='font-size:11px; color:#a78bfa; background:rgba(167,139,250,0.12); "
        "padding:1px 6px; border-radius:4px; border:1px solid rgba(167,139,250,0.3);'>"
        "🔮 מוערך (Gemini)</span>"
    )

    # --- שורת EPS + הכנסות מוערכות (מ-Gemini) — EPS ראשון, אחר כך הכנסות, תג אחד בסוף ---
    rev_row = ""
    _combined_parts: list[str] = []

    # חלק EPS — רק אם שני השדות קיימים ואינם null
    _eps_act = rec.get("eps_actual")
    _eps_est = rec.get("eps_estimate")
    if _eps_act is not None and _eps_est is not None:
        try:
            _ea_f = float(_eps_act)
            _ee_f = float(_eps_est)
            _eps_parts = [
                f"EPS: <b>{_ccy_sym}{_ea_f:,.2f}</b> בפועל",
                f"<span style='color:#9ca3af;'>{_ccy_sym}{_ee_f:,.2f} צפי</span>",
            ]
            if _ee_f != 0:
                _es = _ea_f / _ee_f * 100 - 100
                _es_col = "#22c55e" if _es > 0 else ("#ef4444" if _es < 0 else "#9ca3af")
                _es_sign = "+" if _es > 0 else ""
                _eps_parts.append(
                    f"<span style='color:{_es_col}; font-weight:700;'>{_es_sign}{_es:.1f}% הפתעה</span>"
                )
            _combined_parts.extend(_eps_parts)
        except (TypeError, ValueError):
            pass

    # חלק הכנסות — רק אם שני השדות קיימים ואינם null
    _rev_act = rec.get("revenue_actual_b")
    _rev_est = rec.get("revenue_estimate_b")
    if _rev_act is not None and _rev_est is not None:
        try:
            _rev_act_f = float(_rev_act)
            _rev_est_f = float(_rev_est)
            _rev_parts = [
                "הכנסות: <b>" + fmt_money_b(_rev_act_f, _ccy_sym) + "</b> בפועל",
                "<span style='color:#9ca3af;'>" + fmt_money_b(_rev_est_f, _ccy_sym) + " צפי</span>",
            ]
            if _rev_est_f != 0:
                _rs = _rev_act_f / _rev_est_f * 100 - 100
                _rs_col = "#22c55e" if _rs > 0 else ("#ef4444" if _rs < 0 else "#9ca3af")
                _rs_sign = "+" if _rs > 0 else ""
                _rev_parts.append(
                    f"<span style='color:{_rs_col}; font-weight:700;'>{_rs_sign}{_rs:.1f}% הפתעה</span>"
                )
            _combined_parts.extend(_rev_parts)
        except (TypeError, ValueError):
            pass

    if _combined_parts:
        rev_row = (
            "<div dir='rtl' style='display:flex; gap:12px; margin:0 0 6px; flex-wrap:wrap; "
            "align-items:center; font-size:13px; background:rgba(30,37,51,0.6); "
            "padding:5px 10px; border-radius:6px;'>"
            + " · ".join(_combined_parts) + " " + _gemini_tag + "</div>"
        )

    # --- שורת תחזית לרבעון הבא (מ-Gemini, מוצגת רק אם יש לפחות ערך אחד שאינו null) ---
    guid_row = ""
    _nqg = rec.get("next_q_guidance")
    if isinstance(_nqg, dict):
        _nq_parts = []
        _nq_rev = _nqg.get("revenue_b")
        _nq_eps = _nqg.get("eps")
        _nq_arv = _nqg.get("analyst_revenue_b")
        _nq_vs = _nqg.get("vs_consensus", "none")
        if _nq_rev is not None:
            try:
                _nq_parts.append("צפי הכנסות רבעון הבא: <b>" + fmt_money_b(float(_nq_rev), _ccy_sym) + "</b>")
            except (TypeError, ValueError):
                pass
        if _nq_eps is not None:
            try:
                _nq_parts.append(f"EPS: <b>{_ccy_sym}{float(_nq_eps):,.2f}</b>")
            except (TypeError, ValueError):
                pass
        if _nq_arv is not None:
            try:
                _nq_parts.append(
                    "<span style='color:#9ca3af;'>קונצנזוס: " + fmt_money_b(float(_nq_arv), _ccy_sym) + "</span>"
                )
            except (TypeError, ValueError):
                pass
        if _nq_vs and _nq_vs != "none":
            _vs_map = {
                "above": "🟢 מעל הקונצנזוס",
                "inline": "⚪ בקו עם הקונצנזוס",
                "below": "🔴 מתחת לקונצנזוס",
            }
            _vs_lbl = _vs_map.get(_nq_vs, "")
            if _vs_lbl:
                _nq_parts.append(_vs_lbl)
        if _nq_parts:
            guid_row = (
                "<div dir='rtl' style='display:flex; gap:12px; margin:0 0 6px; flex-wrap:wrap; "
                "align-items:center; font-size:13px; background:rgba(30,37,51,0.6); "
                "padding:5px 10px; border-radius:6px;'>"
                + " · ".join(_nq_parts) + " " + _gemini_tag + "</div>"
            )

    st.markdown(
        "<div dir='rtl' style='text-align:right; margin-bottom:6px;'>"
        "<span style='font-size:17px; font-weight:800;'>" + _z6_chosen + "</span>"
        + (" <span style='font-size:11px; color:#9ca3af; background:#1e2533; padding:1px 6px; border-radius:4px;'>" + label + "</span>" if label else "") +
        "<span style='color:#6b7280; font-size:13px; margin-right:10px;'> " + _z6_season + " · " + html.escape(report_date) + "</span></div>"
        + mkt_row + alert_html + rev_row + guid_row +
        "<div dir='rtl' style='display:flex; gap:20px; margin:6px 0 10px; flex-wrap:wrap; font-size:14px;'>"
        "<span>סנטימנט: " + emoji + " <b style='color:" + col + ";'>" + str(pct) + "%</b></span>"
        "<span>תוצאות: " + res_txt + "</span>"
        "<span>הנחיה: " + guid_txt + "</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    if summary or signals:
        st.markdown(
            "<div dir='rtl' style='margin:10px 0 8px; padding-top:10px; "
            "border-top:1px solid rgba(255,255,255,0.10); "
            "font-size:12px; color:#6b7280; font-weight:700; letter-spacing:0.03em; text-align:right;'>📝 ניתוח</div>",
            unsafe_allow_html=True,
        )
    if summary:
        st.markdown(
            "<div dir='rtl' style='color:#d1d5db; font-size:14px; line-height:1.6; margin-bottom:8px; text-align:right;'>"
            + html.escape(summary) + "</div>",
            unsafe_allow_html=True,
        )
    if signals:
        dir_map = {"improving": "🟢⬆️", "stable": "⚪➡️", "deteriorating": "🔴⬇️"}
        sig_rows = "".join(
            "<tr>"
            "<td style='text-align:right; padding:4px 8px; font-size:13px;'>" + s.get("domain", "") + "</td>"
            "<td style='text-align:center; padding:4px 8px;'>" + dir_map.get(s.get("direction", ""), "") + "</td>"
            "<td style='text-align:right; padding:4px 8px; color:#9ca3af; font-size:12px;'>" + html.escape(s.get("note", "")) + "</td>"
            "</tr>"
            for s in signals
        )
        st.markdown(
            "<div dir='rtl' style='text-align:right;'><b style='font-size:13px;'>סיגנלים תחומיים:</b>"
            "<table dir='rtl' style='width:100%; border-collapse:collapse; margin-top:4px;'>"
            "<tr>"
            "<th style='text-align:right; padding:4px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>תחום</th>"
            "<th style='text-align:center; padding:4px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>כיוון</th>"
            "<th style='text-align:right; padding:4px 8px; font-size:12px; color:#9ca3af; border-bottom:1px solid #444;'>הערה</th>"
            "</tr>" + sig_rows + "</table></div>",
            unsafe_allow_html=True,
        )
        # --- נגיעה בחברות הישראליות (הצלבה מקומית, ללא AI) ---
        _il_matches = israeli_exposure_to_signals(signals)
        if _il_matches:
            _il_dir_map = {"improving": "🟢⬆️", "stable": "⚪➡️", "deteriorating": "🔴⬇️"}
            _il_rows_html = []
            for _il_sym in ["TSEM", "NVMI", "CAMT"]:
                _il_hits = _il_matches.get(_il_sym)
                if not _il_hits:
                    continue
                _il_parts = [f"<b>{_il_sym}</b>"]
                for _il_dom, _il_dir, _ in _il_hits:
                    _il_icon = _il_dir_map.get(_il_dir, "")
                    _il_parts.append(f"{_il_icon} {_il_dom}")
                _il_rows_html.append(" · ".join(_il_parts))
            if _il_rows_html:
                st.markdown(
                    "<div dir='rtl' style='text-align:right; margin-top:8px; "
                    "background:rgba(20,24,36,0.7); border:1px solid #2d3748; "
                    "border-radius:6px; padding:8px 12px;'>"
                    "<div style='font-size:13px; font-weight:700; color:#e5e7eb; margin-bottom:6px;'>"
                    "🇮🇱 נגיעה בחברות הישראליות:</div>"
                    + "".join(
                        "<div style='font-size:13px; color:#d1d5db; margin-bottom:3px;'>" + r + "</div>"
                        for r in _il_rows_html
                    )
                    + "<div style='font-size:11px; color:#6b7280; margin-top:6px;'>"
                    "הצלבה אוטומטית של סיגנלי הדוח עם חשיפות החברות ב-TECH_GROUPS — לא ניתוח AI"
                    "</div></div>",
                    unsafe_allow_html=True,
                )


with st.container(border=True):
    # --- תוצאה ממתינה לאישור (מ-Gemini, טרם נשמרה) — מצב מפתח בלבד ---
    if DEV_MODE and _z6_pending:
        if "error" in _z6_pending:
            st.warning(_z6_pending["error"])
        else:
            st.info("ניתוח חדש ממתין לאישור שמירה:")

            # --- helper: parse optional float field (text → float or None) ---
            def _parse_opt_float(raw, field_label):
                """מחרוזת ריקה → None; מספר תקין → float; אחרת → מחזיר None ומציג אזהרה."""
                s = raw.strip()
                if s == "":
                    return None, True
                try:
                    return float(s), True
                except ValueError:
                    st.warning("⚠️ שדה " + field_label + " — ערך לא חוקי: " + s + ". יישמר ללא שינוי.")
                    return None, False

            # --- list of all domain names from TECH_GROUPS (for signals selectbox) ---
            _all_domains = sorted({
                grp
                for axis in TECH_GROUPS.values()
                for grp in axis.keys()
            })

            _ed_hash = hashlib.md5(
                json.dumps(_z6_pending, sort_keys=True, default=str).encode()
            ).hexdigest()[:6]
            _ed_prefix = _z6_chosen + "_" + _z6_season + "_" + _ed_hash + "_"
            _edit_key = "z6_edit_mode_" + _ed_prefix
            _edit_mode = st.toggle("✏️ ערוך ערכים לפני שמירה", key=_edit_key, value=False)

            with st.container(border=True):
                if not _edit_mode:
                    # ───── מצב צפייה (ברירת מחדל) ─────
                    _render_analysis_record(_z6_pending, symbol=_z6_chosen)
                else:
                    # ───── מצב עריכה ─────
                    st.markdown("<div dir='rtl' style='font-size:13px; color:#9ca3af; margin-bottom:10px;'>עורכת רשומה — שינויים ייכנסו רק אחרי לחיצה על שמור.</div>", unsafe_allow_html=True)

                    # שלב 1 — שדות סקלריים ובחירה
                    _ec1, _ec2 = st.columns(2)
                    with _ec1:
                        _ed_date = st.text_input("תאריך דוח (YYYY-MM-DD)",
                            value=_z6_pending.get("report_date", "") or "",
                            key="z6_ed_date_" + _ed_prefix)
                        _RESULTS_OPTS = ["beat", "meet", "miss"]
                        _cur_res = _z6_pending.get("results_vs_expectations", "beat") or "beat"
                        _ed_results = st.selectbox("תוצאות מול ציפיות",
                            options=_RESULTS_OPTS,
                            index=_RESULTS_OPTS.index(_cur_res) if _cur_res in _RESULTS_OPTS else 0,
                            key="z6_ed_results_" + _ed_prefix)
                        _GUID_OPTS = ["raised", "maintained", "lowered", "none"]
                        _cur_guid = _z6_pending.get("guidance_direction", "maintained") or "maintained"
                        _ed_guid = st.selectbox("כיוון תחזית (guidance)",
                            options=_GUID_OPTS,
                            index=_GUID_OPTS.index(_cur_guid) if _cur_guid in _GUID_OPTS else 1,
                            key="z6_ed_guid_" + _ed_prefix)
                    with _ec2:
                        _ed_score_raw = float(_z6_pending.get("sentiment_score") or 0.0)
                        _ed_score = st.number_input("ציון סנטימנט (0%–100%, 50% = ניטרלי)",
                            min_value=0, max_value=100, step=5,
                            value=sentiment_pct(_ed_score_raw),
                            key="z6_ed_score_" + _ed_prefix)
                        st.caption("50% = ניטרלי · 63% = הסף הירוק · 38% = הסף האדום · 💡 תיקון מספרים לא משנה את הציון אוטומטית — אם התיקון הופך את התמונה (miss↔beat), עדכני גם את הציון והתוצאות ידנית.")
                    _ed_summary = st.text_area("סיכום",
                        value=_z6_pending.get("summary", "") or "",
                        height=100,
                        key="z6_ed_summary_" + _ed_prefix)

                    # שלב 2 — שדות מספריים אופציונליים (text → float/None)
                    st.markdown("**מספרים (ריק = לא ידוע)**")
                    _nf1, _nf2, _nf3, _nf4 = st.columns(4)
                    def _fstr(v):
                        return "" if v is None else str(v)
                    with _nf1:
                        _ed_eps_act = st.text_input("EPS בפועל",
                            value=_fstr(_z6_pending.get("eps_actual")),
                            key="z6_ed_epsact_" + _ed_prefix)
                    with _nf2:
                        _ed_eps_est = st.text_input("EPS תחזית",
                            value=_fstr(_z6_pending.get("eps_estimate")),
                            key="z6_ed_epsest_" + _ed_prefix)
                    with _nf3:
                        _ed_rev_act = st.text_input("הכנסות בפועל (B$)",
                            value=_fstr(_z6_pending.get("revenue_actual_b")),
                            key="z6_ed_revact_" + _ed_prefix)
                    with _nf4:
                        _ed_rev_est = st.text_input("הכנסות תחזית (B$)",
                            value=_fstr(_z6_pending.get("revenue_estimate_b")),
                            key="z6_ed_revest_" + _ed_prefix)

                    # שלב 3 — next_q_guidance
                    _nqg = _z6_pending.get("next_q_guidance") or {}
                    st.markdown("**תחזית רבעון הבא**")
                    _nq1, _nq2, _nq3, _nq4 = st.columns(4)
                    with _nq1:
                        _ed_nq_rev = st.text_input("הכנסות Q הבא (B$)",
                            value=_fstr(_nqg.get("revenue_b")),
                            key="z6_ed_nqrev_" + _ed_prefix)
                    with _nq2:
                        _ed_nq_eps = st.text_input("EPS Q הבא",
                            value=_fstr(_nqg.get("eps")),
                            key="z6_ed_nqeps_" + _ed_prefix)
                    with _nq3:
                        _ed_nq_arev = st.text_input("הכנסות אנליסטים (B$)",
                            value=_fstr(_nqg.get("analyst_revenue_b")),
                            key="z6_ed_nqarev_" + _ed_prefix)
                    with _nq4:
                        _CONS_OPTS = ["above", "inline", "below", "none"]
                        _cur_cons = _nqg.get("vs_consensus", "none") or "none"
                        _ed_nq_cons = st.selectbox("מול קונצנזוס",
                            options=_CONS_OPTS,
                            index=_CONS_OPTS.index(_cur_cons) if _cur_cons in _CONS_OPTS else 3,
                            key="z6_ed_nqcons_" + _ed_prefix)

                    # שלב 4 — domain_signals
                    _DIR_OPTS = ["improving", "stable", "deteriorating"]
                    _existing_sigs = list(_z6_pending.get("domain_signals") or [])
                    st.markdown("**סיגנלים תחומיים**")
                    _sig_rows = []
                    _delete_flags = []
                    for _si, _sig in enumerate(_existing_sigs):
                        _sc0, _sc1, _sc2, _sc3 = st.columns([0.3, 2, 1.5, 3])
                        with _sc0:
                            _del = st.checkbox("מחק", key="z6_sigdel_" + str(_si) + "_" + _ed_prefix, label_visibility="collapsed")
                            _delete_flags.append(_del)
                        with _sc1:
                            _cur_dom = _sig.get("domain", _all_domains[0])
                            _dom_i = _all_domains.index(_cur_dom) if _cur_dom in _all_domains else 0
                            _ed_dom = st.selectbox("תחום", options=_all_domains, index=_dom_i,
                                key="z6_sigdom_" + str(_si) + "_" + _ed_prefix,
                                label_visibility="collapsed")
                        with _sc2:
                            _cur_dir = _sig.get("direction", "stable")
                            _ed_dir = st.selectbox("כיוון", options=_DIR_OPTS,
                                index=_DIR_OPTS.index(_cur_dir) if _cur_dir in _DIR_OPTS else 1,
                                key="z6_sigdir_" + str(_si) + "_" + _ed_prefix,
                                label_visibility="collapsed")
                        with _sc3:
                            _ed_note = st.text_input("הערה", value=_sig.get("note", "") or "",
                                key="z6_signote_" + str(_si) + "_" + _ed_prefix,
                                label_visibility="collapsed")
                        _sig_rows.append({"domain": _ed_dom, "direction": _ed_dir, "note": _ed_note})

                    # שורת הוספה
                    st.markdown("*➕ סיגנל חדש (אופציונלי)*")
                    _an1, _an2, _an3 = st.columns([2, 1.5, 3])
                    with _an1:
                        _new_dom = st.selectbox("תחום חדש", options=[""] + _all_domains,
                            key="z6_newdom_" + _ed_prefix, label_visibility="collapsed")
                    with _an2:
                        _new_dir = st.selectbox("כיוון חדש", options=_DIR_OPTS,
                            key="z6_newdir_" + _ed_prefix, label_visibility="collapsed")
                    with _an3:
                        _new_note = st.text_input("הערה חדשה", value="",
                            key="z6_newnote_" + _ed_prefix, label_visibility="collapsed")

                # ─── כפתורים (משותפים לשני המצבים) ───
                _sc, _dc = st.columns(2)
                with _sc:
                    if st.button("✅ שמור לקובץ", key="z6_savebtn_" + _z6_chosen,
                                 width='stretch', type="primary"):
                        _save_ok = True
                        if _edit_mode:
                            # --- בנה record מהשדות הערוכים ---
                            _v_eps_act, _ok1 = _parse_opt_float(_ed_eps_act, "EPS בפועל")
                            _v_eps_est, _ok2 = _parse_opt_float(_ed_eps_est, "EPS תחזית")
                            _v_rev_act, _ok3 = _parse_opt_float(_ed_rev_act, "הכנסות בפועל")
                            _v_rev_est, _ok4 = _parse_opt_float(_ed_rev_est, "הכנסות תחזית")
                            _v_nq_rev,  _ok5 = _parse_opt_float(_ed_nq_rev, "הכנסות Q הבא")
                            _v_nq_eps,  _ok6 = _parse_opt_float(_ed_nq_eps, "EPS Q הבא")
                            _v_nq_arev, _ok7 = _parse_opt_float(_ed_nq_arev, "הכנסות אנליסטים")
                            _save_ok = all([_ok1, _ok2, _ok3, _ok4, _ok5, _ok6, _ok7])

                            _final_sigs = [
                                _sig_rows[i]
                                for i in range(len(_sig_rows))
                                if not _delete_flags[i]
                            ]
                            if _new_dom:
                                _final_sigs.append({"domain": _new_dom, "direction": _new_dir, "note": _new_note})

                            _record = {
                                "report_date": _ed_date.strip(),
                                "sentiment_score": round(_ed_score / 100 * 2 - 1, 4),
                                "results_vs_expectations": _ed_results,
                                "guidance_direction": _ed_guid,
                                "summary": _ed_summary.strip(),
                                "domain_signals": _final_sigs,
                                "revenue_actual_b": _v_rev_act,
                                "revenue_estimate_b": _v_rev_est,
                                "eps_actual": _v_eps_act,
                                "eps_estimate": _v_eps_est,
                                "next_q_guidance": {
                                    "revenue_b": _v_nq_rev,
                                    "eps": _v_nq_eps,
                                    "analyst_revenue_b": _v_nq_arev,
                                    "vs_consensus": _ed_nq_cons,
                                },
                                "currency": _z6_pending.get("currency") or record_currency(_z6_chosen, _z6_pending),
                                "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            }
                        else:
                            # --- ללא עריכה: שמור כמו שהוא ---
                            _record = {
                                "report_date": _z6_pending.get("report_date", ""),
                                "sentiment_score": _z6_pending.get("sentiment_score"),
                                "results_vs_expectations": _z6_pending.get("results_vs_expectations", ""),
                                "guidance_direction": _z6_pending.get("guidance_direction", ""),
                                "summary": _z6_pending.get("summary", ""),
                                "domain_signals": _z6_pending.get("domain_signals", []),
                                "revenue_actual_b": _z6_pending.get("revenue_actual_b"),
                                "revenue_estimate_b": _z6_pending.get("revenue_estimate_b"),
                                "eps_actual": _z6_pending.get("eps_actual"),
                                "eps_estimate": _z6_pending.get("eps_estimate"),
                                "next_q_guidance": _z6_pending.get("next_q_guidance"),
                                "currency": _z6_pending.get("currency") or record_currency(_z6_chosen, _z6_pending),
                                "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            }

                        if _save_ok:
                            save_sentiment_record(_z6_chosen, _z6_season, _record)
                            del st.session_state[_z6_result_key]
                            for _k in [k for k in st.session_state
                                       if k.startswith(("z6_ed_", "z6_sig", "z6_new", "z6_edit_mode_"))]:
                                del st.session_state[_k]
                            st.session_state["z6_save_msg"] = "נשמר: " + _z6_chosen + " / " + _z6_season
                            st.rerun()
                with _dc:
                    if st.button("🗑️ בטל", key="z6_discardbtn_" + _z6_chosen, width='stretch'):
                        del st.session_state[_z6_result_key]
                        for _k in [k for k in st.session_state
                                   if k.startswith(("z6_ed_", "z6_sig", "z6_new", "z6_edit_mode_"))]:
                            del st.session_state[_k]
                        st.rerun()

    # --- ניתוח שמור בקובץ ---
    elif _z6_saved_rec:
        _z6_eps_surp = None
        _z6_react = None
        _z6_rd = _z6_saved_rec.get("report_date")
        if _z6_rd and _z6_rd != "—":
            for _e in _z6_all_entries:
                if _e["symbol"] == _z6_chosen and str(_e["date"]) == _z6_rd:
                    _z6_eps_surp = _e.get("surprise")
                    break
            _z6_react, _ = get_stock_reaction(_z6_chosen, _z6_rd)
        with st.container(border=True):
            _render_analysis_record(_z6_saved_rec, label="שמור",
                                    eps_surprise=_z6_eps_surp, stock_reaction=_z6_react,
                                    symbol=_z6_chosen)
        if DEV_MODE:
            if st.button("🔄 עדכן ניתוח עם Gemini", key="z6_analyzebtn_" + _z6_chosen):
                with st.spinner("מחפש דוח ושיחת ועידה עם Gemini..."):
                    _z6_new_result = gemini_analyze_earnings(_z6_chosen, _z6_season)
                if _z6_new_result is None:
                    st.error("⚠️ הניתוח נכשל — לא התקבלה תשובה מ-Gemini. נסי שוב.")
                else:
                    st.session_state[_z6_result_key] = _z6_new_result
                    st.rerun()

    # --- אין ניתוח עדיין ---
    else:
        st.markdown(
            "<div dir='rtl' style='text-align:center; padding:20px 12px; "
            "background:rgba(255,255,255,0.03); border-radius:8px; color:#9ca3af; font-size:14px;'>"
            "ℹ️ אין ניתוח שמור לחברה זו בעונה " + _z6_season + " — טרם נותח."
            "</div>",
            unsafe_allow_html=True,
        )
        if DEV_MODE:
            if st.button("🧠 נתח דוח עם Gemini", key="z6_analyzebtn_" + _z6_chosen, type="primary"):
                with st.spinner("מחפש דוח ושיחת ועידה עם Gemini..."):
                    _z6_new_result = gemini_analyze_earnings(_z6_chosen, _z6_season)
                if _z6_new_result is None:
                    st.error("⚠️ הניתוח נכשל — לא התקבלה תשובה מ-Gemini. נסי שוב.")
                else:
                    st.session_state[_z6_result_key] = _z6_new_result
                    st.rerun()

# --- היסטוריית תוצאות מול צפי ---
with st.container(border=True):
    with st.expander("📊 היסטוריית תוצאות מול צפי", expanded=False):
        _hist_eps_df = get_earnings_history(_z6_chosen)
        _hist_rev_s, _hist_rev_name = get_quarterly_revenue(_z6_chosen)
        _hist_ccy = get_financial_currency(_z6_chosen)

        if _hist_eps_df is None:
            st.caption("אין נתוני EPS היסטוריים זמינים לחברה זו.")
        else:
            # מיפוי YYYYQN → נתוני EPS
            _h_eps_by_q: dict[str, dict] = {}
            for _hdt, _hrow in _hist_eps_df.iterrows():
                _hqk = season_from_date(_hdt)
                _h_eps_by_q[_hqk] = {
                    "date": str(_hdt.date()) if hasattr(_hdt, "date") else str(_hdt)[:10],
                    "actual": _hrow.get("Reported EPS"),
                    "est":    _hrow.get("EPS Estimate"),
                    "surp":   _hrow.get("Surprise(%)"),
                }

            # מיפוי YYYYQN → הכנסות
            _h_rev_by_q: dict[str, float] = {}
            if _hist_rev_s is not None:
                for _rdt, _rv in zip(_hist_rev_s.index, _hist_rev_s.values):
                    _h_rev_by_q[season_from_date(_rdt)] = float(_rv)

            _h_has_rev = bool(_h_rev_by_q)

            # מיפוי YYYYQN → רשומת סנטימנט מ-Gemini (_z6_sent_data כבר בסקופ)
            _h_sent_by_q: dict[str, dict] = {
                _sqk: _srec
                for _sqk, _srec in (_z6_sent_data.get(_z6_chosen) or {}).items()
            }

            # רק רבעונים מנותחים ושמורים — הטבלה תצבור כל ניתוח חדש
            _h_quarters = sorted(_h_sent_by_q.keys(), reverse=True)

            if not _h_quarters:
                st.caption("טרם נותחו רבעונים לחברה זו.")
            else:
                def _hfmt(v, dec=2):
                    if v is None or (isinstance(v, float) and math.isnan(v)):
                        return "<span style='color:#6b7280;'>—</span>"
                    return f"{v:,.{dec}f}"

                def _hfmt_surp(v):
                    if v is None or (isinstance(v, float) and math.isnan(v)):
                        return "<span style='color:#6b7280;'>—</span>"
                    c = "#22c55e" if v > 0 else ("#ef4444" if v < 0 else "#9ca3af")
                    s = "+" if v > 0 else ""
                    return f"<span style='color:{c}; font-weight:700;'>{s}{v:.1f}%</span>"

                def _hfmt_sent(score):
                    sc = float(score)
                    pct = sentiment_pct(sc)
                    col = "#22c55e" if sc >= SENTIMENT_POS else ("#ef4444" if sc <= SENTIMENT_NEG else "#9ca3af")
                    emoji = "🟢" if sc >= SENTIMENT_POS else ("🔴" if sc <= SENTIMENT_NEG else "⚪")
                    return f"{emoji} <span style='color:{col}; font-weight:700;'>{pct}%</span>"

                _rev_hdr_txt = f"הכנסות ({_hist_ccy}, B)" if _h_has_rev else ""
                _h_thdr = (
                    "<tr style='border-bottom:1px solid #444;'>"
                    "<th style='text-align:right; padding:6px 10px; color:#9ca3af;'>רבעון</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>תאריך</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>EPS בפועל</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>EPS צפי</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>הפתעה %</th>"
                    + (f"<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>{_rev_hdr_txt}</th>"
                       if _h_has_rev else "")
                    + "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>הכנסות צפי 🔮 (B)</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>הפתעת הכנסות 🔮</th>"
                    "<th style='text-align:center; padding:6px 10px; color:#9ca3af;'>סנטימנט</th>"
                    "</tr>"
                )
                _h_td_dash = "<td style='text-align:center; padding:6px 10px; color:#6b7280;'>—</td>"
                _h_rows_html = ""
                for _hqk in _h_quarters:
                    _hq = _h_eps_by_q.get(_hqk) or {}
                    _h_srec = _h_sent_by_q.get(_hqk) or {}

                    # --- מצב פיצול: מטבע הרשומה שונה ממטבע yfinance ---
                    _row_ccy = record_currency(_z6_chosen, _h_srec) if _h_srec else _hist_ccy
                    _is_split = bool(_h_srec) and _row_ccy != _hist_ccy
                    _split_tip = (
                        "<div class='chip-tip'>"
                        f"מוצג מנתוני הניתוח (Gemini) ב-{_row_ccy} · yfinance מדווח ב-{_hist_ccy}"
                        "</div>"
                    ) if _is_split else ""

                    # --- הכנסות בפועל ---
                    _rev_cell = ""
                    if _h_has_rev:
                        if _is_split:
                            _rva = _h_srec.get("revenue_actual_b")
                            if _rva is not None:
                                try:
                                    _rva_html = fmt_money_b(float(_rva), currency_symbol(_row_ccy))
                                    _rev_cell = (
                                        "<td style='text-align:center; padding:6px 10px;'>"
                                        f"<span class='chip-future' style='position:relative;'>{_rva_html}{_split_tip}</span></td>"
                                    )
                                except (TypeError, ValueError):
                                    _rev_cell = _h_td_dash
                            else:
                                _rev_cell = _h_td_dash
                        else:
                            _hrv = _h_rev_by_q.get(_hqk)
                            if _hrv is not None and not (isinstance(_hrv, float) and math.isnan(_hrv)):
                                _rev_cell = "<td style='text-align:center; padding:6px 10px;'>" + fmt_money_b(_hrv) + "</td>"
                            else:
                                _rev_cell = _h_td_dash

                    # --- EPS בפועל, צפי, הפתעה ---
                    if _is_split:
                        _eps_a = _h_srec.get("eps_actual")
                        _eps_e = _h_srec.get("eps_estimate")
                        _eps_act_cell = (
                            "<td style='text-align:center; padding:6px 10px;'>"
                            f"<span class='chip-future' style='position:relative;'>{_hfmt(_eps_a)}{_split_tip}</span></td>"
                        )
                        _eps_est_cell = (
                            "<td style='text-align:center; padding:6px 10px; color:#9ca3af;'>"
                            f"<span class='chip-future' style='position:relative;'>{_hfmt(_eps_e)}{_split_tip}</span></td>"
                        )
                        _eps_surp_inner = "<span style='color:#6b7280;'>—</span>"
                        if _eps_a is not None and _eps_e is not None:
                            try:
                                _ge = float(_eps_e)
                                _ga = float(_eps_a)
                                if _ge != 0:
                                    _eps_surp_inner = _hfmt_surp(_ga / _ge * 100 - 100)
                            except (TypeError, ValueError):
                                pass
                        _eps_surp_cell = (
                            "<td style='text-align:center; padding:6px 10px;'>"
                            f"<span class='chip-future' style='position:relative;'>{_eps_surp_inner}{_split_tip}</span></td>"
                        )
                    else:
                        _eps_act_cell  = f"<td style='text-align:center; padding:6px 10px;'>{_hfmt(_hq.get('actual'))}</td>"
                        _eps_est_cell  = f"<td style='text-align:center; padding:6px 10px; color:#9ca3af;'>{_hfmt(_hq.get('est'))}</td>"
                        _eps_surp_cell = f"<td style='text-align:center; padding:6px 10px;'>{_hfmt_surp(_hq.get('surp'))}</td>"

                    # --- תאי Gemini: הכנסות צפי / הפתעת הכנסות / סנטימנט ---
                    _h_rev_est_gem = _h_srec.get("revenue_estimate_b")
                    _h_rev_act_gem = _h_srec.get("revenue_actual_b")
                    _h_sent_score  = _h_srec.get("sentiment_score")

                    _gem_est_cell = _h_td_dash
                    if _h_rev_est_gem is not None:
                        try:
                            _gem_est_cell = "<td style='text-align:center; padding:6px 10px;'>" + fmt_money_b(float(_h_rev_est_gem), currency_symbol(record_currency(_z6_chosen, _h_srec))) + "</td>"
                        except (TypeError, ValueError):
                            pass

                    _gem_surp_cell = _h_td_dash
                    if _h_rev_act_gem is not None and _h_rev_est_gem is not None:
                        try:
                            _ge_f = float(_h_rev_est_gem)
                            _ga_f = float(_h_rev_act_gem)
                            if _ge_f != 0:
                                _gem_surp_cell = f"<td style='text-align:center; padding:6px 10px;'>{_hfmt_surp(_ga_f / _ge_f * 100 - 100)}</td>"
                        except (TypeError, ValueError):
                            pass

                    _gem_sent_cell = _h_td_dash
                    if _h_sent_score is not None:
                        try:
                            _gem_sent_cell = f"<td style='text-align:center; padding:6px 10px;'>{_hfmt_sent(_h_sent_score)}</td>"
                        except (TypeError, ValueError):
                            pass

                    _h_date_val = _hq.get('date') or _h_srec.get('report_date', '—')
                    _h_rows_html += (
                        "<tr style='border-top:1px solid rgba(255,255,255,0.07);'>"
                        f"<td style='text-align:right; padding:6px 10px; font-weight:600;'>{_hqk}</td>"
                        f"<td style='text-align:center; padding:6px 10px; color:#9ca3af; font-size:11px;'>{_h_date_val}</td>"
                        + _eps_act_cell + _eps_est_cell + _eps_surp_cell
                        + _rev_cell
                        + _gem_est_cell + _gem_surp_cell + _gem_sent_cell
                        + "</tr>"
                    )
                st.markdown(
                    "<div dir='rtl' style='overflow-x:auto;'>"
                    "<table dir='rtl' style='width:100%; border-collapse:collapse; font-size:13px;'>"
                    + _h_thdr + _h_rows_html + "</table></div>",
                    unsafe_allow_html=True,
                )
                if not _h_has_rev:
                    st.caption("אין נתוני הכנסות רבעוניים זמינים לחברה זו.")

# ======================================================
# אזור 8 — דירוגי אנליסטים ומחירי יעד
# ======================================================
st.markdown(
    "<div style='margin:48px 0 32px; border-top:2px solid rgba(255,255,255,0.10); "
    "position:relative;'></div>",
    unsafe_allow_html=True,
)
section_banner(8, 8, "🎯", "דירוגי אנליסטים ומחירי יעד", "#ec4899",
               subtitle="שדרוגים, הורדות ומחירי יעד לפי חברה",
               period_dependent=False)

# --- א) Top/Bottom 5 אנליסטים ---
_z8_sorted = sorted(_analyst_scores.items(), key=lambda x: x[1]["score"], reverse=True)
_z8_top5   = _z8_sorted[:5]
_z8_bot5   = list(reversed(_z8_sorted[-5:])) if len(_z8_sorted) >= 5 else list(reversed(_z8_sorted))

# (תווית, יישור th+td, מפתח) — מקור אמת יחיד לכותרות ולשורות
_AN_COLS = [
    ("מניה",       "right",  "sym"),
    ("ציון",       "center", "score"),
    ("פירוט",      "right",  "detail"),
    ("אנליסטים",   "center", "n"),
    ("פוטנציאל",   "center", "upside"),
]

def _z8_analyst_row(sym, sc, med):
    _iso = lambda t: ("<span dir='ltr' style='unicode-bidi:isolate; display:inline-block;'>"
                      + str(t) + "</span>")
    color = analyst_color(sc["score"], med)
    score_txt = str(round(sc["score"], 2))
    detail = (str(sc["buy"]) + " קנייה · "
              + str(sc["hold"]) + " החזקה · "
              + str(sc["sell"]) + " מכירה")

    # פוטנציאל תשואה — אותו חישוב בדיוק כמו _z8_upside בחלק ד' (מחירי היעד),
    # לא הגדרה חדשה. חסר אצל מניות רבות שאינן אמריקאיות (כמו 000660.KS,
    # 005930.KS) שאין להן מחיר יעד ב-yfinance — מוצג "—" אפור ולא זורק שגיאה.
    _pt = get_price_targets(sym)
    _upside = None
    if _pt:
        _pt_cur = _pt.get("current")
        _pt_mean = _pt.get("mean")
        if _pt_cur and _pt_mean:
            try:
                _upside = (_pt_mean - _pt_cur) / _pt_cur * 100
            except Exception:
                _upside = None
    if _upside is None:
        upside_html = "<span style='color:#6b7280;'>—</span>"
    else:
        _up_color = "#22c55e" if _upside >= 0 else "#ef4444"
        _up_sign = "+" if _upside >= 0 else ""
        upside_html = _iso(
            "<span style='color:" + _up_color + "; font-weight:700;'>"
            + _up_sign + str(round(_upside, 1)) + "%</span>"
        )

    cells = {
        "sym":    ("<td style='padding:5px 10px; text-align:right; font-weight:600;'>"
                   + _iso(sym) + "</td>"),
        "score":  ("<td style='padding:5px 10px; text-align:center; color:" + color
                   + "; font-weight:700;'>" + _iso(score_txt) + "</td>"),
        "detail": ("<td style='padding:5px 10px; text-align:right; color:#9ca3af; font-size:11px;'>"
                   + detail + "</td>"),
        "n":      ("<td style='padding:5px 10px; text-align:center; color:#6b7280; font-size:11px;'>"
                   + _iso("n=" + str(sc["n"])) + "</td>"),
        "upside": ("<td style='padding:5px 10px; text-align:center;'>" + upside_html + "</td>"),
    }
    return (
        "<tr style='border-top:1px solid rgba(255,255,255,0.06);'>"
        + "".join(cells[key] for _, _, key in _AN_COLS)
        + "</tr>"
    )

_z8_tbl_hdr = (
    "<table dir='rtl' style='width:100%; border-collapse:collapse; font-size:12px;'>"
    "<tr style='color:#6b7280; font-size:11px;'>"
    + "".join(
        "<th style='padding:4px 10px; text-align:" + align + ";'>" + label + "</th>"
        for label, align, _ in _AN_COLS
    )
    + "</tr>"
)

_z8_col_top, _z8_col_bot = st.columns(2)
with _z8_col_top:
    st.markdown(
        "<div dir='rtl' style='text-align:right; font-weight:700; font-size:16px; margin-bottom:6px;'>🏆 5 המדורגות הגבוהות</div>",
        unsafe_allow_html=True,
    )
    _z8_top_rows = "".join(_z8_analyst_row(s, sc, _analyst_med) for s, sc in _z8_top5)
    st.markdown(_z8_tbl_hdr + _z8_top_rows + "</table>", unsafe_allow_html=True)

with _z8_col_bot:
    st.markdown(
        "<div dir='rtl' style='text-align:right; font-weight:700; font-size:16px; margin-bottom:6px;'>⚠️ 5 המדורגות הנמוכות</div>",
        unsafe_allow_html=True,
    )
    _z8_bot_rows = "".join(_z8_analyst_row(s, sc, _analyst_med) for s, sc in _z8_bot5)
    st.markdown(_z8_tbl_hdr + _z8_bot_rows + "</table>", unsafe_allow_html=True)

# --- ב) בורר חברה ---
_z8_sym = st.selectbox(
    "בחרי חברה לניתוח מחירי יעד ודירוגים:",
    list(_rating_universe),
    key="z8_sym",
)

# --- ציון אנליסטים לחברה הנבחרת ---
_z8_ascore = get_analyst_score(_z8_sym)
if _z8_ascore and _z8_ascore.get("score") is not None:
    _z8_sc = round(_z8_ascore["score"], 2)
    _z8_sc_n = _z8_ascore.get("n", 0)
    _z8_buy  = _z8_ascore.get("buy", 0)
    _z8_hld  = _z8_ascore.get("hold", 0)
    _z8_sel  = _z8_ascore.get("sell", 0)
    _z8_dist_txt = (
        str(_z8_buy) + " קנייה · "
        + str(_z8_hld) + " החזקה · "
        + str(_z8_sel) + " מכירה"
    )
    st.markdown(
        "<div dir='rtl' style='background:rgba(255,255,255,0.04); border-radius:8px; "
        "padding:10px 14px; margin:8px 0; text-align:right;'>"
        "<span style='color:#9ca3af; font-size:12px;'>ציון אנליסטים: </span>"
        "<span style='color:#e5e7eb; font-weight:700; font-size:16px;'>" + str(_z8_sc) + "</span>"
        "<span style='color:#6b7280; font-size:11px;'> / 5 &nbsp;(n=" + str(_z8_sc_n) + ")</span>"
        "<br><span style='color:#9ca3af; font-size:11px;'>" + _z8_dist_txt + "</span>"
        "</div>",
        unsafe_allow_html=True,
    )

# --- ג) מחירי יעד ---
_z8_pt = get_price_targets(_z8_sym)
if _z8_pt:
    _z8_ccy = currency_symbol(_z8_pt.get("currency", "USD"))
    _z8_cur  = _z8_pt.get("current")
    _z8_mean = _z8_pt.get("mean")
    _z8_low  = _z8_pt.get("low")
    _z8_high = _z8_pt.get("high")
    _z8_med  = _z8_pt.get("median")

    _z8_upside = None
    if _z8_cur and _z8_mean:
        try:
            _z8_upside = (_z8_mean - _z8_cur) / _z8_cur * 100
        except Exception:
            pass

    _z8_c1, _z8_c2, _z8_c3, _z8_c4 = st.columns(4)
    for _col, _lbl, _val in [
        (_z8_c1, "מחיר נוכחי",  _z8_cur),
        (_z8_c2, "יעד ממוצע",   _z8_mean),
        (_z8_c3, "יעד נמוך",    _z8_low),
        (_z8_c4, "יעד גבוה",    _z8_high),
    ]:
        with _col:
            _vf = (_z8_ccy + str(round(_val, 2))) if _val is not None else "—"
            st.metric(_lbl, _vf)

    if _z8_upside is not None:
        _z8_us_c = "#22c55e" if _z8_upside >= 0 else "#ef4444"
        st.markdown(
            "<div dir='rtl' style='text-align:right; margin-top:4px;'>"
            "<span style='color:" + _z8_us_c + "; font-size:12px;'>"
            + ("+" if _z8_upside >= 0 else "") + str(round(_z8_upside, 1)) + "% פוטנציאל</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    if all(v is not None for v in [_z8_cur, _z8_low, _z8_high]):
        _z8_fig = go.Figure()
        _z8_fig.add_trace(go.Bar(
            x=[_z8_sym], y=[_z8_high - _z8_low],
            base=[_z8_low], marker_color="rgba(59,130,246,0.35)",
            name="טווח יעדים", hovertemplate="נמוך: " + _z8_ccy + str(round(_z8_low, 2)) +
                "<br>גבוה: " + _z8_ccy + str(round(_z8_high, 2)) + "<extra></extra>",
        ))
        if _z8_mean:
            _z8_fig.add_hline(
                y=_z8_mean, line_dash="dot", line_color="#facc15", line_width=2,
                annotation_text="ממוצע " + _z8_ccy + str(round(_z8_mean, 2)),
                annotation_position="right",
                annotation_font_color="#facc15",
            )
        _z8_fig.add_hline(
            y=_z8_cur, line_dash="dash", line_color="#f59e0b",
            annotation_text="נוכחי " + _z8_ccy + str(round(_z8_cur, 2)),
            annotation_position="right",
            annotation_font_color="#f59e0b",
        )
        _z8_fig.update_layout(
            height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(color="#9ca3af"), xaxis=dict(color="#9ca3af"),
            showlegend=False, margin=dict(l=10, r=80, t=20, b=10),
        )
        st.plotly_chart(_z8_fig, width='stretch')
else:
    st.caption("אין נתוני מחירי יעד זמינים לחברה זו.")

# --- ד) התפלגות המלצות ---
_z8_rec = get_recommendation_dist(_z8_sym)
if _z8_rec:
    _z8_rec_total = sum(_z8_rec.values()) or 1
    _z8_rec_labels = [
        ("קנייה חזקה", "#22c55e", _z8_rec.get("strongBuy", 0)),
        ("קנייה",      "#86efac", _z8_rec.get("buy", 0)),
        ("החזקה",      "#eab308", _z8_rec.get("hold", 0)),
        ("מכירה",      "#f97316", _z8_rec.get("sell", 0)),
        ("מכירה חזקה", "#ef4444", _z8_rec.get("strongSell", 0)),
    ]
    # RTL: קנייה חזקה בימין — הופך את סדר הרכיבים בפס
    _z8_bar = "<div dir='rtl' style='display:flex; flex-direction:row-reverse; height:22px; border-radius:6px; overflow:hidden; margin:8px 0;'>"
    _z8_legend = "<div dir='rtl' style='display:flex; flex-wrap:wrap; gap:10px; font-size:11px; color:#9ca3af; margin-top:4px; text-align:right;'>"
    for _lbl, _col, _cnt in reversed(_z8_rec_labels):
        if _cnt > 0:
            _pct = _cnt / _z8_rec_total * 100
            _z8_bar += ("<span style='background:" + _col + "; width:" + str(round(_pct, 1)) + "%;'"
                        " title='" + _lbl + ": " + str(_cnt) + "'></span>")
    for _lbl, _col, _cnt in _z8_rec_labels:
        if _cnt > 0:
            _z8_legend += ("<span><span style='color:" + _col + "; font-weight:700;'>■</span> "
                           + _lbl + " (" + str(_cnt) + ")</span>")
    _z8_bar += "</div>"
    _z8_legend += "</div>"
    st.markdown(
        "<div dir='rtl' style='margin:8px 0; text-align:right;'>"
        "<div style='font-size:13px; font-weight:700; margin-bottom:4px;'>התפלגות המלצות אנליסטים</div>"
        + _z8_bar + _z8_legend + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.caption("אין נתוני התפלגות המלצות זמינים לחברה זו.")

# --- ה) טבלת שדרוגים/הורדות ---
_z8_ud = get_upgrades_downgrades(_z8_sym, limit=200)
_z8_ud_cutoff = (datetime.now(timezone.utc).date() - timedelta(days=365))
_z8_ud_tbl = (
    _z8_ud[_z8_ud["date"] >= _z8_ud_cutoff].reset_index(drop=True)
    if _z8_ud is not None and not _z8_ud.empty else None
)
if _z8_ud_tbl is not None and not _z8_ud_tbl.empty:
    _z8_rows = ""
    for _, _row in _z8_ud_tbl.iterrows():
        _act = str(_row.get("Action", _row.get("action", ""))).lower()
        _bg  = "rgba(34,197,94,0.10)" if _act == "up" else ("rgba(239,68,68,0.10)" if _act == "down" else "transparent")
        _dir = "⬆️ שדרוג" if _act == "up" else ("⬇️ הורדה" if _act == "down" else _act)
        _dir_col = "#22c55e" if _act == "up" else ("#ef4444" if _act == "down" else "#9ca3af")
        _grade_col = "#22c55e" if _act == "up" else ("#ef4444" if _act == "down" else "#eab308")
        _raw_date = _row.get("date", "")
        try:
            _date_str = _raw_date.strftime("%d/%m/%Y")
        except AttributeError:
            _ds = str(_raw_date)
            _date_str = _ds[8:10] + "/" + _ds[5:7] + "/" + _ds[:4] if len(_ds) >= 10 and _ds[4] == "-" else _ds
        _z8_rows += (
            "<tr style='background:" + _bg + "; border-top:1px solid rgba(255,255,255,0.05);'>"
            "<td style='padding:6px 10px; text-align:right; color:#9ca3af;'>" + _date_str + "</td>"
            "<td style='padding:6px 10px; text-align:right;'>" + str(_row.get("Firm", _row.get("firm", ""))) + "</td>"
            "<td style='padding:6px 10px; text-align:right; color:" + _dir_col + "; font-weight:700;'>" + _dir + "</td>"
            "<td style='padding:6px 10px; text-align:right; color:" + _grade_col + "; font-size:11px;'>"
            + str(_row.get("FromGrade", "")) + " → " + str(_row.get("ToGrade", "")) + "</td>"
            "</tr>"
        )
    st.markdown(
        "<div dir='rtl' style='overflow-x:auto; margin-top:12px; text-align:right;'>"
        "<div style='font-size:13px; font-weight:700; margin-bottom:6px;'>שדרוגים / הורדות — 12 החודשים האחרונים</div>"
        "<table dir='rtl' style='width:100%; border-collapse:collapse; font-size:12px;'>"
        "<tr style='color:#6b7280; font-size:11px;'>"
        "<th style='padding:4px 10px; text-align:right;'>תאריך</th>"
        "<th style='padding:4px 10px; text-align:right;'>בית השקעות</th>"
        "<th style='padding:4px 10px; text-align:right;'>פעולה</th>"
        "<th style='padding:4px 10px; text-align:right;'>דירוג</th>"
        "</tr>"
        + _z8_rows + "</table></div>",
        unsafe_allow_html=True,
    )
else:
    st.caption("אין נתוני שדרוגים/הורדות זמינים לחברה זו.")

# --- ו) כפתור Gemini ---
_z8_gemini_key = "z8_gemini_" + _z8_sym
if _z8_ud is not None and not _z8_ud.empty:
    _z8_latest = _z8_ud.iloc[0]
    _z8_act    = str(_z8_latest.get("Action", _z8_latest.get("action", ""))).lower()
    if _z8_act in ("up", "down"):
        if st.button("🧠 הסבר את שינוי הדירוג האחרון", key="z8_gem_btn_" + _z8_sym):
            with st.spinner("מחפש ברשת ומנתח..."):
                _z8_txt, _z8_srcs = gemini_explain_rating(
                    symbol=_z8_sym,
                    firm=str(_z8_latest.get("Firm", _z8_latest.get("firm", ""))),
                    action=_z8_act,
                    from_grade=str(_z8_latest.get("FromGrade", "")),
                    to_grade=str(_z8_latest.get("ToGrade", "")),
                    grade_date=str(_z8_latest.get("date", "")),
                )
            st.session_state[_z8_gemini_key] = {"text": _z8_txt, "sources": _z8_srcs}

    if _z8_gemini_key in st.session_state:
        _z8_saved = st.session_state[_z8_gemini_key]
        if _z8_saved.get("text"):
            st.markdown(
                "<div dir='rtl' style='background:rgba(236,72,153,0.07); border:1px solid rgba(236,72,153,0.30);"
                " border-radius:8px; padding:12px 16px; margin-top:8px; font-size:13px; line-height:1.7;'>"
                + html.escape(_z8_saved["text"]) + "</div>",
                unsafe_allow_html=True,
            )
        if _z8_saved.get("sources"):
            with st.expander("מקורות"):
                for _z8_title, _z8_uri in _z8_saved["sources"]:
                    st.markdown("• [" + (_z8_title or _z8_uri) + "](" + _z8_uri + ")")
