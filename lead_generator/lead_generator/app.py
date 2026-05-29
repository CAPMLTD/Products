import streamlit as st
import requests
import anthropic
import json
import csv
import io
from datetime import datetime, timedelta
from time import sleep

st.set_page_config(page_title="AI Lead Generator", page_icon="🎯", layout="wide")

st.markdown("""
<style>
    .score-high { background: #eaf3de; color: #3b6d11; border: 1px solid #639922; border-radius: 8px; padding: 4px 12px; font-weight: 600; font-size: 1.1em; }
    .score-mid  { background: #faeeda; color: #854f0b; border: 1px solid #ba7517; border-radius: 8px; padding: 4px 12px; font-weight: 600; font-size: 1.1em; }
    .score-low  { background: #fcebeb; color: #a32d2d; border: 1px solid #e24b4a; border-radius: 8px; padding: 4px 12px; font-weight: 600; font-size: 1.1em; }
    .tag { background: #f1efe8; color: #5f5e5a; border-radius: 6px; padding: 2px 8px; font-size: 0.8em; margin-right: 4px; }
    .company-card { border-left: 4px solid #639922; padding-left: 12px; }
    .company-card-mid { border-left: 4px solid #ba7517; padding-left: 12px; }
    .company-card-low { border-left: 4px solid #e24b4a; padding-left: 12px; }
</style>
""", unsafe_allow_html=True)

CH_BASE = "https://api.company-information.service.gov.uk"

AI_SIC_CODES = {
    "62012", "62020", "62090", "63110", "63120",
    "58290", "72190", "62011", "47910", "47990",
    "62010", "62030", "63990", "74909", "72110",
    "72200", "70229", "82990", "58210", "58190"
}
RETAIL_SIC_CODES = {
    "47190", "47910", "47990", "47410", "47610",
    "56302", "47710", "47210", "47110", "47910",
    "46900", "46690", "47910", "47990", "53202"
}
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "computer vision",
    "deep learning", "automation", "data analytics", "predictive",
    "generative", "llm", "nlp", "retail tech", "vision ai", "loss prevention",
    "data", "tech", "digital", "software", "platform", "smart", "intelligent",
    "analytics", "insight", "cloud", "saas", "neural", "robotics"
]

CONTRACTOR_PROFILE = """
Fractional AI Product & Delivery Lead with deep experience in:
- ML governance auditing, model cards, EU AI Act Article 11 compliance
- Computer vision / Vision AI product delivery (SeeChange Technologies)
- Retail & eCommerce technology (Klarna across 5 Estée Lauder brands — £300k incremental revenue in 3 months)
- Data platform programmes and delivery leadership (Walgreens Boots Alliance)
- Agile/PRINCE2 delivery in early-stage AI startups
- Stakeholder management at C-Suite / Board level
- Annotation quality frameworks, CRISP-DM, TDSP lifecycle governance
- Shopify headless, PIM implementations, payment integrations (Klarna, Adyen)
- Built EU AI Act Model Card Generator tool (Streamlit + Claude API)
Operates outside IR35 via CA Project Management Services Ltd at £850–950/day
Seeking early-stage UK AI product companies, especially Retail/eCommerce AI
"""

DEFAULT_KEYWORDS = [
    "AI", "machine learning", "computer vision",
    "retail tech", "ecommerce", "automation", "vision"
]


def build_date_from(years_back: int) -> str:
    d = datetime.now() - timedelta(days=years_back * 365)
    return d.strftime("%Y-%m-%d")


def search_companies(ch_api_key: str, keyword: str, from_date: str) -> list:
    params = {
        "company_name_includes": keyword,
        "company_status": "active",
        "incorporated_from": from_date,
        "size": "100",
    }
    try:
        resp = requests.get(
            f"{CH_BASE}/advanced-search/companies",
            params=params,
            auth=(ch_api_key, ""),
            timeout=15
        )
        if resp.status_code == 401:
            st.error("Companies House API key invalid or unauthorised. Please check your key.")
            return []
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])
    except requests.RequestException:
        return []


def is_relevant(company: dict) -> bool:
    name = (company.get("company_name") or "").lower()
    sics = set(company.get("sic_codes") or [])
    name_hit = any(kw in name for kw in AI_KEYWORDS)
    sic_hit = bool(sics & AI_SIC_CODES) or bool(sics & RETAIL_SIC_CODES)
    no_sic = len(sics) == 0
    return name_hit or sic_hit or no_sic


def score_company(anthropic_key: str, company: dict) -> dict:
    client = anthropic.Anthropic(api_key=anthropic_key)
    address = ", ".join(
        v for v in (company.get("registered_office_address") or {}).values()
        if v and isinstance(v, str)
    )
    prompt = f"""You are evaluating a UK company as a potential client for a Fractional AI Product & Delivery Lead.

CONTRACTOR PROFILE:
{CONTRACTOR_PROFILE}

COMPANY:
Name: {company.get('company_name')}
Incorporated: {company.get('date_of_creation')}
SIC codes: {', '.join(company.get('sic_codes') or [])}
Address: {address or 'UK'}

Score this company 0-100 for fit with the contractor's profile. Consider:
- AI/ML focus (high weight)
- Retail/eCommerce industry (medium weight)
- Early-stage startup needing fractional leadership (high weight)
- UK-based (required)
- Likely outside IR35 structure possible

Reply ONLY with valid JSON, no markdown:
{{"score": <number>, "reason": "<2 sentences>", "tags": ["<tag1>","<tag2>","<tag3>"], "fit_summary": "<one punchy line>"}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        st.warning(f"Scoring error for {company.get('company_name')}: {str(e)}")
        return {"score": 0, "reason": f"Error: {str(e)}", "tags": [], "fit_summary": ""}


def company_age_label(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        years = (datetime.now() - datetime.strptime(date_str, "%Y-%m-%d")).days / 365
        if years < 1:
            return "< 1 yr old"
        return f"{int(years)} yr{'s' if int(years) != 1 else ''} old"
    except Exception as e:
        return ""




def build_csv(scored: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Rank", "Score", "Company Name", "Fit Summary", "AI Reason",
        "Tags", "Incorporated", "Age", "Company Number",
        "Address", "SIC Codes", "Companies House URL", "LinkedIn URL"
    ])
    for i, s in enumerate(scored):
        c = s["company"]
        ai = s["ai"]
        address = ", ".join(
            v for v in (c.get("registered_office_address") or {}).values()
            if v and isinstance(v, str)
        )
        ch_url = f"https://find-and-update.company-information.service.gov.uk/company/{c.get('company_number')}"
        li_url = f"https://www.linkedin.com/search/results/companies/?keywords={c.get('company_name','')}"
        writer.writerow([
            i + 1,
            ai.get("score", 0),
            c.get("company_name", ""),
            ai.get("fit_summary", ""),
            ai.get("reason", ""),
            ", ".join(ai.get("tags", [])),
            c.get("date_of_creation", ""),
            company_age_label(c.get("date_of_creation", "")),
            c.get("company_number", ""),
            address,
            ", ".join(c.get("sic_codes") or []),
            ch_url,
            li_url,
        ])
    return output.getvalue()

def render_result(i: int, company: dict, ai: dict):
    score = ai.get("score", 0)
    if score >= 70:
        card_class = "company-card"
        score_class = "score-high"
    elif score >= 40:
        card_class = "company-card-mid"
        score_class = "score-mid"
    else:
        card_class = "company-card-low"
        score_class = "score-low"

    ch_url = f"https://find-and-update.company-information.service.gov.uk/company/{company.get('company_number')}"
    li_url = f"https://www.linkedin.com/search/results/companies/?keywords={requests.utils.quote(company.get('company_name', ''))}"
    age = company_age_label(company.get("date_of_creation", ""))
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in ai.get("tags", []))

    with st.container():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
<div class="{card_class}">
  <strong>#{i+1} <a href="{ch_url}" target="_blank">{company.get('company_name')}</a></strong>
  {"&nbsp;&nbsp;<small style='color:#888'>"+age+"</small>" if age else ""}
  <br><em style="color:#5f5e5a; font-size:0.9em">{ai.get('fit_summary','')}</em>
  <br>{tags_html}
</div>
""", unsafe_allow_html=True)
        with col2:
            st.markdown(f'<span class="{score_class}">{score}</span>', unsafe_allow_html=True)

        with st.expander("Details"):
            st.markdown(f"**AI fit analysis:** {ai.get('reason','')}")
            addr = ", ".join(
                v for v in (company.get("registered_office_address") or {}).values()
                if v and isinstance(v, str)
            )
            st.markdown(f"**Address:** {addr or '—'}")
            st.markdown(f"**Incorporated:** {company.get('date_of_creation','—')}  |  **Company no:** `{company.get('company_number','')}`")
            sics = company.get("sic_codes") or []
            if sics:
                st.markdown(f"**SIC codes:** `{'`, `'.join(sics)}`")
            st.markdown(f"[View on Companies House]({ch_url}) &nbsp;|&nbsp; [Find on LinkedIn]({li_url})", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🎯 Lead Generator")
    st.caption("Fractional AI Product & Delivery Lead — UK startup prospecting")
    st.divider()

    ch_key = st.text_input("Companies House API key", type="password", help="From developer.company-information.service.gov.uk")
    anthropic_key = st.text_input("Anthropic API key", type="password", help="From console.anthropic.com")
    st.divider()

    industry = st.selectbox("Industry focus", ["All (AI + Retail)", "AI / Tech only", "Retail / eCommerce only"])
    max_age = st.slider("Max company age (years)", 1, 10, 5)
    extra_kw = st.text_input("Additional keyword (optional)", placeholder="e.g. loss prevention, shrink…")
    st.divider()
    run = st.button("🔍 Find leads", use_container_width=True, type="primary")


# ── Main ─────────────────────────────────────────────────────────────────────

st.title("AI Startup Lead Generator")
st.caption("Finds early-stage UK AI companies on Companies House, then scores each for fit using Claude")

if run:
    if not ch_key or not anthropic_key:
        st.error("Please enter both API keys in the sidebar.")
        st.stop()

    # Test Anthropic key first
    try:
        test_client = anthropic.Anthropic(api_key=anthropic_key)
        test_client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=10, messages=[{"role": "user", "content": "hi"}])
    except Exception as e:
        st.error(f"Anthropic API key error: {str(e)}")
        st.stop()

    from_date = build_date_from(max_age)
    kw_list = ([extra_kw] if extra_kw.strip() else []) + DEFAULT_KEYWORDS

    # ── Phase 1: fetch ──────────────────────────────────────────────────────
    progress = st.progress(0, text="Searching Companies House…")
    all_companies = []
    seen = set()

    for idx, kw in enumerate(kw_list):
        progress.progress(int((idx / len(kw_list)) * 40), text=f'Searching for "{kw}"…')
        results = search_companies(ch_key, kw, from_date)
        for c in results:
            if c.get("company_number") not in seen and c.get("company_status") == "active":
                seen.add(c["company_number"])
                all_companies.append(c)
        sleep(0.3)

    # ── Phase 2: filter ─────────────────────────────────────────────────────
    progress.progress(45, text="Filtering for AI / retail relevance…")
    filtered = [c for c in all_companies if is_relevant(c)]

    if not filtered:
        st.warning("No matching companies found. Try adjusting the filters or keyword.")
        st.stop()

    to_score = filtered[:30]

    # ── Phase 3: score ──────────────────────────────────────────────────────
    scored = []
    for idx, company in enumerate(to_score):
        pct = 45 + int((idx / len(to_score)) * 55)
        progress.progress(pct, text=f"Scoring {company.get('company_name')} ({idx+1}/{len(to_score)})…")
        ai_result = score_company(anthropic_key, company)
        scored.append({"company": company, "ai": ai_result})

    progress.progress(100, text="Done!")
    progress.empty()

    scored.sort(key=lambda x: x["ai"].get("score", 0), reverse=True)

    # ── Summary metrics ─────────────────────────────────────────────────────
    top = sum(1 for s in scored if s["ai"].get("score", 0) >= 70)
    mid = sum(1 for s in scored if 40 <= s["ai"].get("score", 0) < 70)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Companies searched", len(all_companies))
    m2.metric("After relevance filter", len(filtered))
    m3.metric("Strong fit (70+)", top)
    m4.metric("Worth exploring (40–69)", mid)


    # ── CSV Export ───────────────────────────────────────────────────────────
    csv_data = build_csv(scored)
    st.download_button(
        label="⬇️ Download results as CSV",
        data=csv_data,
        file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    st.divider()

    # ── Results ─────────────────────────────────────────────────────────────
    tabs = st.tabs(["🟢 Strong fit (70+)", "🟡 Worth exploring (40–69)", "🔴 Low fit (< 40)", "📋 All results"])

    strong = [s for s in scored if s["ai"].get("score", 0) >= 70]
    medium = [s for s in scored if 40 <= s["ai"].get("score", 0) < 70]
    low    = [s for s in scored if s["ai"].get("score", 0) < 40]

    with tabs[0]:
        if strong:
            for i, s in enumerate(strong):
                render_result(i, s["company"], s["ai"])
        else:
            st.info("No strong-fit companies found in this search. Try broadening the filters.")

    with tabs[1]:
        for i, s in enumerate(medium):
            render_result(i, s["company"], s["ai"])

    with tabs[2]:
        for i, s in enumerate(low):
            render_result(i, s["company"], s["ai"])

    with tabs[3]:
        for i, s in enumerate(scored):
            render_result(i, s["company"], s["ai"])

elif not run:
    st.info("Enter your API keys in the sidebar and click **Find leads** to start.")
    with st.expander("What does this tool do?"):
        st.markdown("""
This tool finds early-stage UK AI companies that are a strong fit for a **Fractional AI Product & Delivery Lead** engagement.

**How it works:**
1. Searches Companies House Advanced Search API across multiple AI/retail keywords
2. Filters results by SIC code and company name for AI/ML/retail relevance
3. Scores each company 0–100 using Claude, against the contractor's specific profile
4. Ranks and tabulates results with fit rationale, tags, and direct links

**What you need:**
- A free Companies House API key from [developer.company-information.service.gov.uk](https://developer.company-information.service.gov.uk)
- An Anthropic API key from [console.anthropic.com](https://console.anthropic.com)
""")
