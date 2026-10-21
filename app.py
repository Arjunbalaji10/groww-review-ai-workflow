import streamlit as st
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
import json
import re

import pandas as pd
import streamlit as st


# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DATA = ROOT / "data"
ANALYSIS = DATA / "analysis"
MCP_FILE = ROOT / "src" / "mcp_server.py"

PULSE_FILE = OUTPUTS / "weekly_product_pulse.md"
SUMMARY_FILE = OUTPUTS / "analysis_summary.md"
EMAIL_FILE = OUTPUTS / "customer_email_draft.md"
UPDATES_MD_FILE = OUTPUTS / "product_updates.md"
UPDATES_JSONL_FILE = OUTPUTS / "product_updates.jsonl"

RAW_REVIEWS_FILE = DATA / "reviews_raw.csv"
CLASSIFIED_FILE = ANALYSIS / "classified_reviews.csv"
FEE_CANDIDATES_FILE = ANALYSIS / "fee_candidate_reviews.csv"

OFFICIAL_LINKS = [
    "https://groww.in/pricing",
    "https://groww.in/help/stocks/sx-reports/what-are-the-different-charges-mentioned-in-the-report",
    "https://groww.in/help/payments/payments-charges/where-can-i-see-the-fees-i-ve-been-charged--43",
]
def call_local_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Call a tool on the local MCP server over stdio."""

    async def _call() -> str:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(MCP_FILE)],
            cwd=str(ROOT),
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

                if result.isError:
                    raise RuntimeError(
                        f"MCP tool {tool_name} returned an error."
                    )

                return "\n".join(
                    item.text
                    for item in result.content
                    if hasattr(item, "text")
                )

    return asyncio.run(_call())

# ============================================================
# Page setup
# ============================================================

st.set_page_config(
    page_title="Groww Review Intelligence",
    page_icon="ðŸ“Š",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Minimalist UI theme
# ============================================================

st.markdown("""
<style>
/* Use Streamlit's own theme variables so light/dark mode stays consistent. */
.stApp {
    background: var(--background-color);
    color: var(--text-color);
}
.block-container {
    max-width: 1180px;
    padding-top: 1.6rem;
    padding-bottom: 2.5rem;
}
h1, h2, h3, h4, p, li, label { color: var(--text-color); }
h1, h2, h3 { letter-spacing: -0.02em; }
h1 { font-size: 2rem !important; font-weight: 650 !important; }
h2 { font-size: 1.35rem !important; font-weight: 600 !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; }
p, li, label { line-height: 1.6; }

/* Sidebar: rely on theme colors instead of forcing a light or dark palette. */
section[data-testid="stSidebar"] {
    background: var(--secondary-background-color);
    border-right: 1px solid var(--border-color, rgba(128,128,128,.25));
}
section[data-testid="stSidebar"] > div { padding-top: 1.25rem; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label { color: var(--text-color) !important; }
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { opacity: .75; }
/* Kizuki-style sidebar navigation: grouped links, no radio controls. */
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4 {
    font-size: .78rem !important;
    font-weight: 600 !important;
    letter-spacing: .04em;
    text-transform: uppercase;
    opacity: .72;
    margin: 1.15rem 0 .35rem 0;
}
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    justify-content: flex-start;
    text-align: left;
    background: transparent;
    color: var(--text-color);
    border: 1px solid transparent;
    border-radius: 9px;
    min-height: 2.35rem;
    padding: .45rem .65rem;
    box-shadow: none;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--secondary-background-color);
    border-color: var(--border-color, rgba(128,128,128,.25));
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--primary-color);
    color: white !important;
    border-color: var(--primary-color);
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] p {
    color: white !important;
}

/* Cards, data, and controls use the selected Streamlit theme. */
div[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border: 1px solid var(--border-color, rgba(128,128,128,.25));
    border-radius: 12px; padding: 14px 16px;
}
div[data-testid="stMetricLabel"] { opacity: .8; }
div[data-testid="stMetricValue"] { color: var(--text-color); font-weight: 650; }
button[data-baseweb="tab"] { color: var(--text-color); font-weight: 500; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--primary-color); }
.stButton > button, .stDownloadButton > button {
    border-radius: 8px; min-height: 2.5rem; font-weight: 550;
}
.stButton > button[kind="primary"] {
    background: var(--primary-color); border-color: var(--primary-color);
    color: white;
}
details[data-testid="stExpander"] {
    background: var(--secondary-background-color);
    border: 1px solid var(--border-color, rgba(128,128,128,.25));
    border-radius: 10px;
}
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
div[data-testid="stAlert"] { border-radius: 10px; }
hr { border-color: var(--border-color, rgba(128,128,128,.25)); }
div[data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# File helpers
# ============================================================

def read_text(path: Path, fallback: str = "") -> str:
    """Read a UTF-8 text file safely."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return fallback


def read_csv(path: Path):
    """Read a CSV safely, returning None if unavailable."""
    try:
        return pd.read_csv(path)
    except (OSError, ValueError, UnicodeError, pd.errors.ParserError):
        return None


def count_words(text: str) -> int:
    """Count words while excluding Markdown formatting."""
    cleaned = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"(?m)^\s*#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"[*_`>#]", " ", cleaned)
    return len(re.findall(r"\b[\wâ€™'-]+\b", cleaned))


def extract_urls(text: str) -> list[str]:
    """Extract and normalize URLs from Markdown/text."""
    matches = re.findall(r"https?://[^\s<>\])\"']+", text)
    return sorted({url.rstrip(".,;:") for url in matches})


def is_official_https_url(url: str) -> bool:
    """Check HTTPS and the official Groww domain."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and (hostname == "groww.in" or hostname.endswith(".groww.in"))
        )
    except ValueError:
        return False


def extract_bullets(text: str) -> list[str]:
    """Return Markdown bullet lines."""
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"^\s*[-*]\s+", line)
    ]


def extract_quotes(text: str) -> list[str]:
    """Extract excerpts enclosed in straight or Unicode quotation marks."""
    patterns = [
        r"\u201c([^\u201d]+)\u201d",
        r'"([^"]{12,})"',
        r"\u2018([^\u2019]+)\u2019",
        r"`([^`]{12,})`",
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(re.findall(pattern, text))

    return list(dict.fromkeys(q.strip() for q in candidates if q.strip()))


# ============================================================
# Load current project outputs
# ============================================================

pulse = read_text(PULSE_FILE, "Weekly Product Pulse file not found.")
summary = read_text(SUMMARY_FILE, "Analysis summary file not found.")
email_draft = read_text(EMAIL_FILE, "Customer email draft file not found.")
updates_md = read_text(UPDATES_MD_FILE, "No product updates Markdown file found.")

raw_reviews = read_csv(RAW_REVIEWS_FILE)
classified_reviews = read_csv(CLASSIFIED_FILE)
fee_candidates = read_csv(FEE_CANDIDATES_FILE)

if raw_reviews is not None:
    raw_review_count = len(raw_reviews)
else:
    raw_review_count = 0

if classified_reviews is not None:
    classified_review_count = len(classified_reviews)
else:
    classified_review_count = 0


# ============================================================
# Evaluation engine
# ============================================================

def find_review_text_column(frame: pd.DataFrame | None):
    """Identify a likely review-text column."""
    if frame is None:
        return None

    candidates = [
        "review_text",
        "content",
        "text",
        "review",
        "review_content",
    ]

    lower_map = {str(col).lower(): col for col in frame.columns}

    for name in candidates:
        if name in lower_map:
            return lower_map[name]

    return None


def find_rating_column(frame: pd.DataFrame | None):
    """Identify a likely rating column."""
    if frame is None:
        return None

    lower_map = {str(col).lower(): col for col in frame.columns}

    for name in ("rating", "score", "stars"):
        if name in lower_map:
            return lower_map[name]

    return None


def find_date_column(frame: pd.DataFrame | None):
    """Identify a likely review-date column."""
    if frame is None:
        return None

    lower_map = {str(col).lower(): col for col in frame.columns}

    for name in ("date", "review_date", "at", "created_at"):
        if name in lower_map:
            return lower_map[name]

    return None


def run_evaluations() -> pd.DataFrame:
    """
    Run deterministic checks against existing project files.

    A PASS indicates that the specific programmed condition passed.
    It does not prove that all product insights are factually correct.
    """
    results = []

    def add_result(name, passed, details, severity="Required"):
        results.append({
            "Evaluation": name,
            "Result": "PASS" if bool(passed) else "FAIL",
            "Severity": severity,
            "Details": str(details),
        })

    # 1. Required output files
    add_result(
        "Weekly pulse file exists",
        PULSE_FILE.is_file() and bool(pulse.strip())
        and not pulse.startswith("Weekly Product Pulse file not found."),
        str(PULSE_FILE),
    )

    add_result(
        "Analysis summary exists",
        SUMMARY_FILE.is_file() and bool(summary.strip())
        and not summary.startswith("Analysis summary file not found."),
        str(SUMMARY_FILE),
    )

    add_result(
        "Fee/email draft file exists",
        EMAIL_FILE.is_file() and bool(email_draft.strip())
        and not email_draft.startswith("Customer email draft file not found."),
        str(EMAIL_FILE),
    )

    # 2. Weekly pulse word limit
    pulse_word_count = count_words(pulse)
    add_result(
        "Weekly pulse word limit",
        0 < pulse_word_count <= 250,
        f"{pulse_word_count} words; required range: 1â€“250.",
    )

    # 3. Customer quote count
    quotes = extract_quotes(pulse)
    add_result(
        "At least three quoted passages",
        len(quotes) >= 3,
        f"Found {len(quotes)} quoted passages. Manually confirm they are real reviews.",
    )

    # 4. Verify quoted excerpts against raw reviews linked to classified review IDs.
    quote_source = None
    review_column = find_review_text_column(classified_reviews)

    if review_column is not None:
        quote_source = classified_reviews
    elif (
        raw_reviews is not None
        and classified_reviews is not None
        and "review_id" in raw_reviews.columns
        and "review_id" in classified_reviews.columns
    ):
        classified_ids = classified_reviews[["review_id"]].dropna().drop_duplicates()
        quote_source = raw_reviews.merge(
            classified_ids,
            on="review_id",
            how="inner",
        )
        review_column = find_review_text_column(quote_source)

    if quote_source is not None and review_column and quotes:
        review_texts = (
            quote_source[review_column]
            .dropna()
            .astype(str)
            .tolist()
        )

        def normalize_quote(value: str) -> str:
            value = value.casefold()
            value = re.sub(r"[^a-z0-9]+", " ", value)
            return " ".join(value.split())

        normalized_reviews = [
            normalize_quote(review) for review in review_texts
        ]
        verified_quotes = [
            quote for quote in quotes
            if len(normalize_quote(quote)) >= 12
            and any(
                normalize_quote(quote) in review
                for review in normalized_reviews
            )
        ]
        verified_count = len(set(verified_quotes))

        add_result(
            "Quotes match classified review text",
            verified_count >= 3,
            f"{verified_count}/{len(quotes)} quoted excerpts matched classified review text.",
        )
    else:
        add_result(
            "Quotes match classified review text",
            False,
            "Could not find review text for the classified reviews or extract quotes.",
        )

    # 5. Count recommended actions under the recognized heading.
    action_heading_pattern = re.compile(
        r"(?im)^\s*#{0,4}\s*"
        r"(?:recommended\s+(?:product\s+)?actions|recommendations|"
        r"actions|next\s+steps|what\s+we\s+should\s+do|product\s+actions)"
        r"\s*:?\s*$"
    )

    action_match = action_heading_pattern.search(pulse)
    action_count = 0

    if action_match:
        remaining_text = pulse[action_match.end():]
        next_heading = re.search(r"(?m)^\s*#{1,4}\s+", remaining_text)
        if next_heading:
            remaining_text = remaining_text[:next_heading.start()]

        action_count = len(
            re.findall(
                r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)",
                remaining_text,
            )
        )

    add_result(
        "Three recommended actions",
        action_count >= 3,
        f"Found {action_count} action items under a recognized heading. Required: at least 3.",
    )

    # 6. Fee explainer bullet limit
    bullets = extract_bullets(email_draft)

    add_result(
        "Three recommended actions",
        action_count >= 3,
        f"Found {action_count} action items under a recognized heading. Required: at least 3.",
    )

    # 7. Official links in the draft and summary
    combined_text = email_draft + "\n" + summary
    links = extract_urls(combined_text)
    official_links = sorted({
        link for link in links if is_official_https_url(link)
    })

    add_result(
        "At least two official HTTPS Groww links",
        len(official_links) >= 2,
        f"Found {len(official_links)} distinct official Groww links.",
    )

    # 8. Last-checked date
    last_checked_match = re.search(
        r"(?im)last\s+checked\s*:\s*(.+)",
        email_draft,
    )

    add_result(
        "Fee explanation has last-checked date",
        bool(last_checked_match),
        (
            f"Found: {last_checked_match.group(1).strip()}"
            if last_checked_match
            else "Missing a 'Last checked:' label in the draft file."
        ),
    )

    # 9. Coverage disclosure
    pulse_has_classified_count = bool(
        re.search(r"\b865\b", pulse)
    )
    pulse_has_full_count = bool(
        re.search(r"12,?835", pulse)
    )

    add_result(
        "Review coverage disclosure",
        pulse_has_classified_count and pulse_has_full_count,
        (
            "The pulse mentions both 865 classified and 12,835 total reviews."
            if pulse_has_classified_count and pulse_has_full_count
            else "The pulse should disclose the classified subset and total dataset."
        ),
        severity="Review",
    )

    # 10. Raw dataset available and readable
    add_result(
        "Raw reviews dataset readable",
        raw_reviews is not None and len(raw_reviews) > 0,
        (
            f"Loaded {len(raw_reviews):,} rows."
            if raw_reviews is not None
            else "Raw CSV is missing or could not be read."
        ),
    )

    # 11. Basic review-data structure
    required_columns = {"review_id", "date", "rating", "review_text"}

    if raw_reviews is not None:
        actual_columns = {str(col).lower() for col in raw_reviews.columns}
        missing = sorted(required_columns - actual_columns)
        structure_ok = len(missing) == 0
    else:
        missing = sorted(required_columns)
        structure_ok = False

    add_result(
        "Raw review schema",
        structure_ok,
        (
            "Required columns found."
            if structure_ok
            else "Missing expected columns: " + ", ".join(missing)
        ),
    )

    # 12. Ratings in valid range
    rating_column = find_rating_column(raw_reviews)

    if rating_column and raw_reviews is not None:
        ratings = pd.to_numeric(raw_reviews[rating_column], errors="coerce")
        valid_ratings = ratings.notna() & ratings.between(1, 5)
        rating_ok = len(ratings) > 0 and bool(valid_ratings.all())

        add_result(
            "Ratings in range 1â€“5",
            rating_ok,
            f"{int(valid_ratings.sum())}/{len(ratings)} ratings are numeric and within 1â€“5.",
        )
    else:
        add_result(
            "Ratings in range 1â€“5",
            False,
            "Could not identify a rating column.",
        )

    # 13. Classified review data available
    add_result(
        "Classified reviews available",
        classified_reviews is not None and len(classified_reviews) > 0,
        (
            f"{len(classified_reviews):,} classified rows loaded."
            if classified_reviews is not None
            else "Classified review CSV is missing or unreadable."
        ),
    )

    # 14. MCP source contains approval checks
    mcp_code = read_text(MCP_FILE, "")

    approval_guard_present = (
        "approval_status" in mcp_code
        and "APPROVED" in mcp_code
    )

    add_result(
        "MCP approval guard in source",
        approval_guard_present,
        "Static source check only; it does not execute an approval/rejection test.",
    )

    # 15. Draft-only disclosure
    draft_discloses_not_sent = bool(
        re.search(r"(?i)\b(draft only|not sent|does not send)\b", email_draft)
    )

    add_result(
        "Email draft-only disclosure",
        draft_discloses_not_sent,
        (
            "Draft-only disclaimer found."
            if draft_discloses_not_sent
            else "Add an explicit statement that the draft is not sent automatically."
        ),
        severity="Review",
    )

    # 16. Product update files exist
    add_result(
        "Product updates Markdown available",
        UPDATES_MD_FILE.is_file() and bool(updates_md.strip())
        and not updates_md.startswith("No product updates Markdown file found."),
        str(UPDATES_MD_FILE),
        severity="Review",
    )

    # 17. Product update JSONL parses
    jsonl_ok = False
    jsonl_count = 0
    jsonl_details = "Product update JSONL file not found."

    if UPDATES_JSONL_FILE.is_file():
        try:
            lines = [
                line.strip()
                for line in UPDATES_JSONL_FILE.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            parsed_records = [json.loads(line) for line in lines]
            jsonl_count = len(parsed_records)
            jsonl_ok = all(isinstance(record, dict) for record in parsed_records)
            jsonl_details = f"{jsonl_count} valid JSON record(s)."
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            jsonl_details = f"Invalid JSONL: {type(exc).__name__}."

    add_result(
        "Product updates JSONL valid",
        jsonl_ok,
        jsonl_details,
        severity="Review",
    )

    # 18. Official URL references included in source list
    source_file = ROOT / "source_urls.md"
    source_text = read_text(source_file, "")
    source_urls = extract_urls(source_text)
    source_official_urls = sorted({
        url for url in source_urls if is_official_https_url(url)
    })

    add_result(
        "Official links in source list",
        len(source_official_urls) >= 2,
        f"Found {len(source_official_urls)} distinct official Groww links in source_urls.md.",
    )

    # 19. Fee-candidate data available
    add_result(
        "Fee candidate dataset available",
        fee_candidates is not None and len(fee_candidates) > 0,
        (
            f"{len(fee_candidates):,} candidate rows loaded."
            if fee_candidates is not None
            else "Fee-candidate CSV is missing or unreadable."
        ),
        severity="Review",
    )

    # 20. Avoid claiming all reviews were classified
    coverage_is_honest = (
        raw_review_count > 0
        and classified_review_count > 0
        and classified_review_count <= raw_review_count
    )

    add_result(
        "Classification coverage is plausible",
        coverage_is_honest,
        (
            f"{classified_review_count:,} classified out of "
            f"{raw_review_count:,} raw reviews."
        ),
    )

    return pd.DataFrame(results)


# ============================================================
# Sidebar navigation
# ============================================================

st.sidebar.markdown("## â—‰ Groww Intelligence")
st.sidebar.caption("PRODUCT FEEDBACK WORKFLOW")

# Keep navigation state across Streamlit reruns.
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "Overview"


def nav_item(label: str, icon: str, page_name: str) -> None:
    """Render one Kizuki-style sidebar navigation item."""
    button_type = "primary" if st.session_state["active_page"] == page_name else "secondary"
    if st.sidebar.button(f"{icon}  {label}", key=f"nav_{page_name}", type=button_type, use_container_width=True):
        st.session_state["active_page"] = page_name
        st.rerun()

st.sidebar.markdown("#### Analyse")
nav_item("Overview", "â–¦", "Overview")
nav_item("Weekly Pulse", "â†—", "Weekly Pulse")
nav_item("Fee Explainer", "â–¤", "Fee Explainer")
nav_item("Review Evidence", "âŒ•", "Review Evidence")

st.sidebar.markdown("#### Publish")
nav_item("Approve & Export", "âœ“", "Approve & Export")
nav_item("History", "â—·", "History")

st.sidebar.markdown("#### Quality")
nav_item("Evals", "â˜·", "Evals")

page = st.session_state["active_page"]

st.sidebar.divider()
st.sidebar.caption("MCP tools write to local files.")
st.sidebar.caption("Google Docs/Gmail are not connected.")


# ============================================================
# Header and overview metrics
# ============================================================
st.title("Groww Review Intelligence")
st.caption(
    "Turn customer feedback into product insights "
    "and approved communication."
)
st.markdown(
    "Review trends, identify fee confusion, and prepare "
    "a weekly product update."
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Reviews in dataset", f"{raw_review_count:,}")
col2.metric("Classified reviews", f"{classified_review_count:,}")
col3.metric(
    "Fee candidates",
    f"{len(fee_candidates):,}" if fee_candidates is not None else "N/A",
)
col4.metric("Human approval", "Required")


# ============================================================
# Overview
# ============================================================

if page == "Overview":
    st.subheader("Project overview")

    left, right = st.columns([1.3, 1])

    with left:
        st.markdown("### Latest weekly product pulse")
        st.markdown(pulse)

    with right:
        st.markdown("### Workflow status")
        st.write("1. Review dataset collected")
        st.write("2. Reviews validated and analyzed")
        st.write("3. Product pulse generated")
        st.write("4. Fee clarification drafted")
        st.write("5. Human approval required")
        st.write("6. Export generated on approval")

        st.warning(
            "The dashboard's approval checkbox creates a download. "
            "It does not call the MCP server or publish to Google Docs/Gmail."
        )

    with st.expander("Analysis summary"):
        st.markdown(summary)


# ============================================================
# Weekly pulse
# ============================================================

elif page == "Weekly Pulse":
    st.subheader("Weekly Product Pulse")
    st.caption(f"Word count: {count_words(pulse)} / 250")
    st.markdown(pulse)

    st.download_button(
        "Download weekly pulse",
        data=pulse,
        file_name="weekly_product_pulse.md",
        mime="text/markdown",
        key="download_pulse",
    )

    with st.expander("Analysis summary"):
        st.markdown(summary)


# ============================================================
# Fee explainer
# ============================================================

elif page == "Fee Explainer":
    st.subheader("Customer Fee Clarification")
    st.markdown(email_draft)

    st.markdown("### Official reference pages")

    for link in OFFICIAL_LINKS:
        st.markdown(f"- [{link}]({link})")

    st.caption(
        "Review the current official pages before sending any customer "
        "communication. Review complaints alone do not prove incorrect charging."
    )

    st.download_button(
        "Download fee clarification",
        data=email_draft,
        file_name="customer_fee_clarification.md",
        mime="text/markdown",
        key="download_fee",
    )


# ============================================================
# Review evidence
# ============================================================

elif page == "Review Evidence":
    st.subheader("Review Evidence")

    if raw_reviews is not None:
        st.markdown("### Raw reviews")
        st.caption(f"{len(raw_reviews):,} rows available.")

        rating_col = find_rating_column(raw_reviews)

        if rating_col:
            ratings = pd.to_numeric(
                raw_reviews[rating_col], errors="coerce"
            )
            rating_counts = (
                ratings.value_counts()
                .sort_index()
                .rename_axis("Rating")
                .reset_index(name="Reviews")
            )
            st.markdown("#### Rating distribution")
            st.bar_chart(rating_counts.set_index("Rating"))

        st.dataframe(
            raw_reviews.head(100),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.error("Raw reviews CSV is missing or unreadable.")

    if classified_reviews is not None:
        st.markdown("### Classified reviews")
        st.caption(f"{len(classified_reviews):,} rows available.")
        st.dataframe(
            classified_reviews.head(100),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Classified review CSV is missing or unreadable.")

    if fee_candidates is not None:
        with st.expander("Fee-related review candidates"):
            st.dataframe(
                fee_candidates.head(100),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# Approval and export
# ============================================================

elif page == "Approve & Export":
    st.subheader("Human approval")
    st.write(
        "Review the saved outputs before approving the local MCP actions."
    )

    approval_confirmed = st.checkbox(
        "I have reviewed the output and approve this prototype export.",
        key="prototype_approval",
    )

    if not approval_confirmed:
        st.warning("Approval pending. No MCP action has been performed.")
    else:
        payload = {
            "date": date.today().isoformat(),
            "top_themes": [
                "High Fees & Charges",
                "Bugs & Crashes",
                "Customer Support Issues",
            ],
            "weekly_pulse": pulse,
            "identified_fee_issue": (
                "Some reviewers report confusion about trading charges "
                "and final proceeds. These reports do not establish that "
                "any charge was incorrect."
            ),
            "explanation_bullets": extract_bullets(email_draft),
            "source_links": OFFICIAL_LINKS[:2],
        }

        approval_status = "APPROVED"

        st.warning(
            "Approval authorizes local document and draft-file actions only. "
            "No Google Docs or Gmail account is connected."
        )

        if st.button("Run approved MCP actions", key="run_approved_mcp"):
            try:
                import hashlib

                approval_payload = {
                    key: payload[key]
                    for key in (
                        "date",
                        "top_themes",
                        "weekly_pulse",
                        "identified_fee_issue",
                        "explanation_bullets",
                        "source_links",
                    )
                }

                serialized = json.dumps(
                    approval_payload,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                approval_hash = hashlib.sha256(
                    serialized.encode("utf-8")
                ).hexdigest()

                append_result = call_local_mcp_tool(
                    "append_to_doc",
                    {
                        **approval_payload,
                        "approval_status": approval_status,
                        "approval_hash": approval_hash,
                    },
                )

                st.write("Document action:", append_result)

                if not append_result.startswith(
                    "Approved update appended and verified"
                ):
                    st.error(
                        "Document action did not confirm success. "
                        "Email draft was not created."
                    )
                else:
                    fee_explanation = "\n".join(
                        f"- {bullet.lstrip('-* ').strip()}"
                        for bullet in payload["explanation_bullets"]
                    )

                    email_result = call_local_mcp_tool(
                        "create_email_draft",
                        {
                            "subject": (
                                "Weekly Product Pulse + Customer Clarification "
                                "â€” Groww charges"
                            ),
                            "weekly_pulse": payload["weekly_pulse"],
                            "fee_explanation": fee_explanation,
                            "approval_status": approval_status,
                        },
                    )
                    st.write("Email draft action:", email_result)
                    st.success(
                        "Local MCP actions completed. No email was sent."
                    )

            except Exception as exc:
                st.error(f"MCP action failed: {exc}")

        st.download_button(
            "Download approved update (JSON)",
            data=json.dumps(
                {
                    **payload,
                    "approval_status": approval_status,
                    "destination_status": (
                        "Local MCP actions only; no Google Docs or Gmail action."
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file_name="approved_product_update.json",
            mime="application/json",
            key="download_approved_json",
        )

        st.download_button(
            "Download approved weekly pulse (Markdown)",
            data=pulse,
            file_name="weekly_product_pulse.md",
            mime="text/markdown",
            key="download_approved_pulse",
        )

        st.download_button(
            "Download fee clarification (Markdown)",
            data=email_draft,
            file_name="customer_fee_clarification.md",
            mime="text/markdown",
            key="download_approved_fee",
        )
# ============================================================
# Evals
# ============================================================

elif page == "Evals":
    st.subheader("Quality evaluations")
    st.write(
        "Run repeatable checks against saved project outputs. A PASS means "
        "the programmed condition passed; it does not independently prove "
        "the analysis or fee facts are correct."
    )

    if st.button("Run evaluations", type="primary"):
        st.session_state["eval_results"] = run_evaluations()

    eval_results = st.session_state.get("eval_results")

    if eval_results is None:
        st.info("Click 'Run evaluations' to execute the checks.")
    else:
        passed_count = int((eval_results["Result"] == "PASS").sum())
        failed_count = int((eval_results["Result"] == "FAIL").sum())
        total_count = len(eval_results)

        c1, c2, c3 = st.columns(3)
        c1.metric("Checks passed", passed_count)
        c2.metric("Checks failed", failed_count)
        c3.metric("Total checks", total_count)

        if failed_count == 0:
            st.success("All programmed checks passed.")
        else:
            st.warning(
                f"{failed_count} check(s) failed. Review the details below."
            )

        st.dataframe(
            eval_results,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download evaluation report (CSV)",
            data=eval_results.to_csv(index=False),
            file_name="milestone5_evaluation_results.csv",
            mime="text/csv",
            key="download_eval_results",
        )

        failed_results = eval_results[eval_results["Result"] == "FAIL"]

        if not failed_results.empty:
            st.markdown("### Checks needing attention")
            for _, row in failed_results.iterrows():
                st.markdown(
                    f"- **{row['Evaluation']}** â€” {row['Details']}"
                )


# ============================================================
# History
# ============================================================

elif page == "History":
    st.subheader("Product update history")

    if UPDATES_JSONL_FILE.is_file():
        records = []
        errors = []

        try:
            lines = UPDATES_JSONL_FILE.read_text(
                encoding="utf-8"
            ).splitlines()

            for line_number, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    errors.append(line_number)

        except (OSError, UnicodeError) as exc:
            st.error(f"Unable to read update history: {exc}")

        if records:
            st.dataframe(
                pd.json_normalize(records),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No valid product update records were found.")

        if errors:
            st.warning(
                "Invalid JSON was found on line(s): "
                + ", ".join(map(str, errors))
            )
    else:
        st.info("No product update JSONL file exists yet.")

    with st.expander("Readable product updates"):
        st.markdown(updates_md)


# ============================================================
# Footer
# ============================================================

st.divider()
st.caption(
    "Milestone 5 prototype Â· Human review required Â· "
    "Local file outputs Â· No automatic email sending"
)

