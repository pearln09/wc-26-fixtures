import streamlit as st
import json
import pandas as pd
from datetime import datetime, timezone
import pytz
import os

st.set_page_config(page_title="WC26 Tracker", page_icon="🏆", layout="wide")

DATA_PATH = "data/matches.json"
IST = pytz.timezone("Asia/Kolkata")

FLAG_MAP = {
    "MEX":"🇲🇽","RSA":"🇿🇦","KOR":"🇰🇷","CAN":"🇨🇦","QAT":"🇶🇦","SUI":"🇨🇭",
    "BRA":"🇧🇷","MAR":"🇲🇦","HAI":"🇭🇹","SCO":"🏴","USA":"🇺🇸","PAR":"🇵🇾",
    "AUS":"🇦🇺","GER":"🇩🇪","CUW":"🇨🇼","CIV":"🇨🇮","ECU":"🇪🇨","NED":"🇳🇱",
    "JPN":"🇯🇵","TUN":"🇹🇳","BEL":"🇧🇪","EGY":"🇪🇬","IRN":"🇮🇷","NZL":"🇳🇿",
    "ESP":"🇪🇸","CPV":"🇨🇻","KSA":"🇸🇦","URU":"🇺🇾","FRA":"🇫🇷","SEN":"🇸🇳",
    "NOR":"🇳🇴","ARG":"🇦🇷","ALG":"🇩🇿","AUT":"🇦🇹","JOR":"🇯🇴","POR":"🇵🇹",
    "UZB":"🇺🇿","COL":"🇨🇴","ENG":"🏴","CRO":"🇭🇷","GHA":"🇬🇭","PAN":"🇵🇦",
}


def flag(code: str) -> str:
    return FLAG_MAP.get(code, "🏳️")


@st.cache_data(ttl=60, show_spinner=False)
def load_data():
    if not os.path.exists(DATA_PATH):
        return None, None
    with open(DATA_PATH) as f:
        payload = json.load(f)
    return payload.get("results", []), payload.get("fetched_at_utc")


def team_name(side):
    if not side:
        return "TBD"
    try:
        return side["TeamName"][0]["Description"]
    except Exception:
        return "TBD"


def team_code(side):
    return (side or {}).get("Abbreviation", "")


def to_ist(date_str):
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(IST)
    return dt.strftime("%a %d %b, %I:%M %p IST")


def derive_status(m):
    now = datetime.now(timezone.utc)
    kickoff = datetime.fromisoformat(m["Date"].replace("Z", "+00:00"))
    hs, aw = (m.get("Home") or {}).get("Score"), (m.get("Away") or {}).get("Score")
    if hs is None and aw is None:
        return "Upcoming" if now < kickoff else "Live"
    hrs_since = (now - kickoff).total_seconds() / 3600
    if hrs_since < 0:
        return "Upcoming"
    if hrs_since < 2.5:
        return "Live" + (f" {m.get('MatchTime')}" if m.get("MatchTime") else "")
    return "Full Time"


def build_standings(group_matches):
    teams = {}
    for m in group_matches:
        for side in (m.get("Home"), m.get("Away")):
            name = team_name(side)
            if name not in teams:
                teams[name] = {"Team": f"{flag(team_code(side))} {name}",
                                "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
    for m in group_matches:
        hs, aw = (m.get("Home") or {}).get("Score"), (m.get("Away") or {}).get("Score")
        if hs is None or aw is None:
            continue
        hn, an = team_name(m["Home"]), team_name(m["Away"])
        h, a = teams[hn], teams[an]
        h["P"] += 1; a["P"] += 1
        h["GF"] += hs; h["GA"] += aw
        a["GF"] += aw; a["GA"] += hs
        if hs > aw:
            h["W"] += 1; h["Pts"] += 3; a["L"] += 1
        elif hs < aw:
            a["W"] += 1; a["Pts"] += 3; h["L"] += 1
        else:
            h["D"] += 1; a["D"] += 1; h["Pts"] += 1; a["Pts"] += 1
    df = pd.DataFrame(teams.values())
    if df.empty:
        return df
    df["GD"] = df["GF"] - df["GA"]
    df = df.sort_values(["Pts", "GD", "GF"], ascending=False).reset_index(drop=True)
    return df[["Team", "P", "W", "D", "L", "GD", "Pts"]]


def get_stage_matches(matches, *keywords):
    out = []
    for m in matches:
        s = m.get("StageName", [{}])[0].get("Description", "").lower()
        if any(k in s for k in keywords):
            out.append(m)
    out.sort(key=lambda m: m["Date"])
    return out


KNOCKOUT_ORDER = [
    "round of 32", "round of 16", "quarter-final", "quarter final",
    "semi-final", "semi final", "play-off for third place", "third place", "final",
]


def knockout_rank(stage_desc: str) -> int:
    s = stage_desc.lower()
    for i, key in enumerate(KNOCKOUT_ORDER):
        if key in s:
            return i
    return len(KNOCKOUT_ORDER)


# ---------------- Mobile-friendly global styling ----------------
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #7ed957 0%, #1ea36b 55%, #0f7a52 100%); }
    .main .block-container { padding-top: 1.5rem; padding-left: 1rem; padding-right: 1rem; max-width: 1300px; }
    h1 { color:#fff !important; text-shadow:0 2px 6px rgba(0,0,0,0.25); text-align:center; font-size: clamp(22px, 5vw, 38px) !important; }
    h2 { color:#fff !important; text-shadow:0 1px 4px rgba(0,0,0,0.3); border-bottom:2px solid rgba(255,255,255,0.3); padding-bottom:8px; margin-top:2rem; font-size: clamp(18px, 4vw, 26px) !important; }
    h3 { color:#fff !important; background:#0b3d39; padding:8px 14px; border-radius:6px; font-size: clamp(14px, 3.5vw, 17px) !important; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background:#fff; border-radius:10px !important; box-shadow:0 6px 14px rgba(0,0,0,0.18); border:none !important;
    }
    .stDataFrame { border-radius:8px; overflow:hidden; font-size: 13px; }

    /* Tighten things up on small screens */
    @media (max-width: 640px) {
        .main .block-container { padding-left: 0.6rem; padding-right: 0.6rem; }
        [data-testid="column"] { padding: 0 4px !important; }
        .stDataFrame { font-size: 11px; }
    }
</style>
""", unsafe_allow_html=True)

st.title("🏆 FIFA World Cup 26 — Tracker")
st.caption("Group standings, knockout fixtures (Round of 32 through the Final) & live scores — times in IST")

matches, fetched_at = load_data()

if matches is None:
    st.error("No data file found yet. Run the GitHub Actions fetcher at least once.")
    st.stop()

if fetched_at:
    fetched_dt = datetime.fromisoformat(fetched_at).astimezone(IST)
    age_minutes = (datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)).total_seconds() / 60
    st.success(f"Data last updated {fetched_dt.strftime('%I:%M %p IST')} ({int(age_minutes)} min ago)")

# ---- Group Stage ----
st.header("Group Stage")
group_matches = get_stage_matches(matches, "group", "first stage")

if not group_matches:
    st.info("No group-stage data in the latest snapshot.")
else:
    groups = {}
    for m in group_matches:
        g = m.get("GroupName", [{}])[0].get("Description", "Group ?")
        groups.setdefault(g, []).append(m)
    group_names = sorted(groups.keys())
    # 2 columns on desktop, Streamlit auto-stacks to 1 column on narrow/mobile screens
    cols = st.columns(2)
    for i, gname in enumerate(group_names):
        with cols[i % 2]:
            st.subheader(gname)
            df = build_standings(groups[gname])
            st.dataframe(df, hide_index=True, use_container_width=True)

# ---- Knockout Stage (Round of 32 through Final), simple stacked cards ----
st.header("Knockout Stage")

knockout_matches = [
    m for m in matches
    if knockout_rank(m.get("StageName", [{}])[0].get("Description", "")) < len(KNOCKOUT_ORDER)
]

if not knockout_matches:
    st.info("Knockout fixtures aren't published yet — they lock in once the group stage finishes. "
            "They'll appear automatically once the background fetcher picks them up.")
else:
    stages = {}
    for m in knockout_matches:
        stage_desc = m.get("StageName", [{}])[0].get("Description", "Knockout")
        stages.setdefault(stage_desc, []).append(m)

    ordered_stage_names = sorted(stages.keys(), key=lambda s: (knockout_rank(s), s))

    for stage_name in ordered_stage_names:
        stage_matches = sorted(stages[stage_name], key=lambda m: m["Date"])
        st.subheader(stage_name)
        # 2 columns on desktop, stacks to 1 on phones automatically
        cols = st.columns(2)
        for i, m in enumerate(stage_matches):
            with cols[i % 2]:
                with st.container(border=True):
                    status = derive_status(m)
                    hs = (m.get("Home") or {}).get("Score")
                    aw = (m.get("Away") or {}).get("Score")
                    badge_color = "#e0432b" if "Live" in status else ("#0b3d39" if status == "Full Time" else "#6b7a76")
                    st.markdown(f"""
                    <div style="padding:2px 0;">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:4px;">
                        <span style="font-size:11px; color:#7a8a85;">{m.get('Stadium', {}).get('Name', [{{}}])[0].get('Description', '')}</span>
                        <span style="background:{badge_color}; color:#fff; font-size:10px; font-weight:700; padding:2px 10px; border-radius:10px; white-space:nowrap;">{status}</span>
                      </div>
                      <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
                        <span style="font-weight:700; font-size:14.5px;">{flag(team_code(m.get('Home')))} {team_name(m.get('Home'))}</span>
                        <span style="font-weight:800; font-size:16px; color:#0b3d39;">{'–' if hs is None else hs}</span>
                      </div>
                      <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
                        <span style="font-weight:700; font-size:14.5px;">{flag(team_code(m.get('Away')))} {team_name(m.get('Away'))}</span>
                        <span style="font-weight:800; font-size:16px; color:#0b3d39;">{'–' if aw is None else aw}</span>
                      </div>
                      <div style="margin-top:8px; padding-top:8px; border-top:1px dashed #e4e4e4; font-size:12px; color:#5c6e69;">
                        🕒 {to_ist(m['Date'])}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
        st.markdown("")

st.divider()
st.caption("Data refreshed in the background by GitHub Actions · this app never calls FIFA directly.")
