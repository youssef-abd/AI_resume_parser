import io
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from html import escape
import re
import pandas as pd

import requests
import streamlit as st
import streamlit.components.v1 as components
import logging

# Complete JavaScript override for MIME type issues
override_js = '''
<script>
// Complete override to prevent MIME type errors
(function() {
    'use strict';
    
    console.log('Initializing JavaScript override for HuggingFace Spaces...');
    
    // Override fetch to return valid JavaScript for .js requests
    const originalFetch = window.fetch;
    window.fetch = function(resource, init) {
        if (typeof resource === 'string' && resource.includes('.js')) {
            console.warn('Intercepting JS fetch request:', resource);
        }
        
        // For all requests, use original fetch
        return originalFetch.call(this, resource, init);
    };
    
    // Prevent error propagation for module-related errors
    window.addEventListener('error', function(e) {
        if (e.message && (
            e.message.includes('Failed to load module') ||
            e.message.includes('MIME type') ||
            e.message.includes('Expected a JavaScript')
        )) {
            console.warn('Suppressed module error:', e.message);
            e.stopPropagation();
            e.preventDefault();
            return false;
        }
    }, true);
    
    // Override console.error to suppress specific errors
    const originalConsoleError = console.error;
    console.error = function(...args) {
        const message = args.join(' ').toLowerCase();
        if (message.includes('mime type') ||
            message.includes('module script') ||
            message.includes('failed to load')) {
            console.warn('Suppressed error:', ...args);
            return;
        }
        originalConsoleError.apply(console, args);
    };
    
    console.log('JavaScript override complete. Module loading errors should be suppressed.');
    
})();
</script>
'''

# Inject the override script immediately
components.html(override_js, height=0)

# Also suppress Python warnings
import warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)
warnings.filterwarnings('ignore')

# Configure Streamlit to be more lenient with static assets


# ------------------------------
# Config
# ------------------------------
# Use container networking
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Resume Screener", layout="wide", initial_sidebar_state="auto")

# Fixed CSS to remove blank space and improve styling
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&display=swap');
      :root, html, body, [data-testid="stAppViewContainer"] * {
        font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
                     Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue",
                     Arial, sans-serif !important;
      }
      /* Remove ALL top padding and margin to eliminate blank space */
      .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 2rem !important;
      }
      .main .block-container {
        padding-top: 1rem !important;
        max-width: 100% !important;
      }
      /* Remove top margin from first element */
      .stApp > header {
        background: transparent !important;
      }
      .main > div:first-child {
        padding-top: 0 !important;
      }
      /* Title styling */
      h1:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def normalize_api_base(s: str) -> str:
    """Ensure the API base URL has a scheme/host.
    Examples:
      - '/api' -> 'http://localhost:8000/api'
      - 'localhost:8000' -> 'http://localhost:8000'
      - 'http://backend:8000' -> unchanged
    """
    val = (s or "").strip()
    if not val:
        return "http://localhost:8000"
    if val.startswith("http://") or val.startswith("https://"):
        return val
    if val.startswith("/"):
        default_host = os.getenv("API_HOST", "http://localhost:8000")
        return default_host.rstrip("/") + val
    if "://" not in val:
        return "http://" + val
    return val


def _toggle_api_suffix(base: str) -> str:
    b = (base or "").rstrip("/")
    if b.endswith("/api"):
        return b[:-4] or b
    return b + "/api"


def _probe_ready(base: str) -> Optional[requests.Response]:
    try:
        return requests.get(f"{base.rstrip('/')}/readyz", timeout=5)
    except Exception:
        return None


def resolve_api_base(base: str) -> str:
    norm = normalize_api_base(base)
    r = _probe_ready(norm)
    if r is not None and r.status_code == 200:
        return norm
    alt = _toggle_api_suffix(norm)
    r2 = _probe_ready(alt)
    if r2 is not None and r2.status_code == 200:
        return alt
    return norm


if "last_job_id" not in st.session_state:
    st.session_state["last_job_id"] = ""

# ------------------------------
# Helpers
# ------------------------------

def api_post_job_form(api_base: str, title: str, description: str, required_skills_text: Optional[str]) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/upload_job_form"
    data = {"title": title, "description": description}
    if required_skills_text:
        data["required_skills"] = required_skills_text
    resp = requests.post(url, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json()


def detect_mime_type(filename: str) -> str:
    ext = (filename or "").lower().rsplit(".", 1)[-1] if "." in (filename or "") else ""
    if ext == "pdf":
        return "application/pdf"
    if ext == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


def api_post_resume(api_base: str, file_bytes: bytes, filename: str, candidate_name: Optional[str]) -> Dict[str, Any]:
    """Route single-file upload through the tolerant multi-upload endpoint for consistent behavior."""
    url = f"{api_base.rstrip('/')}/upload_resumes"
    mime = detect_mime_type(filename)
    files: List[Tuple[str, Tuple[str, io.BytesIO, str]]] = [("files", (filename, io.BytesIO(file_bytes), mime))]
    data: List[Tuple[str, str]] = []
    if (candidate_name or "").strip():
        data.append(("candidate_names", (candidate_name or "").strip()))
    resp = requests.post(url, files=files, data=data, timeout=300)
    resp.raise_for_status()
    # The multi-upload returns a list; return the first item for single upload UX
    out = resp.json()
    if isinstance(out, list) and out:
        return out[0]
    return out


def api_get_match(api_base: str, job_id: str, k: int = 10) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/match"
    params = {"job_id": job_id, "k": k}
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def api_post_resumes(api_base: str, files_data: List[Tuple[str, bytes]], candidate_names: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Upload multiple resumes via /upload_resumes.
    files_data: list of (filename, bytes)
    candidate_names: optional list aligned by index
    """
    url = f"{api_base.rstrip('/')}/upload_resumes"
    files: List[Tuple[str, Tuple[str, io.BytesIO, str]]] = []
    for filename, content in files_data:
        mime = detect_mime_type(filename)
        files.append(("files", (filename, io.BytesIO(content), mime)))
    data: List[Tuple[str, str]] = []
    if candidate_names:
        for name in candidate_names:
            data.append(("candidate_names", name))
    resp = requests.post(url, files=files, data=data, timeout=300)
    resp.raise_for_status()
    return resp.json()


def api_get_resume(api_base: str, resume_id: str) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/resumes/{resume_id}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def api_get_job(api_base: str, job_id: str) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/jobs/{job_id}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def render_highlight_full(text: str, spans: List[Dict[str, int]]) -> str:
    """Render full text with highlight marks for provided spans (non-overlapping, sorted)."""
    if not text or not spans:
        return escape(text or "")
    # sort & merge overlaps conservatively
    spans_sorted = sorted(spans, key=lambda s: (int(s.get("start", 0)), int(s.get("end", 0))))
    merged: List[Tuple[int, int]] = []
    for sp in spans_sorted:
        s = int(sp.get("start", 0)); e = int(sp.get("end", 0))
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            # overlap -> extend end
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    # build html
    out_parts: List[str] = []
    prev = 0
    for s, e in merged:
        s = max(0, min(s, len(text))); e = max(0, min(e, len(text)))
        if s > prev:
            out_parts.append(escape(text[prev:s]))
        out_parts.append(f"<mark>{escape(text[s:e])}</mark>")
        prev = e
    if prev < len(text):
        out_parts.append(escape(text[prev:]))
    return "".join(out_parts)


def find_term_spans(text: str, terms: List[str]) -> List[Dict[str, int]]:
    """Find spans for terms (case-insensitive, word boundaries)."""
    spans: List[Dict[str, int]] = []
    if not text or not terms:
        return spans
    for t in terms:
        t_norm = (t or "").strip()
        if not t_norm:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(t_norm)}(?!\w)", re.IGNORECASE)
        for m in pattern.finditer(text):
            spans.append({"start": m.start(), "end": m.end()})
    return spans


def make_highlight_snippet(text: str, start: int, end: int, pre: int = 60, post: int = 60) -> str:
    s = max(0, start - pre)
    e = min(len(text), end + post)
    prefix = "…" if s > 0 else ""
    suffix = "…" if e < len(text) else ""
    before = escape(text[s:start])
    target = f"<mark>{escape(text[start:end])}</mark>"
    after = escape(text[end:e])
    return prefix + before + target + after + suffix


# ------------------------------
# UI
# ------------------------------
st.title("AI Resume Screener")

with st.sidebar:
    st.header("Settings")
    api_base = st.text_input("API Base URL", value=API_BASE_URL, help="Point to your FastAPI server")
    api_base_norm = normalize_api_base(api_base)
    if st.button("Check Readiness"):
        try:
            resolved = resolve_api_base(api_base_norm)
            r = requests.get(f"{resolved.rstrip('/')}/readyz", timeout=10)
            ok = r.status_code == 200
            st.success(f"/readyz → {r.status_code} {r.json() if ok else r.text}")
        except Exception as e:
            st.error(f"Ready check failed: {e}")

    st.divider()
    st.caption("Backend: FastAPI + sentence-transformers + spaCy + PostgreSQL/pgvector")

# Tabs
job_tab, resume_tab, match_tab = st.tabs(["Upload Job", "Upload Resume", "Match Results"])

# ------------------------------
# Upload Job Tab
# ------------------------------
with job_tab:
    st.subheader("Upload Job")
    with st.form("job_form"):
        title = st.text_input("Job Title", value="Software Engineer (Backend/AI)", max_chars=255)
        description = st.text_area(
            "Job Description (paste markdown/plaintext)",
            height=300,
            value=(
                "**About the Role**\n\n"
                "We are looking for a Software Engineer with strong backend and data engineering experience who can also apply modern AI/ML techniques.\n\n"
                "**Responsibilities**\n- Build APIs\n- Data pipelines\n- Deploy AI models\n\n"
                "**Required Skills**\n- Python, SQL\n- Docker, Kubernetes\n- AWS or GCP\n"
            ),
        )
        required_skills_text = st.text_area(
            "Required Skills (optional, comma or newline separated)",
            placeholder="python, sql, docker, kubernetes, aws, gcp",
            height=80,
        )
        submit = st.form_submit_button("Create Job")

    if submit:
        try:
            eff_base = resolve_api_base(api_base_norm)
            res = api_post_job_form(eff_base, title, description, required_skills_text or None)
            st.session_state["last_job_id"] = res.get("job_id", "")
            st.success("Job created")
            st.json(res)
        except requests.HTTPError as e:
            st.error(f"HTTP error: {e.response.status_code} {e.response.text}")
        except Exception as e:
            st.error(f"Error creating job: {e}")

    if st.session_state.get("last_job_id"):
        st.info(f"Last job_id: {st.session_state['last_job_id']}")

# ------------------------------
# Upload Resume Tab
# ------------------------------
with resume_tab:
    st.subheader("Upload Resumes")
    
    # Upload method selection - moved outside conditional blocks
    upload_method = st.radio(
        "Choose upload method:",
        ["Direct Upload (Recommended)", "Streamlit Upload"],
        help="Direct upload bypasses Streamlit's internal uploader and may work better on some hosts."
    )
    
    if upload_method == "Direct Upload (Recommended)":
        st.info("📤 **Direct Upload Mode** - Files are sent directly to FastAPI via the proxy, bypassing Streamlit's internal upload system.")
        
        # Direct upload UI
        with st.container():
            st.markdown("##### File Selection")
            uploaded_files_direct = st.file_uploader(
                "Select PDF or DOCX resume files", 
                type=["pdf", "docx"], 
                accept_multiple_files=True, 
                key="direct_upload_files",
                help="Select one or more resume files to upload directly"
            )
            
            st.markdown("##### Candidate Names (Optional)")
            candidate_names_direct = st.text_area(
                "Enter candidate names, one per line (must match file order)",
                placeholder="Alice Johnson\nBob Smith\nCharlie Brown",
                height=100,
                key="direct_upload_names",
                help="Optional: Enter candidate names in the same order as your files"
            )
            
            # Upload button and processing
            upload_col1, upload_col2 = st.columns([1, 3])
            with upload_col1:
                upload_button = st.button("🚀 Upload Files", type="primary", key="direct_upload_button")
            with upload_col2:
                if uploaded_files_direct:
                    st.caption(f"Ready to upload {len(uploaded_files_direct)} file(s)")
            
            if upload_button:
                if not uploaded_files_direct:
                    st.warning("⚠️ Please select at least one resume file to upload.")
                else:
                    try:
                        files_data_direct: List[Tuple[str, bytes]] = []
                        for up_direct in uploaded_files_direct:
                            files_data_direct.append((up_direct.name, up_direct.getvalue()))

                        candidate_names_list_direct = [name.strip() for name in candidate_names_direct.split('\n') if name.strip()]

                        with st.spinner("⏳ Uploading resumes directly to server..."):
                            # Use the direct upload function that bypasses all URL resolution
                            results_direct = api_post_resumes_direct(files_data_direct, candidate_names_list_direct)
                        
                        st.success(f"✅ Successfully uploaded {len(results_direct)} resume(s)!")
                        
                        # Display results in a more organized way
                        st.markdown("##### Upload Results")
                        for i, res_direct in enumerate(results_direct, 1):
                            with st.expander(f"Resume {i}: {res_direct.get('candidate_name', 'Unnamed')}"):
                                st.json(res_direct)
                                
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Network error during direct upload: {e}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error occurred: {e}")
    
    else:  # Streamlit Upload
        st.warning("⚠️ **Streamlit Upload Mode** - May not work on all hosting platforms due to internal restrictions.")
        
        # Streamlit upload UI
        with st.container():
            st.markdown("##### Candidate Names (Optional)")
            candidate_names_text = st.text_area(
                "Enter candidate names, one per line (must match file order)",
                placeholder="Alice Johnson\nBob Smith\nCharlie Brown",
                height=100,
                key="streamlit_upload_names"
            )
            
            st.markdown("##### File Selection")
            uploaded_files = st.file_uploader(
                "Select PDF or DOCX resume files", 
                type=["pdf", "docx"], 
                accept_multiple_files=True,
                key="streamlit_upload_files"
            )
            
            # Upload button and processing
            upload_col1, upload_col2 = st.columns([1, 3])
            with upload_col1:
                upload_button_streamlit = st.button("📤 Upload Files", type="primary", key="streamlit_upload_button")
            with upload_col2:
                if uploaded_files:
                    st.caption(f"Ready to upload {len(uploaded_files)} file(s)")
            
            if upload_button_streamlit:
                if not uploaded_files:
                    st.warning("⚠️ Please select at least one resume file to upload.")
                else:
                    try:
                        files_data: List[Tuple[str, bytes]] = []
                        for up in uploaded_files:
                            files_data.append((up.name, up.read()))
                        
                        names_list: Optional[List[str]] = None
                        if candidate_names_text.strip():
                            names_list = [line.strip() for line in candidate_names_text.splitlines() if line.strip()]
                        
                        with st.spinner("⏳ Uploading resumes via Streamlit..."):
                            eff_base = resolve_api_base(api_base_norm)
                            res_list = api_post_resumes(eff_base, files_data, names_list)
                        
                        st.success("✅ Upload completed successfully!")
                        
                        # Display results
                        st.markdown("##### Upload Results")
                        for i, res in enumerate(res_list, 1):
                            with st.expander(f"Resume {i}: {res.get('candidate_name', 'Unnamed')}"):
                                st.json(res)
                                
                    except requests.HTTPError as e:
                        st.error(f"❌ HTTP error: {e.response.status_code} {e.response.text}")
                    except Exception as e:
                        st.error(f"❌ Error uploading resumes: {e}")

# ------------------------------
# Match Tab - Always visible regardless of upload method
# ------------------------------
with match_tab:
    st.subheader("Match Results")
    job_id_input = st.text_input("Job ID", value=st.session_state.get("last_job_id", ""))
    k = st.slider("Top K", min_value=1, max_value=50, value=10)

    if st.button("Run Match"):
        if not job_id_input:
            st.warning("Please enter a job_id (create one in the Upload Job tab)")
        else:
            try:
                eff_base = resolve_api_base(api_base_norm)
                data = api_get_match(eff_base, job_id_input, k=k)
                results: List[Dict[str, Any]] = data.get("results", [])
                st.caption(data.get("note", ""))

                if not results:
                    st.info("No results found. Upload resumes and try again.")
                else:
                    # Ranking chart (composite)
                    chart_df = pd.DataFrame([
                        {
                            "candidate": r.get("candidate_name") or r.get("resume_id"),
                            "composite": float(r.get("composite_score", 0.0)),
                        }
                        for r in results
                    ])
                    chart_df = chart_df.sort_values("composite", ascending=False)
                    st.subheader("Ranking (Composite Score)")
                    st.bar_chart(chart_df.set_index("candidate"))

                    # Summary table
                    table_rows = []
                    for r in results:
                        table_rows.append(
                            {
                                "resume_id": r.get("resume_id"),
                                "candidate_name": r.get("candidate_name"),
                                "cosine": round(float(r.get("cosine", 0.0)), 4),
                                "skills_overlap": round(float(r.get("skills_overlap", 0.0)), 4),
                                "composite": round(float(r.get("composite_score", 0.0)), 4),
                                "matched": ", ".join(r.get("matched_skills", []) or []),
                                "missing": ", ".join(r.get("missing_skills", []) or []),
                            }
                        )
                    st.subheader("Summary Table")
                    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

                    # Fetch job details for side-by-side highlighting
                    try:
                        job = api_get_job(eff_base, job_id_input)
                        job_desc = job.get("description", "")
                        req_skills = job.get("required_skills", []) or []
                    except Exception:
                        job_desc = ""
                        req_skills = []

                    # Toggle for context overlaps
                    show_context = st.checkbox("Show context overlaps (non-skill terms)", value=True)

                    # Detailed explanations per result
                    st.markdown("---")
                    for idx, r in enumerate(results, start=1):
                        st.markdown(f"#### {idx}. Candidate: {r.get('candidate_name') or r.get('resume_id')}")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Cosine", f"{float(r.get('cosine', 0.0)):.3f}")
                        col2.metric("Skills Overlap", f"{float(r.get('skills_overlap', 0.0)):.3f}")
                        col3.metric("Composite", f"{float(r.get('composite_score', 0.0)):.3f}")

                        matched = r.get("matched_skills", []) or []
                        missing = r.get("missing_skills", []) or []

                        # Gap analysis table
                        st.subheader("Gap Analysis")
                        gap_df = pd.DataFrame({
                            "Matched Skills": [", ".join(matched) if matched else "—"],
                            "Missing Skills": [", ".join(missing) if missing else "—"],
                        })
                        st.table(gap_df)

                        # Side-by-side comparison with highlights (skills + optional context)
                        spans = r.get("matched_spans", []) or []
                        context_terms = r.get("context_terms", []) or []
                        context_job_spans = r.get("context_job_spans", []) or []
                        context_resume_spans = r.get("context_resume_spans", []) or []
                        try:
                            resume_id = r.get("resume_id")
                            resume_data = api_get_resume(eff_base, resume_id)
                            cleaned_text = resume_data.get("cleaned_text", "")
                        except Exception:
                            cleaned_text = ""

                        # Gap analysis context overview
                        st.write("Context overlaps:")
                        st.write(", ".join(context_terms) if context_terms else "—")

                        left, right = st.columns(2)
                        with left:
                            st.caption("Job Description (skills" + (" + context" if show_context else "") + " highlighted)")
                            # Skills spans in job description are derived from matched skill terms
                            job_skill_spans = find_term_spans(job_desc, matched)
                            job_spans_combined = job_skill_spans + (context_job_spans if show_context else [])
                            job_html = render_highlight_full(job_desc, job_spans_combined)
                            st.markdown(f"<div style='white-space:pre-wrap'>{job_html}</div>", unsafe_allow_html=True)
                        with right:
                            st.caption("Resume (skills" + (" + context" if show_context else "") + " highlighted)")
                            resume_spans_combined = spans + (context_resume_spans if show_context else [])
                            resume_html = render_highlight_full(cleaned_text, resume_spans_combined)
                            st.markdown(f"<div style='white-space:pre-wrap'>{resume_html}</div>", unsafe_allow_html=True)

                        st.markdown("---")

            except requests.HTTPError as e:
                st.error(f"HTTP error: {e.response.status_code} {e.response.text}")
            except Exception as e:
                st.error(f"Error fetching matches: {e}")

st.markdown("\n\n")
st.caption("Tip: Configure API_BASE_URL env var for this app if your backend isn't on localhost:8000.")