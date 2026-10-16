"""Streamlit version of the Global Major Industrial Accident Report.

Run:  streamlit run streamlit-app/app.py
Data: data/accidents.json (inside this folder)
Optional AI summary: set GEMINI_API_KEY (and optionally GEMINI_MODEL) in
.streamlit/secrets.toml or as environment variables.
"""
import base64
import json
import os
import re
import time
from datetime import date, timedelta
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "data" / "accidents.json"
LOGO = HERE / "logo.png"

TH_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
             "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
TH_MONTHS_SHORT = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
                   "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
CARDS_PER_PAGE = 6

NAVY, RED, ORA, BLU = "#1a2744", "#DC2626", "#EA580C", "#2563EB"

st.set_page_config(page_title="รายงานอุบัติเหตุอุตสาหกรรมโลก",
                   page_icon=str(LOGO) if LOGO.exists() else "🏭", layout="wide")

st.markdown(f"""
<style>
  .stApp {{ background: linear-gradient(180deg,#E8EEF7 0%,#F0F4F8 260px); }}
  .block-container {{ max-width: 1200px; padding-top: 1.2rem; }}
  header[data-testid="stHeader"] {{ background: transparent; }}

  /* Hero */
  .hero {{ background: linear-gradient(120deg,{NAVY} 0%,#1e3a8a 55%,#2563EB 100%); color:#fff;
           border-radius:18px; padding:20px 28px; display:flex; align-items:center; gap:20px;
           box-shadow:0 10px 30px rgba(26,39,68,.28); position:relative; overflow:hidden; }}
  .hero::after {{ content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px;
                  border-radius:50%; background:rgba(255,255,255,.07); }}
  .hero img {{ height:62px; background:#fff; border-radius:12px; padding:6px; }}
  .hero-title {{ font-size:26px; font-weight:800; letter-spacing:.2px; }}
  .hero-sub {{ font-size:13px; opacity:.8; margin-top:2px; }}
  .hero-period {{ margin-left:auto; text-align:right; z-index:1; }}
  .hero-period .k {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; opacity:.7; }}
  .hero-period .v {{ font-size:20px; font-weight:700; background:rgba(255,255,255,.15);
                     padding:4px 14px; border-radius:20px; margin-top:4px; display:inline-block; }}

  /* Section titles */
  .sec {{ display:flex; align-items:center; gap:10px; margin:30px 0 12px; font-size:19px;
          font-weight:800; color:{NAVY}; }}
  .sec::before {{ content:""; width:6px; height:24px; border-radius:3px;
                  background:linear-gradient(180deg,{BLU},{RED}); }}

  /* KPI cards */
  .kpi {{ background:#fff; border-radius:14px; padding:16px 20px; border-top:5px solid var(--c);
          box-shadow:0 4px 14px rgba(15,23,42,.07); height:100%; }}
  .kpi .k {{ font-size:12px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:.05em; }}
  .kpi .v {{ font-size:38px; font-weight:800; color:var(--c); line-height:1.15; }}
  .kpi .i {{ float:right; font-size:26px; opacity:.85; }}

  /* Event cards */
  .acc-card {{ background:#fff; border-radius:14px; padding:16px 18px; margin-bottom:16px;
               border-left:7px solid {BLU}; color:#1E293B; box-shadow:0 4px 14px rgba(15,23,42,.08); }}
  .acc-card.red {{ border-left-color:{RED}; background:linear-gradient(90deg,#FEF2F2 0,#fff 140px); }}
  .acc-card.ora {{ border-left-color:{ORA}; background:linear-gradient(90deg,#FFF7ED 0,#fff 140px); }}
  .acc-card.blu {{ background:linear-gradient(90deg,#EFF6FF 0,#fff 140px); }}
  .acc-top {{ display:flex; justify-content:space-between; gap:8px; align-items:flex-start; }}
  .acc-loc {{ font-weight:800; font-size:15px; color:{NAVY}; }}
  .acc-date {{ font-size:12px; color:#64748B; }}
  .badge {{ font-size:12px; font-weight:700; padding:4px 12px; border-radius:20px; white-space:nowrap;
            background:{BLU}; color:#fff; }}
  .red .badge {{ background:{RED}; }}
  .ora .badge {{ background:{ORA}; }}
  .lbl {{ font-size:11px; font-weight:800; color:#64748B; text-transform:uppercase;
          letter-spacing:.07em; margin-top:12px; }}
  .txt {{ font-size:14px; line-height:1.55; }}
  .acc-card a {{ color:{BLU}; text-decoration:none; font-size:13px; font-weight:600; }}

  .ai-box {{ background:#fff; border-radius:14px; padding:18px 22px; margin-top:12px; line-height:1.75;
             border-left:6px solid {BLU}; box-shadow:0 4px 14px rgba(15,23,42,.08); color:#1E293B; }}

  /* Widgets */
  div[data-testid="stDataFrame"] {{ border-radius:14px; overflow:hidden;
                                    box-shadow:0 4px 14px rgba(15,23,42,.07); }}
  div[data-testid="stDeckGlJsonChart"] {{ border-radius:14px; overflow:hidden;
                                          box-shadow:0 4px 14px rgba(15,23,42,.1); }}
  div[data-testid="stAlert"] {{ border-radius:12px; }}
  .stButton > button {{ background:linear-gradient(120deg,{NAVY},{BLU}); color:#fff; border:0;
                        border-radius:10px; padding:.55rem 1.4rem; font-weight:700; }}
  .stButton > button:hover {{ filter:brightness(1.12); color:#fff; }}
  .legend span.d {{ display:inline-block; width:11px; height:11px; border-radius:50%; margin:0 5px 0 12px; }}
</style>
""", unsafe_allow_html=True)


def sec(title: str) -> None:
    st.markdown(f'<div class="sec">{escape(title)}</div>', unsafe_allow_html=True)


def kpi(col, label: str, value, color: str, icon: str) -> None:
    col.markdown(f'<div class="kpi" style="--c:{color}"><span class="i">{icon}</span>'
                 f'<div class="k">{escape(label)}</div><div class="v">{value}</div></div>',
                 unsafe_allow_html=True)


def th_date(d: date) -> str:
    return f"{d.day} {TH_MONTHS[d.month - 1]} {d.year + 543}"


def sev(f: int, i: int) -> str:
    return "red" if f > 0 else "ora" if i > 0 else "blu"


def sev_label(f: int, i: int) -> str:
    return f"เสียชีวิต {f} ราย" if f > 0 else f"บาดเจ็บ {i} ราย" if i > 0 else "ไม่มีผู้บาดเจ็บ"


def impact(f: int, i: int) -> str:
    if f > 0 and i > 0:
        return f"ผู้เสียชีวิต {f} ราย และผู้ได้รับบาดเจ็บ {i} ราย"
    if f > 0:
        return f"ผู้เสียชีวิต {f} ราย"
    if i > 0:
        return f"ผู้ได้รับบาดเจ็บ {i} ราย"
    return "ไม่มีผู้ได้รับบาดเจ็บหรือเสียชีวิต"


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or url[:40]).removeprefix("www.")
    except Exception:
        return url[:40]


@st.cache_data(ttl=300)
def load() -> pd.DataFrame:
    df = pd.DataFrame(json.loads(DATA_FILE.read_text(encoding="utf-8")))
    df["date"] = pd.to_datetime(df["date"])
    for c in ("fatalities", "injuries"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df.sort_values("date", ascending=False).reset_index(drop=True)


def secret(name: str, default: str = "") -> str:
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


def ai_summary(rows: pd.DataFrame, period: str) -> str:
    key = secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("ไม่พบ GEMINI_API_KEY (ตั้งค่าใน .streamlit/secrets.toml)")
    custom = secret("GEMINI_MODEL")
    models = [custom] if custom else ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    listing = "\n\n".join(
        f"เหตุการณ์ที่ {r.id}: {r.date:%Y-%m-%d} — {r.location}\nเหตุการณ์: {r.event}\n"
        f"ผลกระทบ: เสียชีวิต {r.fatalities} ราย บาดเจ็บ {r.injuries} ราย"
        for r in rows.itertuples())
    prompt = (
        "คุณเป็นผู้เชี่ยวชาญด้านความปลอดภัยในอุตสาหกรรม (Safety Engineer) ระดับอาวุโส\n\n"
        "กรุณาสรุปเหตุการณ์อุบัติเหตุอุตสาหกรรมรายใหญ่ทั่วโลกต่อไปนี้เป็นภาษาไทย 2-3 ย่อหน้า โดย:\n"
        "1. ระบุภาพรวมจำนวนเหตุการณ์ทั้งหมด ผู้เสียชีวิต และผู้บาดเจ็บ\n"
        "2. เน้นเหตุการณ์ที่มีความรุนแรงสูงสุด\n"
        "3. วิเคราะห์ประเภทอุบัติเหตุที่พบบ่อย (ระเบิด/ไฟไหม้/สารเคมี ฯลฯ)\n"
        "4. ระบุภูมิภาคหรือประเทศที่ได้รับผลกระทบมากที่สุด\n"
        "5. ใช้ภาษาทางการ เหมาะสำหรับรายงานความปลอดภัยระดับองค์กร\n\n"
        f"ช่วงเวลา: {period}\n"
        f"สถิติรวม: เหตุการณ์ทั้งหมด {len(rows)} ครั้ง ผู้เสียชีวิตรวม {rows.fatalities.sum()} ราย "
        f"ผู้บาดเจ็บรวม {rows.injuries.sum()} ราย\n\nรายละเอียดเหตุการณ์:\n{listing}")
    # Try each model in turn: a model may be retired (404), rate limited (429) or busy (503)
    r = None
    for model in models:
        for attempt in range(2):
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096}},
                timeout=90)
            if r.status_code != 503:
                break
            time.sleep(2)  # busy: retry once, then move to the next model
        if r.ok or r.status_code not in (404, 429, 500, 503):
            break
    if not r.ok:
        raise RuntimeError(f"Gemini API ตอบกลับผิดพลาด: {r.status_code} (ลองใหม่อีกครั้งในภายหลัง)")
    parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text:
        raise RuntimeError("ไม่สามารถรับข้อมูลสรุปจาก Gemini ได้")
    return text


GEMINI_MODELS = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.8-flash"]


def gemini_call(body: dict, key: str, models: list) -> dict:
    """POST to Gemini, trying each model in turn (404 retired / 429 limit / 5xx busy)."""
    r = None
    for model in models:
        for _ in range(2):
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=body, timeout=180)
            if r.status_code != 503:
                break
            time.sleep(2)
        if r.ok or r.status_code not in (404, 429, 500, 503):
            break
    if not r.ok:
        raise RuntimeError(f"Gemini API ตอบกลับผิดพลาด: {r.status_code} {r.text[:200]}")
    return r.json()


def parse_records(raw: str) -> list:
    """Extract the JSON array from a model reply (handles fences, citations, truncation)."""
    t = re.sub(r"```(?:json)?", "", raw)
    t = re.sub(r"\[cite:[^\]]*\]|\[cite_start\]|\[cite_end\]", "", t)
    start = t.find("[")
    if start == -1:
        return []
    chunk = t[start:]
    end = chunk.rfind("]")
    for candidate in ([chunk[:end + 1]] if end != -1 else []) + \
                     ([chunk[:chunk.rfind("},") + 1] + "]"] if "}," in chunk else []):
        try:
            data = json.loads(candidate)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            continue
    return []


def fetch_new_records(date_from: date, date_to: date) -> list:
    key = secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("ไม่พบ GEMINI_API_KEY (ตั้งค่าใน .streamlit/secrets.toml)")
    prompt = f"""You are a data extraction assistant. Search the web for major industrial accidents \
(explosions, fires, chemical leaks, structural collapses at factories, plants, refineries, mines, or warehouses) \
that occurred worldwide between {date_from} and {date_to}.

CRITICAL RULES:
- Return ONLY a raw JSON array. No markdown, no code fences, no explanation text.
- Do NOT include any citation markers, [cite:], [1], footnotes, or reference annotations anywhere inside the JSON.
- All string values must be plain text with no special markers.

Each element must have exactly these fields:
{{
  "date": "YYYY-MM-DD",
  "location": "Site/City, Country",
  "country": "English country name",
  "lat": <decimal number>,
  "lng": <decimal number>,
  "event": "<2-3 sentence Thai description of what happened and the cause if known>",
  "fatalities": <integer, 0 if unknown>,
  "injuries": <integer, 0 if unknown>,
  "reference": "<direct URL to a reliable news source>"
}}

Include only confirmed events with a verifiable news source URL. Return [] if none found."""
    custom = secret("GEMINI_MODEL")
    data = gemini_call({"contents": [{"parts": [{"text": prompt}]}],
                        "tools": [{"googleSearch": {}}],
                        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}},
                       key, [custom] if custom else GEMINI_MODELS)
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    seen, texts = set(), []
    for p in parts:  # skip thinking parts and identical duplicate chunks
        t = p.get("text", "")
        if p.get("thought") or t in seen:
            continue
        seen.add(t)
        texts.append(t)
    return parse_records("".join(texts))


def valid_record(r: dict) -> bool:
    try:
        date.fromisoformat(str(r["date"]))
        float(r["lat"]), float(r["lng"])
        return bool(r.get("location")) and str(r.get("reference", "")).startswith("http")
    except (KeyError, ValueError, TypeError):
        return False


def merge_records(existing: list, new: list) -> list:
    """Add records not already present (same date + location); assign sequential ids."""
    keys = {f'{a["date"]}|{a["location"]}' for a in existing}
    next_id = max((a.get("id", 0) for a in existing), default=0) + 1
    added = []
    for r in new:
        if not valid_record(r):
            continue
        k = f'{r["date"]}|{r["location"]}'
        if k in keys:
            continue
        keys.add(k)
        added.append({"id": next_id, "date": str(r["date"]), "location": str(r["location"]),
                      "country": str(r.get("country", "")), "lat": float(r["lat"]), "lng": float(r["lng"]),
                      "event": str(r.get("event", "")),
                      "fatalities": int(r.get("fatalities") or 0), "injuries": int(r.get("injuries") or 0),
                      "reference": str(r["reference"])})
        next_id += 1
    return added


def github_cfg():
    """(token, repo, branch) when GitHub saving is configured, else None."""
    token, repo = secret("GITHUB_TOKEN"), secret("GITHUB_REPO")
    if not (token and repo):
        return None
    return token, repo, secret("GITHUB_BRANCH", "main")


def _gh(cfg):
    token, repo, branch = cfg
    url = f"https://api.github.com/repos/{repo}/contents/data/accidents.json"
    hdr = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json",
           "User-Agent": "accident-events-streamlit"}
    return url, hdr, branch


def read_current(cfg):
    """Return (records, sha). With GitHub configured, GitHub is the source of truth, so
    a stale local copy (e.g. after the Vercel cron committed) never overwrites newer data."""
    if cfg is None:
        return json.loads(DATA_FILE.read_text(encoding="utf-8")), None
    url, hdr, branch = _gh(cfg)
    r = requests.get(url, headers=hdr, params={"ref": branch}, timeout=30)
    if not r.ok:
        raise RuntimeError(f"อ่านข้อมูลจาก GitHub ไม่สำเร็จ: {r.status_code} (ตรวจสอบ GITHUB_TOKEN / GITHUB_REPO)")
    j = r.json()
    return json.loads(base64.b64decode(j["content"]).decode("utf-8")), j["sha"]


def save_records(records: list, cfg, sha) -> str:
    """Write data/accidents.json locally (shown immediately), then commit it to GitHub if configured."""
    records = sorted(records, key=lambda a: a["date"], reverse=True)
    text = json.dumps(records, ensure_ascii=False, indent=2)
    try:
        DATA_FILE.write_text(text, encoding="utf-8")
    except OSError:
        if cfg is None:
            raise
    if cfg is None:
        return "บันทึกลงไฟล์ในเครื่องแล้ว (ยังไม่ได้ส่งขึ้น GitHub)"
    url, hdr, branch = _gh(cfg)
    put = requests.put(url, headers=hdr, timeout=30, json={
        "message": "chore: update accidents data from Streamlit app",
        "content": base64.b64encode(text.encode("utf-8")).decode(), "sha": sha, "branch": branch})
    if put.status_code == 409:
        raise RuntimeError("มีการอัปเดตข้อมูลซ้อนกัน กรุณากดอัปเดตอีกครั้ง")
    if not put.ok:
        raise RuntimeError(f"commit ไป GitHub ไม่สำเร็จ: {put.status_code} {put.text[:150]} "
                           "(token ต้องมีสิทธิ์ Contents: write)")
    return "บันทึกและ commit ไปที่ GitHub แล้ว (Streamlit Cloud จะ deploy ข้อมูลใหม่อัตโนมัติ)"


df = load()
today = date.today()

# ---- Header ----
logo_b64 = base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""
logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="logo">' if logo_b64 else ""
st.markdown(f"""
<div class="hero">
  {logo_img}
  <div><div class="hero-title">รายงานอุบัติเหตุอุตสาหกรรมโลก</div>
       <div class="hero-sub">Global Major Industrial Accident Report · ปี {today.year + 543} ({today.year})</div></div>
  <div class="hero-period"><div class="k">เดือนปัจจุบัน</div>
       <div class="v">{TH_MONTHS[today.month - 1]} {today.year + 543}</div></div>
</div>
""", unsafe_allow_html=True)
st.write("")

# ---- Update data (search the web with Gemini + Google Search, merge into accidents.json) ----
sec("อัปเดตข้อมูลล่าสุด")
u1, u2 = st.columns([1, 3], vertical_alignment="bottom")
days = u1.number_input("ค้นหาย้อนหลัง (วัน)", 1, 60, 7)
password = secret("UPDATE_PASSWORD")
if password:
    entered = u2.text_input("รหัสผ่านสำหรับอัปเดตข้อมูล", type="password")
allowed = (not password) or entered == password
if st.button("🔄 อัปเดตข้อมูลล่าสุด", disabled=not allowed):
    with st.spinner("กำลังค้นหาข่าวอุบัติเหตุล่าสุดด้วย AI (อาจใช้เวลา 20-60 วินาที)..."):
        try:
            found = fetch_new_records(date.today() - timedelta(days=int(days)), date.today())
            cfg = github_cfg()
            current, sha = read_current(cfg)
            added = merge_records(current, found)
            if added:
                msg = save_records(current + added, cfg, sha)
                load.clear()
                st.success(f"เพิ่มข้อมูลใหม่ {len(added)} รายการ · {msg}")
                st.dataframe(pd.DataFrame(added)[["date", "location", "fatalities", "injuries", "reference"]],
                             hide_index=True, width="stretch")
                st.caption("กดรีเฟรชหน้า (R) เพื่อดูข้อมูลล่าสุดในแผนที่และตาราง")
            else:
                st.info(f"ค้นหาแล้วพบ {len(found)} รายการ แต่ไม่มีเหตุการณ์ใหม่ที่ยังไม่อยู่ในระบบ")
        except Exception as e:
            st.error(str(e))
if github_cfg() is None:
    st.caption("⚠️ ยังไม่ได้ตั้งค่า GITHUB_TOKEN / GITHUB_REPO: ข้อมูลที่อัปเดตจะบันทึกในเครื่องเท่านั้น "
               "และจะหายเมื่อแอปบน Streamlit Cloud รีสตาร์ท")
if password and not allowed:
    st.caption("กรอกรหัสผ่านให้ถูกต้องเพื่อเปิดใช้งานปุ่มอัปเดต")

# ---- Month selection (drives stats, map, cards) ----
months = sorted({(d.year, d.month) for d in df["date"]}, reverse=True)
if (today.year, today.month) not in months:
    months.insert(0, (today.year, today.month))
month_label = lambda ym: "ทั้งหมด" if ym is None else f"{TH_MONTHS[ym[1] - 1]} {ym[0] + 543}"
sel = st.selectbox("เลือกเดือน", [None] + months, index=0, format_func=month_label)  # None = all months
in_month = df if sel is None else df[(df["date"].dt.year == sel[0]) & (df["date"].dt.month == sel[1])]
period = month_label(sel)

m1, m2, m3 = st.columns(3)
kpi(m1, "จำนวนเหตุการณ์ทั้งหมด" if sel is None else "จำนวนเหตุการณ์เดือนนี้", len(in_month), BLU, "🏭")
kpi(m2, "ผู้เสียชีวิต (ราย)", int(in_month.fatalities.sum()), RED, "⚠️")
kpi(m3, "ผู้บาดเจ็บ (ราย)", int(in_month.injuries.sum()), ORA, "🩹")

# ---- Map ----
sec("แผนที่เหตุการณ์ทั่วโลก")
mp = in_month.copy()
if mp.empty:
    st.info("ไม่มีเหตุการณ์ที่จะแสดงบนแผนที่")
else:
    palette = {"red": [220, 38, 38], "ora": [234, 88, 12], "blu": [37, 99, 235]}
    mp["color"] = [palette[sev(f, i)] for f, i in zip(mp.fatalities, mp.injuries)]
    mp["date_th"] = [th_date(d.date()) for d in mp["date"]]
    mp["impact"] = [impact(f, i) for f, i in zip(mp.fatalities, mp.injuries)]
    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(latitude=25, longitude=20, zoom=1),
        layers=[pdk.Layer("ScatterplotLayer",
                          data=mp[["lat", "lng", "color", "location", "date_th", "impact"]],
                          get_position="[lng, lat]", get_fill_color="color", get_radius=180000,
                          radius_min_pixels=7, radius_max_pixels=18, pickable=True, opacity=0.85)],
        tooltip={"html": "<b>{location}</b><br/>{date_th}<br/>{impact}"}))
    st.markdown(f'<div class="legend"><span class="d" style="background:{RED}"></span>มีผู้เสียชีวิต'
                f'<span class="d" style="background:{ORA}"></span>มีผู้บาดเจ็บ'
                f'<span class="d" style="background:{BLU}"></span>ไม่มีผู้บาดเจ็บ</div>',
                unsafe_allow_html=True)

# ---- Monthly summary table + chart (selected year) ----
yr = int(df["date"].dt.year.max()) if sel is None else sel[0]  # all months: show the latest year
sec(f"สรุปรายเดือน ปี {yr + 543} (มกราคม – ธันวาคม)")
ydf = df[df["date"].dt.year == yr]
rows = []
for mi in range(12):
    s = ydf[ydf["date"].dt.month == mi + 1]
    rows.append({"เดือน": TH_MONTHS[mi], "จำนวนเหตุการณ์": len(s),
                 "ผู้เสียชีวิต (ราย)": int(s.fatalities.sum()), "ผู้บาดเจ็บ (ราย)": int(s.injuries.sum())})
tbl = pd.DataFrame(rows)
st.dataframe(tbl, hide_index=True, width="stretch")
t1, t2, t3 = st.columns(3)
kpi(t1, "รวมเหตุการณ์", int(tbl["จำนวนเหตุการณ์"].sum()), BLU, "📊")
kpi(t2, "รวมเสียชีวิต", int(tbl["ผู้เสียชีวิต (ราย)"].sum()), RED, "⚠️")
kpi(t3, "รวมบาดเจ็บ", int(tbl["ผู้บาดเจ็บ (ราย)"].sum()), ORA, "🩹")

sec("กราฟสถิติรายเดือน")
have = tbl[tbl["จำนวนเหตุการณ์"] > 0].copy()
if have.empty:
    st.info("ยังไม่มีข้อมูลในปีนี้")
else:
    have["ord"] = [TH_MONTHS.index(m) for m in have["เดือน"]]
    have["m"] = [TH_MONTHS_SHORT[o] for o in have["ord"]]
    long = have.melt(id_vars=["m", "ord"],
                     value_vars=["จำนวนเหตุการณ์", "ผู้เสียชีวิต (ราย)", "ผู้บาดเจ็บ (ราย)"],
                     var_name="ประเภท", value_name="จำนวน")
    st.altair_chart(
        alt.Chart(long).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("m:N", sort=alt.EncodingSortField("ord"), title=None),
            xOffset="ประเภท:N", y=alt.Y("จำนวน:Q", title=None),
            color=alt.Color("ประเภท:N", scale=alt.Scale(
                domain=["จำนวนเหตุการณ์", "ผู้เสียชีวิต (ราย)", "ผู้บาดเจ็บ (ราย)"],
                range=[BLU, RED, ORA]), legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["m", "ประเภท", "จำนวน"]).properties(height=320),
        width="stretch")

# ---- Cards ----
sec(f"รายละเอียดเหตุการณ์ · {period}")
if in_month.empty:
    st.info("📭 ไม่มีเหตุการณ์ที่บันทึกไว้ในเดือนนี้")
else:
    pages = -(-len(in_month) // CARDS_PER_PAGE)
    page = st.number_input("หน้า", 1, pages, 1) if pages > 1 else 1
    chunk = in_month.iloc[(page - 1) * CARDS_PER_PAGE: page * CARDS_PER_PAGE]
    cols = st.columns(2)
    for n, r in enumerate(chunk.itertuples()):
        ref = escape(str(r.reference), quote=True)
        cols[n % 2].markdown(f"""
<div class="acc-card {sev(r.fatalities, r.injuries)}">
  <div class="acc-top">
    <div><div class="acc-loc">#{r.id} {escape(r.location)}</div>
         <div class="acc-date">{th_date(r.date.date())}</div></div>
    <div class="badge">{sev_label(r.fatalities, r.injuries)}</div>
  </div>
  <div class="lbl">เหตุการณ์</div><div class="txt">{escape(r.event)}</div>
  <div class="lbl">ผลกระทบ</div><div class="txt">{impact(r.fatalities, r.injuries)}</div>
  <div class="lbl">อ้างอิง</div><a href="{ref}" target="_blank" rel="noopener noreferrer">↗ {escape(host(str(r.reference)))}</a>
</div>""", unsafe_allow_html=True)

# ---- AI summary (button is always visible; disabled when the month has no events) ----
sec("สรุปด้วย AI")
summary_key = f"summary-{sel}"
if st.button("✨ สร้างบทสรุปด้วย AI", disabled=in_month.empty,
             help="ต้องมีเหตุการณ์ในเดือนที่เลือกอย่างน้อย 1 รายการ" if in_month.empty else None):
    with st.spinner("กำลังสรุปด้วย AI..."):
        try:
            st.session_state[summary_key] = ai_summary(in_month, period)
        except Exception as e:  # show a friendly error instead of a traceback
            st.session_state.pop(summary_key, None)
            st.error(str(e))
if in_month.empty:
    st.caption("เดือนนี้ยังไม่มีเหตุการณ์ให้สรุป ลองเลือกเดือนอื่นหรือ \"ทั้งหมด\"")
if summary_key in st.session_state:
    st.markdown(f'<div class="ai-box">{escape(st.session_state[summary_key]).replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True)
