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

st.set_page_config(
    page_title="AI Resume Screener", 
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# Enhanced styling with modern UI
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
      
      :root, html, body, [data-testid="stAppViewContainer"] * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
                     Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue",
                     Arial, sans-serif !important;
      }
      
      /* Main app styling */
      .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
      }
      
      /* Header styling */
      h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
        font-size: 3rem !important;
        text-align: center;
        margin-bottom: 2rem;
      }
      
      /* Tab styling */
      .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 8px;
        border-radius: 12px;
        margin-bottom: 2rem;
      }
      
      .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 24px;
        background: transparent;
        border-radius: 8px;
        color: #495057;
        font-weight: 500;
        border: none;
        transition: all 0.3s ease;
      }
      
      .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
      }
      
      /* Form styling */
      .stTextInput > div > div > input,
      .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 2px solid #e9ecef;
        transition: all 0.3s ease;
      }
      
      .stTextInput > div > div > input:focus,
      .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
      }
      
      /* Button styling */
      .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      }
      
      .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
      }
      
      /* Sidebar styling */
      .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
      }
      
      /* Metrics styling */
      [data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e9ecef;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      }
      
      /* Success/Error message styling */
      .stSuccess {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-left: 4px solid #28a745;
        border-radius: 8px;
      }
      
      .stError {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-left: 4px solid #dc3545;
        border-radius: 8px;
      }
      
      .stInfo {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        border-left: 4px solid #17a2b8;
        border-radius: 8px;
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
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="margin-bottom: 0.5rem;">🎯 AI Resume Screener</h1>
    <p style="font-size: 1.2rem; color: #6c757d; margin: 0;">
        Intelligent resume matching powered by AI • Fast • Accurate • Scalable
    </p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    api_base = st.text_input(
        "🌐 API Base URL", 
        value=API_BASE_URL, 
        help="Point to your FastAPI server endpoint"
    )
    api_base_norm = normalize_api_base(api_base)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Check Status", use_container_width=True):
            with st.spinner("Checking..."):
                try:
                    resolved = resolve_api_base(api_base_norm)
                    r = requests.get(f"{resolved.rstrip('/')}/readyz", timeout=10)
                    ok = r.status_code == 200
                    if ok:
                        st.success(f"✅ API Ready ({r.status_code})")
                        if r.headers.get('content-type', '').startswith('application/json'):
                            st.json(r.json())
                    else:
                        st.error(f"❌ API Error ({r.status_code})")
                        st.code(r.text)
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")
    
    with col2:
        st.metric("Endpoint", "Ready" if api_base_norm else "Not Set")

    st.markdown("---")
    
    # System info
    st.markdown("### 📊 System Info")
    st.markdown("""
    **Backend Stack:**
    - 🚀 FastAPI (REST API)
    - 🧠 sentence-transformers (Embeddings)
    - 📝 spaCy (NLP Processing)  
    - 🗄️ PostgreSQL + pgvector (Vector DB)
    
    **Features:**
    - ✨ Semantic similarity matching
    - 🎯 Skills extraction & analysis
    - 📈 Composite scoring algorithm
    - 🔍 Context-aware highlighting
    """)
    
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.info("""
    **For best results:**
    - Use detailed job descriptions
    - Include specific required skills
    - Upload resumes in PDF/DOCX format
    - Ensure file names are descriptive
    """)
    
    st.markdown("---")
    st.caption("🔧 Configure API_BASE_URL environment variable if your backend isn't on localhost:8000")

# Tabs with icons and better names
job_tab, resume_tab, match_tab = st.tabs(["💼 Create Job", "📄 Upload Resumes", "🎯 Match & Analyze"])

# ------------------------------
# Upload Job Tab
# ------------------------------
with job_tab:
    st.markdown("### 💼 Create Job Posting")
    st.markdown("Define the job requirements and description to match against candidate resumes")
    
    with st.form("job_form", clear_on_submit=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            title = st.text_input(
                "🏷️ Job Title", 
                value="Software Engineer (Backend/AI)", 
                max_chars=255,
                help="Enter a clear, descriptive job title"
            )
            
        with col2:
            st.markdown("#### 📊 Quick Stats")
            if st.session_state.get("last_job_id"):
                st.success(f"✅ Last Job ID: `{st.session_state['last_job_id']}`")
            else:
                st.info("No job created yet")
        
        description = st.text_area(
            "📝 Job Description",
            height=300,
            value=(
                "**About the Role**\n\n"
                "We are looking for a Software Engineer with strong backend and data engineering experience who can also apply modern AI/ML techniques.\n\n"
                "**Responsibilities**\n"
                "• Build scalable APIs and microservices\n"
                "• Design and implement data pipelines\n"
                "• Deploy and maintain AI/ML models in production\n"
                "• Collaborate with cross-functional teams\n\n"
                "**Requirements**\n"
                "• 3+ years of backend development experience\n"
                "• Strong proficiency in Python and SQL\n"
                "• Experience with containerization (Docker, Kubernetes)\n"
                "• Cloud platform experience (AWS, GCP, or Azure)\n"
                "• Understanding of ML model deployment\n\n"
                "**Nice to Have**\n"
                "• Experience with FastAPI or similar frameworks\n"
                "• Knowledge of vector databases\n"
                "• MLOps experience"
            ),
            help="Provide a detailed job description including responsibilities, requirements, and qualifications"
        )
        
        required_skills_text = st.text_area(
            "🎯 Required Skills (Optional)",
            placeholder="Enter skills separated by commas or new lines:\n\npython, sql, docker, kubernetes, aws, gcp, fastapi, postgresql, redis, machine learning, data engineering",
            height=100,
            help="List specific skills that are required for this position. These will be used for skill matching."
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit = st.form_submit_button("🚀 Create Job Posting", use_container_width=True)

    if submit:
        if not title.strip():
            st.error("❌ Job title is required")
        elif not description.strip():
            st.error("❌ Job description is required")
        else:
            with st.spinner("Creating job posting..."):
                try:
                    eff_base = resolve_api_base(api_base_norm)
                    res = api_post_job_form(eff_base, title, description, required_skills_text or None)
                    st.session_state["last_job_id"] = res.get("job_id", "")
                    
                    st.success("✅ Job posting created successfully!")
                    
                    # Display results in a nice format
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Job ID", res.get("job_id", "N/A"))
                        st.metric("Status", res.get("status", "Created"))
                    
                    with col2:
                        if "required_skills" in res and res["required_skills"]:
                            st.write("**Extracted Skills:**")
                            skills = res["required_skills"]
                            if isinstance(skills, list):
                                st.write(", ".join(skills))
                            else:
                                st.write(skills)
                    
                    with st.expander("📋 View Full Response", expanded=False):
                        st.json(res)
                        
                except requests.HTTPError as e:
                    st.error(f"❌ HTTP error: {e.response.status_code}")
                    with st.expander("Error Details"):
                        st.code(e.response.text)
                except Exception as e:
                    st.error(f"❌ Error creating job: {str(e)}")

    # Show current job info if available
    if st.session_state.get("last_job_id"):
        st.markdown("---")
        st.markdown("#### 📋 Current Job Summary")
        job_col1, job_col2 = st.columns([3, 1])
        
        with job_col1:
            st.info(f"**Job ID:** `{st.session_state['last_job_id']}`\n\n**Title:** {title}")
        
        with job_col2:
            if st.button("🔄 Refresh Job", help="Fetch latest job details from API"):
                try:
                    eff_base = resolve_api_base(api_base_norm)
                    job_data = api_get_job(eff_base, st.session_state['last_job_id'])
                    st.success("Job data refreshed!")
                    with st.expander("Job Details"):
                        st.json(job_data)
                except Exception as e:
                    st.error(f"Failed to refresh: {e}")

# ------------------------------
# Upload Resume Tab
# ------------------------------
with resume_tab:
    st.subheader("📄 Upload Resumes")
    st.markdown("**Direct browser upload** - Files are sent directly to the API for processing")
    
    # Enhanced direct upload interface
    html = """
    <style>
        .upload-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 30px;
            margin: 20px 0;
            color: white;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .upload-form {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 8px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .file-input-wrapper {
            position: relative;
            display: inline-block;
            width: 100%;
            margin-bottom: 20px;
        }
        .file-input {
            width: 100%;
            padding: 15px;
            border: 2px dashed rgba(255,255,255,0.5);
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .file-input:hover {
            border-color: rgba(255,255,255,0.8);
            background: rgba(255,255,255,0.2);
        }
        .file-input::file-selector-button {
            background: rgba(255,255,255,0.2);
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 600;
            margin-right: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .file-input::file-selector-button:hover {
            background: rgba(255,255,255,0.3);
        }
        .names-textarea {
            width: 100%;
            padding: 15px;
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 14px;
            resize: vertical;
            min-height: 100px;
            margin-bottom: 20px;
        }
        .names-textarea::placeholder {
            color: rgba(255,255,255,0.7);
        }
        .upload-btn {
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .upload-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        .upload-btn:disabled {
            background: rgba(255,255,255,0.3);
            cursor: not-allowed;
            transform: none;
        }
        .result-container {
            margin-top: 20px;
            padding: 20px;
            background: rgba(0,0,0,0.8);
            border-radius: 8px;
            border-left: 4px solid #00d4aa;
        }
        .result-text {
            color: #00ff88;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
            margin: 0;
        }
        .file-info {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 6px;
            margin: 10px 0;
            font-size: 14px;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
            overflow: hidden;
            margin: 10px 0;
            display: none;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4aa, #00ff88);
            width: 0%;
            transition: width 0.3s ease;
        }
        .label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 16px;
        }
    </style>
    
    <div class="upload-container">
        <h3 style="margin-top: 0; text-align: center;">🚀 Resume Upload Center</h3>
        <div class="upload-form">
            <form id="direct-upload-form" onsubmit="upload(event)">
                <label class="label">📁 Select Resume Files (PDF/DOCX)</label>
                <input type="file" name="files" multiple accept=".pdf,.docx" class="file-input" onchange="showFileInfo()" />
                <div id="file-info" class="file-info" style="display: none;"></div>
                
                <label class="label">👥 Candidate Names (Optional)</label>
                <textarea name="candidate_names" class="names-textarea" placeholder="Enter candidate names, one per line:&#10;Alice Johnson&#10;Bob Smith&#10;Charlie Brown&#10;&#10;Note: Order should match file selection order"></textarea>
                
                <div class="progress-bar" id="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                
                <button type="submit" class="upload-btn" id="upload-btn">
                    📤 Upload Resumes
                </button>
            </form>
        </div>
        
        <div id="result-container" class="result-container" style="display: none;">
            <h4 style="margin-top: 0; color: #00ff88;">📊 Upload Results</h4>
            <pre id="result" class="result-text"></pre>
        </div>
    </div>

    <script>
        function showFileInfo() {
            const input = document.querySelector('input[type=file]');
            const fileInfo = document.getElementById('file-info');
            const files = input.files;
            
            if (files && files.length > 0) {
                let info = `Selected ${files.length} file(s):\\n`;
                for (let i = 0; i < files.length; i++) {
                    const size = (files[i].size / 1024 / 1024).toFixed(2);
                    info += `${i + 1}. ${files[i].name} (${size} MB)\\n`;
                }
                fileInfo.textContent = info;
                fileInfo.style.display = 'block';
            } else {
                fileInfo.style.display = 'none';
            }
        }
        
        async function upload(e) {
            e.preventDefault();
            
            const form = document.getElementById('direct-upload-form');
            const uploadBtn = document.getElementById('upload-btn');
            const resultContainer = document.getElementById('result-container');
            const resultElement = document.getElementById('result');
            const progressBar = document.getElementById('progress-bar');
            const progressFill = document.getElementById('progress-fill');
            
            const input = form.querySelector('input[type=file]');
            const files = input && input.files ? input.files : [];
            
            if (!files || files.length === 0) {
                resultElement.textContent = '⚠️ Please select at least one resume file.';
                resultContainer.style.display = 'block';
                return;
            }
            
            // Show progress and disable button
            uploadBtn.disabled = true;
            uploadBtn.textContent = '⏳ Uploading...';
            progressBar.style.display = 'block';
            progressFill.style.width = '20%';
            resultContainer.style.display = 'none';
            
            const fd = new FormData();
            
            // Add files
            for (let i = 0; i < files.length; i++) {
                fd.append('files', files[i], files[i].name);
            }
            
            // Add candidate names if provided
            const namesRaw = (form.querySelector('textarea[name=candidate_names]')?.value || '').trim();
            if (namesRaw) {
                const names = namesRaw.split('\\n').map(s => s.trim()).filter(Boolean);
                for (const n of names) {
                    fd.append('candidate_names', n);
                }
            }
            
            try {
                progressFill.style.width = '60%';
                
                const resp = await fetch('/api/upload_resumes', {
                    method: 'POST',
                    body: fd,
                    credentials: 'omit'
                });
                
                progressFill.style.width = '90%';
                
                const text = await resp.text();
                let result = '';
                
                if (resp.ok) {
                    result = '✅ Upload Successful!\\n\\n';
                    try {
                        const jsonData = JSON.parse(text);
                        if (Array.isArray(jsonData)) {
                            result += `📊 Processed ${jsonData.length} resume(s):\\n\\n`;
                            jsonData.forEach((item, index) => {
                                result += `${index + 1}. Resume ID: ${item.resume_id || 'N/A'}\\n`;
                                result += `   Candidate: ${item.candidate_name || 'Unnamed'}\\n`;
                                result += `   Status: ${item.status || 'Unknown'}\\n\\n`;
                            });
                        } else {
                            result += JSON.stringify(jsonData, null, 2);
                        }
                    } catch {
                        result += text;
                    }
                } else {
                    result = `❌ Upload Failed (HTTP ${resp.status})\\n\\n${text}`;
                }
                
                progressFill.style.width = '100%';
                resultElement.textContent = result;
                resultContainer.style.display = 'block';
                
            } catch (err) {
                resultElement.textContent = `💥 Network Error: ${err.message}`;
                resultContainer.style.display = 'block';
            } finally {
                // Reset UI
                setTimeout(() => {
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = '📤 Upload Resumes';
                    progressBar.style.display = 'none';
                    progressFill.style.width = '0%';
                }, 1000);
            }
        }
    </script>
    """
    
    st.components.v1.html(html, height=600)

# ------------------------------
# Match Tab
# ------------------------------
with match_tab:
    st.markdown("### 🎯 Resume Matching Results")
    st.markdown("Analyze and rank resumes against your job requirements using AI-powered matching")
    
    # Input section with better layout
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        job_id_input = st.text_input(
            "🆔 Job ID", 
            value=st.session_state.get("last_job_id", ""),
            help="Enter the Job ID from the job creation step"
        )
    
    with col2:
        k = st.slider(
            "📊 Top K Results", 
            min_value=1, 
            max_value=50, 
            value=10,
            help="Number of top matches to display"
        )
    
    with col3:
        st.markdown("#### 🚀 Actions")
        match_button = st.button("🔍 Run Matching", use_container_width=True, type="primary")

    if match_button:
        if not job_id_input:
            st.warning("⚠️ Please enter a job_id (create one in the Upload Job tab)")
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
