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

def knockout_result(m):
    home = m.get("Home") or {}
    away = m.get("Away") or {}

    home_name = team_name(home)
    away_name = team_name(away)

    hs = m.get("HomeTeamScore")
    aw = m.get("AwayTeamScore")

    if hs is None or aw is None:
        return None, None, None

    winner = m.get("Winner")
    home_id = home.get("IdTeam")
    away_id = away.get("IdTeam")

    if winner == home_id:
        winner_name = home_name
    elif winner == away_id:
        winner_name = away_name
    else:
        winner_name = None

    match_time = m.get("MatchTime", "")
    result_type = m.get("ResultType")

    # -------- Penalty Shootout --------
    hp = m.get("HomeTeamPenaltyScore")
    ap = m.get("AwayTeamPenaltyScore")

    if hp is not None and ap is not None:
        return winner_name, (
            f"🏆 **{winner_name}** won **{max(hp, ap)}–{min(hp, ap)}** "
            f"on penalties after a **{hs}–{aw}** draw."
        )

    # -------- Normal / Extra Time --------
    if winner_name:

        try:
            minute = int(match_time.replace("'", ""))
        except:
            minute = 90

        if minute > 120 or result_type == 2:
            ending = "after penalties"
        elif minute > 90:
            ending = "after extra time"
        else:
            ending = "after regular time"

        return winner_name, (
            f"🏆 **{winner_name}** won **{max(hs, aw)}–{min(hs, aw)}** "
            f"{ending}."
        )

    return None, None


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


# ---------------- UI ----------------
st.title("🏆 FIFA World Cup 26 — Tracker")
st.caption("Group standings, knockout fixtures (Round of 32 through the Final) & live scores — times shown in IST")

matches, fetched_at = load_data()

if matches is None:
    st.error("No data file found yet. The background fetcher (GitHub Actions) hasn't run for the first time, "
              "or hasn't pushed data/matches.json. Trigger it manually from the Actions tab if needed.")
    st.stop()

if fetched_at:
    fetched_dt = datetime.fromisoformat(fetched_at).astimezone(IST)
    age_minutes = (datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)).total_seconds() / 60
    st.success(f"Data last updated {fetched_dt.strftime('%I:%M %p IST')} ({int(age_minutes)} min ago)")

# ---- Group Stage ----
st.header("Group Stage")
group_matches = [m for m in matches if "group" in (m.get("StageName", [{}])[0].get("Description", "").lower())
                  or "first stage" in (m.get("StageName", [{}])[0].get("Description", "").lower())]

if not group_matches:
    st.info("No group-stage data in the latest snapshot.")
else:
    groups = {}
    for m in group_matches:
        g = m.get("GroupName", [{}])[0].get("Description", "Group ?")
        groups.setdefault(g, []).append(m)

    group_names = sorted(groups.keys())
    cols = st.columns(2)
    for i, gname in enumerate(group_names):
        with cols[i % 2]:
            st.subheader(gname)
            df = build_standings(groups[gname])
            st.dataframe(df, hide_index=True, use_container_width=True)

# ---- Knockout Stage (Round of 32 through Final) ----
st.header("Knockout Stage")

KNOCKOUT_ORDER = [
    "round of 32",
    "round of 16",
    "quarter-final",
    "quarter final",
    "semi-final",
    "semi final",
    "play-off for third place",
    "third place",
    "final",
]

def knockout_rank(stage_desc: str) -> int:
    s = stage_desc.lower()
    for i, key in enumerate(KNOCKOUT_ORDER):
        if key in s:
            return i
    return len(KNOCKOUT_ORDER)


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
        cols = st.columns(2)
        for i, m in enumerate(stage_matches):
            with cols[i % 2]:
                with st.container(border=True):
                    status = derive_status(m)
                    st.markdown(f"**{status}**  ·  {m.get('Stadium', {}).get('Name', [{}])[0].get('Description', '')}")
                    hs = (m.get("Home") or {}).get("Score")
                    aw = (m.get("Away") or {}).get("Score")
                    winner_name, result_text = knockout_result(m)

                    home_name = team_name(m.get("Home"))
                    away_name = team_name(m.get("Away"))

                    if winner_name == home_name:
                        home_display = f"**{home_name}**"
                        away_display = away_name
                    elif winner_name == away_name:
                        home_display = home_name
                        away_display = f"**{away_name}**"
                    else:
                        home_display = home_name
                        away_display = away_name

                    st.markdown(
                        f"{flag(team_code(m.get('Home')))} {home_display} — "
                        f"{'–' if hs is None else hs} : {'–' if aw is None else aw} — "
                        f"{away_display} {flag(team_code(m.get('Away')))}"
                    )
                    st.caption(f"🕒 {to_ist(m['Date'])}")
                    if result_text:
                        st.caption(result_text)
        st.markdown("")

st.divider()
st.caption("Data refreshed in the background by GitHub Actions · this app never calls FIFA directly.")
