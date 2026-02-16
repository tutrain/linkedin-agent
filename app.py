"""
TuTrain LinkedIn Educator Discovery Agent — Phase 1-7
SerpAPI Discovery → Apify Enrichment → Hard Filters → AI Classification → Contact & Tiering → Deep Loop → Dashboard
"""

import streamlit as st
import pandas as pd
import re
import time
import warnings
import json
import google.generativeai as genai
import plotly.express as px
from datetime import datetime

warnings.filterwarnings("ignore")

# ————————————————————————————————————————————————————————————————————————————
# CONSTANTS
# ──────────────────────────────────────────────

INSTITUTE_KEYWORDS = [
    'Academy', 'Institute', 'Classes', 'Coaching', 'Tutorial', 'School',
    'Education', 'Center', 'Hub', 'Campus', 'Group', 'Team',
    'System', 'Official', 'Centre', 'Learning', 'Foundation'
]

BRAND_BLACKLIST = [
    'PW', 'Physics Wallah', 'Unacademy', 'Vedantu', 'Byju', 'Allen',
    'Adda247', 'Sankalp', 'Magnet Brains', 'Xylem', 'Utkarsh',
    'Motion', 'Careerwill', 'Apna College', 'Infinity Learn', 'Doubtnut',
    'Mahendra', 'Wi-Fi Study', 'Exampur', 'Next Toppers',
    'Infosys', 'TCS', 'Wipro', 'HCL', 'Accenture', 'Cognizant',
    'Amazon', 'Google', 'Microsoft', 'Meta', 'Facebook', 'Apple', 'OpenAI',
    'Flipkart', 'Zomato', 'Swiggy', 'Paytm', 'Ola', 'Uber'
]

EDUCATION_ROLES = [
    'teacher', 'tutor', 'educator', 'professor', 'lecturer', 'faculty',
    'principal', 'vice principal', 'director', 'head of department', 'hod',
    'academic head', 'dean', 'founder', 'co-founder', 'ceo', 'coo', 'cto',
    'owner', 'managing director', 'administrator', 'coordinator'
]

INDIAN_CITIES = [
    "Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Jaipur", "Lucknow", "Kota", "Patna", "Chandigarh",
    "Ahmedabad", "Indore", "Bhopal", "Nagpur", "Varanasi", "Ranchi",
    "Dehradun", "Allahabad", "Noida", "Gurgaon", "Sikar", "Jodhpur"
]

SYSTEM_PAGES = [
    'login', 'signup', 'jobs', 'feed', 'mynetwork', 'messaging',
    'notifications', 'learning', 'pulse', 'posts', 'company/login'
]

# Safety Limits
MAX_SERPAPI_QUERIES = 50
MAX_APIFY_SCRAPES = 300
MAX_GEMINI_CALLS = 300

ROLE_OPTIONS = [
    "All Roles", "Tutor/Teacher", "Principal/Director",
    "Founder/CEO", "HOD/Academic Head", "Coaching Owner"
]

CITY_OPTIONS = ["All Cities"] + INDIAN_CITIES

# Phase 3 — Hard Filter Constants
EDUCATION_KEYWORDS = [
    'teacher', 'tutor', 'educator', 'professor', 'lecturer', 'faculty',
    'principal', 'vice principal', 'director of education', 'academic',
    'head of department', 'hod', 'dean', 'coaching', 'classes',
    'school', 'academy', 'institute', 'college', 'university',
    'cbse', 'icse', 'igcse', 'ib', 'cambridge', 'neet', 'jee',
    'curriculum', 'pedagogy', 'learning', 'education', 'edtech',
    'tuition', 'teaching', 'instruction', 'mentoring', 'training',
    'mathematics', 'physics', 'chemistry', 'biology', 'english', 'science',
    'founder', 'ceo', 'coo', 'managing director'
]

NON_EDUCATION_KEYWORDS = [
    'software engineer', 'data scientist', 'product manager', 'marketing',
    'sales executive', 'business development', 'consultant', 'analyst',
    'recruiter', 'hr manager', 'finance', 'banking', 'real estate',
    'insurance', 'automotive', 'hospitality', 'retail'
]

INDIA_INDICATORS = [
    'india', 'delhi', 'mumbai', 'bangalore', 'bengaluru', 'hyderabad',
    'chennai', 'kolkata', 'pune', 'jaipur', 'lucknow', 'kota', 'patna',
    'chandigarh', 'ahmedabad', 'indore', 'bhopal', 'nagpur', 'varanasi',
    'ranchi', 'dehradun', 'noida', 'gurgaon', 'gurugram', 'greater noida',
    'ghaziabad', 'faridabad', 'new delhi', 'navi mumbai', 'thane',
    'karnataka', 'maharashtra', 'tamil nadu', 'telangana', 'kerala',
    'uttar pradesh', 'rajasthan', 'gujarat', 'madhya pradesh', 'bihar',
    'west bengal', 'andhra pradesh', 'odisha', 'jharkhand', 'haryana', 'punjab'
]

MIN_CONNECTIONS = 100
MAX_CONNECTIONS = 30000
MIN_COMPANY_FOLLOWERS = 50
MAX_COMPANY_FOLLOWERS = 500000


# ──────────────────────────────────────────────
# APIFY KEY MANAGER — Multi-Key Rotation
# ──────────────────────────────────────────────

class ApifyKeyManager:
    """Manage multiple Apify API keys with auto-rotation on quota exhaustion."""

    def __init__(self, keys: list):
        self.keys = [k for k in keys if k]
        self.current_index = 0
        self.exhausted_keys: set[int] = set()

    def get_current_key(self) -> str | None:
        """Return current active key, or None if all exhausted."""
        while self.current_index < len(self.keys):
            if self.current_index not in self.exhausted_keys:
                return self.keys[self.current_index]
            self.current_index += 1
        return None

    def mark_exhausted(self) -> str | None:
        """Mark current key as exhausted and rotate to next."""
        self.exhausted_keys.add(self.current_index)
        self.current_index += 1
        if self.current_index < len(self.keys):
            return self.keys[self.current_index]
        return None

    def get_status(self) -> str:
        """Return status string for sidebar display."""
        active = len(self.keys) - len(self.exhausted_keys)
        if not self.keys:
            return "No Apify keys loaded"
        return f"{active}/{len(self.keys)} keys active (using key #{self.current_index + 1})"

    def has_keys(self) -> bool:
        return len(self.keys) > 0

    def is_exhausted(self) -> bool:
        return self.get_current_key() is None


# ──────────────────────────────────────────────
# HELPER: load a secret with sidebar fallback
# ──────────────────────────────────────────────

def _load_key(secret_name: str, label: str, sidebar_container) -> str:
    """Try st.secrets first, then show a sidebar text_input."""
    value = ""
    try:
        value = st.secrets.get(secret_name, "")
    except Exception:
        pass
    if not value:
        value = sidebar_container.text_input(label, type="password", key=f"input_{secret_name}")
    return value.strip() if value else ""


# ──────────────────────────────────────────────
# SERPAPI QUERY GENERATOR
# ──────────────────────────────────────────────

def generate_linkedin_queries(subject: str, roles: list, cities: list, round_num: int) -> list:
    """
    Generate diverse Google-dork queries for SerpAPI.
    Each round produces different queries so the deep loop keeps finding new profiles.
    """
    queries = []
    subj = subject.strip()

    if round_num == 0:
        # Round 0 — core role-based queries
        queries = [
            f'site:linkedin.com/in/ "{subj}" "teacher" India',
            f'site:linkedin.com/in/ "{subj}" "tutor" CBSE',
            f'site:linkedin.com/in/ "{subj}" "coaching" "founder"',
            f'site:linkedin.com/in/ "principal" "school" India',
            f'site:linkedin.com/in/ "director" "education" India',
        ]

    elif round_num == 1:
        # Round 1 — alternate phrasing
        queries = [
            f'site:linkedin.com/in/ "{subj}" "educator" "classes"',
            f'site:linkedin.com/in/ "head of department" "{subj}" school',
            f'site:linkedin.com/in/ "academic head" school India',
            f'site:linkedin.com/in/ "vice principal" school India',
            f'site:linkedin.com/in/ "{subj}" "faculty" India',
        ]

    elif 2 <= round_num <= 5:
        # Rounds 2-5 — city-based queries (6 cities per round)
        start_idx = (round_num - 2) * 6
        round_cities = INDIAN_CITIES[start_idx:start_idx + 6]
        for city in round_cities:
            queries.append(f'site:linkedin.com/in/ "{subj}" teacher {city}')
            queries.append(f'site:linkedin.com/in/ "principal" school {city}')
            queries.append(f'site:linkedin.com/in/ "coaching" "director" {city}')

    elif 6 <= round_num <= 8:
        # Rounds 6-8 — company page discovery
        start_idx = (round_num - 6) * 6
        round_cities = INDIAN_CITIES[start_idx:start_idx + 6]
        for city in round_cities:
            queries.append(f'site:linkedin.com/company/ "coaching" "classes" {city}')
            queries.append(f'site:linkedin.com/company/ "school" "education" {city}')
            queries.append(f'site:linkedin.com/company/ "academy" "institute" {city}')

    else:
        # Round 9+ — re-run earlier patterns with pagination offsets
        page_offset = (round_num - 9) * 10 + 10  # 10, 20, 30 …
        queries = [
            f'site:linkedin.com/in/ "{subj}" "teacher" India',
            f'site:linkedin.com/in/ "{subj}" "tutor" India',
            f'site:linkedin.com/in/ "{subj}" "coaching" India',
            f'site:linkedin.com/in/ "principal" "school" India',
            f'site:linkedin.com/in/ "founder" "education" India',
        ]
        # page_offset is passed separately when calling SerpAPI (start param)
        return queries, page_offset

    return queries, 0


# ──────────────────────────────────────────────
# URL PARSER
# ──────────────────────────────────────────────

_INDIVIDUAL_RE = re.compile(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', re.IGNORECASE)
_COMPANY_RE = re.compile(r'linkedin\.com/company/([a-zA-Z0-9_-]+)', re.IGNORECASE)


def extract_linkedin_info_from_url(url: str, snippet: str = "", title: str = "") -> dict | None:
    """
    Parse a SerpAPI organic result into a profile dict.
    Returns None if the URL is a system page or invalid.
    """
    url = (url or "").strip()
    if not url:
        return None

    # Determine profile type
    ind_match = _INDIVIDUAL_RE.search(url)
    comp_match = _COMPANY_RE.search(url)

    if ind_match:
        username = ind_match.group(1).lower()
        if username in SYSTEM_PAGES:
            return None
        profile_type = "individual"
        normalized_url = f"https://www.linkedin.com/in/{username}"
    elif comp_match:
        slug = comp_match.group(1).lower()
        if slug in SYSTEM_PAGES:
            return None
        profile_type = "company"
        normalized_url = f"https://www.linkedin.com/company/{slug}"
    else:
        return None

    # Parse title  (typical: "FirstName LastName - Role - Company | LinkedIn")
    name, headline, organization = "", "", ""
    if title:
        title_clean = title.replace(" | LinkedIn", "").replace("| LinkedIn", "").strip()
        parts = [p.strip() for p in title_clean.split(" - ")]
        if len(parts) >= 1:
            name = parts[0]
        if len(parts) >= 2:
            headline = parts[1]
        if len(parts) >= 3:
            organization = parts[2]

    return {
        "url": normalized_url,
        "name": name,
        "headline": headline,
        "organization": organization,
        "profile_type": profile_type,
        "snippet": (snippet or "")[:300],
    }


# ──────────────────────────────────────────────
# SERPAPI DISCOVERY
# ──────────────────────────────────────────────

def discover_via_serpapi(
    subject: str,
    roles: list,
    cities: list,
    serpapi_key: str,
    status_container,
    round_num: int = 0,
) -> list:
    """
    Execute SerpAPI queries for one round and return a list of unique
    LinkedIn profile dicts.
    """
    from serpapi import GoogleSearch

    queries, page_offset = generate_linkedin_queries(subject, roles, cities, round_num)
    all_profiles: list[dict] = []
    seen_urls: set[str] = set()

    for i, query in enumerate(queries):
        try:
            params = {
                "q": query,
                "api_key": serpapi_key,
                "engine": "google",
                "num": 20,
                "gl": "in",
                "hl": "en",
            }
            if page_offset:
                params["start"] = page_offset

            search = GoogleSearch(params)
            results = search.get_dict()

            organic = results.get("organic_results", [])
            status_container.write(
                f"🔍 Query {i+1}/{len(queries)} → {len(organic)} results"
            )

            for item in organic:
                profile = extract_linkedin_info_from_url(
                    item.get("link", ""),
                    item.get("snippet", ""),
                    item.get("title", ""),
                )
                if profile and profile["url"] not in seen_urls:
                    seen_urls.add(profile["url"])
                    all_profiles.append(profile)

        except Exception as e:
            err_str = str(e).lower()
            if any(kw in err_str for kw in ["invalid", "key", "unauthorized"]):
                status_container.write("❌ SerpAPI: Invalid API key.")
                return all_profiles
            if any(kw in err_str for kw in ["quota", "limit", "exceeded"]):
                status_container.write("⚠ï¸ SerpAPI quota exhausted.")
                return all_profiles
            status_container.write(f"⚠ï¸ SerpAPI error: {e}")

        # Rate limit between queries
        time.sleep(1.5)

    status_container.write(
        f"📊 Round {round_num} discovery: {len(all_profiles)} unique profiles found"
    )
    return all_profiles


# ──────────────────────────────────────────────
# DEDUPLICATION — Master CSV
# ──────────────────────────────────────────────

def load_existing_linkedin_leads(uploaded_file) -> tuple[set, set, int, str]:
    """
    Read a master CSV and return:
      (existing_urls_set, existing_names_set, count, error_message)
    """
    existing_urls: set[str] = set()
    existing_names: set[str] = set()
    error_msg = ""

    try:
        df = pd.read_csv(uploaded_file)
        # Try common column names for the LinkedIn URL
        url_col = None
        for col in df.columns:
            if "linkedin" in col.lower() and "url" in col.lower():
                url_col = col
                break
        if url_col is None:
            for col in df.columns:
                if "url" in col.lower() or "link" in col.lower():
                    url_col = col
                    break

        if url_col:
            for val in df[url_col].dropna():
                existing_urls.add(str(val).strip().lower().rstrip("/"))
        else:
            error_msg = "⚠ï¸ No URL/Link column found in CSV. Dedup by URL skipped."

        # Names
        name_col = None
        for col in df.columns:
            if col.lower() in ["name", "full name", "full_name", "fullname"]:
                name_col = col
                break
        if name_col:
            for val in df[name_col].dropna():
                existing_names.add(str(val).strip().lower())

    except Exception as e:
        error_msg = f"❌ Error reading CSV: {e}"

    return existing_urls, existing_names, len(existing_urls), error_msg


# ──────────────────────────────────────────────
# APIFY — Profile Scraping (Phase 2)
# ──────────────────────────────────────────────

def _is_apify_quota_error(err) -> bool:
    """Check if an error indicates Apify quota/credit exhaustion."""
    err_str = str(err).lower()
    return any(kw in err_str for kw in ["quota", "credit", "limit", "402", "payment", "subscription"])


def _parse_experience(experience_list: list) -> tuple[str, str, int]:
    """
    Parse an Apify experience array.
    Returns (current_company, current_role, experience_years).
    """
    current_company = ""
    current_role = ""
    experience_years = 0

    if not experience_list:
        return current_company, current_role, experience_years

    # Find current role (isCurrent=True or first entry)
    for exp in experience_list:
        if isinstance(exp, dict):
            if exp.get("isCurrent", False):
                current_company = exp.get("companyName", "") or exp.get("company", "")
                current_role = exp.get("title", "") or exp.get("role", "")
                break
    if not current_company and experience_list:
        first = experience_list[0] if isinstance(experience_list[0], dict) else {}
        current_company = first.get("companyName", "") or first.get("company", "")
        current_role = first.get("title", "") or first.get("role", "")

    # Calculate experience years from earliest date
    try:
        years = []
        for exp in experience_list:
            if isinstance(exp, dict):
                start = exp.get("startDate", "") or exp.get("dateRange", "")
                if start and isinstance(start, str):
                    for token in start.replace(",", " ").split():
                        if token.isdigit() and 1970 <= int(token) <= 2030:
                            years.append(int(token))
        if years:
            experience_years = datetime.now().year - min(years)
    except Exception:
        pass

    return current_company, current_role, experience_years


def _parse_apify_profile_item(item: dict) -> dict:
    """
    Parse a single Apify profile result into a standardised dict.
    Handles multiple output schemas from different Apify actors.
    """
    bi = item.get("basic_info", {}) or {}

    loc_raw = item.get("location") or bi.get("location") or ""
    if isinstance(loc_raw, dict):
        loc_str = loc_raw.get("city", "") or loc_raw.get("default", "") or loc_raw.get("country", "")
    else:
        loc_str = str(loc_raw)

    profile = {
        "linkedin_url": (
            item.get("linkedinUrl") or item.get("url") or item.get("profileUrl")
            or item.get("profile_url") or item.get("linkedInUrl")
            or bi.get("profile_url") or bi.get("linkedinUrl") or ""
        ),
        "full_name": (
            item.get("fullName")
            or item.get("name")
            or item.get("full_name")
            or ((item.get("firstName", "") or "") + " " + (item.get("lastName", "") or "")).strip()
            or bi.get("fullname") or bi.get("full_name") or "Unknown"
        ),
        "headline": (
            item.get("headline") or item.get("jobTitle") or item.get("title")
            or item.get("position") or bi.get("headline") or ""
        ),
        "location": loc_str,
        "about": (
            item.get("about") or item.get("summary") or item.get("description")
            or bi.get("about") or ""
        )[:500],
        "followers": item.get("followersCount") or item.get("followers") or item.get("follower_count") or bi.get("follower_count") or 0,
        "connections": item.get("connectionsCount") or item.get("connections") or item.get("connections_count") or bi.get("connections_count") or 0,
        "current_company": item.get("companyName") or item.get("current_company") or item.get("jobCompanyName") or bi.get("current_company") or "",
        "current_role": "",
        "experience_years": 0,
        "education": "",
        "skills": item.get("skills", []) or [],
        "profile_type": "individual",
        "raw_experience": item.get("experience", []) or item.get("experiences", []) or [],
        "raw_education": item.get("education", []) or item.get("educations", []) or [],
        "enrichment_status": "enriched",
    }

    experience = profile["raw_experience"]
    if experience and isinstance(experience, list) and len(experience) > 0:
        current = experience[0] if isinstance(experience[0], dict) else {}
        if not profile["current_company"]:
            profile["current_company"] = (
                current.get("companyName") or current.get("company")
                or current.get("company_name") or ""
            )
        profile["current_role"] = (
            current.get("title") or current.get("role")
            or current.get("position") or ""
        )

    if profile["raw_experience"]:
        _, _, exp_years = _parse_experience(profile["raw_experience"])
        profile["experience_years"] = exp_years

    if profile["raw_education"] and isinstance(profile["raw_education"], list):
        for edu in profile["raw_education"]:
            if isinstance(edu, dict):
                school = edu.get("schoolName", "") or edu.get("school", "") or edu.get("school_name", "")
                degree = edu.get("degreeName", "") or edu.get("degree", "") or edu.get("degree_name", "")
                if school:
                    profile["education"] = f"{degree} - {school}" if degree else school
                    break

    return profile


APIFY_PROFILE_ACTORS = [
    {
        "id": "harvestapi/linkedin-profile-scraper",
        "label": "HarvestAPI (4.8\u2605)",
        "build_input": lambda urls: {
            "profileScraperMode": "Profile details no email ($4 per 1k)",
            "queries": urls,
        },
    },
    {
        "id": "apimaestro/linkedin-profile-detail",
        "label": "APIMaestro",
        "build_input": lambda urls: {
            "profileUrls": urls,
        },
    },
    {
        "id": "supreme_coder/linkedin-profile-scraper",
        "label": "SupremeCoder",
        "build_input": lambda urls: {
            "urls": [{"url": u} for u in urls],
        },
    },
]


def scrape_linkedin_profiles(
    urls: list,
    apify_manager: ApifyKeyManager,
    status_container,
) -> list:
    """
    Scrape LinkedIn profiles using multiple Apify actors with automatic fallback.
    Tries actors in order: HarvestAPI > APIMaestro > SupremeCoder.
    """
    from apify_client import ApifyClient

    enriched_profiles: list[dict] = []
    batch_size = 20
    working_actor_idx = st.session_state.get("_working_actor_idx", 0)

    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i : i + batch_size]
        current_key = apify_manager.get_current_key()

        if not current_key:
            status_container.warning("All Apify keys exhausted. Skipping remaining enrichment.")
            break

        status_container.write(
            f"Scraping batch {i // batch_size + 1} ({len(batch_urls)} URLs) "
            f"with key #{apify_manager.current_index + 1}"
        )

        batch_results = []
        for actor_offset in range(len(APIFY_PROFILE_ACTORS)):
            actor_idx = (working_actor_idx + actor_offset) % len(APIFY_PROFILE_ACTORS)
            actor = APIFY_PROFILE_ACTORS[actor_idx]

            try:
                client = ApifyClient(current_key)
                run_input = actor["build_input"](batch_urls)
                status_container.write(f"   Trying: {actor['label']} ...")

                run = client.actor(actor["id"]).call(
                    run_input=run_input,
                    timeout_secs=180,
                )

                if run:
                    dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items

                    if dataset_items and len(dataset_items) > 0:
                        for item in dataset_items:
                            profile = _parse_apify_profile_item(item)
                            if profile["full_name"] != "Unknown" or profile["headline"]:
                                batch_results.append(profile)

                        if batch_results:
                            working_actor_idx = actor_idx
                            st.session_state["_working_actor_idx"] = actor_idx
                            status_container.write(
                                f"   Got {len(batch_results)} enriched profiles via {actor['label']}"
                            )
                            break
                        else:
                            status_container.write(
                                f"   {actor['label']} returned items but none usable. Trying next..."
                            )
                    else:
                        status_container.write(
                            f"   {actor['label']} returned 0 results. Trying next..."
                        )

            except Exception as e:
                error_msg = str(e).lower()
                # Rate-limit: wait and retry same actor (don't rotate key)
                if any(kw in error_msg for kw in ["429", "rate limit", "too many requests", "rate-limit"]):
                    status_container.write(f"   Rate limited on {actor['label']} — waiting 30s and retrying...")
                    time.sleep(30)
                    try:
                        client = ApifyClient(current_key)
                        run_input = actor["build_input"](batch_urls)
                        run = client.actor(actor["id"]).call(run_input=run_input, timeout_secs=180)
                        if run:
                            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
                            if dataset_items:
                                for item in dataset_items:
                                    profile = _parse_apify_profile_item(item)
                                    if profile["full_name"] != "Unknown" or profile["headline"]:
                                        batch_results.append(profile)
                                if batch_results:
                                    working_actor_idx = actor_idx
                                    st.session_state["_working_actor_idx"] = actor_idx
                                    status_container.write(f"   Retry OK: {len(batch_results)} profiles via {actor['label']}")
                                    break
                    except Exception:
                        status_container.write(f"   Retry also failed, trying next actor...")
                    continue
                elif _is_apify_quota_error(e):
                    status_container.write(
                        f"   Key #{apify_manager.current_index + 1} quota exhausted - rotating"
                    )
                    next_key = apify_manager.mark_exhausted()
                    if next_key is None:
                        status_container.write("   All Apify keys exhausted.")
                        break
                    current_key = next_key
                    continue
                elif "not found" in error_msg:
                    status_container.write(f"   Actor {actor['label']} not found, trying next...")
                    continue
                else:
                    status_container.write(f"   {actor['label']} error: {str(e)[:120]}")
                    continue

        enriched_profiles.extend(batch_results)
        time.sleep(3)

    return enriched_profiles


def scrape_linkedin_companies(
    urls: list[str],
    apify_manager: ApifyKeyManager,
    status_container,
) -> list[dict]:
    """
    Scrape LinkedIn company pages via Apify.
    Returns list of enriched company dicts.
    """
    from apify_client import ApifyClient

    enriched: list[dict] = []
    batch_size = 30

    for batch_start in range(0, len(urls), batch_size):
        batch_urls = urls[batch_start : batch_start + batch_size]
        key = apify_manager.get_current_key()
        if key is None:
            status_container.write("⚠ï¸ All Apify keys exhausted — stopping company scraping.")
            break

        status_container.write(
            f"🏢 Scraping companies batch {batch_start // batch_size + 1} "
            f"({len(batch_urls)} URLs) with key #{apify_manager.current_index + 1}…"
        )

        try:
            client = ApifyClient(key)
            # dev_fusion company scraper (no cookies)
            run = client.actor("dev_fusion/linkedin-company-scraper").call(
                run_input={"companyUrls": batch_urls}
            )
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            for item in items:
                hq = item.get("headquarters", {})
                if not isinstance(hq, dict):
                    hq = {}

                company = {
                    "linkedin_url": item.get("url", ""),
                    "full_name": item.get("name", ""),
                    "company_name": item.get("name", ""),
                    "headline": item.get("description", "")[:200] if item.get("description") else "",
                    "about": (item.get("description", "") or "")[:500],
                    "location": hq.get("city", "") or hq.get("geographicArea", ""),
                    "industry": item.get("industry", ""),
                    "company_size": item.get("employeeCount", "") or item.get("staffCount", ""),
                    "website": item.get("website", ""),
                    "founded": item.get("founded", ""),
                    "specialties": item.get("specialties", []),
                    "followers": item.get("followersCount", 0) or 0,
                    "connections": 0,
                    "current_company": item.get("name", ""),
                    "current_role": "Company Page",
                    "experience_years": 0,
                    "education": "",
                    "skills": [],
                    "profile_type": "company",
                    "raw_experience": [],
                    "raw_education": [],
                    "enrichment_status": "enriched",
                }
                enriched.append(company)

            status_container.write(f"   ✅ Got {len(items)} enriched companies from this batch")

        except Exception as e:
            if _is_apify_quota_error(e):
                status_container.write(
                    f"⚠ï¸ Apify key #{apify_manager.current_index + 1} quota exhausted — rotating…"
                )
                next_key = apify_manager.mark_exhausted()
                if next_key is None:
                    status_container.write("⚠ï¸ All Apify keys exhausted.")
                    break
                continue
            else:
                status_container.write(f"⚠ï¸ Apify company scrape error: {e}")

        time.sleep(3)

    return enriched


# ──────────────────────────────────────────────
# UNIFIED ENRICHMENT (Phase 2)
# ──────────────────────────────────────────────

def enrich_discovered_profiles(
    discovered: list[dict],
    apify_manager: ApifyKeyManager,
    status_container,
) -> list[dict]:
    """
    Enrich discovered profiles by scraping full data via Apify.
    Falls back to SerpAPI-only data if all keys are exhausted.
    """
    if not apify_manager.has_keys() or apify_manager.is_exhausted():
        status_container.write("No Apify keys available - returning SerpAPI-only data.")
        for p in discovered:
            p.setdefault("enrichment_status", "serpapi_only")
            p.setdefault("full_name", p.get("name", ""))
            p.setdefault("location", "")
            p.setdefault("about", p.get("snippet", ""))
            p.setdefault("followers", 0)
            p.setdefault("connections", 0)
            p.setdefault("current_company", p.get("organization", ""))
            p.setdefault("current_role", p.get("headline", ""))
            p.setdefault("experience_years", 0)
            p.setdefault("education", "")
            p.setdefault("skills", [])
            p.setdefault("raw_experience", [])
            p.setdefault("raw_education", [])
        return discovered

    # Separate individual vs company URLs
    individual_urls = [p["url"] for p in discovered if p.get("profile_type") == "individual"]
    company_urls = [p["url"] for p in discovered if p.get("profile_type") == "company"]

    status_container.write(
        f"Enrichment targets: {len(individual_urls)} individuals, {len(company_urls)} companies"
    )

    # Scrape
    enriched_profiles = scrape_linkedin_profiles(individual_urls, apify_manager, status_container)
    enriched_companies = scrape_linkedin_companies(company_urls, apify_manager, status_container)

    # Helper to normalize LinkedIn URLs for matching
    def _norm_url(url_str: str) -> str:
        """Normalize a LinkedIn URL to just the username/slug for matching."""
        url_str = (url_str or "").lower().strip().rstrip("/")
        # Extract username from /in/username or /company/slug
        m = re.search(r'linkedin\.com/in/([a-z0-9_-]+)', url_str)
        if m:
            return f"in/{m.group(1)}"
        m = re.search(r'linkedin\.com/company/([a-z0-9_-]+)', url_str)
        if m:
            return f"company/{m.group(1)}"
        return url_str

    # Build normalized URL -> enriched data map
    enriched_map: dict[str, dict] = {}
    for ep in enriched_profiles + enriched_companies:
        # Try multiple URL fields since different actors use different field names
        ep_url = (
            ep.get("linkedin_url", "")
            or ep.get("linkedinUrl", "")
            or ep.get("url", "")
            or ep.get("profileUrl", "")
            or ep.get("profile_url", "")
            or ep.get("linkedInUrl", "")
            or ""
        )
        norm = _norm_url(ep_url)
        if norm:
            enriched_map[norm] = ep

    status_container.write(
        f"Enrichment map built: {len(enriched_map)} profiles matched from scraping"
    )

    # Also map by publicIdentifier for actors that use it (e.g., HarvestAPI)
    for ep in enriched_profiles + enriched_companies:
        pub_id = ep.get("publicIdentifier", "") or ""
        if pub_id and pub_id.strip():
            key = f"in/{pub_id.strip().lower()}"
            if key not in enriched_map:
                enriched_map[key] = ep

    # Debug: show sample URLs from both sides to diagnose matching issues
    if enriched_profiles and not enriched_map:
        # Enriched profiles exist but none mapped - log the raw URL fields
        sample_ep = enriched_profiles[0]
        status_container.write(
            f"DEBUG: Sample enriched profile keys: {list(sample_ep.keys())[:15]}"
        )
        status_container.write(
            f"DEBUG: Enriched URL fields -> "
            f"linkedin_url='{sample_ep.get('linkedin_url', 'N/A')}' | "
            f"url='{sample_ep.get('url', 'N/A')}' | "
            f"profileUrl='{sample_ep.get('profileUrl', 'N/A')}' | "
            f"profile_url='{sample_ep.get('profile_url', 'N/A')}'"
        )
    if enriched_map:
        sample_keys = list(enriched_map.keys())[:3]
        status_container.write(f"DEBUG: Enriched map sample keys: {sample_keys}")
    if discovered:
        sample_disc = [_norm_url(p["url"]) for p in discovered[:3]]
        status_container.write(f"DEBUG: Discovered sample norm URLs: {sample_disc}")

    # Merge enriched data back into discovered list
    result: list[dict] = []
    enriched_count = 0
    for p in discovered:
        norm_url = _norm_url(p["url"])
        if norm_url in enriched_map:
            ep = enriched_map[norm_url]
            merged = {**p, **ep}
            # Preserve the original url field name
            merged["url"] = p["url"]
            if not merged.get("full_name") or merged["full_name"] == "Unknown":
                merged["full_name"] = p.get("name", "")
            merged["enrichment_status"] = "enriched"
            result.append(merged)
            enriched_count += 1
        else:
            # Fallback to SerpAPI-only data
            p["enrichment_status"] = "serpapi_only"
            p.setdefault("full_name", p.get("name", ""))
            p.setdefault("location", "")
            p.setdefault("about", p.get("snippet", ""))
            p.setdefault("followers", 0)
            p.setdefault("connections", 0)
            p.setdefault("current_company", p.get("organization", ""))
            p.setdefault("current_role", p.get("headline", ""))
            p.setdefault("experience_years", 0)
            p.setdefault("education", "")
            p.setdefault("skills", [])
            p.setdefault("raw_experience", [])
            p.setdefault("raw_education", [])
            result.append(p)

    serpapi_only = len(result) - enriched_count
    status_container.write(
        f"Enrichment done: {enriched_count} enriched, {serpapi_only} SerpAPI-only"
    )

    return result



# ──────────────────────────────────────────────

def is_complete_profile(profile: dict) -> tuple[bool, str]:
    """
    Reject profiles that are too sparse to be useful.
    Must have at least: name AND (headline OR current_role).
    SerpAPI-only profiles need education keyword in snippet.
    """
    name = (profile.get("full_name") or profile.get("name") or "").strip()
    if not name:
        return False, "Missing name"

    headline = (profile.get("headline") or "").strip()
    current_role = (profile.get("current_role") or "").strip()

    if not headline and not current_role:
        return False, "Missing both headline and role"

    # SerpAPI-only profiles need extra check
    if profile.get("enrichment_status") == "serpapi_only":
        snippet = (profile.get("snippet") or "").lower()
        combined = f"{name} {headline} {current_role} {snippet}".lower()
        has_edu = any(kw in combined for kw in EDUCATION_KEYWORDS)
        if not has_edu:
            return False, "SerpAPI-only profile with no education signal"

    return True, "Complete"


def is_blacklisted_brand(profile: dict) -> tuple[bool, str]:
    """
    Check if profile belongs to a blacklisted brand (Big EdTech / Big Corp).
    Returns (True, reason) if blacklisted — i.e. should be REJECTED.
    """
    name = (profile.get("full_name") or profile.get("name") or "").lower()
    headline = (profile.get("headline") or "").lower()
    company = (profile.get("current_company") or profile.get("organization") or "").lower()
    company_name = (profile.get("company_name") or "").lower()

    text_to_check = f"{name} ||| {headline} ||| {company} ||| {company_name}"

    for brand in BRAND_BLACKLIST:
        if brand.lower() in text_to_check:
            return True, f"Blacklisted brand: {brand}"

    return False, "Not blacklisted"


def is_india_based(profile: dict) -> tuple[bool, str]:
    """
    Check if profile is India-based.
    If location is empty, check headline + about for India indicators.
    If still unclear → PASS (benefit of doubt).
    """
    location = (profile.get("location") or "").lower()

    # Check location field first
    if location:
        for indicator in INDIA_INDICATORS:
            if indicator in location:
                return True, f"India location: {location}"
        # Location is present but doesn't match India
        return False, f"Non-India location: {location}"

    # Location missing — check headline + about for India clues
    headline = (profile.get("headline") or "").lower()
    about = (profile.get("about") or profile.get("snippet") or "").lower()
    combined = f"{headline} {about}"

    for indicator in INDIA_INDICATORS:
        if indicator in combined:
            return True, f"India indicator in text: {indicator}"

    # No location data, no India clues — benefit of doubt
    return True, "Location unknown — passing (benefit of doubt)"


def is_connection_in_range(profile: dict) -> tuple[bool, str]:
    """
    Check if connections/followers are within acceptable range.
    Zero or missing values → PASS (benefit of doubt).
    """
    profile_type = profile.get("profile_type", "individual")
    connections = profile.get("connections", 0) or 0
    followers = profile.get("followers", 0) or 0

    if profile_type == "company":
        # Company pages use followers
        if followers == 0:
            return True, "Company followers unknown — passing"
        if followers < MIN_COMPANY_FOLLOWERS:
            return False, f"Too few company followers: {followers} (min {MIN_COMPANY_FOLLOWERS})"
        if followers > MAX_COMPANY_FOLLOWERS:
            return False, f"Too many company followers: {followers} (max {MAX_COMPANY_FOLLOWERS})"
        return True, f"Company followers OK: {followers}"
    else:
        # Individual profiles use connections
        if connections == 0:
            return True, "Connections unknown — passing"
        if connections < MIN_CONNECTIONS:
            return False, f"Too few connections: {connections} (min {MIN_CONNECTIONS})"
        if connections > MAX_CONNECTIONS:
            return False, f"Too many connections: {connections} (max {MAX_CONNECTIONS})"
        return True, f"Connections OK: {connections}"


def is_education_relevant(profile: dict) -> tuple[bool, str]:
    """
    Check if the profile is education-relevant.
    Combines headline + about + current_role + current_company + skills.
    Founder/CEO/Director profiles need additional education context.
    """
    headline = (profile.get("headline") or "").lower()
    about = (profile.get("about") or profile.get("snippet") or "").lower()
    role = (profile.get("current_role") or "").lower()
    company = (profile.get("current_company") or profile.get("organization") or "").lower()
    skills = " ".join(s.lower() if isinstance(s, str) else "" for s in (profile.get("skills") or []))

    combined = f"{headline} {about} {role} {company} {skills}"

    # If combined text is basically empty, pass (benefit of doubt)
    if len(combined.strip()) < 5:
        return True, "Insufficient text to evaluate — passing"

    # Check for education keywords
    edu_matches = [kw for kw in EDUCATION_KEYWORDS if kw in combined]
    non_edu_matches = [kw for kw in NON_EDUCATION_KEYWORDS if kw in combined]

    # Leadership roles that need education context
    leadership_keywords = ['founder', 'ceo', 'coo', 'managing director', 'director']
    is_leadership = any(lk in combined for lk in leadership_keywords)

    if not edu_matches:
        return False, f"No education keywords found"

    if non_edu_matches and not any(
        kw for kw in edu_matches if kw not in leadership_keywords
    ):
        # Only leadership keywords matched + non-education keywords present
        return False, f"Leadership role without education context (non-edu: {', '.join(non_edu_matches[:3])})"

    if is_leadership:
        # Leadership profiles need at least one non-leadership education keyword
        edu_context_keywords = [
            'school', 'academy', 'institute', 'college', 'university',
            'coaching', 'classes', 'education', 'edtech', 'teaching',
            'cbse', 'icse', 'igcse', 'ib', 'neet', 'jee', 'tuition',
            'curriculum', 'pedagogy', 'learning', 'training'
        ]
        has_context = any(ck in combined for ck in edu_context_keywords)
        if not has_context:
            return False, "Leadership role without education context"

    return True, f"Education relevant ({', '.join(edu_matches[:3])})"


def apply_hard_filters(
    profiles: list[dict], status_container
) -> tuple[list[dict], dict]:
    """
    Apply hard filters in order (cheapest first):
    1. Completeness  2. Brand blacklist  3. Location  4. Connections  5. Education relevance
    Returns (filtered_profiles, rejection_stats).
    """
    stats = {
        "input": len(profiles),
        "incomplete": 0,
        "blacklisted": 0,
        "non_india": 0,
        "connection_range": 0,
        "non_education": 0,
        "passed": 0,
    }
    passed: list[dict] = []

    for p in profiles:
        # 1. Completeness
        ok, reason = is_complete_profile(p)
        if not ok:
            stats["incomplete"] += 1
            continue

        # 2. Brand blacklist
        blacklisted, reason = is_blacklisted_brand(p)
        if blacklisted:
            stats["blacklisted"] += 1
            continue

        # 3. Location (India-based)
        india, reason = is_india_based(p)
        if not india:
            stats["non_india"] += 1
            continue

        # 4. Connection / follower range
        in_range, reason = is_connection_in_range(p)
        if not in_range:
            stats["connection_range"] += 1
            continue

        # 5. Education relevance
        edu_ok, reason = is_education_relevant(p)
        if not edu_ok:
            stats["non_education"] += 1
            continue

        passed.append(p)

    stats["passed"] = len(passed)
    rejected = stats["input"] - stats["passed"]

    status_container.write(
        f"🔍 **Hard Filters Applied:**\n"
        f"   Input: {stats['input']} | ✅ Passed: {stats['passed']} | ❌ Rejected: {rejected}"
    )
    status_container.write(
        f"   📋 Rejections: "
        f"Incomplete: {stats['incomplete']} | "
        f"Blacklisted: {stats['blacklisted']} | "
        f"Non-India: {stats['non_india']} | "
        f"Connection range: {stats['connection_range']} | "
        f"Non-education: {stats['non_education']}"
    )

    return passed, stats


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 4: GEMINI AI CLASSIFICATION
# ──────────────────────────────────────────────────────────────────────────────

def fallback_classify(profile: dict) -> dict:
    """Keyword-based classification when Gemini is unavailable."""
    headline = (profile.get("headline", "") or "").lower()
    company = (profile.get("current_company", "") or "").lower()
    
    # Check for institute keywords
    if any(kw.lower() in company for kw in INSTITUTE_KEYWORDS):
        return {
            "persona_type": "Coaching Institute Owner",
            "is_relevant": True,
            "reason": "Institute keyword match"
        }
    
    # Check for school roles
    if any(role in headline for role in ["principal", "vice principal", "headmaster", "director"]):
        return {
            "persona_type": "Institute Leader",
            "is_relevant": True,
            "reason": "School leadership role match"
        }
    
    # Check for founder/CEO
    if any(role in headline for role in ["founder", "ceo", "co-founder"]):
        if any(kw in headline + company for kw in ["education", "edtech", "learn", "school", "academy"]):
            return {
                "persona_type": "EdTech Decision-Maker",
                "is_relevant": True,
                "reason": "EdTech founder match"
            }
    
    # Default
    return {
        "persona_type": "Individual Tutor",
        "is_relevant": True,
        "reason": "Fallback default"
    }

def classify_linkedin_profile(profile: dict, api_key: str) -> dict:
    """Classify profile using Gemini AI."""
    if not api_key:
        return fallback_classify(profile)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = f"""Analyze this LinkedIn profile for an education platform collaboration. Return ONLY valid JSON.

        Profile Data:
        - Name: {profile.get('full_name', '')}
        - Headline: {profile.get('headline', '')}
        - Location: {profile.get('location', '')}
        - About: {profile.get('about', '')[:500]}
        - Current Company: {profile.get('current_company', '')}
        - Current Role: {profile.get('current_role', '')}
        - Experience: {str(profile.get('raw_experience', []))[:500]}
        - Education: {str(profile.get('raw_education', []))[:300]}
        - Skills: {str(profile.get('skills', []))[:200]}

        Classify into ONE persona type:
        - "Individual Tutor": Single teacher/tutor
        - "Institute Leader": Principal, VP, Director of school/coaching
        - "EdTech Decision-Maker": Founder/CEO/COO of edtech
        - "School Administrator": HOD, Academic Head, Coordinator
        - "Coaching Institute Owner": Owner of coaching center
        - "Irrelevant": Not education related or Big Corp employee

        Also detect:
        - subjects: [Mathematics, Physics, Chemistry, Biology, English, etc]
        - grades: [6,7,8,9,10,11,12]
        - boards: [CBSE, ICSE, IB, IGCSE, Cambridge]
        - seniority: "Owner/Founder", "C-Level", "Director", "Principal", "HOD", "Teacher"
        - collaboration_potential: "High" (decision-maker), "Medium", "Low"

        Return ONLY JSON:
        {{"persona_type": "...", "subjects": [...], "grades": [...], "boards": [...], "seniority": "...", "collaboration_potential": "...", "is_relevant": true, "reason": "..."}}
        """

        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean markdown if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text)

    except Exception as e:
        return fallback_classify(profile)

# ──────────────────────────────────────────────────────────────────────────────
# PHASE 5: CONTACT EXTRACTION + TIER SCORING
# ──────────────────────────────────────────────────────────────────────────────

def extract_linkedin_contacts(profile: dict) -> dict:
    """Extract email, phone, and social links from text fields."""
    text_blob = (
        f"{profile.get('about', '')} {profile.get('headline', '')} "
        f"{profile.get('website', '')}"
    ).lower()

    contacts = {
        "email": "", "phone": "", "website": "", "twitter": "",
        "facebook": "", "instagram": "", "youtube": "", "whatsapp": ""
    }

    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text_blob)
    if email_match:
        contacts["email"] = email_match.group(0)

    # Phone (Indian format mostly)
    phone_match = re.search(r'(?:\+91[\s-]?)?(?:0)?[6-9]\d{9}', text_blob)
    if phone_match:
        contacts["phone"] = phone_match.group(0)
    
    # Socials
    if "wa.me" in text_blob or "chat.whatsapp" in text_blob:
        contacts["whatsapp"] = "Yes"
    if "instagram.com" in text_blob:
        contacts["instagram"] = "Yes"
    if "youtube.com" in text_blob or "youtu.be" in text_blob:
        contacts["youtube"] = "Yes"
    
    # External Website from Apify
    if profile.get("website"):
        contacts["website"] = profile.get("website")

    return contacts

def calculate_contact_confidence(contacts: dict) -> str:
    if contacts["email"] and contacts["phone"]: return "High"
    if contacts["email"] or contacts["phone"]: return "Medium"
    if contacts["website"] or contacts["whatsapp"]: return "Medium-Low"
    return "LinkedIn Only"

def calculate_linkedin_tier(profile: dict, contacts: dict, classification: dict) -> str:
    """
    Tier A: Decision Maker + High Potential + Contact Info
    Tier B: Relevant + Senior Role + Contact Info
    Tier C: Relevant + LinkedIn Only
    Tier D: Low priority
    """
    persona = classification.get("persona_type", "")
    seniority = classification.get("seniority", "")
    is_relevant = classification.get("is_relevant", True)
    has_contact = bool(contacts["email"] or contacts["phone"] or contacts["website"])
    
    if not is_relevant:
        return "D"

    # Tier A: Decision Makers with Contact
    if has_contact and (
        "Founder" in seniority or "Owner" in seniority or 
        "Principal" in seniority or "Director" in seniority or "C-Level" in seniority
    ):
        return "A"
    
    # Tier B: HODs/Teachers with Contact OR Decision Makers without contact
    if has_contact or "Founder" in seniority or "Principal" in seniority:
        return "B"
        
    # Tier C: Teachers/Tutors (LinkedIn reachout)
    if persona in ["Individual Tutor", "Teacher"]:
        return "C"
        
    return "D"

def generate_linkedin_fit_summary(profile: dict, api_key: str) -> str:
    """Generate 2-sentence fit summary for Tier A/B."""
    if not api_key: return "Fit summary unavailable (no key)."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""Write a 2-sentence summary of why this LinkedIn professional is a good B2B lead for an online tutoring platform.
        Profile: {profile.get('full_name')} | {profile.get('headline')} | {profile.get('persona_type')}
        Return ONLY the summary."""
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return f"{profile.get('persona_type')} based in {profile.get('location')}."

# ──────────────────────────────────────────────────────────────────────────────
# PHASE 6: DEEP FILTERING ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────────────

def smart_fetch_linkedin_profiles(
    subject, roles, cities, target_count,
    serpapi_key, apify_manager, google_api_key,
    status_container, existing_urls
) -> list:
    
    approved_leads = []
    seen_urls = existing_urls.copy() if existing_urls else set()
    
    # Counters
    gemini_calls = 0
    serpapi_calls = 0
    search_round = 0
    max_rounds = 15
    consecutive_empty = 0
    
    while len(approved_leads) < target_count and search_round < max_rounds:
        search_round += 1
        
        # 1. DISCOVERY
        # ------------------------------------------------------------------
        if consecutive_empty >= 4:
            status_container.warning("⚠️ Stopping: No new profiles found in last 4 rounds.")
            break
            
        discovered = discover_via_serpapi(
            subject, roles, cities, serpapi_key, status_container, round_num=search_round-1
        )
        serpapi_calls += 5
        
        # Dedup
        new_profiles = [p for p in discovered if p["url"].lower().rstrip("/") not in seen_urls]
        if not new_profiles:
            consecutive_empty += 1
            status_container.write(f"   Round {search_round}: All duplicates. Retrying...")
            continue
        consecutive_empty = 0
        
        # Add to seen
        for p in new_profiles:
            seen_urls.add(p["url"].lower().rstrip("/"))

        # 2. ENRICHMENT (Batch logic)
        # ------------------------------------------------------------------
        needed = target_count - len(approved_leads)
        batch_size = min(needed * 2, 40, len(new_profiles))
        batch_to_enrich = new_profiles[:batch_size]
        
        enriched = enrich_discovered_profiles(batch_to_enrich, apify_manager, status_container)
        
        # 3. HARD FILTERS
        # ------------------------------------------------------------------
        filtered, _ = apply_hard_filters(enriched, status_container)
        
        # 4. CLASSIFICATION & SCORING
        # ------------------------------------------------------------------
        for profile in filtered:
            if len(approved_leads) >= target_count: break
            if gemini_calls >= MAX_GEMINI_CALLS: break
            
            # AI Classify
            classification = classify_linkedin_profile(profile, google_api_key)
            gemini_calls += 1
            time.sleep(4)  # Gemini free tier: ~15 req/min
            
            # Merge classification data
            profile.update(classification)
            
            # Check relevance from AI
            if not profile.get("is_relevant", True):
                continue
                
            # Extract Contact
            contacts = extract_linkedin_contacts(profile)
            profile.update(contacts)
            profile["contact_confidence"] = calculate_contact_confidence(contacts)
            
            # Tier Scoring
            profile["tier"] = calculate_linkedin_tier(profile, contacts, classification)
            
            # Strings for display
            profile["subjects_str"] = ", ".join(profile.get("subjects", []))
            
            # AI Summary (Only for high value to save credits)
            if profile["tier"] in ["A", "B"] and gemini_calls < MAX_GEMINI_CALLS:
                profile["ai_summary"] = generate_linkedin_fit_summary(profile, google_api_key)
                gemini_calls += 1
                time.sleep(4)  # Gemini free tier: ~15 req/min
            else:
                profile["ai_summary"] = f"{profile.get('headline', '')}"
                
            approved_leads.append(profile)
            status_container.write(f"   ✨ Approved: {profile['full_name']} ({profile['persona_type']}) - Tier {profile['tier']}")
            
        status_container.write(f"📊 **Progress:** {len(approved_leads)} / {target_count} leads found")
        time.sleep(1)
        
    return approved_leads



# ──────────────────────────────────────────────────────────────────────────────
# STREAMLIT — PAGE CONFIG + STYLING
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TuTrain LinkedIn Discovery",
    page_icon="💼",
    layout="wide",
)

st.markdown("""
<style>
/* ---- Header ---- */
.main-header {
    background: linear-gradient(135deg, #0077B5 0%, #004182 100%);
    padding: 2rem 2.5rem;
    border-radius: 14px;
    margin-bottom: 1.8rem;
    box-shadow: 0 4px 20px rgba(0,65,130,0.25);
}
.main-header h1 { color: #ffffff !important; margin-bottom: 0.3rem; }
.main-header p  { color: #cce5ff !important; font-size: 1.08rem; }

/* ---- Sidebar status badges ---- */
.key-ok  { color: #27ae60; font-weight: 600; }
.key-bad { color: #e67e22; font-weight: 600; }

/* ---- Results table tweaks ---- */
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💼 TuTrain LinkedIn Discovery Engine</h1>
    <p>Discover Educators, Principals, Directors &amp; EdTech Leaders for Collaboration</p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# SIDEBAR — API Keys
# ──────────────────────────────────────────────

with st.sidebar:
    st.header("🔑 API Keys")

    serpapi_key = _load_key("SERPAPI_KEY", "SerpAPI Key", st.sidebar)
    google_api_key = _load_key("GOOGLE_API_KEY", "Google API Key (Gemini)", st.sidebar)

    st.subheader("🔑 Apify Keys (Rotation)")
    apify_key_1 = _load_key("APIFY_KEY_1", "Apify Key 1", st.sidebar)
    apify_key_2 = _load_key("APIFY_KEY_2", "Apify Key 2", st.sidebar)
    apify_key_3 = _load_key("APIFY_KEY_3", "Apify Key 3", st.sidebar)
    apify_key_4 = _load_key("APIFY_KEY_4", "Apify Key 4", st.sidebar)

    # Build the Apify key manager
    apify_keys_list = [apify_key_1, apify_key_2, apify_key_3, apify_key_4]
    apify_manager = ApifyKeyManager(apify_keys_list)

    # Status indicators
    st.markdown("---")
    st.subheader("📡 Key Status")
    st.markdown(
        f"SerpAPI: <span class='{'key-ok' if serpapi_key else 'key-bad'}'>{'✅ loaded' if serpapi_key else '⚠ï¸ missing'}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"Gemini: <span class='{'key-ok' if google_api_key else 'key-bad'}'>{'✅ loaded' if google_api_key else '⚠ï¸ missing'}</span>",
        unsafe_allow_html=True,
    )
    apify_count = sum(1 for k in apify_keys_list if k)
    st.markdown(
        f"Apify: <span class='{'key-ok' if apify_count else 'key-bad'}'>{apify_count}/4 keys loaded</span>",
        unsafe_allow_html=True,
    )
    if apify_count:
        st.caption(f"🔄 {apify_manager.get_status()}")

    # ── Active filters display ──
    st.markdown("---")
    st.subheader("📋 Active Filters")
    st.markdown(f"""
**Region:** India 🇮🇳  
**Blacklist:** Big EdTech + Big Corp  
**Max SerpAPI Queries:** {MAX_SERPAPI_QUERIES}  
**Max Gemini Calls:** {MAX_GEMINI_CALLS}
    """)

    # ── Deduplication uploader ──
    st.markdown("---")
    st.subheader("📂 Deduplication")
    master_csv = st.file_uploader("Upload Master Lead CSV", type=["csv"])
    if master_csv is not None:
        urls, names, count, err = load_existing_linkedin_leads(master_csv)
        if err:
            st.warning(err)
        else:
            st.success(f"Loaded {count} existing leads for dedup")
        st.session_state["existing_urls"] = urls
        st.session_state["existing_names"] = names
    else:
        if "existing_urls" not in st.session_state:
            st.session_state["existing_urls"] = set()
            st.session_state["existing_names"] = set()

    # ── Phase info ──
    st.markdown("---")
    st.subheader("💼 Agent Info")
    st.markdown("""
✅ SerpAPI Google Dorking  
✅ Apify LinkedIn Enrichment *(Phase 2)*  
✅ Hard Filters *(Phase 3)*  
✅ Gemini AI Classification *(Phase 4)*  
✅ Contact Extraction + Tier Scoring *(Phase 5)*  
✅ Deep Filtering Loop *(Phase 6)*  
✅ Dashboard + CSV Export *(Phase 7)*  
    """)


# ──────────────────────────────────────────────
# MAIN AREA — Search Inputs
# ──────────────────────────────────────────────

SEARCH_PRESETS = {
    "-- Custom Search --": "",
    "EdTech Founders & CEOs": "edtech founder",
    "School Principals & Directors": "school principal",
    "Coaching Institute Owners": "coaching institute owner",
    "Physics Teachers & Tutors": "physics teacher",
    "Mathematics Teachers & Tutors": "mathematics teacher",
    "Chemistry Teachers & Tutors": "chemistry teacher",
    "Biology / Science Teachers": "biology science teacher",
    "English Teachers & Tutors": "english teacher",
    "CBSE School Leaders": "CBSE school",
    "ICSE / IB School Leaders": "ICSE IB school director",
    "NEET / JEE Coaching": "NEET JEE coaching",
    "Academic HODs & Coordinators": "academic head of department school",
}

preset_choice = st.selectbox(
    "⚡ Quick Search (pick a preset or type your own below)",
    list(SEARCH_PRESETS.keys()),
)

col_input1, col_input2 = st.columns([2, 1])

with col_input1:
    default_subject = SEARCH_PRESETS.get(preset_choice, "")
    subject = st.text_input(
        "🔎 Subject / Role / Keyword",
        value=default_subject,
        placeholder="e.g. Physics Teacher, School Principal, EdTech Founder",
    )

with col_input2:
    target_count = st.slider("🎯 Target Lead Count", 5, 100, 25, step=5)

col_role, col_city = st.columns(2)

with col_role:
    selected_roles = st.multiselect("👤 Role Filter", ROLE_OPTIONS, default=["All Roles"])

with col_city:
    selected_cities = st.multiselect("🏙️ City Filter", CITY_OPTIONS, default=["All Cities"])


# ──────────────────────────────────────────────
# SEARCH BUTTON
# ──────────────────────────────────────────────

search_clicked = st.button("🚀 Discover LinkedIn Profiles", type="primary", use_container_width=True)

if search_clicked:
    # ─── Validation ───
    if not subject.strip():
        st.error("⚠️ Please enter a subject or keyword to search.")
        st.stop()
    if not serpapi_key:
        st.error("⚠️ Please provide your SerpAPI key.")
        st.stop()

    existing_urls = st.session_state.get("existing_urls", set())
    
    # Run the Smart Loop
    with st.status("🚀 TuTrain Agent Active...", expanded=True) as status_box:
        results = smart_fetch_linkedin_profiles(
            subject, selected_roles, selected_cities, target_count,
            serpapi_key, apify_manager, google_api_key,
            status_box, existing_urls
        )
        
        if results:
            status_box.update(label=f"✅ Mission Complete! Found {len(results)} leads.", state="complete")
        else:
            status_box.update(label="❌ No leads found matching criteria.", state="error")

    # ─── Store results ───
    st.session_state["results"] = results


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 7: DASHBOARD & EXPORT
# ──────────────────────────────────────────────────────────────────────────────

results = st.session_state.get("results", [])

if results:
    st.divider()
    
    # ─── 1. KPI Cards ───
    df = pd.DataFrame(results)
    
    # Metrics calculation
    total_leads = len(df)
    tier_a = len(df[df["tier"] == "A"]) if "tier" in df.columns else 0
    tier_b = len(df[df["tier"] == "B"]) if "tier" in df.columns else 0
    decision_makers = len(df[df["tier"].isin(["A", "B"])]) if "tier" in df.columns else 0
    avg_connections = int(df["connections"].mean()) if "connections" in df.columns else 0

    # Custom CSS for cards
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #f0f2f6 0%, #ffffff 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #0077B5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-title { font-size: 0.9rem; color: #555; font-weight: 600; margin-bottom: 5px; }
    .metric-value { font-size: 1.8rem; color: #000; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Total Leads</div><div class="metric-value">{total_leads}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Decision Makers</div><div class="metric-value">{decision_makers}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Avg Connections</div><div class="metric-value">{avg_connections}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">High Priority (A+B)</div><div class="metric-value">{tier_a + tier_b}</div></div>', unsafe_allow_html=True)

    st.write("") # Spacer

    # ─── 2. Visualizations ───
    if "tier" in df.columns and "persona_type" in df.columns:
        tab1, tab2 = st.tabs(["📊 Charts", "🎯 Quality Map"])
        
        with tab1:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                # Persona Distribution
                fig_persona = px.pie(df, names="persona_type", title="Persona Distribution", hole=0.4,
                                    color_discrete_sequence=px.colors.qualitative.Prism)
                fig_persona.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300)
                st.plotly_chart(fig_persona, use_container_width=True)
            
            with col_chart2:
                # Tier Distribution
                tier_counts = df["tier"].value_counts().reset_index()
                tier_counts.columns = ["tier", "count"]
                color_map = {"A": "#2ecc71", "B": "#3498db", "C": "#f1c40f", "D": "#e74c3c"}
                
                fig_tier = px.bar(tier_counts, x="tier", y="count", title="Lead Quality Tiers",
                                 color="tier", color_discrete_map=color_map)
                fig_tier.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300)
                st.plotly_chart(fig_tier, use_container_width=True)

        with tab2:
            # Scatter Plot: Connections vs Tier
            if "connections" in df.columns:
                color_map = {"A": "#2ecc71", "B": "#3498db", "C": "#f1c40f", "D": "#e74c3c"}
                fig_map = px.scatter(
                    df, 
                    x="connections", 
                    y="persona_type", 
                    color="tier",
                    size="connections", 
                    hover_data=["full_name", "current_company", "location"],
                    color_discrete_map=color_map,
                    title="🎯 Lead Quality Map: Influence vs Persona"
                )
                st.plotly_chart(fig_map, use_container_width=True)

    # ─── 3. Detailed Data Table ───
    st.subheader("📋 Lead Details")
    
    # Filter Tiers
    selected_tiers = st.multiselect("Filter Tiers:", ["A", "B", "C", "D"], default=["A", "B", "C"])
    if "tier" in df.columns:
        filtered_df = df[df["tier"].isin(selected_tiers)]
    else:
        filtered_df = df

    # Select columns for display
    display_cols = {
        "tier": "Tier",
        "full_name": "Name",
        "persona_type": "Persona",
        "current_company": "Organization",
        "current_role": "Role",
        "location": "Location",
        "contact_confidence": "Contact Info",
        "linkedin_url": "LinkedIn"
    }
    
    # Filter to only existing columns
    final_cols = {k: v for k, v in display_cols.items() if k in filtered_df.columns}
    
    st.dataframe(
        filtered_df[list(final_cols.keys())].rename(columns=final_cols),
        column_config={
            "LinkedIn": st.column_config.LinkColumn("LinkedIn", display_text="Open Profile"),
            "Tier": st.column_config.Column("Tier", width="small"),
        },
        use_container_width=True,
        hide_index=True
    )

    # ─── 4. Export Section ───
    st.divider()
    col_ex1, col_ex2 = st.columns(2)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    # Button 1: Full Export
    csv_full = df.to_csv(index=False).encode('utf-8')
    col_ex1.download_button(
        "📥 Download ALL Leads (CSV)",
        data=csv_full,
        file_name=f"linkedin_leads_full_{timestamp}.csv",
        mime="text/csv",
        type="primary"
    )
    
    # Button 2: High Priority Only (Tier A + B)
    if "tier" in df.columns:
        high_pri_df = df[df["tier"].isin(["A", "B"])]
        csv_high = high_pri_df.to_csv(index=False).encode('utf-8')
        col_ex2.download_button(
            "📥 Download High Priority (Tier A/B)",
            data=csv_high,
            file_name=f"linkedin_leads_priority_{timestamp}.csv",
            mime="text/csv"
        )

else:
    st.info("👋 Welcome! Enter a subject (e.g., 'EdTech Founder') and click **Discover** to start finding leads.")