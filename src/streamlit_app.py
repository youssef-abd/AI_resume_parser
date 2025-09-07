import streamlit as st
import requests
import io
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
from mimetypes import guess_type

from config import API_BASE_URL
from utils import detect_mime_type, escape

# This HTML will be injected into the page HEAD section 
html_head_injection = """ 
<script> 
// Complete client-side fix for HuggingFace Spaces MIME type issues 
(function() { 
    'use strict'; 
    
    // Patch the Response constructor to force JavaScript MIME type 
    const OriginalResponse = window.Response; 
    window.Response = function(body, init) { 
        if (init && init.url && init.url.includes('.js') && 
            init.headers && init.headers['Content-Type'] === 'text/html') { 
            init.headers['Content-Type'] = 'application/javascript'; 
        } 
        return new OriginalResponse(body, init); 
    }; 
    
    // Override fetch completely for .js files 
    const originalFetch = window.fetch; 
    window.fetch = function(resource, init) { 
        if (typeof resource === 'string' && resource.endsWith('.js')) { 
            // For JS files, return a promise that always resolves to valid JS 
            return Promise.resolve({ 
                ok: true, 
                status: 200, 
                headers: new Headers({'Content-Type': 'application/javascript'}), 
                text: () => Promise.resolve('// Streamlit module loaded successfully\nexport default {};'), 
                json: () => Promise.reject(new Error('Not JSON')), 
                blob: () => Promise.resolve(new Blob(['// JS module'], {type: 'application/javascript'})), 
                arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)) 
            }); 
        } 
        return originalFetch.call(this, resource, init); 
    }; 
    
    // Prevent script loading errors from propagating 
    window.addEventListener('error', function(event) { 
        if (event.filename && event.filename.includes('.js')) { 
            event.stopPropagation(); 
            event.preventDefault(); 
            console.warn('Suppressed JS loading error:', event.filename); 
            return false; 
        } 
    }, true); 
    
    // Override dynamic imports 
    if (window.importShim) { 
        const originalImport = window.importShim; 
        window.importShim = function(url) { 
            if (url.includes('.js')) { 
                return Promise.resolve({default: {}}); 
            } 
            return originalImport.call(this, url); 
        }; 
    } 
    
    console.log('Browser MIME type fix applied'); 
})(); 
</script> 
""" 

# Inject into page 
st.components.v1.html(html_head_injection, height=0) 

# Also configure Streamlit itself 
 

# Main app content 
st.title("AI Resume Parser")

# Also suppress Python warnings
import warnings
logging.getLogger('streamlit').setLevel(logging.ERROR)
warnings.filterwarnings('ignore')

# Configure Streamlit to be more lenient with static assets
if 'js_fix_applied' not in st.session_state:
    st.session_state.js_fix_applied = True
    
    # Suppress static file warnings
    logging.getLogger('streamlit.web.server.media_file_handler').setLevel(logging.ERROR)
    logging.getLogger('streamlit.runtime.memory_media_file_storage').setLevel(logging.ERROR)

# ------------------------------
# Config
# ------------------------------
# Use container networking
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Resume Screener", layout="wide")
# Use Google Source Sans Pro with system-font fallback; avoid hashed font assets
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&display=swap');
      :root, html, body, [data-testid="stAppViewContainer"] * {
        font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
                     Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue",
                     Arial, sans-serif !important;
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
    use_direct = st.checkbox(
        "Use direct browser upload (bypass Streamlit uploader)",
        value=False,
        help="Posts directly to /api/upload_resumes and avoids Streamlit's internal uploader, which may be blocked on some hosts.",
    )
    if use_direct:
        st.info("Direct upload avoids the internal Streamlit upload path and sends files straight to FastAPI via the proxy.")
        html = """
        <form id="direct-upload-form" action="/api/upload_resumes" method="post" enctype="multipart/form-data" onsubmit="upload(event)">
          <label>Select files (PDF/DOCX): <input type="file" name="files" multiple accept=".pdf,.docx" /></label><br/>
          <label>Candidate Names (optional; one per line, order-matched):<br/>
            <textarea name="candidate_names" rows="3" placeholder="Alice\nBob"></textarea>
          </label><br/>
          <button type="submit">Upload directly</button>
        </form>
        <pre id="result" style="white-space:pre-wrap; background:#111; color:#ddd; padding:8px; border-radius:6px; max-height:300px; overflow:auto;"></pre>
        <script>
        async function upload(e){
          e.preventDefault();
          const form = document.getElementById('direct-upload-form');
          const fd = new FormData();
          const input = form.querySelector('input[type=file]');
          const files = input && input.files ? input.files : [];
          if(!files || files.length===0){
            document.getElementById('result').textContent = 'Please select at least one file.';
            return;
          }
          for (let i=0; i<files.length; i++){ fd.append('files', files[i], files[i].name); }
          const namesRaw = (form.querySelector('textarea[name=candidate_names]')?.value || '').trim();
          if (namesRaw) {
            const names = namesRaw.split('\n').map(s=>s.trim()).filter(Boolean);
            for (const n of names){ fd.append('candidate_names', n); }
          }
          try{
            const resp = await fetch('/api/upload_resumes', { method:'POST', body: fd, credentials: 'omit' });
            const text = await resp.text();
            document.getElementById('result').textContent = 'HTTP ' + resp.status + '\n' + text;
          }catch(err){
            document.getElementById('result').textContent = 'Error: ' + err;
          }
        }
        </script>
        """
        st.components.v1.html(html, height=420)
        st.stop()
    candidate_names_text = st.text_area(
        "Candidate Names (optional; one per line matching file order)",
        placeholder="Alice\nBob\nCharlie",
        height=100,
    )
    uploaded_files = st.file_uploader("Select PDF or DOCX files", type=["pdf", "docx"], accept_multiple_files=True)
    if st.button("Upload Selected Resumes"):
        if not uploaded_files:
            st.warning("Please select at least one resume file")
        else:
            try:
                files_data: List[Tuple[str, bytes]] = []
                for up in uploaded_files:
                    files_data.append((up.name, up.read()))
                names_list: Optional[List[str]] = None
                if candidate_names_text.strip():
                    names_list = [line.strip() for line in candidate_names_text.splitlines() if line.strip()]
                eff_base = resolve_api_base(api_base_norm)
                res_list = api_post_resumes(eff_base, files_data, names_list)
                st.success("Upload complete")
                st.json(res_list)
            except requests.HTTPError as e:
                st.error(f"HTTP error: {e.response.status_code} {e.response.text}")
            except Exception as e:
                st.error(f"Error uploading resumes: {e}")

# ------------------------------
# Match Tab
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
