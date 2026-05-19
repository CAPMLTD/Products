# 🛡️ EU AI Act Model Card Generator

A comprehensive, Claude-powered model card generator built for EU AI Act compliance. Covers Articles 9, 10, 11, 13, 14, 15 and 62.

Built by **CA Project Management Services Ltd**.

---

## Features

- **Risk Classification Wizard** — guided tier determination (Unacceptable / High / Limited / Minimal Risk)
- **Dynamic form** — fields adapt based on risk tier; High Risk surfaces all mandatory Article obligations
- **Claude-generated narrative** — structured, professional model card with compliance gap analysis
- **Three export formats** — Markdown, HTML, Word (.docx)
- **Completeness score** — real-time coverage indicator before generation

## EU AI Act Coverage

| Article | Obligation | Covered |
|---------|-----------|---------|
| Art. 5  | Prohibited practices | ✅ Risk wizard |
| Art. 9  | Risk management system | ✅ Post-market monitoring |
| Art. 10 | Data governance | ✅ Training data + governance section |
| Art. 11 / Annex IV | Technical documentation | ✅ Full model description |
| Art. 13 | Transparency & information | ✅ Deployment context + limitations |
| Art. 14 | Human oversight | ✅ Dedicated section |
| Art. 15 | Accuracy, robustness, cybersecurity | ✅ Performance + robustness section |
| Art. 43 | Conformity assessment | ✅ Assessment type + CE marking |
| Art. 62 | Incident reporting | ✅ Dedicated section |

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
set ANTHROPIC_API_KEY=your-key-here        # Windows
export ANTHROPIC_API_KEY=your-key-here     # Mac/Linux

# 4. Run
python -m streamlit run app.py
```

---

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your repo → set `app.py` as the main file
4. Under **Advanced settings → Secrets**, add:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

5. Click **Deploy** — your app will be live at `https://yourapp.streamlit.app`

---

## Linking from Your Website

Once deployed, add a button or link on your IONOS site pointing to your Streamlit URL. For a seamless embed, use an iframe:

```html
<iframe src="https://yourapp.streamlit.app?embed=true" 
        width="100%" height="900px" frameborder="0">
</iframe>
```

---

## ⚠️ API Key Security

- **Never** commit your API key to GitHub
- On Streamlit Cloud, always use the **Secrets** manager
- Locally, use environment variables or a `.env` file (excluded by `.gitignore`)

---

## Built With

- [Streamlit](https://streamlit.io)
- [Anthropic Claude API](https://www.anthropic.com)
- [python-docx](https://python-docx.readthedocs.io)

---

*CA Project Management Services Ltd — Fractional AI Product & Delivery*
