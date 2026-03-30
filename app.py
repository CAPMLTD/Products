import io
import os
import re

import anthropic
import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Model Card Generator",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    .section-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        color: #e2e8f0;
        padding: 0.6rem 1rem;
        border-radius: 6px;
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
        border-left: 4px solid #4f8ef7;
    }
    .stTextArea textarea { font-size: 0.9rem; }
    div[data-testid="stExpander"] { border: 1px solid #2d3748; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert AI documentation specialist who produces rigorously structured model cards following industry best practices (Google Model Cards, Hugging Face model cards, and the ACM FAccT model card framework).

## Model Card Best Practice Standards

A high-quality model card MUST include:

1. **Model Details** – name, version, type/architecture, developers, release date, license, contact.
2. **Intended Use** – primary intended uses, intended users, out-of-scope uses.
3. **Training Data** – data sources, preprocessing steps, demographic breakdown, known biases.
4. **Evaluation Data & Metrics** – datasets used for evaluation, metrics chosen, justification.
5. **Performance** – quantitative results per metric, disaggregated evaluation across subgroups where possible.
6. **Known Limitations & Biases** – technical limitations, ethical considerations, fairness analysis.
7. **Deployment Context** – recommended hardware/software, latency expectations, integration notes.
8. **Ethical Considerations** – potential harms, mitigation strategies, human oversight recommendations.
9. **Recommendations** – guidance for users/deployers, red-teaming notes, monitoring advice.
10. **References & Acknowledgements** – related papers, datasets, funding.

## Formatting Guidelines

- Use clear Markdown with `##` section headings matching the ten sections above.
- Under each heading use bullet lists, numbered lists, or short paragraphs as appropriate.
- Use **bold** for key terms and `inline code` for technical identifiers (model IDs, metric names).
- For performance tables use Markdown table syntax.
- Be precise, neutral in tone, and flag missing information explicitly with *[Information not provided – recommend supplying before deployment]* rather than fabricating values.
- End with a "Last Updated" line using the ISO-8601 format.

Produce ONLY the model card Markdown—no preamble, no closing commentary."""


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def build_user_message(fields: dict) -> str:
    """Assemble the structured user message from form fields."""
    return f"""Please generate a complete, industry-standard model card from the following information provided by the model developer.

---
## 1. Model Description

**Model name:** {fields['model_name']}
**Version:** {fields['model_version']}
**Model type / architecture:** {fields['model_type']}
**Developers / Organization:** {fields['developers']}
**Release date:** {fields['release_date']}
**License:** {fields['license']}
**Contact:** {fields['contact']}
**Description:**
{fields['model_description']}

---
## 2. Training Data Characteristics

**Data sources:**
{fields['data_sources']}

**Data size / volume:** {fields['data_volume']}
**Date range of data:** {fields['data_date_range']}
**Preprocessing / cleaning steps:**
{fields['preprocessing']}

**Known data biases or gaps:**
{fields['data_biases']}

**Demographic representation notes:**
{fields['demographic_notes']}

---
## 3. Performance Metrics

**Evaluation datasets:**
{fields['eval_datasets']}

**Metrics used:** {fields['metrics_used']}
**Results summary:**
{fields['results_summary']}

**Disaggregated evaluation (subgroups):**
{fields['disaggregated_eval']}

**Benchmark comparisons:**
{fields['benchmarks']}

---
## 4. Known Limitations

**Technical limitations:**
{fields['technical_limitations']}

**Fairness / bias concerns:**
{fields['fairness_concerns']}

**Failure modes:**
{fields['failure_modes']}

**Conditions under which performance degrades:**
{fields['degradation_conditions']}

---
## 5. Intended Deployment Context

**Primary use cases:**
{fields['primary_use_cases']}

**Intended users / audience:**
{fields['intended_users']}

**Recommended deployment environment:**
{fields['deployment_env']}

**Human oversight requirements:**
{fields['human_oversight']}

**Regulatory / compliance notes:**
{fields['compliance_notes']}

---
## 6. Out-of-Scope Uses

**Explicitly out-of-scope uses:**
{fields['oos_uses']}

**Potential misuse scenarios:**
{fields['misuse_scenarios']}

**Prohibited use cases:**
{fields['prohibited_uses']}

---
Additional notes from developer:
{fields['additional_notes']}
---

Generate the complete model card now."""


def add_heading_style(doc: Document, text: str, level: int) -> None:
    """Add a heading with custom style."""
    para = doc.add_heading(text, level=level)
    run = para.runs[0] if para.runs else para.add_run(text)
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E) if level == 1 else RGBColor(0x2D, 0x3A, 0x6B)
    run.font.bold = True


def set_cell_background(cell, fill_color: str) -> None:
    """Set table cell background color."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_color)
    tcPr.append(shd)


def markdown_to_docx(markdown_text: str) -> bytes:
    """Convert markdown model card text to a formatted Word document."""
    doc = Document()

    # ── Document title ──
    title = doc.add_heading("Model Card", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
        run.font.size = Pt(24)

    doc.add_paragraph()  # spacer

    lines = markdown_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # ── Headings ──
        if line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)

        # ── Markdown table ──
        elif line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            # Collect table rows
            header_row = [c.strip() for c in line.strip("|").split("|")]
            i += 1  # skip separator
            data_rows = []
            while i + 1 < len(lines) and lines[i + 1].startswith("|"):
                i += 1
                data_rows.append([c.strip() for c in lines[i].strip("|").split("|")])

            cols = max(len(header_row), max((len(r) for r in data_rows), default=0))
            tbl = doc.add_table(rows=1 + len(data_rows), cols=cols)
            tbl.style = "Table Grid"

            # Header row
            for j, cell_text in enumerate(header_row[:cols]):
                cell = tbl.cell(0, j)
                cell.text = cell_text
                set_cell_background(cell, "2D3A6B")
                for run in cell.paragraphs[0].runs:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

            # Data rows
            for r_idx, row_data in enumerate(data_rows):
                for j, cell_text in enumerate(row_data[:cols]):
                    cell = tbl.cell(r_idx + 1, j)
                    cell.text = cell_text
                    if r_idx % 2 == 1:
                        set_cell_background(cell, "EEF2FF")

            doc.add_paragraph()

        # ── Bullet list (- or *) ──
        elif re.match(r"^(\s*)[-*]\s+(.+)", line):
            m = re.match(r"^(\s*)[-*]\s+(.+)", line)
            indent = len(m.group(1)) // 2
            style = "List Bullet 2" if indent > 0 else "List Bullet"
            content = m.group(2)
            para = doc.add_paragraph(style=style)
            _add_inline_formatting(para, content)

        # ── Numbered list ──
        elif re.match(r"^\d+\.\s+(.+)", line):
            m = re.match(r"^\d+\.\s+(.+)", line)
            para = doc.add_paragraph(style="List Number")
            _add_inline_formatting(para, m.group(1))

        # ── Horizontal rule ──
        elif line.strip() in ("---", "***", "___"):
            doc.add_paragraph("─" * 60)

        # ── Normal paragraph (skip blanks) ──
        elif line.strip():
            para = doc.add_paragraph()
            _add_inline_formatting(para, line)

        else:
            # Blank line – small spacer only between non-empty content
            if i > 0 and lines[i - 1].strip():
                doc.add_paragraph()

        i += 1

    # ── Footer ──
    section = doc.sections[0]
    footer = section.footer
    footer_para = footer.paragraphs[0]
    footer_para.text = "Generated by Model Card Generator · Powered by Claude AI"
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in footer_para.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x9E, 0x9E, 0x9E)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _add_inline_formatting(para, text: str) -> None:
    """Parse inline bold (**text**) and inline code (`text`) into runs."""
    # Split on bold or code markers
    tokens = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
    for token in tokens:
        if token.startswith("**") and token.endswith("**"):
            run = para.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("`") and token.endswith("`"):
            run = para.add_run(token[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(9)
        else:
            para.add_run(token)


# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
if "model_card_md" not in st.session_state:
    st.session_state.model_card_md = ""
if "generating" not in st.session_state:
    st.session_state.generating = False

# ──────────────────────────────────────────────
# Sidebar – API key
# ──────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")
    api_key_input = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Your key is used only for this session and never stored.",
    )
    st.markdown("---")
    st.markdown(
        """
**About this tool**

Fills in a structured form → sends to **Claude** with model card best-practice guidelines → produces an industry-standard model card → exports as a Word document.

Built on:
- [Streamlit](https://streamlit.io)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [python-docx](https://python-docx.readthedocs.io)
"""
    )

# ──────────────────────────────────────────────
# Main header
# ──────────────────────────────────────────────
st.title("🃏 Model Card Generator")
st.markdown(
    "Complete each section below. Claude will synthesise your inputs into a structured, "
    "industry-standard model card that you can download as a Word document."
)
st.markdown("---")

# ──────────────────────────────────────────────
# Form
# ──────────────────────────────────────────────
with st.form("model_card_form"):

    # ── Section 1: Model Description ──────────
    st.markdown('<div class="section-header">1 · Model Description</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        model_name = st.text_input("Model name *", placeholder="e.g. BioMed-BERT-v2")
        model_version = st.text_input("Version", placeholder="e.g. 2.1.0")
        model_type = st.text_input(
            "Model type / architecture *",
            placeholder="e.g. Transformer-based text classifier (BERT fine-tune)",
        )
        developers = st.text_input("Developers / Organization *", placeholder="e.g. Acme AI Lab")
    with col2:
        release_date = st.text_input("Release date", placeholder="e.g. 2025-06-01")
        license_type = st.text_input("License", placeholder="e.g. Apache 2.0")
        contact = st.text_input("Contact email / URL", placeholder="e.g. models@acme.ai")

    model_description = st.text_area(
        "Detailed model description *",
        height=140,
        placeholder=(
            "Describe the model's purpose, key capabilities, what problem it solves, "
            "and any notable architectural decisions."
        ),
    )

    st.markdown("---")

    # ── Section 2: Training Data ───────────────
    st.markdown(
        '<div class="section-header">2 · Training Data Characteristics</div>',
        unsafe_allow_html=True,
    )
    col3, col4 = st.columns(2)
    with col3:
        data_sources = st.text_area(
            "Data sources *",
            height=100,
            placeholder="List datasets, databases, web-scraped sources, proprietary data, etc.",
        )
        data_volume = st.text_input(
            "Data size / volume", placeholder="e.g. 2.4 M samples, 15 GB text"
        )
        data_date_range = st.text_input(
            "Date range of data", placeholder="e.g. Jan 2018 – Dec 2023"
        )
    with col4:
        preprocessing = st.text_area(
            "Preprocessing / cleaning steps",
            height=100,
            placeholder="Tokenisation, deduplication, filtering, anonymisation, etc.",
        )
        data_biases = st.text_area(
            "Known data biases or gaps",
            height=60,
            placeholder="Describe any known imbalances, missing demographics, or selection biases.",
        )
        demographic_notes = st.text_area(
            "Demographic representation notes",
            height=60,
            placeholder="Language, geography, age, gender distribution if known.",
        )

    st.markdown("---")

    # ── Section 3: Performance Metrics ────────
    st.markdown(
        '<div class="section-header">3 · Performance Metrics</div>', unsafe_allow_html=True
    )
    col5, col6 = st.columns(2)
    with col5:
        eval_datasets = st.text_area(
            "Evaluation datasets *",
            height=80,
            placeholder="Name each evaluation split or benchmark dataset.",
        )
        metrics_used = st.text_input(
            "Metrics used *",
            placeholder="e.g. Accuracy, F1-macro, AUC-ROC, BLEU, ROUGE-L",
        )
    with col6:
        results_summary = st.text_area(
            "Results summary *",
            height=80,
            placeholder="Paste key numbers, e.g. F1=0.91 on test set, AUC=0.95 on held-out set.",
        )
        disaggregated_eval = st.text_area(
            "Disaggregated evaluation (subgroups)",
            height=60,
            placeholder="Performance broken down by demographic, domain, or data slice if available.",
        )
    benchmarks = st.text_area(
        "Benchmark comparisons",
        height=60,
        placeholder="How does the model compare to baselines or state-of-the-art?",
    )

    st.markdown("---")

    # ── Section 4: Known Limitations ──────────
    st.markdown(
        '<div class="section-header">4 · Known Limitations</div>', unsafe_allow_html=True
    )
    col7, col8 = st.columns(2)
    with col7:
        technical_limitations = st.text_area(
            "Technical limitations *",
            height=90,
            placeholder="Context length limits, input modalities, inference speed, memory footprint, etc.",
        )
        failure_modes = st.text_area(
            "Failure modes",
            height=90,
            placeholder="Describe known edge cases or input types where the model fails.",
        )
    with col8:
        fairness_concerns = st.text_area(
            "Fairness / bias concerns *",
            height=90,
            placeholder="Known disparities in performance across demographic groups or protected attributes.",
        )
        degradation_conditions = st.text_area(
            "Conditions where performance degrades",
            height=90,
            placeholder="Domain shift, adversarial inputs, low-resource scenarios, etc.",
        )

    st.markdown("---")

    # ── Section 5: Intended Deployment Context ─
    st.markdown(
        '<div class="section-header">5 · Intended Deployment Context</div>',
        unsafe_allow_html=True,
    )
    col9, col10 = st.columns(2)
    with col9:
        primary_use_cases = st.text_area(
            "Primary use cases *",
            height=90,
            placeholder="Specific tasks and scenarios this model is designed for.",
        )
        intended_users = st.text_area(
            "Intended users / audience",
            height=90,
            placeholder="Clinicians, data scientists, end-consumers, enterprise customers, etc.",
        )
    with col10:
        deployment_env = st.text_area(
            "Recommended deployment environment",
            height=90,
            placeholder="Cloud, on-prem, edge device; GPU/CPU requirements; API vs embedded.",
        )
        human_oversight = st.text_area(
            "Human oversight requirements",
            height=90,
            placeholder="When should a human review model outputs? Any mandatory review workflows?",
        )
    compliance_notes = st.text_area(
        "Regulatory / compliance notes",
        height=60,
        placeholder="GDPR, HIPAA, EU AI Act risk tier, FINRA, etc.",
    )

    st.markdown("---")

    # ── Section 6: Out-of-Scope Uses ──────────
    st.markdown(
        '<div class="section-header">6 · Out-of-Scope Uses</div>', unsafe_allow_html=True
    )
    col11, col12 = st.columns(2)
    with col11:
        oos_uses = st.text_area(
            "Explicitly out-of-scope uses *",
            height=90,
            placeholder="Use cases that the model was NOT designed for and may perform poorly on.",
        )
        misuse_scenarios = st.text_area(
            "Potential misuse scenarios",
            height=90,
            placeholder="Ways the model could be deliberately misused.",
        )
    with col12:
        prohibited_uses = st.text_area(
            "Prohibited use cases",
            height=90,
            placeholder="Uses that are explicitly forbidden by the license or ethics policy.",
        )

    st.markdown("---")

    # ── Additional Notes ───────────────────────
    additional_notes = st.text_area(
        "Additional notes for the model card (optional)",
        height=80,
        placeholder="Acknowledgements, related papers, funding sources, version history, etc.",
    )

    st.markdown("---")
    submitted = st.form_submit_button(
        "✨ Generate Model Card",
        use_container_width=True,
        type="primary",
    )

# ──────────────────────────────────────────────
# Generation logic
# ──────────────────────────────────────────────
if submitted:
    # Validate required fields
    required = {
        "Model name": model_name,
        "Model type / architecture": model_type,
        "Developers / Organization": developers,
        "Model description": model_description,
        "Data sources": data_sources,
        "Evaluation datasets": eval_datasets,
        "Metrics used": metrics_used,
        "Results summary": results_summary,
        "Technical limitations": technical_limitations,
        "Fairness / bias concerns": fairness_concerns,
        "Primary use cases": primary_use_cases,
        "Out-of-scope uses": oos_uses,
    }
    missing = [k for k, v in required.items() if not v.strip()]
    if missing:
        st.error(f"Please fill in the required fields: {', '.join(missing)}")
    elif not api_key_input.strip():
        st.error("Please enter your Anthropic API key in the sidebar.")
    else:
        fields = {
            "model_name": model_name,
            "model_version": model_version or "1.0.0",
            "model_type": model_type,
            "developers": developers,
            "release_date": release_date or "Not specified",
            "license": license_type or "Not specified",
            "contact": contact or "Not specified",
            "model_description": model_description,
            "data_sources": data_sources,
            "data_volume": data_volume or "Not specified",
            "data_date_range": data_date_range or "Not specified",
            "preprocessing": preprocessing or "Not specified",
            "data_biases": data_biases or "Not specified",
            "demographic_notes": demographic_notes or "Not specified",
            "eval_datasets": eval_datasets,
            "metrics_used": metrics_used,
            "results_summary": results_summary,
            "disaggregated_eval": disaggregated_eval or "Not provided",
            "benchmarks": benchmarks or "Not provided",
            "technical_limitations": technical_limitations,
            "fairness_concerns": fairness_concerns,
            "failure_modes": failure_modes or "Not specified",
            "degradation_conditions": degradation_conditions or "Not specified",
            "primary_use_cases": primary_use_cases,
            "intended_users": intended_users or "Not specified",
            "deployment_env": deployment_env or "Not specified",
            "human_oversight": human_oversight or "Not specified",
            "compliance_notes": compliance_notes or "Not specified",
            "oos_uses": oos_uses,
            "misuse_scenarios": misuse_scenarios or "Not specified",
            "prohibited_uses": prohibited_uses or "Not specified",
            "additional_notes": additional_notes or "None",
        }

        user_message = build_user_message(fields)

        with st.spinner("Generating model card with Claude…"):
            try:
                client = anthropic.Anthropic(api_key=api_key_input.strip())
                response = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_message}],
                )
                st.session_state.model_card_md = response.content[0].text
                st.success("Model card generated successfully!")
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Please check your Anthropic API key in the sidebar.")
            except anthropic.RateLimitError:
                st.error("Rate limit reached. Please wait a moment and try again.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# ──────────────────────────────────────────────
# Output area
# ──────────────────────────────────────────────
if st.session_state.model_card_md:
    st.markdown("---")
    st.subheader("Generated Model Card")

    tab_preview, tab_raw = st.tabs(["📄 Preview", "🔤 Markdown Source"])

    with tab_preview:
        st.markdown(st.session_state.model_card_md)

    with tab_raw:
        st.code(st.session_state.model_card_md, language="markdown")

    st.markdown("---")
    st.subheader("Export")

    col_dl1, col_dl2 = st.columns([1, 3])
    with col_dl1:
        try:
            docx_bytes = markdown_to_docx(st.session_state.model_card_md)
            st.download_button(
                label="⬇️ Download Word (.docx)",
                data=docx_bytes,
                file_name="model_card.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Word export failed: {e}")

    with col_dl2:
        st.download_button(
            label="⬇️ Download Markdown (.md)",
            data=st.session_state.model_card_md.encode("utf-8"),
            file_name="model_card.md",
            mime="text/markdown",
            use_container_width=True,
        )
