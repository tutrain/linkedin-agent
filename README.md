# TuTrain LinkedIn Educator Discovery Agent

Discover LinkedIn profiles of educators, tutors, principals, directors, and EdTech leaders for B2B collaboration outreach.

## Features

- **SerpAPI Google Dorking** — Find LinkedIn profiles via smart search queries
- **Apify LinkedIn Enrichment** — Scrape full profiles with multi-key rotation
- **Hard Filters** — Location, brand blacklist, connection range, education relevance
- **Gemini AI Classification** — Classify personas (Tutor, Principal, Founder, etc.)
- **Contact Extraction & Tier Scoring** — Extract emails/phones, assign priority tiers
- **Deep Filtering Loop** — Iteratively discover until target count is reached
- **Dashboard & CSV Export** — Visualizations, KPI cards, and downloadable reports

## Deployment

This app is deployed on [Streamlit Cloud](https://streamlit.io/cloud).

### API Keys Required

Add the following keys in **Streamlit Cloud → Settings → Secrets** (TOML format):

```toml
SERPAPI_KEY = "your_serpapi_key_here"
GOOGLE_API_KEY = "your_google_gemini_api_key_here"
APIFY_KEY_1 = "your_apify_key_1_here"
APIFY_KEY_2 = "your_apify_key_2_here"
APIFY_KEY_3 = "your_apify_key_3_here"
APIFY_KEY_4 = "your_apify_key_4_here"
```

### Local Development

1. Clone this repo
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your keys
4. Run: `streamlit run app.py`

## Tech Stack

- **Streamlit** — UI framework
- **SerpAPI** — Google search results
- **Apify** — LinkedIn profile scraping
- **Google Gemini** — AI classification
- **Pandas** / **Plotly** — Data processing & visualization
