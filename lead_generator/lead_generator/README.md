# AI Lead Generator

Finds early-stage UK AI startups via the Companies House API, then scores each for fit using Claude — built for a Fractional AI Product & Delivery Lead prospecting workflow.

## Setup & deployment

### Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Community Cloud

1. Push this folder to a GitHub repo (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**
3. Point to the repo, branch `main`, file `app.py`
4. Deploy — no secrets needed (API keys are entered in the sidebar at runtime)

## Usage

1. Enter your **Companies House API key** — free from [developer.company-information.service.gov.uk](https://developer.company-information.service.gov.uk)
2. Enter your **Anthropic API key** — from [console.anthropic.com](https://console.anthropic.com)
3. Set filters (industry focus, max company age, optional keyword)
4. Click **Find leads**

Results are scored 0–100 and split across tabs: Strong fit (70+), Worth exploring (40–69), Low fit.

## How it works

- Searches Companies House Advanced Search across 7 default keywords (AI, machine learning, computer vision, retail tech, ecommerce, automation, vision) plus any custom keyword you add
- Filters results by SIC code and company name for AI/ML/retail relevance
- Scores each company against the contractor profile using `claude-sonnet-4-20250514`
- Ranks and displays results with fit rationale, tags, age, address, and direct links to Companies House + LinkedIn
