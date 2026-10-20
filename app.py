from pathlib import Path
from datetime import date
import json

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DATA = ROOT / "data"

st.set_page_config(
    page_title="Groww Review Intelligence",
    page_icon="📊",
    layout="wide",
)

def read_text(path: Path, fallback: str = "File not found.") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return fallback

def read_csv(path: Path):
    try:
        return pd.read_csv(path)
    except (OSError, ValueError, UnicodeError):
        return None

pulse = read_text(OUTPUTS / "weekly_product_pulse.md")
summary = read_text(OUTPUTS / "analysis_summary.md")
fee_draft = read_text(OUTPUTS / "customer_email_draft.md")
updates = read_text(OUTPUTS / "product_updates.md")
reviews = read_csv(DATA / "reviews_raw.csv")
classified = read_csv(DATA / "analysis" / "classified_reviews.csv")

st.title("📊 Groww Review Intelligence")
st.caption("Milestone 5 · Customer feedback → product insights → human approval")

st.info(
    "Prototype mode: this app displays saved project outputs and prepares "
    "an approval package for download. It does not send emails or write to "
    "Google Docs/Gmail."
)

# Dashboard metrics
m1, m2, m3 = st.columns(3)

m1.metric(
    "Reviews in dataset",
    f"{len(reviews):,}" if reviews is not None else "Unavailable",
)
m2.metric(
    "Classified reviews",
    f"{len(classified):,}" if classified is not None else "Unavailable",
)
m3.metric("Approval required", "Yes")

pulse_tab, fee_tab, reviews_tab, approval_tab = st.tabs(
    [
        "Weekly Product Pulse",
        "Fee Clarification",
        "Review Evidence",
        "Approval & Export",
    ]
)

with pulse_tab:
    st.subheader("Weekly product pulse")
    st.markdown(pulse)

    with st.expander("Analysis summary"):
        st.markdown(summary)

    with st.expander("Previously approved product updates"):
        st.markdown(updates)

with fee_tab:
    st.subheader("Customer fee clarification")
    st.markdown(fee_draft)

    st.markdown("**Official reference pages**")
    st.markdown("[Groww pricing](https://groww.in/pricing)")
    st.markdown(
        "[Charges in the report](https://groww.in/help/stocks/"
        "sx-reports/what-are-the-different-charges-mentioned-in-the-report)"
    )
    st.markdown(
        "[Where to see fees charged](https://groww.in/help/payments/"
        "payments-charges/where-can-i-see-the-fees-i-ve-been-charged--43)"
    )
    st.caption(
        "Verify the current official pages before sending any customer "
        "communication. Review complaints alone do not prove incorrect charging."
    )

with reviews_tab:
    st.subheader("Review evidence")

    if reviews is not None:
        st.write("Raw review sample")
        st.dataframe(reviews.head(100), use_container_width=True)

        if "rating" in reviews.columns:
            st.write("Rating distribution")
            ratings = (
                reviews["rating"]
                .value_counts()
                .sort_index()
                .rename_axis("Rating")
                .reset_index(name="Reviews")
            )
            st.bar_chart(ratings.set_index("Rating"))
    else:
        st.warning("The raw review CSV was not found.")

    if classified is not None:
        st.write("Classified review sample")
        st.dataframe(classified.head(100), use_container_width=True)

with approval_tab:
    st.subheader("Human approval gate")
    st.write(
        "Review the pulse and fee clarification before approving this "
        "export. Approval here prepares a downloadable record only."
    )

    confirmed = st.checkbox(
        "I reviewed the output and approve this prototype export."
    )

    if confirmed:
        payload = {
            "date": date.today().isoformat(),
            "top_themes": [
                "High Fees & Charges",
                "Bugs & Crashes",
                "Customer Support Issues",
                "Performance & Speed Issues",
                "Missing Features & Functionality",
            ],
            "weekly_pulse": pulse,
            "identified_fee_issue": (
                "Some reviewers report confusion about trading charges "
                "and final proceeds. These reports are not proof of "
                "incorrect charges."
            ),
            "explanation_bullets": [
                line.lstrip("- ").strip()
                for line in fee_draft.splitlines()
                if line.strip().startswith("-")
            ],
            "source_links": [
                "https://groww.in/pricing",
                "https://groww.in/help/stocks/sx-reports/"
                "what-are-the-different-charges-mentioned-in-the-report",
                "https://groww.in/help/payments/payments-charges/"
                "where-can-i-see-the-fees-i-ve-been-charged--43",
            ],
            "approval_status": "APPROVED",
            "destination_status": (
                "Download only; no Google Docs or Gmail action performed."
            ),
        }

        st.success("Prototype export approved.")
        st.download_button(
            "Download approved update (JSON)",
            data=json.dumps(payload, ensure_ascii=False, indent=2),
            file_name="approved_product_update.json",
            mime="application/json",
        )

        st.download_button(
            "Download weekly pulse (Markdown)",
            data=pulse,
            file_name="weekly_product_pulse.md",
            mime="text/markdown",
        )
    else:
        st.warning("Pending your review. No export is marked approved.")

st.divider()
st.caption(
    "Milestone 5 prototype · Saved analysis outputs · "
    "Human review required · No automatic email sending"
)