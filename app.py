# ================================================================
# BrainForge — NCERT AI Tutor v4.0
# NEW IN v4.0:
#   1. Profile-based auth (Gmail SMTP OTP — works for ALL emails)
#   2. Quiz batch mode (5 / 10 / 15 / 20 questions + scorecard)
#   3. Exam Mode (real board-style questions, image + voice answers, marks)
#   4. Weak Topics AI (auto-detect from wrong answers + revision tips)
#   5. Voice Input in Chat & Exam (streamlit-mic-recorder)
#   6. Caching layer (@st.cache_data) + cheaper/faster models
# ================================================================

import os, re, json, base64, datetime, random, uuid, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from groq import Groq
from supabase import create_client, Client
from PIL import Image
import io

try:
    from streamlit_mic_recorder import speech_to_text
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# ════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════

GROQ_MODEL        = "llama-3.1-8b-instant"           # fast + cheap
GROQ_VISION_MODEL = "llama-3.2-11b-vision-preview"   # smaller vision
MAX_HISTORY       = 6
DAILY_LIMIT       = 15
TOP_K             = 6
OTP_EXPIRY_MINUTES = 10
QUIZ_COUNTS       = [5, 10, 15, 20]

CLASSES       = ["Class 8", "Class 9", "Class 10"]
SUBJECTS      = ["Both", "Mathematics", "Science"]
SUBJECT_ICONS = {"Mathematics": "📐", "Science": "🔬", "Both": "📚"}
CLASS_ICONS   = {"Class 8": "8️⃣", "Class 9": "9️⃣", "Class 10": "🔟"}
CLASS_COLORS  = {"Class 8": "#7c3aed", "Class 9": "#0284c7", "Class 10": "#059669"}

CHAPTER_INDEX = {
    "Class 8": {
        "Mathematics": {
            "hemh101": "Chapter 1 — Rational Numbers",
            "hemh102": "Chapter 2 — Linear Equations in One Variable",
            "hemh103": "Chapter 3 — Understanding Quadrilaterals",
            "hemh104": "Chapter 4 — Data Handling",
            "hemh105": "Chapter 5 — Squares and Square Roots",
            "hemh106": "Chapter 6 — Cubes and Cube Roots",
            "hemh107": "Chapter 7 — Comparing Quantities",
            "hemh108": "Chapter 8 — Algebraic Expressions and Identities",
            "hemh109": "Chapter 9 — Mensuration",
            "hemh110": "Chapter 10 — Exponents and Powers",
            "hemh111": "Chapter 11 — Direct and Inverse Proportions",
            "hemh112": "Chapter 12 — Factorisation",
            "hemh113": "Chapter 13 — Introduction to Graphs",
        },
        "Science": {
            "hesc101": "Chapter 1 — Crop Production and Management",
            "hesc102": "Chapter 2 — Microorganisms: Friend and Foe",
            "hesc103": "Chapter 3 — Synthetic Fibres and Plastics",
            "hesc104": "Chapter 4 — Materials: Metals and Non-Metals",
            "hesc105": "Chapter 5 — Coal and Petroleum",
            "hesc106": "Chapter 6 — Combustion and Flame",
            "hesc107": "Chapter 7 — Conservation of Plants and Animals",
            "hesc108": "Chapter 8 — Cell Structure and Functions",
            "hesc109": "Chapter 9 — Reproduction in Animals",
            "hesc110": "Chapter 10 — Reaching the Age of Adolescence",
            "hesc111": "Chapter 11 — Force and Pressure",
            "hesc112": "Chapter 12 — Friction",
            "hesc113": "Chapter 13 — Sound",
            "hesc1ps": "Chapter 14 — Chemical Effects of Electric Current",
        },
    },
    "Class 9": {
        "Mathematics": {
            "iemh101": "Chapter 1 — Number Systems",
            "iemh102": "Chapter 2 — Polynomials",
            "iemh103": "Chapter 3 — Coordinate Geometry",
            "iemh104": "Chapter 4 — Linear Equations in Two Variables",
            "iemh105": "Chapter 5 — Introduction to Euclid's Geometry",
            "iemh106": "Chapter 6 — Lines and Angles",
            "iemh107": "Chapter 7 — Triangles",
            "iemh108": "Chapter 8 — Quadrilaterals",
            "iemh109": "Chapter 9 — Circles",
            "iemh110": "Chapter 10 — Heron's Formula",
            "iemh111": "Chapter 11 — Surface Areas and Volumes",
            "iemh112": "Chapter 12 — Statistics",
        },
        "Science": {
            "iesc101": "Chapter 1 — Matter in Our Surroundings",
            "iesc102": "Chapter 2 — Is Matter Around Us Pure?",
            "iesc103": "Chapter 3 — Atoms and Molecules",
            "iesc104": "Chapter 4 — Structure of the Atom",
            "iesc105": "Chapter 5 — The Fundamental Unit of Life",
            "iesc106": "Chapter 6 — Tissues",
            "iesc107": "Chapter 7 — Motion",
            "iesc108": "Chapter 8 — Force and Laws of Motion",
            "iesc109": "Chapter 9 — Gravitation",
            "iesc110": "Chapter 10 — Work and Energy",
            "iesc111": "Chapter 11 — Sound",
            "iesc112": "Chapter 12 — Improvement in Food Resources",
        },
    },
    "Class 10": {
        "Mathematics": {
            "jemh101": "Chapter 1 — Real Numbers",
            "jemh102": "Chapter 2 — Polynomials",
            "jemh103": "Chapter 3 — Pair of Linear Equations in Two Variables",
            "jemh104": "Chapter 4 — Quadratic Equations",
            "jemh105": "Chapter 5 — Arithmetic Progressions",
            "jemh106": "Chapter 6 — Triangles",
            "jemh107": "Chapter 7 — Coordinate Geometry",
            "jemh108": "Chapter 8 — Introduction to Trigonometry",
            "jemh109": "Chapter 9 — Some Applications of Trigonometry",
            "jemh110": "Chapter 10 — Circles",
            "jemh111": "Chapter 11 — Areas Related to Circles",
            "jemh112": "Chapter 12 — Surface Areas and Volumes",
            "jemh113": "Chapter 13 — Statistics",
            "jemh114": "Chapter 14 — Probability",
        },
        "Science": {
            "jesc101": "Chapter 1 — Chemical Reactions and Equations",
            "jesc102": "Chapter 2 — Acids, Bases and Salts",
            "jesc103": "Chapter 3 — Metals and Non-Metals",
            "jesc104": "Chapter 4 — Carbon and Its Compounds",
            "jesc105": "Chapter 5 — Life Processes",
            "jesc106": "Chapter 6 — Control and Coordination",
            "jesc107": "Chapter 7 — How do Organisms Reproduce?",
            "jesc108": "Chapter 8 — Heredity",
            "jesc109": "Chapter 9 — Light — Reflection and Refraction",
            "jesc110": "Chapter 10 — The Human Eye and the Colourful World",
            "jesc111": "Chapter 11 — Electricity",
            "jesc112": "Chapter 12 — Magnetic Effects of Electric Current",
            "jesc113": "Chapter 13 — Our Environment",
        },
    },
}

SUGGESTIONS = {
    "Class 8": {
        "Both":        ["What is photosynthesis?","Rational numbers?","Cell structure?","What is friction?","Metals vs non-metals?","Linear equations?"],
        "Mathematics": ["Rational numbers?","Linear equations?","Factorisation?","Area of trapezium?","Algebraic expressions?","Comparing quantities?"],
        "Science":     ["Photosynthesis?","Cell structure?","Friction?","How does sound travel?","Microorganisms?","Force and pressure?"],
    },
    "Class 9": {
        "Both":        ["Irrational numbers?","Newton's laws?","Polynomials?","Gravitation?","Tissues?","Coordinate geometry?"],
        "Mathematics": ["Irrational numbers?","Heron's formula?","Coordinate geometry?","Polynomials?","Euclid's geometry?","Lines and angles?"],
        "Science":     ["Newton's three laws?","Gravitation?","Atoms vs molecules?","Tissues?","Sound production?","Work and energy?"],
    },
    "Class 10": {
        "Both":        ["Real numbers?","Chemical reactions?","Trigonometry?","Acids vs bases?","Probability?","Light reflection?"],
        "Mathematics": ["Real numbers?","Quadratic equations?","Trigonometry?","Arithmetic progressions?","Surface area of cone?","Probability?"],
        "Science":     ["Chemical reactions?","Acids vs bases?","Heredity?","Human eye?","Electricity?","Life processes?"],
    },
}

# ════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="BrainForge — NCERT AI Tutor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&display=swap');
:root {
  --bg:#06070f; --surface:#0d1117; --border:rgba(255,255,255,0.07);
  --accent:#7c3aed; --text:#e2e8f0; --muted:#64748b;
  --success:#10b981; --warn:#f59e0b; --danger:#ef4444;
  --radius:14px; --font:'Space Grotesk',sans-serif;
}
html,body,.stApp { background:var(--bg)!important; color:var(--text)!important; font-family:var(--font)!important; }
#MainMenu,footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent!important; border-bottom:none!important; }
button[data-testid="collapsedControl"] {
  display:block!important; visibility:visible!important; opacity:1!important;
  background:rgba(124,58,237,0.2)!important; border-radius:8px!important; color:#a78bfa!important;
}
section[data-testid="stSidebar"] { background:#080b14!important; border-right:1px solid rgba(124,58,237,0.18)!important; }
section[data-testid="stSidebar"] * { color:var(--text)!important; }
.block-container { padding:1rem 1.5rem 110px 1.5rem!important; max-width:100%!important; }
.stButton>button { background:var(--accent)!important; color:#fff!important; border:none!important;
  border-radius:10px!important; font-weight:700!important; font-size:0.85rem!important; padding:0.5rem 1rem!important; }
.stButton>button:hover { background:#6d28d9!important; }
.stTextInput input,textarea { background:var(--surface)!important; border:1px solid var(--border)!important;
  border-radius:10px!important; color:var(--text)!important; }
textarea:focus,.stTextInput input:focus { border-color:var(--accent)!important; }
div[data-testid="stChatMessage"] { background:transparent!important; border:none!important; }
.msg-user { background:rgba(124,58,237,0.2); border-radius:16px; padding:10px 14px; max-width:80%; }
div[data-testid="stChatInput"] {
  position:sticky!important; bottom:0!important; z-index:10!important;
  background:linear-gradient(to top,#06070f 70%,transparent)!important; padding:14px 20px!important;
}
div[data-testid="stChatInput"] textarea {
  background:#0d1117!important; border:1px solid rgba(124,58,237,0.4)!important;
  border-radius:12px!important; color:var(--text)!important; font-size:0.9rem!important; padding:12px!important;
}
.stTabs [data-baseweb="tab-list"] { background:var(--surface)!important; border-radius:10px!important; padding:4px!important; }
.stTabs [data-baseweb="tab"] { color:var(--muted)!important; font-weight:600!important; }
.stTabs [aria-selected="true"] { background:var(--accent)!important; color:#fff!important; }
.stRadio label { background:rgba(255,255,255,0.03)!important; border:1px solid var(--border)!important;
  border-radius:8px!important; padding:6px 10px!important; }
.bf-card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:14px; margin-bottom:8px; }
.note-card { background:rgba(6,182,212,0.05); border:1px solid rgba(6,182,212,0.2); border-radius:12px; padding:12px; margin-bottom:8px; }
.quiz-opt { background:rgba(255,255,255,0.04); border:1px solid var(--border); border-radius:10px; padding:10px; margin-bottom:6px; cursor:pointer; }
.quiz-opt.correct { border-color:var(--success)!important; background:rgba(16,185,129,0.1); }
.quiz-opt.incorrect { border-color:var(--danger)!important; background:rgba(239,68,68,0.1); }
.img-solution-box { background:rgba(255,255,255,0.025); border:1px solid rgba(124,58,237,0.25); border-radius:14px; padding:18px 20px; margin-top:14px; }
.img-type-badge { display:inline-flex; align-items:center; gap:6px; background:rgba(124,58,237,0.12);
  border:1px solid rgba(124,58,237,0.28); border-radius:8px; padding:4px 12px;
  font-size:0.7rem; font-weight:700; color:#a78bfa; margin-bottom:12px; }
.img-preview-wrap { border:1px solid rgba(255,255,255,0.08); border-radius:12px; overflow:hidden; margin-bottom:12px; }
.streak-badge { display:inline-flex; align-items:center; gap:6px;
  background:linear-gradient(135deg,rgba(251,146,60,0.15),rgba(239,68,68,0.1));
  border:1px solid rgba(251,146,60,0.3); border-radius:10px; padding:6px 12px; margin:6px 0; }
.streak-num { font-size:1.2rem; font-weight:800; color:#fb923c; }
.streak-label { font-size:0.68rem; color:#94a3b8; font-weight:600; }
.ch-visited { display:inline-block; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3);
  border-radius:6px; padding:2px 7px; font-size:0.62rem; color:#10b981; font-weight:700; margin-left:6px; }
.ch-new { display:inline-block; background:rgba(124,58,237,0.1); border:1px solid rgba(124,58,237,0.25);
  border-radius:6px; padding:2px 7px; font-size:0.62rem; color:#a78bfa; font-weight:600; }
.prog-bar-wrap { height:5px; background:rgba(255,255,255,0.07); border-radius:99px; overflow:hidden; margin-top:4px; }
.prog-bar { height:100%; border-radius:99px; transition:width 0.3s; }
.wrong-card { background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.2);
  border-radius:12px; padding:13px 16px; margin-bottom:10px; }
.wrong-card .wc-topic { font-size:0.66rem; color:#f87171; font-weight:700; margin-bottom:4px; }
.wrong-card .wc-q { font-size:0.86rem; color:#e2e8f0; font-weight:600; margin-bottom:6px; }
.wrong-card .wc-ans { font-size:0.78rem; margin-top:4px; }
.wrong-card .wc-exp { font-size:0.76rem; color:#94a3b8; margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.06); }
/* EXAM MODE */
.exam-q-card { background:rgba(124,58,237,0.06); border:1px solid rgba(124,58,237,0.28);
  border-radius:14px; padding:18px 20px; margin-bottom:14px; }
.exam-q-num { font-size:0.66rem; color:#a78bfa; font-weight:700; margin-bottom:6px; }
.exam-q-text { font-size:0.96rem; font-weight:600; color:#e2e8f0; line-height:1.6; }
.exam-marks-badge { display:inline-block; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3);
  border-radius:6px; padding:2px 9px; font-size:0.68rem; color:#10b981; font-weight:700; margin-top:8px; }
.eval-card { border-radius:12px; padding:14px 16px; margin-bottom:10px; }
.eval-card.good { background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.2); }
.eval-card.avg { background:rgba(245,158,11,0.06); border:1px solid rgba(245,158,11,0.2); }
.eval-card.poor { background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.2); }
/* WEAK TOPICS */
.weak-topic-pill { display:inline-flex; align-items:center; gap:5px; background:rgba(239,68,68,0.08);
  border:1px solid rgba(239,68,68,0.22); border-radius:8px; padding:4px 10px;
  font-size:0.72rem; color:#f87171; font-weight:700; margin:3px; }
/* QUIZ PROGRESS */
.quiz-prog-bar { height:6px; background:rgba(255,255,255,0.07); border-radius:99px; overflow:hidden; margin:10px 0; }
.quiz-prog-fill { height:100%; background:linear-gradient(90deg,#7c3aed,#06b6d4); border-radius:99px; transition:width 0.4s; }
/* SCORECARD */
.score-hero { text-align:center; padding:24px; background:rgba(124,58,237,0.07);
  border:1px solid rgba(124,58,237,0.22); border-radius:16px; margin-bottom:16px; }
.score-big { font-size:3rem; font-weight:900; }
.voice-btn { background:rgba(16,185,129,0.1)!important; border:1px solid rgba(16,185,129,0.3)!important;
  border-radius:10px!important; color:#10b981!important; }
@media (max-width:768px) { .block-container { padding:0.5rem 0.75rem 110px 0.75rem!important; } }
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-thumb { background:rgba(124,58,237,0.4); border-radius:99px; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# SECRETS & CLIENTS
# ════════════════════════════════════════════════════════════════

def _secret(k):
    try:    return st.secrets[k]
    except: return os.getenv(k, "")

GROQ_API_KEY    = _secret("GROQ_API_KEY")
SUPABASE_URL    = _secret("SUPABASE_URL")
SUPABASE_KEY    = _secret("SUPABASE_KEY")
GMAIL_USER      = _secret("GMAIL_USER")
GMAIL_PASSWORD  = _secret("GMAIL_APP_PASSWORD")

missing = [k for k, v in {
    "GROQ_API_KEY":     GROQ_API_KEY,
    "SUPABASE_URL":     SUPABASE_URL,
    "SUPABASE_KEY":     SUPABASE_KEY,
    "GMAIL_USER":       GMAIL_USER,
    "GMAIL_APP_PASSWORD": GMAIL_PASSWORD,
}.items() if not v]

if missing:
    st.error(f"Missing secrets: {', '.join(missing)}")
    st.code("\n".join(f'{k} = "..."' for k in missing), language="toml")
    st.stop()

@st.cache_resource
def get_groq():  return Groq(api_key=GROQ_API_KEY)
@st.cache_resource
def get_sb():    return create_client(SUPABASE_URL, SUPABASE_KEY)

groq_client = get_groq()
sb: Client  = get_sb()

# ════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════

def _init():
    defaults = {
        # Auth
        "auth_stage": "input", "auth_identifier": "", "auth_user_id": None,
        "auth_otp_time": None, "user_name": "Student",
        # Chat
        "messages": [], "selected_chapter": None, "chapter_mode": False,
        "selected_class": "Class 8", "selected_subject": "Both",
        # Quiz batch
        "quiz_batch": [], "quiz_batch_idx": 0, "quiz_batch_answers": [],
        "quiz_batch_done": False, "quiz_count": 5, "quiz_topic_input": "",
        # Old single quiz (keep for compatibility)
        "quiz_state": None, "quiz_answered": False, "quiz_last_pick": "", "quiz_topic_last": "",
        # Exam
        "exam_stage": "setup", "exam_questions": [], "exam_current_idx": 0,
        "exam_answers": [], "exam_topic": "", "exam_subject": "Mathematics",
        # Misc
        "usage": None, "streak": None, "chapter_progress": None, "streak_initialized": False,
        "img_solution": None, "img_solution_history": [],
        "show_src": False, "answer_depth": "Simple",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ════════════════════════════════════════════════════════════════
# AUTH — Gmail SMTP
# ════════════════════════════════════════════════════════════════

def _otp():
    return "".join(random.choices("0123456789", k=6))

def send_otp_email(to_email: str, otp: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your BrainForge OTP 🔐"
        msg["From"]    = GMAIL_USER
        msg["To"]      = to_email

        html = f"""
        <div style="font-family:Arial,sans-serif;background:#06070f;color:#e2e8f0;
                    padding:32px;border-radius:12px;max-width:480px;margin:auto">
          <h2 style="color:#7c3aed">🧠 BrainForge</h2>
          <p style="color:#94a3b8">Hi there! Your one-time login code is:</p>
          <div style="font-size:48px;font-weight:900;color:#7c3aed;letter-spacing:14px;
                      margin:24px 0;text-align:center;background:#0d1117;
                      padding:20px;border-radius:12px">{otp}</div>
          <p style="color:#64748b;font-size:13px">
            Valid for {OTP_EXPIRY_MINUTES} minutes. Do not share this code.
          </p>
          <p style="color:#475569;font-size:12px;margin-top:20px">— Team BrainForge</p>
        </div>"""

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"❌ Email failed: {e}")
        return False

def store_otp(identifier: str, otp: str):
    try:
        sb.table("otps").insert({"identifier": identifier.lower().strip(), "otp": otp}).execute()
    except Exception as e:
        st.error(f"OTP store error: {e}")

def verify_otp(identifier: str, otp: str) -> bool:
    try:
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
        r = (sb.table("otps").select("id,otp,used")
               .eq("identifier", identifier.lower().strip())
               .eq("used", False).gte("created_at", cutoff)
               .order("created_at", desc=True).limit(1).execute())
        if not r.data: return False
        row = r.data[0]
        if row["otp"] == otp.strip():
            sb.table("otps").update({"used": True}).eq("id", row["id"]).execute()
            return True
        return False
    except Exception as e:
        st.error(f"OTP verify error: {e}"); return False

def get_or_create_user(identifier: str):
    v = identifier.lower().strip()
    try:
        r = sb.table("users").select("id").eq("identifier", v).execute()
        if r.data: return r.data[0]["id"]
        return sb.table("users").insert({"identifier": v}).execute().data[0]["id"]
    except Exception as e:
        st.error(f"DB error: {e}"); return None

def get_profile(email: str):
    try:
        r = sb.table("profiles").select("*").eq("email", email.lower().strip()).execute()
        return r.data[0] if r.data else None
    except:
        return None

# ════════════════════════════════════════════════════════════════
# AUTH — Render
# ════════════════════════════════════════════════════════════════

def render_auth():
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("""
        <div style="background:#0d1117;border:1px solid rgba(124,58,237,0.28);border-radius:20px;
             padding:36px 30px;text-align:center;margin-top:40px">
          <div style="font-size:3rem">🧠</div>
          <div style="font-size:1.4rem;font-weight:800;color:#e2e8f0;margin:10px 0 4px">BrainForge</div>
          <div style="font-size:0.8rem;color:#64748b;margin-bottom:6px">
            NCERT AI Tutor · Class 8, 9 &amp; 10
          </div>
          <div style="font-size:0.75rem;color:#475569">
            15 free questions · Daily streak · Quiz + Exam mode
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Landing: Choose action ────────────────────────────
        if st.session_state.auth_stage == "input":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👤 Create Profile", use_container_width=True, type="primary"):
                    st.session_state.auth_stage = "create_profile"; st.rerun()
            with c2:
                if st.button("🔑 Login", use_container_width=True):
                    st.session_state.auth_stage = "login"; st.rerun()

        # ── Create Profile ────────────────────────────────────
        elif st.session_state.auth_stage == "create_profile":
            st.markdown("### 👤 Create Your Profile")

            name      = st.text_input("Full Name *", placeholder="e.g. Riya Sharma")
            email     = st.text_input("Email Address *", placeholder="you@example.com")
            age       = st.number_input("Age *", min_value=10, max_value=20, value=14)
            sel_class = st.selectbox("Your Class *", CLASSES)
            subj_pref = st.selectbox("Favourite Subject", SUBJECTS)
            school    = st.text_input("School Name", placeholder="e.g. DPS Delhi (optional)")
            city      = st.text_input("City", placeholder="e.g. Delhi (optional)")

            st.markdown("<div style='font-size:0.7rem;color:#64748b'>* Required fields</div>",
                        unsafe_allow_html=True)
            st.markdown("")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Create Profile", type="primary", use_container_width=True):
                    if not name.strip():
                        st.error("Please enter your name.", icon="❌")
                    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip().lower()):
                        st.error("Enter a valid email address.", icon="❌")
                    else:
                        existing = sb.table("profiles").select("id").eq("email", email.strip().lower()).execute()
                        if existing.data:
                            st.warning("⚠️ Email already registered. Please login instead.")
                        else:
                            try:
                                sb.table("profiles").insert({
                                    "email":              email.strip().lower(),
                                    "name":               name.strip(),
                                    "age":                int(age),
                                    "class":              sel_class,
                                    "subject_preference": subj_pref,
                                    "school":             school.strip() or None,
                                    "city":               city.strip() or None,
                                }).execute()
                                first = name.strip().split()[0]
                                st.success(f"🎉 Welcome, {first}! Profile created. Please login now.")
                                st.session_state.auth_stage = "login"; st.rerun()
                            except Exception as e:
                                st.error(f"Could not save profile: {e}", icon="❌")
            with col2:
                if st.button("← Back", use_container_width=True):
                    st.session_state.auth_stage = "input"; st.rerun()

        # ── Login ─────────────────────────────────────────────
        elif st.session_state.auth_stage == "login":
            st.markdown("### 🔑 Login")
            identifier = st.text_input("📧 Registered Email",
                                        placeholder="you@example.com", key="auth_id_input")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Send OTP →", type="primary", use_container_width=True):
                    email_clean = identifier.strip().lower()
                    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
                        st.error("Enter a valid email address.", icon="❌")
                    else:
                        profile = get_profile(email_clean)
                        if not profile:
                            st.error("❌ No profile found. Please create a profile first.")
                        else:
                            otp = _otp()
                            store_otp(email_clean, otp)
                            if send_otp_email(email_clean, otp):
                                st.success("📩 OTP sent! Check your inbox.")
                                st.session_state.auth_identifier = email_clean
                                st.session_state.auth_otp_time   = datetime.datetime.utcnow()
                                st.session_state.auth_stage      = "otp"
                                st.rerun()
            with col2:
                if st.button("← Back", use_container_width=True):
                    st.session_state.auth_stage = "input"; st.rerun()

            st.markdown("<div style='text-align:center;margin-top:12px;font-size:0.74rem;color:#475569'>"
                        "New here? Click <b>Create Profile</b> first.</div>", unsafe_allow_html=True)

        # ── OTP Verify ────────────────────────────────────────
        elif st.session_state.auth_stage == "otp":
            ident = st.session_state.auth_identifier
            st.info(f"OTP sent to **{ident}**")
            otp_in = st.text_input("Enter 6-digit OTP", max_chars=6, placeholder="······", key="otp_in")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Verify", type="primary", use_container_width=True):
                    if verify_otp(ident, otp_in):
                        profile = get_profile(ident)
                        uid = get_or_create_user(ident)
                        if uid and profile:
                            st.session_state.auth_user_id     = uid
                            st.session_state.auth_stage       = "done"
                            st.session_state.user_name        = profile.get("name", "Student")
                            st.session_state.selected_class   = profile.get("class", "Class 8")
                            st.session_state.selected_subject = profile.get("subject_preference", "Both")
                            st.session_state.usage            = None
                            st.rerun()
                        else:
                            st.error("Account error. Please try again.", icon="❌")
                    else:
                        st.error("Wrong or expired OTP.", icon="❌")
            with c2:
                if st.button("🔄 Resend OTP", use_container_width=True):
                    new_otp = _otp(); store_otp(ident, new_otp)
                    if send_otp_email(ident, new_otp): st.success("📩 New OTP sent!")

            if st.button("← Change email", use_container_width=True):
                st.session_state.auth_stage = "login"; st.rerun()

# ── Auth Gate ─────────────────────────────────────────────────
if st.session_state.auth_stage != "done":
    render_auth(); st.stop()

# ════════════════════════════════════════════════════════════════
# RATE LIMITING
# ════════════════════════════════════════════════════════════════

def get_usage():
    try:
        uid   = st.session_state.auth_user_id
        today = datetime.date.today().isoformat()
        r = sb.table("rate_limits").select("count").eq("user_id", uid).eq("day", today).execute()
        return r.data[0]["count"] if r.data else 0
    except: return 0

def increment_usage():
    try:
        uid   = st.session_state.auth_user_id
        today = datetime.date.today().isoformat()
        r = sb.table("rate_limits").select("count").eq("user_id", uid).eq("day", today).execute()
        if r.data:
            new = r.data[0]["count"] + 1
            sb.table("rate_limits").update({"count": new}).eq("user_id", uid).eq("day", today).execute()
        else:
            new = 1
            sb.table("rate_limits").insert({"user_id": uid, "day": today, "count": 1}).execute()
        return new
    except: return 0

def rate_limit_check():
    if st.session_state.usage is None:
        st.session_state.usage = get_usage()
    if st.session_state.usage >= DAILY_LIMIT:
        st.error(f"🚫 Daily limit of **{DAILY_LIMIT} questions** reached. Come back tomorrow! 🌅")
        return False
    return True

# ════════════════════════════════════════════════════════════════
# STREAK
# ════════════════════════════════════════════════════════════════

def update_streak():
    try:
        uid       = st.session_state.auth_user_id
        today     = datetime.date.today().isoformat()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        r = sb.table("streaks").select("*").eq("user_id", uid).execute()
        if r.data:
            row = r.data[0]; last = row.get("last_login_date", "")
            streak = row.get("current_streak", 0); longest = row.get("longest_streak", 0)
            if last == today:    return streak
            elif last == yesterday: streak += 1
            else:                streak = 1
            longest = max(longest, streak)
            sb.table("streaks").update({
                "current_streak": streak, "longest_streak": longest, "last_login_date": today
            }).eq("user_id", uid).execute()
            return streak
        else:
            sb.table("streaks").insert({
                "user_id": uid, "current_streak": 1, "longest_streak": 1, "last_login_date": today
            }).execute()
            return 1
    except Exception as e:
        print(f"[Streak error] {e}"); return 0

if not st.session_state.streak_initialized and st.session_state.auth_user_id:
    st.session_state.streak = update_streak()
    st.session_state.streak_initialized = True

# ════════════════════════════════════════════════════════════════
# CHAPTER PROGRESS
# ════════════════════════════════════════════════════════════════

def mark_chapter_visited(ch_key, cls, subj):
    try:
        uid   = st.session_state.auth_user_id
        today = datetime.date.today().isoformat()
        r = sb.table("chapter_progress").select("id,visit_count").eq("user_id", uid).eq("chapter_key", ch_key).execute()
        if r.data:
            sb.table("chapter_progress").update({
                "last_visited": today, "visit_count": r.data[0]["visit_count"] + 1
            }).eq("id", r.data[0]["id"]).execute()
        else:
            sb.table("chapter_progress").insert({
                "user_id": uid, "class": cls, "subject": subj, "chapter_key": ch_key,
                "first_visited": today, "last_visited": today, "visit_count": 1
            }).execute()
        st.session_state.chapter_progress = None
    except Exception as e: print(f"[Progress error] {e}")

def get_chapter_progress():
    if st.session_state.chapter_progress is not None:
        return st.session_state.chapter_progress
    try:
        r = sb.table("chapter_progress").select("chapter_key,visit_count").eq(
            "user_id", st.session_state.auth_user_id).execute()
        prog = {row["chapter_key"]: row["visit_count"] for row in (r.data or [])}
        st.session_state.chapter_progress = prog; return prog
    except: return {}

def get_class_progress_pct(cls):
    prog  = get_chapter_progress()
    total = sum(len(v) for v in CHAPTER_INDEX.get(cls, {}).values())
    if total == 0: return 0.0
    done  = sum(1 for k in prog if any(k in CHAPTER_INDEX[cls][s] for s in CHAPTER_INDEX.get(cls, {})))
    return min(done / total, 1.0)

# ════════════════════════════════════════════════════════════════
# QUIZ TRACKING
# ════════════════════════════════════════════════════════════════

def save_quiz_attempt(topic, q_data, user_answer, is_correct):
    try:
        sb.table("quiz_attempts").insert({
            "user_id":       st.session_state.auth_user_id,
            "topic":         topic,
            "question":      q_data["question"],
            "options":       json.dumps(q_data["options"]),
            "correct_answer":q_data["correct"],
            "user_answer":   user_answer,
            "explanation":   q_data.get("explanation", ""),
            "is_correct":    is_correct,
            "class":         st.session_state.selected_class,
            "subject":       st.session_state.selected_subject,
        }).execute()
    except Exception as e: print(f"[Quiz attempt error] {e}")

def get_wrong_answers(limit=50):
    try:
        r = (sb.table("quiz_attempts")
               .select("topic,question,options,correct_answer,user_answer,explanation,class,subject,created_at")
               .eq("user_id", st.session_state.auth_user_id)
               .eq("is_correct", False)
               .order("created_at", desc=True).limit(limit).execute())
        return r.data or []
    except: return []

def get_quiz_stats():
    try:
        r = sb.table("quiz_attempts").select("is_correct").eq(
            "user_id", st.session_state.auth_user_id).execute()
        data = r.data or []
        return len(data), sum(1 for d in data if d["is_correct"])
    except: return 0, 0

def save_exam_attempt(topic, questions, answers, total_scored, max_score):
    try:
        sb.table("exam_attempts").insert({
            "user_id":    st.session_state.auth_user_id,
            "topic":      topic,
            "class":      st.session_state.selected_class,
            "subject":    st.session_state.selected_subject,
            "questions":  json.dumps(questions),
            "answers":    json.dumps(answers),
            "total_score":total_scored,
            "max_score":  max_score,
        }).execute()
    except Exception as e: print(f"[Exam save error] {e}")

# ════════════════════════════════════════════════════════════════
# LaTeX RENDERER
# ════════════════════════════════════════════════════════════════

def render_answer_with_math(text):
    parts = re.split(r'(\$\$[\s\S]+?\$\$)', text)
    for part in parts:
        if part.startswith('$$') and part.endswith('$$') and len(part) > 4:
            try:    st.latex(part[2:-2].strip())
            except: st.markdown(f"```\n{part[2:-2].strip()}\n```")
        elif part.strip():
            st.markdown(part)

# ════════════════════════════════════════════════════════════════
# IMAGE PROCESSING
# ════════════════════════════════════════════════════════════════

def prepare_image_for_api(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    if img.width > 1600:
        ratio = 1600 / img.width
        img = img.resize((1600, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8"), "image/jpeg"

def detect_question_type(image_b64, mime):
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                {"type": "text", "text": (
                    "Classify this image in 3-4 words. Reply ONLY with one of: "
                    "'Maths Problem','Science Diagram','Handwritten Question',"
                    "'Textbook Exercise','Chemistry Equation','Physics Numericals',"
                    "'Biology Diagram','Graph or Chart','Mixed Content'. No extra text."
                )},
            ]}],
            max_tokens=20, temperature=0.1,
        )
        return r.choices[0].message.content.strip()
    except: return "Question"

def solve_image_doubt(image_b64, mime, cls, subj, extra_hint=""):
    age = {"Class 8": "13-14", "Class 9": "14-15", "Class 10": "15-16"}.get(cls, "13-16")
    hint_line = f"\nStudent note: {extra_hint}" if extra_hint.strip() else ""
    prompt = (
        f"You are BrainForge — expert CBSE tutor for {cls} students (age {age}).\n"
        f"The student has uploaded a photo of a {subj} question/diagram.{hint_line}\n\n"
        "YOUR JOB:\n1. Read the question/diagram carefully.\n2. Identify the exact topic.\n"
        "3. Solve step-by-step using NCERT methods.\n4. Use LaTeX for ALL math: $$...$$ for display, $...$ for inline.\n"
        "5. Keep language simple and student-friendly.\n\n"
        "FORMAT:\n## 🔍 [Topic Name]\n**What the question asks:** [1-line summary]\n\n"
        "### Step-by-Step Solution\n[numbered steps]\n\n### ✅ Final Answer\n[clearly stated]\n\n"
        f"💡 **Quick Tip:** [memory trick]\n📚 *NCERT {cls} — {subj}*"
    )
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ]}],
            max_tokens=1600, temperature=0.3,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        if "rate_limit" in err.lower() or "429" in err:
            return "⚠️ Vision model rate limit hit. Please wait 30 seconds and try again."
        return f"⚠️ Error: {err}"

# ════════════════════════════════════════════════════════════════
# VECTOR SEARCH — with caching
# ════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def get_embedder():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def embed_cached(text: str):
    m = get_embedder()
    return m.encode(text, normalize_embeddings=True).tolist() if m else None

@st.cache_data(ttl=3600, show_spinner=False)
def retrieve_chunks(query: str, class_label: str, subject: str,
                    chapter_filter: str = "", top_k: int = TOP_K):
    q_emb = embed_cached(query)
    if not q_emb: return []
    try:
        _sb = get_sb()
        r = _sb.rpc("match_chunks", {
            "query_embedding": q_emb,
            "filter_class":    class_label,
            "filter_subject":  subject,
            "filter_chapter":  chapter_filter or "",
            "match_count":     top_k,
        }).execute()
        out = []
        for row in (r.data or []):
            sim = float(row.get("similarity", 0))
            if sim > 0.15:
                out.append({
                    "text":      row["content"],
                    "subject":   row["subject"],
                    "chapter":   row["chapter"],
                    "page":      row.get("page", "?"),
                    "source":    row.get("source", ""),
                    "class":     row["class"],
                    "relevance": round(sim * 100, 1),
                })
        return sorted(out, key=lambda x: x["relevance"], reverse=True)
    except Exception as e:
        st.warning(f"Search error: {e}", icon="⚠️"); return []

# ════════════════════════════════════════════════════════════════
# NOTES
# ════════════════════════════════════════════════════════════════

def save_note(content, cls, subj, chapter=""):
    try:
        sb.table("notes").insert({
            "user_id": st.session_state.auth_user_id,
            "class": cls, "subject": subj, "chapter": chapter, "content": content,
        }).execute(); return True
    except: return False

def get_notes(cls=None):
    try:
        q = sb.table("notes").select("*").eq("user_id", st.session_state.auth_user_id).order("created_at", desc=True)
        if cls: q = q.eq("class", cls)
        return (q.limit(50).execute()).data or []
    except: return []

def delete_note(nid):
    try:
        sb.table("notes").delete().eq("id", nid).eq("user_id", st.session_state.auth_user_id).execute()
        return True
    except: return False

# ════════════════════════════════════════════════════════════════
# AI — TEXT GENERATION
# ════════════════════════════════════════════════════════════════

def build_ctx(chunks):
    if not chunks: return ""
    out = "\n--- NCERT CONTENT ---\n"
    for c in chunks[:6]:
        out += f"\n[{c['class']}|{c['subject']}|{c['chapter']}|p.{c['page']}]\n{c['text']}\n"
    return out + "\n--- END ---\n"

def generate_answer(question, chunks, cls, subj, style, history, ch_ctx=None):
    age = {"Class 8": "13-14", "Class 9": "14-15", "Class 10": "15-16"}.get(cls, "13-16")
    style_instr = {
        "Simple":   "Simple language, short paragraphs.",
        "Detailed": "Comprehensive, cover all sub-topics.",
        "Bullets":  "Use numbered headings and bullet points.",
        "Examples": "Include 2-3 real Indian examples.",
    }.get(style, "Simple language.")
    ch_line = f"\nStudent studying: {ch_ctx}" if ch_ctx else ""
    system = (
        f"You are BrainForge — expert CBSE AI tutor for India.\n"
        f"MATH: Always use LaTeX. Display: $$...$$ Inline: $...$\n"
        f"STYLE: {style_instr} Bold key terms. Add 💡 Quick Tip.\n"
        f"STUDENT: {cls} CBSE, age {age}{ch_line}\n"
        f"FORMAT: ## [Topic] / Explanation / **Key Points:** / 💡 Quick Tip / 📚 NCERT {cls} {subj}\n"
        f"End with: 💬 Want examples, a quiz, or deeper explanation?"
    )
    msgs = [{"role": "system", "content": system}]
    for m in history[-(MAX_HISTORY * 2):]:
        if m["role"] in ("user", "assistant"):
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": f"Q: {question}\n{build_ctx(chunks)}\nAnswer for {cls} student."})
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=msgs, temperature=0.4, max_tokens=1400)
        return r.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        return ("⚠️ AI rate limit hit. Wait 30 s." if "rate_limit" in err.lower() or "429" in err
                else f"⚠️ Error: {err}")

def is_followup(q, history):
    if not history: return False
    ql = q.lower().strip()
    if len(ql.split()) <= 5:
        for p in [r"^(what about|tell me more|explain more|can you|how about|give me|more about)",
                  r"^(example|examples|illustrate|show me)",
                  r"^(i (don't|do not) understand|unclear|confused|simpler)",
                  r"^(test me|quiz me|ask me|mcq)"]:
            if re.match(p, ql): return True
    return False

def process_question(question, ch_ctx=None, ch_filter="", ch_subj=None):
    if not rate_limit_check(): return None, []
    cls_  = st.session_state.selected_class
    subj_ = ch_subj or st.session_state.selected_subject
    style = st.session_state.get("answer_depth", "Simple")
    hist  = st.session_state.messages
    chunks = []
    if not is_followup(question, hist):
        with st.spinner("🔍 Searching NCERT…"):
            chunks = retrieve_chunks(question, cls_, subj_, ch_filter, TOP_K)
    with st.spinner("✍️ Writing answer…"):
        answer = generate_answer(question, chunks, cls_, subj_, style, hist, ch_ctx)
    st.session_state.usage = increment_usage()
    return answer, chunks

def generate_chapter_summary(ch_key, ch_title, cls, subj):
    chunks = retrieve_chunks(ch_title, cls, subj, ch_key, top_k=8)
    ctx    = "\n".join(c["text"] for c in chunks[:6])
    prompt = (
        f"Expert {cls} CBSE teacher. Student opened: {ch_title} ({cls}·{subj})\n"
        f"NCERT: {ctx}\n"
        "Write chapter overview with: What You Will Learn / Key Concepts / Why It Matters / Quick Preview\n"
        'End: "💬 Ask me anything about this chapter!"'
    )
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.4, max_tokens=800)
        return r.choices[0].message.content.strip()
    except Exception as e: return f"Could not load overview: {e}"

# ════════════════════════════════════════════════════════════════
# AI — QUIZ BATCH
# ════════════════════════════════════════════════════════════════

def generate_quiz_batch(topic: str, cls: str, subj: str, chunks: list, count: int = 5):
    prompt = (
        f'You are a CBSE exam setter. Generate exactly {count} MCQ questions '
        f'on "{topic}" for {cls} {subj}.\n'
        f'{build_ctx(chunks[:4])}\n'
        f'Reply ONLY with a valid JSON array — no markdown, no extra text.\n'
        f'Each item: {{"question":"...","options":["A. ...","B. ...","C. ...","D. ..."],'
        f'"correct":"A","explanation":"..."}}\n'
        f'Generate exactly {count} unique questions covering different aspects of the topic.'
    )
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=min(350 * count, 4000),
        )
        text = re.sub(r"```json|```", "", r.choices[0].message.content.strip()).strip()
        data = json.loads(text)
        return data if isinstance(data, list) else None
    except Exception as e:
        print(f"[Quiz batch error] {e}"); return None

# ════════════════════════════════════════════════════════════════
# AI — EXAM MODE
# ════════════════════════════════════════════════════════════════

def generate_exam_questions(topic: str, cls: str, subj: str, count: int = 5):
    prompt = (
        f'You are a CBSE board exam paper setter for {cls} {subj}.\n'
        f'Generate exactly {count} descriptive/written-answer exam questions on "{topic}".\n'
        f'Rules:\n'
        f'- These must be WRITTEN ANSWER questions (NOT multiple choice)\n'
        f'- Like real CBSE board exam questions\n'
        f'- Mix mark values: 1-mark, 2-mark, 3-mark, 5-mark questions\n'
        f'- Cover different aspects of the topic\n\n'
        f'Reply ONLY with a valid JSON array. No markdown.\n'
        f'Format: [{{"question":"...","marks":3,"hint":"key points expected in answer"}},...]\n'
        f'Generate exactly {count} questions.'
    )
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=min(200 * count, 3000),
        )
        text = re.sub(r"```json|```", "", r.choices[0].message.content.strip()).strip()
        data = json.loads(text)
        return data if isinstance(data, list) else None
    except Exception as e:
        print(f"[Exam gen error] {e}"); return None

def evaluate_text_answer(question: str, marks: int, student_answer: str, cls: str, subj: str):
    if not student_answer.strip():
        return {"marks_awarded": 0, "max_marks": marks,
                "feedback": "No answer provided.", "good": "", "missing": "Complete answer missing."}
    prompt = (
        f'You are a strict but fair CBSE examiner for {cls} {subj}.\n'
        f'Question: {question}\n'
        f'Maximum Marks: {marks}\n'
        f"Student's Answer: {student_answer}\n\n"
        f'Evaluate the answer and reply ONLY with valid JSON (no markdown):\n'
        f'{{"marks_awarded":<int between 0 and {marks}>,"max_marks":{marks},'
        f'"feedback":"2-3 sentence overall feedback","good":"what was correct",'
        f'"missing":"what was missing or wrong"}}'
    )
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=350,
        )
        text = re.sub(r"```json|```", "", r.choices[0].message.content.strip()).strip()
        return json.loads(text)
    except:
        return {"marks_awarded": 0, "max_marks": marks,
                "feedback": "Could not evaluate.", "good": "", "missing": ""}

def evaluate_image_answer(question: str, marks: int, image_b64: str, mime: str, cls: str, subj: str):
    prompt = (
        f'You are a strict but fair CBSE examiner for {cls} {subj}.\n'
        f'Question: {question}\n'
        f'Maximum Marks: {marks}\n'
        f'The student has uploaded a handwritten answer image. Read it carefully and evaluate.\n'
        f'Reply ONLY with valid JSON (no markdown):\n'
        f'{{"marks_awarded":<int between 0 and {marks}>,"max_marks":{marks},'
        f'"feedback":"2-3 sentence overall feedback","good":"what was correct",'
        f'"missing":"what was missing or wrong"}}'
    )
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ]}],
            temperature=0.2,
            max_tokens=350,
        )
        text = re.sub(r"```json|```", "", r.choices[0].message.content.strip()).strip()
        return json.loads(text)
    except:
        return {"marks_awarded": 0, "max_marks": marks,
                "feedback": "Could not evaluate image answer.", "good": "", "missing": ""}

# ════════════════════════════════════════════════════════════════
# AI — WEAK TOPICS
# ════════════════════════════════════════════════════════════════

def get_weak_topics():
    wrong = get_wrong_answers(limit=50)
    if not wrong: return []
    topic_counts: dict = {}
    for w in wrong:
        t = w.get("topic", "Unknown").strip()
        topic_counts[t] = topic_counts.get(t, 0) + 1
    return sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]

def generate_weak_topic_insight(weak_topics: list, cls: str, subj: str) -> str:
    topics_str = ", ".join(f"{t} ({c} wrong)" for t, c in weak_topics)
    prompt = (
        f'A {cls} {subj} student has answered these topics incorrectly most:\n{topics_str}\n\n'
        f'Write a short, encouraging message (2 sentences) telling them which topic needs most attention.\n'
        f'Then give exactly 3 specific revision tips for "{weak_topics[0][0]}".\n'
        f'Keep it friendly, motivating, and student-appropriate.'
    )
    try:
        r = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4, max_tokens=300,
        )
        return r.choices[0].message.content.strip()
    except:
        return "Keep practicing! Focus on your weak topics daily for 15 minutes."

# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════

with st.sidebar:
    cls  = st.session_state.selected_class
    subj = st.session_state.selected_subject
    user_name   = st.session_state.get("user_name", "Student")
    streak_val  = st.session_state.streak or 0
    flame       = "🔥" if streak_val >= 2 else "✨"

    st.markdown(f"""
    <div style="padding:8px 0 14px;border-bottom:1px solid rgba(255,255,255,0.07)">
      <div style="font-size:1.15rem;font-weight:800;color:#e2e8f0">🧠 BrainForge</div>
      <div style="font-size:0.68rem;color:#64748b;margin-top:2px">NCERT Class 8 · 9 · 10</div>
      <div style="margin-top:7px;font-size:0.75rem;color:#a78bfa;font-weight:600">
        👤 {user_name}</div>
      <div style="font-size:0.65rem;color:#475569">{st.session_state.auth_identifier}</div>
      <div class="streak-badge" style="margin-top:10px">
        <span style="font-size:1.1rem">{flame}</span>
        <span class="streak-num">{streak_val}</span>
        <span class="streak-label">day streak</span>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("#### 🎓 Class")
    sel_cls = st.radio("cls", CLASSES,
                        format_func=lambda x: f"{CLASS_ICONS[x]} {x}",
                        label_visibility="collapsed", key="cls_radio")
    if sel_cls != st.session_state.selected_class:
        st.session_state.update(
            selected_class=sel_cls, selected_chapter=None, chapter_mode=False,
            messages=[], quiz_batch=[], quiz_batch_idx=0, quiz_batch_done=False,
            exam_stage="setup", chapter_progress=None)

    prog_pct     = get_class_progress_pct(sel_cls)
    prog_pct_int = int(prog_pct * 100)
    prog_color   = "#10b981" if prog_pct >= 0.7 else "#7c3aed" if prog_pct >= 0.3 else "#06b6d4"
    st.markdown(f"""
    <div style="margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:#64748b;margin-bottom:3px">
        <span>Chapter progress</span>
        <span style="color:{prog_color};font-weight:700">{prog_pct_int}%</span>
      </div>
      <div class="prog-bar-wrap">
        <div class="prog-bar" style="width:{prog_pct_int}%;background:{prog_color}"></div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("#### 📚 Subject")
    sel_subj = st.radio("subj", SUBJECTS,
                         format_func=lambda x: f"{SUBJECT_ICONS[x]} {x}",
                         label_visibility="collapsed", key="subj_radio")
    if sel_subj != st.session_state.selected_subject:
        st.session_state.update(
            selected_subject=sel_subj, selected_chapter=None, chapter_mode=False,
            messages=[], quiz_batch=[], quiz_batch_done=False)

    total_q, correct_q = get_quiz_stats()
    acc = int((correct_q / total_q) * 100) if total_q else 0
    if total_q:
        st.markdown(f"""
        <div style="margin:8px 0;padding:8px 10px;background:rgba(16,185,129,0.06);
             border:1px solid rgba(16,185,129,0.18);border-radius:9px">
          <div style="font-size:0.65rem;color:#64748b;font-weight:600;margin-bottom:3px">🎯 Quiz Accuracy</div>
          <div style="font-size:1.1rem;font-weight:800;color:#10b981">{acc}%
            <span style="font-size:0.68rem;color:#64748b">({correct_q}/{total_q})</span></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    if st.session_state.usage is None:
        st.session_state.usage = get_usage()
    used = st.session_state.usage; pct = min(used / DAILY_LIMIT, 1.0)
    bar_c = ("linear-gradient(90deg,#7c3aed,#06b6d4)" if pct < 0.8
             else "linear-gradient(90deg,#f59e0b,#ef4444)")
    st.markdown(f"""
    <div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-size:0.7rem;color:#94a3b8;font-weight:600">Daily Usage</span>
        <span style="font-size:0.7rem;color:#a78bfa;font-weight:700">{used}/{DAILY_LIMIT}</span>
      </div>
      <div class="prog-bar-wrap">
        <div class="prog-bar" style="width:{int(pct*100)}%;background:{bar_c}"></div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    show_src    = st.toggle("📄 Show NCERT sources", value=False, key="show_src")
    answer_depth = st.selectbox("Answer style", ["Simple", "Detailed", "Bullets", "Examples"],
                                 key="answer_depth")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.update(
            messages=[], selected_chapter=None, chapter_mode=False,
            quiz_batch=[], quiz_batch_idx=0, quiz_batch_done=False); st.rerun()

    if st.button("🚪 Sign Out", use_container_width=True):
        for k in ["auth_stage", "auth_identifier", "auth_user_id", "auth_otp_time",
                  "messages", "usage", "quiz_batch", "quiz_batch_idx", "quiz_batch_done",
                  "selected_chapter", "streak", "streak_initialized", "chapter_progress",
                  "img_solution", "img_solution_history", "exam_stage", "exam_questions",
                  "exam_answers", "user_name"]:
            st.session_state[k] = None
        st.session_state.auth_stage = "input"; st.rerun()

# ════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════

cls  = st.session_state.selected_class
subj = st.session_state.selected_subject
c_col = CLASS_COLORS.get(cls, "#7c3aed")

st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(124,58,237,0.09),rgba(6,182,212,0.04));
     border:1px solid {c_col}30;border-radius:14px;padding:12px 18px;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
    <span style="font-size:1.5rem">{CLASS_ICONS.get(cls,'🎓')}</span>
    <div>
      <div style="font-size:1rem;font-weight:800;color:#e2e8f0">NCERT AI Tutor</div>
      <div style="font-size:0.72rem;color:#64748b">
        {cls} · {subj} · NCERT-grounded answers
      </div>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px;flex-wrap:wrap">
      <span style="background:rgba(124,58,237,0.15);border:1px solid rgba(124,58,237,0.3);
            border-radius:6px;padding:3px 9px;font-size:0.68rem;font-weight:700;color:#a78bfa">
        {CLASS_ICONS.get(cls,'')} {cls}</span>
      <span style="background:rgba(6,182,212,0.1);border:1px solid rgba(6,182,212,0.25);
            border-radius:6px;padding:3px 9px;font-size:0.68rem;font-weight:700;color:#67e8f9">
        {SUBJECT_ICONS.get(subj,'')} {subj}</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════

tab_chat, tab_img, tab_idx, tab_quiz, tab_exam, tab_notes = st.tabs([
    "💬 Chat", "📸 Image Doubt", "📖 Chapters", "🎯 Quiz", "📝 Exam Mode", "🗒️ Notes"
])

def render_sources(chunks):
    if not chunks or not st.session_state.get("show_src"): return
    with st.expander(f"📄 {len(chunks)} NCERT passages"):
        for c in chunks:
            rel = c["relevance"]
            bc  = "#10b981" if rel >= 70 else "#f59e0b" if rel >= 45 else "#64748b"
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border-left:3px solid {bc};
                 border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
              <div style="display:flex;justify-content:space-between">
                <span style="color:#a78bfa;font-weight:700;font-size:0.72rem">
                  {CLASS_ICONS.get(c.get('class',''),'')} {c.get('class','')} ·
                  {SUBJECT_ICONS.get(c['subject'],'')} {c['subject']} — {c['chapter'].upper()}</span>
                <span style="color:{bc};font-size:0.68rem;font-weight:700">{rel}%</span>
              </div>
              <div style="color:#64748b;font-size:0.66rem;margin:3px 0">p.{c['page']}</div>
              <div style="color:#cbd5e1;font-size:0.76rem;line-height:1.5">
                {c['text'][:230]}{'…' if len(c['text'])>230 else ''}</div>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ════════════════════════════════════════════════════════════════

with tab_chat:
    ch_ctx    = None; ch_filter = ""; ch_subj_ = subj
    if st.session_state.chapter_mode and st.session_state.selected_chapter:
        ch_key, ch_s = st.session_state.selected_chapter
        ch_title     = CHAPTER_INDEX.get(cls, {}).get(ch_s, {}).get(ch_key, ch_key)
        ch_ctx, ch_filter, ch_subj_ = ch_title, ch_key, ch_s
        b1, b2 = st.columns([5, 1])
        with b1:
            st.markdown(f"""<div style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.22);
                 border-radius:10px;padding:8px 14px;margin-bottom:8px">
              <div style="font-size:0.66rem;color:#a78bfa;font-weight:700">📖 Chapter Mode</div>
              <div style="font-size:0.83rem;color:#e2e8f0;font-weight:600">{ch_title}</div>
            </div>""", unsafe_allow_html=True)
        with b2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✕ Exit", key="exit_ch"):
                st.session_state.update(chapter_mode=False, selected_chapter=None, messages=[])
                st.rerun()

    # ── Voice input in Chat ───────────────────────────────────
    if VOICE_AVAILABLE:
        st.markdown('<div style="margin-bottom:4px">', unsafe_allow_html=True)
        voice_text = speech_to_text(
            language="en-IN",
            start_prompt="🎤 Speak your question",
            stop_prompt="⏹ Stop recording",
            use_container_width=False,
            key="voice_chat_input",
        )
        st.markdown('</div>', unsafe_allow_html=True)
        if voice_text and voice_text.strip():
            st.info(f"🎤 Heard: *{voice_text}*")
            answer, chunks = process_question(voice_text, ch_ctx, ch_filter, ch_subj_)
            if answer:
                st.session_state.messages += [
                    {"role": "user",      "content": voice_text, "chunks": []},
                    {"role": "assistant", "content": answer,     "chunks": chunks},
                ]
            st.rerun()

    # ── Suggestions ───────────────────────────────────────────
    if not st.session_state.messages:
        st.markdown("##### 💡 Try asking:")
        suggs = SUGGESTIONS.get(cls, {}).get(subj, SUGGESTIONS["Class 8"]["Both"])
        c1, c2 = st.columns(2)
        for i, s in enumerate(suggs):
            with (c1 if i % 2 == 0 else c2):
                if st.button(s, key=f"sg{i}"):
                    answer, chunks = process_question(s, ch_ctx, ch_filter, ch_subj_)
                    if answer:
                        st.session_state.messages += [
                            {"role": "user",      "content": s,      "chunks": []},
                            {"role": "assistant", "content": answer, "chunks": chunks},
                        ]
                    st.rerun()
        st.markdown("")

    # ── Message history ───────────────────────────────────────
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(
                f'<div style="display:flex;justify-content:flex-end;margin-bottom:6px">'
                f'<div class="msg-user">{msg["content"]}</div></div>',
                unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:0.68rem;color:#a78bfa;font-weight:700;margin-bottom:4px">'
                        '🧠 BrainForge</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div style="background:rgba(255,255,255,0.035);border:1px solid rgba(255,255,255,0.08);'
                            'border-radius:4px 16px 16px 16px;padding:14px 18px;margin-bottom:4px">',
                            unsafe_allow_html=True)
                render_answer_with_math(msg["content"])
                st.markdown('</div>', unsafe_allow_html=True)
            render_sources(msg.get("chunks", []))
            sv_col, _ = st.columns([1, 5])
            with sv_col:
                if st.button("🗒️ Save", key=f"sv_{idx}"):
                    ok = save_note(msg["content"], cls, subj, ch_filter or "General")
                    st.toast("✅ Saved!" if ok else "❌ Could not save.")

    # ── Chat input ────────────────────────────────────────────
    ph = (f"Ask about {ch_title}…" if ch_ctx
          else f"Ask anything from {cls} {subj}…" if subj != "Both"
          else f"Ask anything from {cls} Maths or Science…")
    question = st.chat_input(ph)
    if question:
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;margin-bottom:6px">'
            f'<div class="msg-user">{question}</div></div>',
            unsafe_allow_html=True)
        answer, chunks = process_question(question, ch_ctx, ch_filter, ch_subj_)
        if answer:
            st.markdown('<div style="font-size:0.68rem;color:#a78bfa;font-weight:700;margin-bottom:4px">'
                        '🧠 BrainForge</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div style="background:rgba(255,255,255,0.035);border:1px solid rgba(255,255,255,0.08);'
                            'border-radius:4px 16px 16px 16px;padding:14px 18px;margin-bottom:4px">',
                            unsafe_allow_html=True)
                render_answer_with_math(answer)
                st.markdown('</div>', unsafe_allow_html=True)
            render_sources(chunks)
            st.session_state.messages += [
                {"role": "user",      "content": question, "chunks": []},
                {"role": "assistant", "content": answer,   "chunks": chunks},
            ]

# ════════════════════════════════════════════════════════════════
# TAB 2 — IMAGE DOUBT SOLVER
# ════════════════════════════════════════════════════════════════

with tab_img:
    st.markdown("#### 📸 Image Doubt Solver")
    st.markdown('<div style="font-size:0.78rem;color:#64748b;margin-bottom:16px">'
                'Photograph any textbook question, handwritten problem, or diagram — '
                'get an instant step-by-step NCERT solution.</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload image", type=["jpg", "jpeg", "png", "webp"],
                                  key="img_uploader", label_visibility="collapsed")
    st.markdown('<div style="text-align:center;color:#475569;font-size:0.72rem;margin:-8px 0 14px">'
                '📷 JPG · PNG · WEBP &nbsp;|&nbsp; '
                'Works great for: equations, diagrams, MCQs, fill-in-the-blanks</div>',
                unsafe_allow_html=True)

    if uploaded:
        img_preview = Image.open(uploaded)
        col_prev, col_info = st.columns([3, 2])
        with col_prev:
            st.markdown('<div class="img-preview-wrap">', unsafe_allow_html=True)
            st.image(img_preview, use_column_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_info:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid var(--border);
                 border-radius:12px;padding:14px">
              <div style="font-size:0.7rem;color:#64748b;font-weight:600;margin-bottom:10px">📎 Image Info</div>
              <div style="font-size:0.78rem;color:#cbd5e1;line-height:2">
                <b>File:</b> {uploaded.name}<br>
                <b>Size:</b> {uploaded.size//1024} KB<br>
                <b>Dimensions:</b> {img_preview.width}×{img_preview.height}px<br>
                <b>Solving as:</b><br>
                <span style="color:#a78bfa;font-weight:700">
                  {CLASS_ICONS.get(cls,'')} {cls} · {SUBJECT_ICONS.get(subj,'')} {subj}
                </span>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")
        hint = st.text_input("💬 Add a hint (optional)",
                              placeholder="e.g. 'Focus on part b', 'Chapter 4', 'Explain simply'…",
                              key="img_hint")

        solve_col, _ = st.columns([1, 2])
        with solve_col:
            solve_btn = st.button("🔍 Solve this Doubt", type="primary",
                                   use_container_width=True, key="solve_img")

        if solve_btn:
            if not rate_limit_check(): st.stop()
            with st.spinner("📸 Reading image…"):
                uploaded.seek(0); img_b64, mime = prepare_image_for_api(uploaded)
            with st.spinner("🔍 Identifying question type…"):
                q_type = detect_question_type(img_b64, mime)
            with st.spinner(f"✍️ Solving {q_type}… (~10 seconds)"):
                solution = solve_image_doubt(img_b64, mime, cls, subj, hint)
            st.session_state.usage = increment_usage()
            ts = datetime.datetime.now().strftime("%H:%M")
            st.session_state.img_solution_history.append(
                {"image_b64": img_b64, "mime": mime, "q_type": q_type,
                 "solution": solution, "ts": ts})
            st.session_state.img_solution = solution
            st.rerun()

    if st.session_state.img_solution_history:
        latest = st.session_state.img_solution_history[-1]
        st.markdown("---")
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
          <span class="img-type-badge">🏷️ {latest['q_type']}</span>
          <span style="font-size:0.65rem;color:#64748b">
            Solved at {latest['ts']} · {CLASS_ICONS.get(cls,'')} {cls} · {SUBJECT_ICONS.get(subj,'')} {subj}
          </span>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div class="img-solution-box">', unsafe_allow_html=True)
        render_answer_with_math(latest["solution"])
        st.markdown('</div>', unsafe_allow_html=True)

        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("🗒️ Save to Notes", use_container_width=True, key="save_img_note"):
                ok = save_note(f"[Image Doubt — {latest['q_type']}]\n\n{latest['solution']}",
                               cls, subj, "Image Doubt")
                st.toast("✅ Saved!" if ok else "❌ Could not save.")
        with a2:
            if st.button("💬 Continue in Chat", use_container_width=True, key="img_to_chat"):
                st.session_state.messages.append({"role": "assistant",
                    "content": f"📸 **From Image Doubt Solver:**\n\n{latest['solution']}", "chunks": []})
                st.toast("✅ Copied to Chat tab!")
        with a3:
            if st.button("🔄 Upload New", use_container_width=True, key="clear_img"):
                st.session_state.img_solution = None
                st.session_state.img_solution_history = []
                st.rerun()
    elif not uploaded:
        st.markdown("""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px">
          <div style="background:rgba(124,58,237,0.05);border:1px solid rgba(124,58,237,0.18);border-radius:12px;padding:14px">
            <div style="font-size:1.1rem;margin-bottom:6px">📐</div>
            <div style="font-size:0.78rem;font-weight:700;color:#e2e8f0;margin-bottom:4px">Maths Problems</div>
            <div style="font-size:0.7rem;color:#64748b">Algebra, geometry, trigonometry — full step-by-step working</div>
          </div>
          <div style="background:rgba(6,182,212,0.05);border:1px solid rgba(6,182,212,0.18);border-radius:12px;padding:14px">
            <div style="font-size:1.1rem;margin-bottom:6px">🔬</div>
            <div style="font-size:0.78rem;font-weight:700;color:#e2e8f0;margin-bottom:4px">Science Diagrams</div>
            <div style="font-size:0.7rem;color:#64748b">Labelled diagrams, chemical equations, physics numericals</div>
          </div>
          <div style="background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.18);border-radius:12px;padding:14px">
            <div style="font-size:1.1rem;margin-bottom:6px">✍️</div>
            <div style="font-size:0.78rem;font-weight:700;color:#e2e8f0;margin-bottom:4px">Handwritten Questions</div>
            <div style="font-size:0.7rem;color:#64748b">Works with clearly written homework and classwork doubts</div>
          </div>
          <div style="background:rgba(245,158,11,0.05);border:1px solid rgba(245,158,11,0.18);border-radius:12px;padding:14px">
            <div style="font-size:1.1rem;margin-bottom:6px">📖</div>
            <div style="font-size:0.78rem;font-weight:700;color:#e2e8f0;margin-bottom:4px">Textbook Exercises</div>
            <div style="font-size:0.7rem;color:#64748b">Snap any NCERT exercise question for instant answers</div>
          </div>
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# TAB 3 — CHAPTERS
# ════════════════════════════════════════════════════════════════

with tab_idx:
    subjs_show = ["Mathematics", "Science"] if subj == "Both" else [subj]
    progress   = get_chapter_progress()

    if st.session_state.selected_chapter and not st.session_state.chapter_mode:
        ch_key, ch_s = st.session_state.selected_chapter
        ch_title     = CHAPTER_INDEX.get(cls, {}).get(ch_s, {}).get(ch_key, ch_key)
        mark_chapter_visited(ch_key, cls, ch_s)
        if st.button("← Back", key="back_idx"):
            st.session_state.selected_chapter = None; st.rerun()
        visits      = progress.get(ch_key, 0)
        visit_color = "#10b981" if visits else "#a78bfa"
        visit_label = f"✅ Visited {visits}×" if visits else "🆕 First visit!"
        st.markdown(f"""
        <div class="bf-card" style="border-color:{c_col}40;margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div style="font-size:0.66rem;color:#a78bfa;font-weight:700;margin-bottom:3px">
                {CLASS_ICONS.get(cls,'')} {cls} · {SUBJECT_ICONS.get(ch_s,'')} {ch_s}</div>
              <div style="font-size:0.95rem;font-weight:700;color:#e2e8f0">{ch_title}</div>
            </div>
            <span style="background:rgba(16,185,129,0.1);border:1px solid {visit_color}40;
                  border-radius:8px;padding:4px 10px;font-size:0.66rem;
                  color:{visit_color};font-weight:700">{visit_label}</span>
          </div>
        </div>""", unsafe_allow_html=True)
        with st.spinner("📖 Loading overview…"):
            summary = generate_chapter_summary(ch_key, ch_title, cls, ch_s)
        render_answer_with_math(summary)
        st.divider()
        if st.button("💬 Chat about this Chapter", use_container_width=True, type="primary"):
            st.session_state.update(chapter_mode=True, selected_subject=ch_s, messages=[{
                "role": "assistant",
                "content": f"📖 Ready! Ask anything about **{ch_title}** ({cls}·{ch_s}).",
                "chunks": [],
            }]); st.rerun()
    else:
        done_count  = sum(1 for s in CHAPTER_INDEX.get(cls, {})
                          for k in CHAPTER_INDEX[cls][s] if k in progress)
        total_count = sum(len(v) for v in CHAPTER_INDEX.get(cls, {}).values())
        st.markdown(f"""
        <div style="margin-bottom:14px;padding:10px 14px;background:rgba(124,58,237,0.05);
             border:1px solid rgba(124,58,237,0.18);border-radius:10px">
          <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#94a3b8;margin-bottom:5px">
            <span>📊 {cls} Progress</span>
            <span style="color:#a78bfa;font-weight:700">{done_count}/{total_count} chapters visited</span>
          </div>
          <div class="prog-bar-wrap">
            <div class="prog-bar" style="width:{int((done_count/total_count)*100) if total_count else 0}%;
                 background:linear-gradient(90deg,#7c3aed,#06b6d4)"></div>
          </div>
        </div>""", unsafe_allow_html=True)
        for s in subjs_show:
            chapters = CHAPTER_INDEX.get(cls, {}).get(s, {})
            if not chapters: continue
            st.markdown(f"#### {SUBJECT_ICONS.get(s,'')} {cls} — {s}")
            for ch_key, ch_title in chapters.items():
                parts  = ch_title.split(" — ", 1)
                ch_num = parts[0] if len(parts) > 1 else ""
                ch_nm  = parts[1] if len(parts) > 1 else ch_title
                visits = progress.get(ch_key, 0)
                badge  = (f'<span class="ch-visited">✅ {visits}× visited</span>' if visits
                          else '<span class="ch-new">New</span>')
                a, b = st.columns([6, 1])
                with a:
                    st.markdown(f"""<div class="bf-card">
                      <div style="font-size:0.66rem;color:#7c3aed;font-weight:700">{ch_num} {badge}</div>
                      <div style="font-size:0.86rem;font-weight:600;color:#e2e8f0">{ch_nm}</div>
                    </div>""", unsafe_allow_html=True)
                with b:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if st.button("Open", key=f"ch_{cls}_{s}_{ch_key}"):
                        st.session_state.selected_chapter = (ch_key, s); st.rerun()
            st.markdown("")

# ════════════════════════════════════════════════════════════════
# TAB 4 — QUIZ (Batch Mode)
# ════════════════════════════════════════════════════════════════

with tab_quiz:
    quiz_main_tab, review_tab = st.tabs(["⚡ Quiz", "📋 Review & Weak Topics"])

    # ── QUIZ MAIN ─────────────────────────────────────────────
    with quiz_main_tab:
        st.markdown("#### 🎯 Quick Quiz")

        # Setup form (only when no active quiz)
        if not st.session_state.quiz_batch or st.session_state.quiz_batch_done:
            if st.session_state.quiz_batch_done:
                # ── SCORECARD ─────────────────────────────────
                batch    = st.session_state.quiz_batch
                answers  = st.session_state.quiz_batch_answers
                correct  = sum(1 for i, q in enumerate(batch)
                               if i < len(answers) and answers[i] == q.get("correct", "").upper())
                total    = len(batch)
                pct_sc   = int((correct / total) * 100) if total else 0
                color_sc = "#10b981" if pct_sc >= 70 else "#f59e0b" if pct_sc >= 40 else "#ef4444"
                emoji_sc = "🏆" if pct_sc >= 80 else "👍" if pct_sc >= 50 else "📚"

                st.markdown(f"""
                <div class="score-hero">
                  <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:8px">Quiz Complete!</div>
                  <div class="score-big" style="color:{color_sc}">{emoji_sc} {correct}/{total}</div>
                  <div style="font-size:1rem;color:{color_sc};font-weight:700;margin-top:4px">
                    {pct_sc}% correct</div>
                  <div style="font-size:0.75rem;color:#64748b;margin-top:6px">
                    {"Excellent! Keep it up! 🌟" if pct_sc>=80 else "Good effort! Review wrong answers below. 💪" if pct_sc>=50 else "Don't give up! Revisit the topic and try again. 📖"}
                  </div>
                </div>""", unsafe_allow_html=True)

                # Show all Q&A
                with st.expander("📋 See all questions"):
                    for i, q in enumerate(batch):
                        user_ans    = answers[i] if i < len(answers) else "—"
                        correct_ans = q.get("correct", "A").upper()
                        is_right    = user_ans == correct_ans
                        icon        = "✅" if is_right else "❌"
                        border_c    = "#10b981" if is_right else "#ef4444"
                        st.markdown(f"""
                        <div style="background:rgba(255,255,255,0.02);border-left:3px solid {border_c};
                             border-radius:0 10px 10px 0;padding:10px 14px;margin-bottom:8px">
                          <div style="font-size:0.68rem;color:#64748b;margin-bottom:4px">Q{i+1} {icon}</div>
                          <div style="font-size:0.84rem;color:#e2e8f0;font-weight:600;margin-bottom:6px">{q['question']}</div>
                          <div style="font-size:0.75rem">
                            <span style="color:#64748b">Your answer: </span>
                            <span style="color:{'#10b981' if is_right else '#f87171'}">{user_ans}</span>
                            {"" if is_right else f' &nbsp;·&nbsp; <span style="color:#64748b">Correct: </span><span style="color:#10b981">{correct_ans}</span>'}
                          </div>
                          <div style="font-size:0.72rem;color:#94a3b8;margin-top:6px">💡 {q.get('explanation','')}</div>
                        </div>""", unsafe_allow_html=True)

                if st.button("🔄 New Quiz", use_container_width=True, type="primary"):
                    st.session_state.update(quiz_batch=[], quiz_batch_idx=0,
                                            quiz_batch_answers=[], quiz_batch_done=False)
                    st.rerun()

            else:
                # ── Setup ─────────────────────────────────────
                quiz_topic = st.text_input("Topic",
                    placeholder="e.g. Photosynthesis, Newton's Laws, Quadratic Equations…",
                    key="qtopic")
                st.markdown("**Number of questions:**")
                quiz_count = st.radio("count", QUIZ_COUNTS,
                    format_func=lambda x: f"{x} Qs",
                    horizontal=True, key="quiz_count_radio",
                    label_visibility="collapsed")
                g1, _ = st.columns([1, 2])
                with g1:
                    gen_btn = st.button("⚡ Generate Quiz", use_container_width=True, type="primary")

                if gen_btn:
                    if not quiz_topic.strip():
                        st.warning("Enter a topic first.", icon="⚠️")
                    elif rate_limit_check():
                        with st.spinner(f"Generating {quiz_count} NCERT questions…"):
                            chunks = retrieve_chunks(quiz_topic, cls, subj, "", top_k=4)
                            batch  = generate_quiz_batch(quiz_topic, cls, subj, chunks, quiz_count)
                        if batch:
                            # Save each as a quiz attempt (is_correct=False until answered)
                            st.session_state.quiz_batch         = batch
                            st.session_state.quiz_batch_idx     = 0
                            st.session_state.quiz_batch_answers = []
                            st.session_state.quiz_batch_done    = False
                            st.session_state.quiz_topic_last    = quiz_topic.strip()
                            st.session_state.usage              = increment_usage()
                            st.rerun()
                        else:
                            st.error("Could not generate quiz. Try a more specific topic.", icon="❌")

        else:
            # ── Active quiz — show current question ───────────
            batch   = st.session_state.quiz_batch
            idx     = st.session_state.quiz_batch_idx
            total   = len(batch)
            answers = st.session_state.quiz_batch_answers

            # Progress bar
            pct_done = idx / total
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#94a3b8;margin-bottom:4px">
              <span>Question {idx + 1} of {total}</span>
              <span style="color:#a78bfa;font-weight:700">{int(pct_done*100)}% done</span>
            </div>
            <div class="quiz-prog-bar">
              <div class="quiz-prog-fill" style="width:{int(pct_done*100)}%"></div>
            </div>""", unsafe_allow_html=True)

            q = batch[idx]
            already_answered = idx < len(answers)
            correct_letter   = q.get("correct", "A").upper()

            st.markdown(f"""<div class="bf-card" style="border-color:rgba(124,58,237,0.38);margin-top:10px">
              <div style="font-size:0.66rem;color:#a78bfa;font-weight:700;margin-bottom:5px">
                {CLASS_ICONS.get(cls,'')} {cls} · {SUBJECT_ICONS.get(subj,'')} {subj} ·
                Q{idx+1}/{total}</div>
              <div style="font-size:0.93rem;font-weight:700;color:#e2e8f0;line-height:1.5">
                {q['question']}</div>
            </div>""", unsafe_allow_html=True)

            if not already_answered:
                for opt in q["options"]:
                    letter = opt[0].upper()
                    if st.button(opt, key=f"qopt_{idx}_{letter}", use_container_width=True):
                        is_correct = (letter == correct_letter)
                        st.session_state.quiz_batch_answers.append(letter)
                        save_quiz_attempt(st.session_state.quiz_topic_last, q, letter, is_correct)
                        st.rerun()
            else:
                chosen = answers[idx]
                for opt in q["options"]:
                    letter = opt[0].upper()
                    sty = "correct" if letter == correct_letter else ("incorrect" if letter == chosen else "")
                    ico = "✅" if letter == correct_letter else ("❌" if letter == chosen else "⬜")
                    st.markdown(f'<div class="quiz-opt {sty}">{ico} {opt}</div>',
                                unsafe_allow_html=True)

                if chosen == correct_letter:
                    st.success("🎉 Correct!")
                else:
                    st.error(f"Correct answer: **{correct_letter}**")

                st.markdown(f"""<div style="background:rgba(6,182,212,0.06);border:1px solid rgba(6,182,212,0.18);
                     border-radius:10px;padding:11px 15px;margin-top:8px;font-size:0.82rem;color:#cbd5e1">
                  💡 <strong>Explanation:</strong> {q.get('explanation','')}</div>""",
                    unsafe_allow_html=True)

                # Next / Finish
                if idx + 1 < total:
                    if st.button("Next Question →", use_container_width=True, type="primary"):
                        st.session_state.quiz_batch_idx += 1; st.rerun()
                else:
                    if st.button("🏁 See Results", use_container_width=True, type="primary"):
                        st.session_state.quiz_batch_done = True; st.rerun()

            # Quit quiz option
            if st.button("✕ Quit Quiz", key="quit_quiz"):
                st.session_state.update(quiz_batch=[], quiz_batch_idx=0,
                                        quiz_batch_answers=[], quiz_batch_done=False)
                st.rerun()

    # ── REVIEW & WEAK TOPICS ──────────────────────────────────
    with review_tab:
        total_q, correct_q = get_quiz_stats()
        wrong_q = total_q - correct_q
        acc     = int((correct_q / total_q) * 100) if total_q else 0

        if total_q:
            r1, r2, r3 = st.columns(3)
            for col, val, label, color in [
                (r1, total_q,   "Attempted", "#a78bfa"),
                (r2, correct_q, "Correct",   "#10b981"),
                (r3, wrong_q,   "Wrong",     "#f87171"),
            ]:
                with col:
                    st.markdown(f"""<div style="text-align:center;padding:12px;
                         background:rgba(255,255,255,0.03);
                         border:1px solid rgba(255,255,255,0.07);border-radius:10px">
                      <div style="font-size:1.4rem;font-weight:800;color:{color}">{val}</div>
                      <div style="font-size:0.65rem;color:#64748b">{label}</div></div>""",
                        unsafe_allow_html=True)
            st.markdown("")

        # ── Weak Topics AI ────────────────────────────────────
        weak = get_weak_topics()
        if weak:
            st.markdown("#### 🧠 Your Weak Topics")
            pills_html = "".join(
                f'<span class="weak-topic-pill">⚠️ {t} <span style="opacity:0.6">({c}✗)</span></span>'
                for t, c in weak
            )
            st.markdown(f'<div style="margin-bottom:12px">{pills_html}</div>', unsafe_allow_html=True)

            if st.button("🤖 Get AI Revision Tips", use_container_width=True, key="weak_tips_btn"):
                with st.spinner("Analysing weak topics…"):
                    insight = generate_weak_topic_insight(weak, cls, subj)
                st.markdown(f"""<div style="background:rgba(124,58,237,0.07);
                     border:1px solid rgba(124,58,237,0.22);border-radius:12px;
                     padding:14px 18px;margin-top:10px">
                  <div style="font-size:0.68rem;color:#a78bfa;font-weight:700;margin-bottom:6px">
                    🤖 AI Revision Insight</div>""", unsafe_allow_html=True)
                render_answer_with_math(insight)
                st.markdown('</div>', unsafe_allow_html=True)

            if st.button(f"⚡ Practice Quiz on '{weak[0][0]}'",
                         use_container_width=True, key="weak_quiz_btn"):
                if rate_limit_check():
                    with st.spinner(f"Generating quiz on {weak[0][0]}…"):
                        chunks = retrieve_chunks(weak[0][0], cls, subj, "", top_k=4)
                        batch  = generate_quiz_batch(weak[0][0], cls, subj, chunks, 5)
                    if batch:
                        st.session_state.quiz_batch         = batch
                        st.session_state.quiz_batch_idx     = 0
                        st.session_state.quiz_batch_answers = []
                        st.session_state.quiz_batch_done    = False
                        st.session_state.quiz_topic_last    = weak[0][0]
                        st.session_state.usage              = increment_usage()
                        st.toast(f"✅ Quiz on '{weak[0][0]}' ready! Go to ⚡ Quiz tab.")
            st.markdown("---")

        # ── Wrong answers list ────────────────────────────────
        wrong_list = get_wrong_answers(limit=20)
        if not wrong_list:
            st.markdown("""<div style="text-align:center;padding:40px 20px;color:#64748b">
              <div style="font-size:2rem">🎉</div>
              <div style="font-weight:600;margin-top:8px">No wrong answers yet!</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"#### 📋 {len(wrong_list)} Wrong Answers to Review")
            for wa in wrong_list:
                try:    opts = json.loads(wa.get("options", "[]"))
                except: opts = []
                correct_text = next((o for o in opts if o.startswith(wa.get("correct_answer", ""))),
                                    wa.get("correct_answer", ""))
                picked_text  = next((o for o in opts if o.startswith(wa.get("user_answer", ""))),
                                    wa.get("user_answer", ""))
                st.markdown(f"""<div class="wrong-card">
                  <div class="wc-topic">📌 {wa.get('topic','?')} ·
                    {CLASS_ICONS.get(wa.get('class',''),'')} {wa.get('class','')} ·
                    {wa.get('created_at','')[:10]}</div>
                  <div class="wc-q">{wa.get('question','')}</div>
                  <div class="wc-ans">
                    ❌ <span style="color:#f87171">You answered:</span> {picked_text}<br>
                    ✅ <span style="color:#10b981">Correct:</span> {correct_text}
                  </div>
                  <div class="wc-exp">💡 {wa.get('explanation','')}</div>
                </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# TAB 5 — EXAM MODE
# ════════════════════════════════════════════════════════════════

with tab_exam:
    st.markdown("#### 📝 Exam Mode")
    st.markdown('<div style="font-size:0.78rem;color:#64748b;margin-bottom:14px">'
                'Real CBSE-style written questions. Answer by uploading your handwritten answer '
                'or by speaking. AI evaluates and gives marks.</div>', unsafe_allow_html=True)

    exam_stage = st.session_state.exam_stage

    # ── SETUP ─────────────────────────────────────────────────
    if exam_stage == "setup":
        exam_topic    = st.text_input("📌 Topic for Exam",
                                       placeholder="e.g. Photosynthesis, Quadratic Equations, Newton's Laws…",
                                       key="exam_topic_input")
        exam_subj_sel = st.selectbox("Subject", ["Mathematics", "Science"], key="exam_subj_sel")
        exam_count    = st.radio("Number of Questions", [3, 5, 10],
                                  format_func=lambda x: f"{x} Questions",
                                  horizontal=True, key="exam_count_radio")

        st.markdown("""
        <div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.2);
             border-radius:10px;padding:10px 14px;font-size:0.75rem;color:#fbbf24;margin:10px 0">
          📋 <strong>How it works:</strong> AI generates real board-style questions →
          You write answers in your notebook → Upload a photo or speak your answer →
          AI gives marks out of the question's marks.
        </div>""", unsafe_allow_html=True)

        if st.button("🚀 Start Exam", type="primary", use_container_width=True, key="start_exam"):
            if not exam_topic.strip():
                st.error("Enter a topic to generate exam questions.", icon="❌")
            else:
                with st.spinner(f"Generating {exam_count} board-style questions on '{exam_topic}'…"):
                    questions = generate_exam_questions(exam_topic, cls, exam_subj_sel, exam_count)
                if questions:
                    st.session_state.exam_questions   = questions
                    st.session_state.exam_current_idx = 0
                    st.session_state.exam_answers     = []
                    st.session_state.exam_topic       = exam_topic.strip()
                    st.session_state.exam_subject     = exam_subj_sel
                    st.session_state.exam_stage       = "answering"
                    st.rerun()
                else:
                    st.error("Could not generate questions. Please try again.", icon="❌")

    # ── ANSWERING ─────────────────────────────────────────────
    elif exam_stage == "answering":
        questions = st.session_state.exam_questions
        idx       = st.session_state.exam_current_idx
        total     = len(questions)
        topic     = st.session_state.exam_topic
        e_subj    = st.session_state.exam_subject

        # Progress
        pct_e = idx / total
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#94a3b8;margin-bottom:4px">
          <span>Question {idx + 1} of {total} · {topic}</span>
          <span style="color:#a78bfa;font-weight:700">{CLASS_ICONS.get(cls,'')} {cls} · {e_subj}</span>
        </div>
        <div class="quiz-prog-bar">
          <div class="quiz-prog-fill" style="width:{int(pct_e*100)}%"></div>
        </div>""", unsafe_allow_html=True)

        q     = questions[idx]
        q_txt = q.get("question", "")
        marks = q.get("marks", 3)
        hint  = q.get("hint", "")

        st.markdown(f"""
        <div class="exam-q-card">
          <div class="exam-q-num">Q{idx+1} · {e_subj}</div>
          <div class="exam-q-text">{q_txt}</div>
          <span class="exam-marks-badge">📊 {marks} marks</span>
          {"<div style='font-size:0.7rem;color:#64748b;margin-top:8px'>💡 Hint: "+hint+"</div>" if hint else ""}
        </div>""", unsafe_allow_html=True)

        st.markdown("**Submit your answer:**")
        ans_tab_img, ans_tab_voice, ans_tab_text = st.tabs(
            ["📷 Upload Handwritten", "🎤 Voice Answer", "⌨️ Type Answer"])

        submitted_eval = None

        # ── Image answer ──────────────────────────────────────
        with ans_tab_img:
            st.markdown('<div style="font-size:0.75rem;color:#64748b;margin-bottom:10px">'
                        'Write your answer in your notebook, then upload a clear photo.</div>',
                        unsafe_allow_html=True)
            ans_img = st.file_uploader("Upload answer photo",
                                        type=["jpg", "jpeg", "png", "webp"],
                                        key=f"exam_img_{idx}", label_visibility="collapsed")
            if ans_img:
                st.image(Image.open(ans_img), use_column_width=True)
                if st.button("📤 Submit Image Answer", type="primary",
                             use_container_width=True, key=f"submit_img_{idx}"):
                    with st.spinner("🔍 Reading handwriting & evaluating…"):
                        ans_img.seek(0)
                        img_b64, mime = prepare_image_for_api(ans_img)
                        result = evaluate_image_answer(q_txt, marks, img_b64, mime, cls, e_subj)
                    submitted_eval = {"type": "image", "content": "[handwritten image]", "eval": result}

        # ── Voice answer ──────────────────────────────────────
        with ans_tab_voice:
            if VOICE_AVAILABLE:
                st.markdown('<div style="font-size:0.75rem;color:#64748b;margin-bottom:10px">'
                            'Speak your answer clearly in English.</div>', unsafe_allow_html=True)
                voice_ans = speech_to_text(
                    language="en-IN",
                    start_prompt="🎤 Speak your answer",
                    stop_prompt="⏹ Stop",
                    use_container_width=True,
                    key=f"voice_exam_{idx}",
                )
                if voice_ans and voice_ans.strip():
                    st.info(f"🎤 Transcribed: *{voice_ans}*")
                    if st.button("📤 Submit Voice Answer", type="primary",
                                 use_container_width=True, key=f"submit_voice_{idx}"):
                        with st.spinner("Evaluating voice answer…"):
                            result = evaluate_text_answer(q_txt, marks, voice_ans, cls, e_subj)
                        submitted_eval = {"type": "voice", "content": voice_ans, "eval": result}
            else:
                st.info("🎤 Voice input not available. Install `streamlit-mic-recorder` to enable.",
                        icon="ℹ️")

        # ── Text answer ───────────────────────────────────────
        with ans_tab_text:
            st.markdown('<div style="font-size:0.75rem;color:#64748b;margin-bottom:10px">'
                        'Type your answer below.</div>', unsafe_allow_html=True)
            typed_ans = st.text_area("Your answer", height=150,
                                      placeholder="Write your answer here…",
                                      key=f"typed_ans_{idx}", label_visibility="collapsed")
            if st.button("📤 Submit Typed Answer", type="primary",
                         use_container_width=True, key=f"submit_typed_{idx}"):
                if not typed_ans.strip():
                    st.warning("Please write something first.", icon="⚠️")
                else:
                    with st.spinner("Evaluating answer…"):
                        result = evaluate_text_answer(q_txt, marks, typed_ans, cls, e_subj)
                    submitted_eval = {"type": "text", "content": typed_ans, "eval": result}

        # ── Show evaluation result inline ─────────────────────
        if submitted_eval:
            ev        = submitted_eval["eval"]
            awarded   = ev.get("marks_awarded", 0)
            max_m     = ev.get("max_marks", marks)
            pct_marks = int((awarded / max_m) * 100) if max_m else 0
            ev_class  = "good" if pct_marks >= 70 else "avg" if pct_marks >= 40 else "poor"
            ev_color  = "#10b981" if pct_marks >= 70 else "#f59e0b" if pct_marks >= 40 else "#ef4444"

            st.markdown(f"""
            <div class="eval-card {ev_class}" style="margin-top:14px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-size:0.72rem;color:#94a3b8;font-weight:600">AI Evaluation</span>
                <span style="font-size:1.3rem;font-weight:900;color:{ev_color}">
                  {awarded}/{max_m}</span>
              </div>
              <div style="font-size:0.82rem;color:#cbd5e1;margin-bottom:6px">
                {ev.get('feedback','')}</div>
              {"<div style='font-size:0.75rem;color:#10b981;margin-top:4px'>✅ "+ev.get('good','')+"</div>" if ev.get('good') else ""}
              {"<div style='font-size:0.75rem;color:#f87171;margin-top:4px'>📝 Missing: "+ev.get('missing','')+"</div>" if ev.get('missing') else ""}
            </div>""", unsafe_allow_html=True)

            # Store and move to next question
            st.session_state.exam_answers.append(submitted_eval)

            if idx + 1 < total:
                if st.button("Next Question →", use_container_width=True,
                             type="primary", key=f"exam_next_{idx}"):
                    st.session_state.exam_current_idx += 1; st.rerun()
            else:
                if st.button("🏁 See Final Results", use_container_width=True,
                             type="primary", key="exam_finish"):
                    # Save to DB
                    total_scored = sum(a["eval"].get("marks_awarded", 0)
                                       for a in st.session_state.exam_answers)
                    max_score    = sum(q.get("marks", 3) for q in questions)
                    save_exam_attempt(topic, questions, st.session_state.exam_answers,
                                      total_scored, max_score)
                    st.session_state.exam_stage = "results"; st.rerun()

        # Quit exam
        if st.button("✕ Quit Exam", key="quit_exam"):
            st.session_state.exam_stage = "setup"; st.rerun()

    # ── RESULTS ───────────────────────────────────────────────
    elif exam_stage == "results":
        questions = st.session_state.exam_questions
        answers   = st.session_state.exam_answers
        topic     = st.session_state.exam_topic

        total_scored = sum(a["eval"].get("marks_awarded", 0) for a in answers)
        max_score    = sum(q.get("marks", 3) for q in questions)
        pct_exam     = int((total_scored / max_score) * 100) if max_score else 0
        color_exam   = "#10b981" if pct_exam >= 70 else "#f59e0b" if pct_exam >= 40 else "#ef4444"
        grade        = ("A+" if pct_exam >= 90 else "A" if pct_exam >= 80 else
                        "B" if pct_exam >= 70 else "C" if pct_exam >= 50 else "D")

        st.markdown(f"""
        <div class="score-hero">
          <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:6px">
            📝 {topic} · {st.session_state.exam_subject}</div>
          <div class="score-big" style="color:{color_exam}">{grade}</div>
          <div style="font-size:1.3rem;font-weight:800;color:{color_exam};margin-top:4px">
            {total_scored} / {max_score} marks</div>
          <div style="font-size:0.85rem;color:{color_exam};margin-top:4px">{pct_exam}%</div>
          <div style="font-size:0.75rem;color:#64748b;margin-top:8px">
            {"Outstanding! Excellent CBSE preparation! 🌟" if pct_exam>=80
             else "Good effort! A little more practice will help. 💪" if pct_exam>=50
             else "Keep revising! You'll get better with practice. 📖"}
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### 📋 Question-wise Breakdown")
        for i, (q, a) in enumerate(zip(questions, answers)):
            ev      = a["eval"]
            awarded = ev.get("marks_awarded", 0)
            max_m   = q.get("marks", 3)
            pct_q   = int((awarded / max_m) * 100) if max_m else 0
            ev_c    = "good" if pct_q >= 70 else "avg" if pct_q >= 40 else "poor"
            ev_col  = "#10b981" if pct_q >= 70 else "#f59e0b" if pct_q >= 40 else "#ef4444"

            with st.expander(f"Q{i+1} — {awarded}/{max_m} marks · {q.get('question','')[:60]}…"):
                st.markdown(f"""
                <div class="eval-card {ev_c}">
                  <div style="font-size:0.82rem;font-weight:600;color:#e2e8f0;margin-bottom:8px">
                    {q.get('question','')}</div>
                  <div style="font-size:0.72rem;color:#64748b;margin-bottom:8px">
                    Answer type: {a.get('type','—').capitalize()}</div>
                  <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                    <span style="font-size:0.78rem;color:#94a3b8">Marks awarded:</span>
                    <span style="font-size:1rem;font-weight:800;color:{ev_col}">{awarded}/{max_m}</span>
                  </div>
                  <div style="font-size:0.8rem;color:#cbd5e1;margin-bottom:6px">
                    {ev.get('feedback','')}</div>
                  {"<div style='font-size:0.74rem;color:#10b981'>✅ "+ev.get('good','')+"</div>" if ev.get('good') else ""}
                  {"<div style='font-size:0.74rem;color:#f87171;margin-top:4px'>📝 "+ev.get('missing','')+"</div>" if ev.get('missing') else ""}
                </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 New Exam", use_container_width=True, type="primary"):
                st.session_state.exam_stage = "setup"; st.rerun()
        with c2:
            if st.button("🗒️ Save Results to Notes", use_container_width=True):
                note_content = (
                    f"## 📝 Exam Results — {topic}\n"
                    f"**Score:** {total_scored}/{max_score} ({pct_exam}%) · Grade: {grade}\n\n"
                )
                for i, (q, a) in enumerate(zip(questions, answers)):
                    ev = a["eval"]
                    note_content += (
                        f"**Q{i+1}:** {q.get('question','')}\n"
                        f"**Marks:** {ev.get('marks_awarded',0)}/{q.get('marks',3)}\n"
                        f"**Feedback:** {ev.get('feedback','')}\n\n"
                    )
                ok = save_note(note_content, cls, st.session_state.exam_subject, "Exam Mode")
                st.toast("✅ Saved to Notes!" if ok else "❌ Could not save.")

# ════════════════════════════════════════════════════════════════
# TAB 6 — NOTES
# ════════════════════════════════════════════════════════════════

with tab_notes:
    st.markdown("#### 🗒️ Saved Notes")
    with st.expander("✏️ Add a custom note"):
        note_txt = st.text_area("Your note",
                                 placeholder="Write something to remember…",
                                 height=90, key="new_note")
        if st.button("💾 Save Note", use_container_width=True):
            if note_txt.strip():
                ok = save_note(note_txt.strip(), cls, subj, "Manual")
                st.toast("✅ Saved!" if ok else "❌ Could not save.", icon="🗒️")
                if ok: st.rerun()
            else:
                st.warning("Note is empty.", icon="⚠️")
    st.markdown("---")
    notes = get_notes(cls)
    if not notes:
        st.markdown("""<div style="text-align:center;padding:36px 20px;color:#64748b">
          <div style="font-size:2rem">🗒️</div>
          <div style="font-weight:600;margin-top:6px">No notes yet</div>
          <div style="font-size:0.78rem;margin-top:4px">Tap "Save" under any answer</div>
        </div>""", unsafe_allow_html=True)
    else:
        for note in notes:
            ts  = note.get("created_at", "")[:16].replace("T", " ")
            ch  = note.get("chapter", "")
            txt = note.get("content", "")
            nid = note.get("id")
            display  = txt[:400] + ("…" if len(txt) > 400 else "")
            na, nb   = st.columns([8, 1])
            with na:
                ch_label = ("· 📸 Image Doubt" if ch == "Image Doubt"
                            else f"· 📝 Exam" if ch == "Exam Mode"
                            else f"· 📖 {ch}" if ch and ch not in ("General", "Manual") else "")
                st.markdown(f"""<div class="note-card">
                  <div style="font-size:0.65rem;color:#64748b;margin-bottom:3px">🕐 {ts}</div>
                  <div style="font-size:0.66rem;color:#a78bfa;font-weight:700;margin-bottom:5px">
                    {CLASS_ICONS.get(note.get('class',''),'')} {note.get('class','')} ·
                    {SUBJECT_ICONS.get(note.get('subject',''),'')} {note.get('subject','')} {ch_label}</div>
                  <div style="font-size:0.82rem;color:#cbd5e1;line-height:1.6">{display}</div>
                </div>""", unsafe_allow_html=True)
            with nb:
                if st.button("🗑️", key=f"del_{nid}", help="Delete"):
                    delete_note(nid); st.rerun()
