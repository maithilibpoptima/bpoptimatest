import streamlit as st
import requests
import base64
import os
import io
import json
import re
import tempfile
from PIL import Image

from document_processors import get_processor_for_file

# ─── Config ───────────────────────────────────────────────────────────────────

AZURE_API_URL = "https://bp-optima-gateway.wittyisland-8238b4dd.southeastasia.azurecontainerapps.io"
AZURE_API_KEY = "bp-optima-2026"

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BP Optima Document Extraction",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Theme / CSS ──────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Jost:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --tobacco:    #B59E7D;
        --vanilla:    #F1EADA;
        --mahogany:   #584738;
        --mountain:   #AAA396;
        --sand:       #CEC1A8;
        --text-dark:  #1C1410;
        --text-mid:   #584738;
        --text-light: #8a7a6a;
    }

    html, body, [class*="css"] {
        font-family: 'Jost', sans-serif;
        background-color: var(--vanilla);
        color: var(--text-dark);
    }
    .stApp { background-color: var(--vanilla); }
    #MainMenu, footer, header { visibility: hidden; }

    .page-heading {
        font-family: 'Cormorant Garamond', serif;
        font-weight: 300;
        font-size: 3.2rem;
        letter-spacing: 0.04em;
        color: var(--mahogany);
        margin-bottom: 0.15rem;
        line-height: 1.1;
    }
    .page-subheading {
        font-family: 'Jost', sans-serif;
        font-weight: 300;
        font-size: 0.85rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--mountain);
        margin-bottom: 2.5rem;
    }
    .panel-label {
        font-size: 0.7rem;
        letter-spacing: 0.25em;
        text-transform: uppercase;
        color: var(--mountain);
        margin-bottom: 0.75rem;
        margin-top: 0;
        border-bottom: 1px solid var(--sand);
        padding-bottom: 0.4rem;
    }
    .upload-label {
        font-size: 0.75rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--text-light);
        margin-bottom: 0.5rem;
    }
    .api-label {
        font-size: 0.75rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--text-light);
        margin-bottom: 0.3rem;
    }
    .thin-divider {
        border: none;
        border-top: 1px solid var(--sand);
        margin: 1.5rem 0;
    }
    [data-testid="stFileUploader"] {
        background: #FAF7F2;
        border: 1.5px dashed var(--tobacco);
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    [data-testid="stFileUploader"] label {
        color: var(--text-mid) !important;
        font-family: 'Jost', sans-serif !important;
        font-size: 0.85rem !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: var(--tobacco) !important;
        color: var(--vanilla) !important;
        border: none !important;
        border-radius: 2px !important;
        font-family: 'Jost', sans-serif !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.1em !important;
        padding: 0.35rem 1rem !important;
    }
    .preview-panel {
        background: #FAF7F2;
        border: 1px solid var(--sand);
        border-radius: 4px;
        padding: 1rem;
        min-height: 420px;
    }
    .result-panel {
        background: #FAF7F2;
        border: 1px solid var(--sand);
        border-radius: 4px;
        padding: 1.25rem 1.5rem;
        min-height: 200px;
        font-family: 'Jost', sans-serif;
        font-size: 0.88rem;
        line-height: 1.7;
        color: var(--text-dark);
        white-space: pre-wrap;
        overflow-y: auto;
    }
    .json-empty {
        background: #FAF7F2;
        border: 1px solid var(--sand);
        border-radius: 4px;
        padding: 1.25rem 1.5rem;
        min-height: 420px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .conf-badge {
        display: inline-block;
        padding: 0.2rem 0.7rem;
        border-radius: 2px;
        font-size: 0.72rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    .conf-high   { background: #d4e6d0; color: #2a5226; }
    .conf-medium { background: #f0e3c8; color: #7a4e10; }
    .conf-low    { background: #efd0cc; color: #7a2020; }
    .doc-type-badge {
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 2px;
        font-size: 0.72rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        background: var(--sand);
        color: var(--mahogany);
        margin-bottom: 1rem;
        margin-left: 0.5rem;
    }
    .status-dot {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .dot-green { background: #4caf50; }
    .dot-red   { background: #e53935; }
    .dot-grey  { background: var(--mountain); }
    .status-text {
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-light);
        vertical-align: middle;
    }
    .stButton > button {
        background-color: var(--mahogany) !important;
        color: var(--vanilla) !important;
        border: none !important;
        border-radius: 2px !important;
        font-family: 'Jost', sans-serif !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.18em !important;
        text-transform: uppercase !important;
        padding: 0.55rem 2rem !important;
        width: 100%;
    }
    .stButton > button:hover { background-color: var(--tobacco) !important; }
    .meta-row  { display: flex; gap: 2rem; margin-bottom: 0.8rem; }
    .meta-item { font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-light); }
    .meta-value { font-weight: 500; color: var(--text-mid); }

    /* ── Field confidence cards ── */
    .field-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 0;
        border-bottom: 1px solid #f0ebe0;
    }
    .field-card:last-child { border-bottom: none; }
    .field-card-left { flex: 1; }
    .field-card-label {
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-light);
        margin-bottom: 0.2rem;
    }
    .field-card-value {
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--text-dark);
    }
    .field-card-right {
        display: flex;
        align-items: center;
        gap: 0.3rem;
        flex-shrink: 0;
        margin-left: 1rem;
    }
    .field-conf-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-high   { background: #4caf50; }
    .dot-medium { background: #f59e0b; }
    .dot-low    { background: #e53935; }
    .dot-unknown{ background: var(--mountain); }
    .field-conf-pct { font-size: 0.78rem; font-weight: 600; }
    .field-conf-high   { color: #2a5226; }
    .field-conf-medium { color: #7a4e10; }
    .field-conf-low    { color: #7a2020; }
    .field-conf-unknown{ color: var(--mountain); }
    .fields-container {
        background: #FAF7F2;
        border: 1px solid var(--sand);
        border-radius: 4px;
        padding: 0.5rem 1.25rem;
        margin-bottom: 1rem;
    }
    .table-section {
        background: #FAF7F2;
        border: 1px solid var(--sand);
        border-radius: 4px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }
    .table-name {
        font-size: 0.72rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--mountain);
        margin-bottom: 0.5rem;
    }
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: var(--vanilla); }
    ::-webkit-scrollbar-thumb { background: var(--sand); border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def api_headers():
    return {"X-API-Key": AZURE_API_KEY}


def conf_class(label: str) -> str:
    label = label.upper()
    if label == "HIGH":    return "field-conf-high"
    elif label == "MEDIUM": return "field-conf-medium"
    elif label == "LOW":    return "field-conf-low"
    return "field-conf-unknown"


def parse_confidence(conf_data) -> tuple:
    if isinstance(conf_data, dict):
        score = conf_data.get("document_confidence", 0.5)
        label = conf_data.get("confidence_label", "MEDIUM").upper()
        if label == "HIGH":   return score, "conf-high", "High"
        elif label == "LOW":  return score, "conf-low", "Low"
        else:                 return score, "conf-medium", "Medium"
    elif isinstance(conf_data, (int, float)):
        score = float(conf_data)
        if score >= 0.85:   return score, "conf-high", "High"
        elif score >= 0.65: return score, "conf-medium", "Medium"
        else:               return score, "conf-low", "Low"
    return 0.5, "conf-medium", "Medium"


def render_fields_with_confidence(fields: list) -> str:
    if not fields:
        return '<p style="color:var(--mountain);font-size:0.8rem;">No fields extracted.</p>'
    cards = ""
    for f in fields:
        label      = f.get("label", f.get("key", ""))
        value      = f.get("value", "")
        confidence = f.get("confidence", 0.0)
        conf_lbl   = f.get("conf_label", "UNKNOWN").upper()
        css_cls    = conf_class(conf_lbl)
        conf_pct   = f"{confidence * 100:.0f}%"
        dot_cls    = f"dot-{conf_lbl.lower()}" if conf_lbl in ("HIGH", "MEDIUM", "LOW") else "dot-unknown"
        cards += (
            f'<div class="field-card">'
            f'<div class="field-card-left">'
            f'<div class="field-card-label">{label}</div>'
            f'<div class="field-card-value">{value}</div>'
            f'</div>'
            f'<div class="field-card-right">'
            f'<span class="field-conf-dot {dot_cls}"></span>'
            f'<span class="field-conf-pct {css_cls}">{conf_pct}</span>'
            f'</div></div>'
        )
    return f'<div class="fields-container">{cards}</div>'


def render_tables(tables: list) -> str:
    if not tables:
        return ""
    html = ""
    for tbl in tables:
        name = tbl.get("table_name", "Table")
        rows = tbl.get("rows", [])
        if not rows:
            continue
        headers = list(rows[0].keys())
        th_parts = []
        for h in headers:
            th_parts.append(
                f'<th style="text-align:left;font-size:0.68rem;letter-spacing:0.15em;'
                f'text-transform:uppercase;color:var(--mountain);border-bottom:1px solid var(--sand);'
                f'padding:0.4rem 0.6rem;">{h}</th>'
            )
        th = "".join(th_parts)
        tr_parts = []
        for row in rows:
            td_parts = []
            for h in headers:
                val = row.get(h, "")
                td_parts.append(f'<td style="padding:0.45rem 0.6rem;border-bottom:1px solid #f0ebe0;font-size:0.85rem;">{val}</td>')
            tr_parts.append("<tr>" + "".join(td_parts) + "</tr>")
        tr = "".join(tr_parts)
        html += (
            f'<div class="table-section">'
            f'<p class="table-name">{name}</p>'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'
        )
    return html


# ─── Header ───────────────────────────────────────────────────────────────────

st.markdown('<p class="page-heading">BP Optima Document Extraction</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="page-subheading">GLM-OCR 0.9B &nbsp;·&nbsp; Vision Extraction &nbsp;+&nbsp; Qwen2.5 1.5B &nbsp;·&nbsp; JSON Structuring</p>',
    unsafe_allow_html=True,
)
st.markdown('<hr class="thin-divider"/>', unsafe_allow_html=True)

# ─── API Status ───────────────────────────────────────────────────────────────

st.markdown('<p class="api-label">Azure API Endpoint</p>', unsafe_allow_html=True)

col_url, col_status = st.columns([5, 1])
with col_url:
    st.markdown(
        f'<p style="font-size:0.85rem;color:var(--text-mid);padding-top:0.5rem;'
        f'font-family:\'JetBrains Mono\',monospace;">{AZURE_API_URL}</p>',
        unsafe_allow_html=True,
    )
with col_status:
    status_placeholder = st.empty()

api_ready = False
try:
    r = requests.get(f"{AZURE_API_URL}/health", timeout=8, headers=api_headers())
    if r.status_code == 200 and r.json().get("status") == "ok":
        status_placeholder.markdown(
            '<span class="status-dot dot-green"></span><span class="status-text">Connected</span>',
            unsafe_allow_html=True,
        )
        api_ready = True
    else:
        status_placeholder.markdown(
            '<span class="status-dot dot-red"></span><span class="status-text">Error</span>',
            unsafe_allow_html=True,
        )
except Exception:
    status_placeholder.markdown(
        '<span class="status-dot dot-red"></span><span class="status-text">Unreachable</span>',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="thin-divider"/>', unsafe_allow_html=True)

# ─── Upload + hint ────────────────────────────────────────────────────────────

st.markdown('<p class="upload-label">Upload Document</p>', unsafe_allow_html=True)

hint_col, _ = st.columns([2, 3])
with hint_col:
    hint = st.text_input(
        "Document hint (optional)",
        placeholder="e.g. invoice, tax form, lease agreement",
        label_visibility="collapsed",
    )

uploaded_file = st.file_uploader(
    label="Supported: PDF, DOCX, DOC, XLSX, XLS, PNG, JPG, JPEG, TIFF, BMP, WEBP, TXT",
    type=["pdf","docx","doc","xlsx","xls","png","jpg","jpeg","tiff","bmp","webp","txt","csv"],
    label_visibility="visible",
)

st.markdown('<hr class="thin-divider"/>', unsafe_allow_html=True)

# ─── Extract button ───────────────────────────────────────────────────────────

btn_col, warn_col = st.columns([1, 3], gap="medium")
with btn_col:
    extract_clicked = st.button(
        "Extract Text",
        disabled=(not api_ready or uploaded_file is None),
    )
with warn_col:
    if not api_ready:
        st.warning("Azure API is not reachable. Check your connection.")
    elif uploaded_file is None:
        st.markdown(
            '<p style="color:var(--text-light);font-size:0.8rem;letter-spacing:0.1em;padding-top:0.6rem;">Upload a file to begin.</p>',
            unsafe_allow_html=True,
        )

st.markdown('<hr class="thin-divider"/>', unsafe_allow_html=True)

# ─── Two-column layout ────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 1], gap="large")

# ── LEFT: document preview ────────────────────────────────────────────────────

with col_left:
    st.markdown('<p class="panel-label">Document Preview</p>', unsafe_allow_html=True)

    if uploaded_file is None:
        st.markdown(
            '<div class="preview-panel" style="display:flex;align-items:center;justify-content:center;">'
            '<span style="color:var(--mountain);font-size:0.8rem;letter-spacing:0.15em;text-transform:uppercase;">'
            'No file uploaded</span></div>',
            unsafe_allow_html=True,
        )
    else:
        file_bytes = uploaded_file.read()
        file_name  = uploaded_file.name
        file_ext   = os.path.splitext(file_name)[1].lower()

        st.markdown(
            f'<p style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;'
            f'color:var(--text-light);margin-bottom:0.4rem;">{file_name}</p>',
            unsafe_allow_html=True,
        )

        if file_ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"]:
            st.image(Image.open(io.BytesIO(file_bytes)), use_container_width=True)
        elif file_ext == ".pdf":
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                pix = doc[0].get_pixmap(dpi=120)
                st.image(
                    Image.frombytes("RGB", [pix.width, pix.height], pix.samples),
                    caption="Page 1 preview",
                    use_container_width=True,
                )
            except Exception:
                st.markdown(
                    '<p style="color:var(--text-light);font-size:0.82rem;">PDF loaded. '
                    'Install PyMuPDF for a visual preview.</p>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f'<div class="preview-panel" style="display:flex;align-items:center;justify-content:center;">'
                f'<p style="color:var(--text-light);font-size:0.82rem;text-align:center;">'
                f'<strong>{file_ext}</strong><br/>File loaded and ready for extraction.</p></div>',
                unsafe_allow_html=True,
            )

# ── RIGHT: Structured output ──────────────────────────────────────────────────

with col_right:
    st.markdown('<p class="panel-label">Structured Output</p>', unsafe_allow_html=True)
    result_placeholder = st.empty()

    with result_placeholder.container():
        st.markdown(
            '<div class="json-empty">'
            '<span style="color:var(--mountain);font-size:0.8rem;letter-spacing:0.15em;text-transform:uppercase;">'
            'Awaiting extraction</span></div>',
            unsafe_allow_html=True,
        )

# ─── Run extraction ───────────────────────────────────────────────────────────

if uploaded_file is not None and extract_clicked:
    with result_placeholder.container():
        with st.spinner("Sending to Azure for extraction... (first request may take 30-60s while GPU warms up)"):
            try:
                response = requests.post(
                    f"{AZURE_API_URL}/extract-file",
                    files={"file": (file_name, file_bytes, "application/octet-stream")},
                    data={"hint": hint or ""},
                    headers=api_headers(),
                    timeout=300,
                )

                if response.status_code != 200:
                    st.error(f"API error: {response.status_code} — {response.text}")
                else:
                    data       = response.json()
                    doc_type   = data.get("document_type", "unknown")
                    fields     = data.get("fields", [])
                    tables     = data.get("tables", [])
                    raw_text   = data.get("raw_text", "")
                    conf_data  = data.get("confidence", {})
                    metadata   = data.get("metadata", {})

                    total_pages   = metadata.get("pages_processed", 1)
                    latency_ms    = metadata.get("latency_ms", 0)
                    gpu_used      = metadata.get("gpu_utilised", False)
                    total_elapsed = latency_ms / 1000

                    conf_score, badge_cls, conf_label = parse_confidence(conf_data)

                    # Meta row
                    st.markdown(
                        f'<div class="meta-row">'
                        f'<span class="meta-item">Pages: <span class="meta-value">{total_pages}</span></span>'
                        f'<span class="meta-item">Time: <span class="meta-value">{total_elapsed:.1f}s</span></span>'
                        f'<span class="meta-item">GPU: <span class="meta-value">{"Yes" if gpu_used else "No"}</span></span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Badges
                    badges = f'<span class="conf-badge {badge_cls}">Overall: {conf_score*100:.1f}% — {conf_label}</span>'
                    if doc_type:
                        badges += f' <span class="doc-type-badge">{doc_type.replace("_", " ")}</span>'
                    st.markdown(badges, unsafe_allow_html=True)

                    # Fields
                    st.markdown('<p class="panel-label" style="margin-top:1rem;">Extracted Fields</p>', unsafe_allow_html=True)
                    st.markdown(render_fields_with_confidence(fields), unsafe_allow_html=True)

                    # Tables
                    if tables:
                        st.markdown('<p class="panel-label">Extracted Tables</p>', unsafe_allow_html=True)
                        st.markdown(render_tables(tables), unsafe_allow_html=True)

                    # Raw text expander
                    with st.expander("Raw Extracted Text (VLM output)", expanded=False):
                        st.markdown(
                            f'<div class="result-panel" style="min-height:unset;">{raw_text}</div>',
                            unsafe_allow_html=True,
                        )

                    # JSON output
                    with st.expander("JSON Output", expanded=False):
                        st.json(data.get("structured_json", {}))

                    # Download
                    st.download_button(
                        label="Download Full JSON",
                        data=json.dumps(data, indent=2, ensure_ascii=False),
                        file_name=f"{os.path.splitext(file_name)[0]}_extracted.json",
                        mime="application/json",
                    )

            except requests.exceptions.Timeout:
                st.error("Request timed out. The GPU may be warming up — try again in 30 seconds.")
            except requests.exceptions.ConnectionError:
                st.error("Could not reach the Azure API. Check your internet connection.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
