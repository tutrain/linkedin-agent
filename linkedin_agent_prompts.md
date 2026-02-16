# TuTrain LinkedIn Educator Discovery Agent — Phase-wise Prompts
## For AI Coding Agent (Antigravity)

---

# ============================================================
# PHASE 1: Project Setup + SerpAPI Discovery Engine
# ============================================================

## Prompt for Phase 1:

```
You are building a LinkedIn Educator Discovery Agent for TuTrain — an online tutoring platform (Grade 4-12, CBSE/ICSE/IB/Cambridge/US boards).

This is a Streamlit app. Create it inside my local directory "linkedin_agent/".

Files to create:
- app.py (main Streamlit app)
- requirements.txt
- .gitignore
- .streamlit/secrets.toml.example

## PURPOSE:
Discover LinkedIn profiles of educators, tutors, principals, directors, COOs, founders of coaching institutes, schools, and edtech companies — for B2B collaboration outreach.

## TARGET PERSONAS (6 types):
1. Individual Tutor — single teacher offering private/online classes
2. Institute Leader — principal/VP/director of school or coaching center
3. EdTech Decision-Maker — founder/CEO/COO/CXO of edtech company
4. School Administrator — admin staff, academic heads, HODs
5. Coaching Institute Owner — owner of small-medium coaching centers
6. Irrelevant — reject (corporate, non-education, big brand)

## PHASE 1 SCOPE — SerpAPI Google Dorking Discovery:

### 1. API Key Management (Sidebar)
- SerpAPI Key: text_input (password type)
- Google API Key (Gemini): text_input (password type)  
- Multiple Apify Keys: support for 3 Apify keys with auto-rotation
  - APIFY_KEY_1, APIFY_KEY_2, APIFY_KEY_3
  - When one key's quota is exhausted (error contains "quota", "credit", "limit", "402"), automatically switch to next key
  - Show which key is currently active in sidebar
- Try loading from st.secrets first, fallback to sidebar input
- Show status indicators (✅ loaded / ⚠️ missing) for each key

### 2. Search Input (Main Area)
- Subject input: text_input (e.g., "Physics Teacher", "School Principal", "EdTech Founder")
- Role filter: multiselect with options:
  ["Tutor/Teacher", "Principal/Director", "Founder/CEO", "HOD/Academic Head", "Coaching Owner", "All Roles"]
- City filter: multiselect with Indian cities:
  ["All Cities", "Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Jaipur", "Lucknow", "Kota", "Patna", "Chandigarh", "Ahmedabad", "Indore", "Bhopal", "Nagpur", "Varanasi", "Ranchi", "Dehradun", "Noida", "Gurgaon", "Sikar", "Jodhpur"]
- Target Lead Count: slider (5 to 100, default 25, step 5)

### 3. SerpAPI Query Generator
Create a function `generate_linkedin_queries(subject, roles, cities, round_num)` that generates diverse Google dorking queries. Each round should produce DIFFERENT queries.

Round strategy:
- Round 0: Core role-based queries
  ```
  site:linkedin.com/in/ "{subject}" "teacher" India
  site:linkedin.com/in/ "{subject}" "tutor" CBSE
  site:linkedin.com/in/ "{subject}" "coaching" "founder"
  site:linkedin.com/in/ "principal" "school" India
  site:linkedin.com/in/ "director" "education" India
  ```
- Round 1: Alternate phrasing
  ```
  site:linkedin.com/in/ "{subject}" "educator" "classes"
  site:linkedin.com/in/ "head of department" "{subject}" school
  site:linkedin.com/in/ "academic head" school India
  site:linkedin.com/in/ "vice principal" school India
  site:linkedin.com/in/ "{subject}" "faculty" India
  ```
- Round 2-5: City-based queries (6 cities per round from the INDIAN_CITIES list)
  ```
  site:linkedin.com/in/ "{subject}" teacher {city}
  site:linkedin.com/in/ "principal" school {city}
  site:linkedin.com/in/ "coaching" "director" {city}
  ```
- Round 6-8: Company page discovery
  ```
  site:linkedin.com/company/ "coaching" "classes" {city}
  site:linkedin.com/company/ "school" "education" {city}
  site:linkedin.com/company/ "academy" "institute" {city}
  ```
- Round 9+: Re-run earlier patterns with page 2/3 offsets (pagination via start parameter)

### 4. URL Parser
Create `extract_linkedin_info_from_url(url, snippet, title)` that extracts:
- LinkedIn profile URL (normalized)
- Name (from title, usually "FirstName LastName - Role - Company | LinkedIn")
- Headline/Role (from title after first " - ")
- Organization (from title, usually after second " - ")
- Profile type: "individual" (linkedin.com/in/) or "company" (linkedin.com/company/)

Regex pattern for individual: `linkedin\.com/in/([a-zA-Z0-9_-]+)`
Regex pattern for company: `linkedin\.com/company/([a-zA-Z0-9_-]+)`

Filter out system pages: ['login', 'signup', 'jobs', 'feed', 'mynetwork', 'messaging', 'notifications', 'learning', 'pulse', 'posts', 'company/login']

### 5. Discovery Function
Create `discover_via_serpapi(subject, roles, cities, serpapi_key, status_container, round_num)`:
- Execute queries from the generator
- Parse results using URL parser
- Return list of unique LinkedIn profile dicts: {url, name, headline, organization, profile_type, snippet}
- Rate limit: time.sleep(1.5) between queries
- Handle errors: invalid key, quota exceeded, etc.
- Log progress to status_container

### 6. Deduplication System
- Sidebar file_uploader for Master CSV
- Function `load_existing_linkedin_leads(uploaded_file)` that reads CSV and returns:
  - set of existing LinkedIn URLs (normalized, lowercase, strip trailing slash)
  - set of existing names (for fuzzy dedup)
  - count and error message
- Store in st.session_state

### 7. Basic UI Layout
- Streamlit page config: title="TuTrain LinkedIn Discovery", icon="💼", layout="wide"
- Header with gradient styling (professional blue theme, not Instagram gradient)
- Sidebar with:
  - API key inputs
  - Active filters display
  - Target settings
  - CSV deduplication uploader
  - Phase info
- Main area: subject input, role filter, city filter, search button
- Status container for progress logs
- Basic results display as dataframe with LinkedIn URL as LinkColumn

### 8. Constants
```python
INSTITUTE_KEYWORDS = ['Academy', 'Institute', 'Classes', 'Coaching', 'Tutorial', 'School', 
    'Education', 'Center', 'Hub', 'Campus', 'Group', 'Team', 
    'System', 'Official', 'Centre', 'Learning', 'Foundation']

BRAND_BLACKLIST = ['PW', 'Physics Wallah', 'Unacademy', 'Vedantu', 'Byju', 
    'Allen', 'Adda247', 'Sankalp', 'Magnet Brains', 'Xylem', 'Utkarsh', 
    'Motion', 'Careerwill', 'Apna College', 'Infinity Learn', 'Doubtnut', 
    'Mahendra', 'Wi-Fi Study', 'Exampur', 'Next Toppers',
    'Infosys', 'TCS', 'Wipro', 'HCL', 'Accenture', 'Cognizant']

EDUCATION_ROLES = ['teacher', 'tutor', 'educator', 'professor', 'lecturer', 'faculty',
    'principal', 'vice principal', 'director', 'head of department', 'hod',
    'academic head', 'dean', 'founder', 'co-founder', 'ceo', 'coo', 'cto',
    'owner', 'managing director', 'administrator', 'coordinator']

INDIAN_CITIES = [
    "Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Jaipur", "Lucknow", "Kota", "Patna", "Chandigarh",
    "Ahmedabad", "Indore", "Bhopal", "Nagpur", "Varanasi", "Ranchi",
    "Dehradun", "Allahabad", "Noida", "Gurgaon", "Sikar", "Jodhpur"
]

# Safety Limits
MAX_SERPAPI_QUERIES = 50
MAX_APIFY_SCRAPES = 300
MAX_GEMINI_CALLS = 300
```

### 9. Requirements.txt
```
streamlit>=1.30.0
google-search-results>=2.4.2
apify-client>=1.6.0
google-generativeai>=0.3.0
pandas>=2.0.0
plotly>=5.18.0
```

The output should be a fully working Streamlit app that:
1. Takes subject + role + city inputs
2. Discovers LinkedIn profiles via SerpAPI Google dorking
3. Deduplicates against uploaded master CSV
4. Displays results in a table
5. Has a clean, professional UI

DO NOT implement Apify enrichment, Gemini classification, or scoring yet — those are later phases.
```

---

# ============================================================
# PHASE 2: Apify LinkedIn Profile Enrichment
# ============================================================

## Prompt for Phase 2:

```
Continue building the LinkedIn Agent (app.py in linkedin_agent/ directory).

## CONTEXT:
Phase 1 is complete. We have SerpAPI discovery that finds LinkedIn URLs + basic info from Google snippets. Now we need to ENRICH these profiles with full data using Apify LinkedIn scrapers.

## PHASE 2 SCOPE — Apify Profile Enrichment:

### 1. Multi-Key Apify Rotation System
Create a class `ApifyKeyManager` that handles multiple Apify API keys:

```python
class ApifyKeyManager:
    def __init__(self, keys: list):
        self.keys = [k for k in keys if k]  # Filter empty keys
        self.current_index = 0
        self.exhausted_keys = set()
    
    def get_current_key(self) -> str:
        """Return current active key, or None if all exhausted"""
        while self.current_index < len(self.keys):
            if self.current_index not in self.exhausted_keys:
                return self.keys[self.current_index]
            self.current_index += 1
        return None
    
    def mark_exhausted(self):
        """Mark current key as exhausted and rotate to next"""
        self.exhausted_keys.add(self.current_index)
        self.current_index += 1
        if self.current_index < len(self.keys):
            return self.keys[self.current_index]
        return None
    
    def get_status(self) -> str:
        """Return status string for sidebar display"""
        active = len(self.keys) - len(self.exhausted_keys)
        return f"{active}/{len(self.keys)} keys active (using key #{self.current_index + 1})"
```

### 2. Profile Scraping Function
Create `scrape_linkedin_profiles(urls: list, apify_manager: ApifyKeyManager, status_container) -> list`:

- Use Apify actor: "apify/linkedin-profile-scraper" (or "curious_coder/linkedin-profile-scraper" as fallback)
- Batch process in groups of 30 profiles (LinkedIn is stricter than Instagram)
- Input format: {"profileUrls": ["https://linkedin.com/in/username1", ...]}
- Extract these fields from each result:
  ```python
  profile = {
      "linkedin_url": item.get("url", ""),
      "full_name": item.get("fullName", "") or item.get("firstName", "") + " " + item.get("lastName", ""),
      "headline": item.get("headline", ""),
      "location": item.get("location", "") or item.get("geoLocation", ""),
      "about": item.get("about", "") or item.get("summary", ""),
      "followers": item.get("followersCount", 0) or item.get("connectionsCount", 0),
      "connections": item.get("connectionsCount", 0),
      "current_company": "",  # Extract from experience[0]
      "current_role": "",     # Extract from experience[0]
      "experience_years": 0,  # Calculate from experience list
      "education": "",        # Extract from education list
      "skills": [],           # Extract from skills list
      "profile_type": "individual",
      "raw_experience": [],   # Store full experience for Gemini
      "raw_education": [],    # Store full education for Gemini
  }
  ```
- Parse experience array to get current_company and current_role (first item where isCurrent=True or most recent)
- Calculate experience_years from the earliest experience date to now
- Handle key rotation: if Apify returns 402/quota error, call apify_manager.mark_exhausted() and retry with next key
- Rate limit: time.sleep(3) between batches
- Log progress to status_container

### 3. Company Page Scraping Function
Create `scrape_linkedin_companies(urls: list, apify_manager: ApifyKeyManager, status_container) -> list`:

- Use Apify actor: "apify/linkedin-company-scraper"
- Extract:
  ```python
  company = {
      "linkedin_url": item.get("url", ""),
      "company_name": item.get("name", ""),
      "description": item.get("description", ""),
      "industry": item.get("industry", ""),
      "company_size": item.get("employeeCount", "") or item.get("staffCount", ""),
      "location": item.get("headquarters", {}).get("city", ""),
      "website": item.get("website", ""),
      "founded": item.get("founded", ""),
      "specialties": item.get("specialties", []),
      "follower_count": item.get("followersCount", 0),
      "profile_type": "company",
  }
  ```
- Same key rotation and error handling as profile scraping

### 4. Unified Enrichment Function
Create `enrich_discovered_profiles(discovered: list, apify_manager: ApifyKeyManager, status_container) -> list`:

- Separate discovered profiles into individual URLs and company URLs
- Scrape individuals and companies separately
- Merge enriched data back with discovery data (keep snippet as fallback if scrape fails)
- Return combined list of enriched profiles
- If Apify is completely exhausted (all keys), return profiles with just discovery data (name, headline from SerpAPI)

### 5. Update UI
- Show ApifyKeyManager status in sidebar
- Add Apify key inputs for 3 keys:
  ```python
  st.sidebar.subheader("🔑 Apify Keys (Rotation)")
  apify_key_1 = st.sidebar.text_input("Apify Key 1", type="password")
  apify_key_2 = st.sidebar.text_input("Apify Key 2", type="password")
  apify_key_3 = st.sidebar.text_input("Apify Key 3", type="password")
  ```
- Show enrichment progress with profile count
- Update results table to show enriched fields (headline, location, company, connections)

### 6. Fallback Handling
If ALL Apify keys are exhausted or not provided:
- Continue with SerpAPI-only data (name, headline, snippet from Google)
- Mark profiles as "enrichment_status": "serpapi_only"
- Show warning in UI: "Profile enrichment skipped (no Apify credits). Results have limited data."

The app should still be fully functional without Apify — just with less data per profile.

IMPORTANT: Do NOT modify the SerpAPI discovery functions from Phase 1. Only ADD the enrichment layer on top.
```

---

# ============================================================
# PHASE 3: Hard Filters + Brand Blacklist
# ============================================================

## Prompt for Phase 3:

```
Continue building the LinkedIn Agent (app.py in linkedin_agent/ directory).

## CONTEXT:
Phase 1 (SerpAPI Discovery) and Phase 2 (Apify Enrichment) are complete. Now we need to filter out unqualified profiles using hard rules before sending to Gemini AI.

## PHASE 3 SCOPE — Hard Filters:

### 1. Education Relevance Filter
Create `is_education_relevant(profile: dict) -> tuple[bool, str]`:

Check headline, about, current_role, current_company, skills for education keywords.

```python
EDUCATION_KEYWORDS = [
    'teacher', 'tutor', 'educator', 'professor', 'lecturer', 'faculty',
    'principal', 'vice principal', 'director of education', 'academic',
    'head of department', 'hod', 'dean', 'coaching', 'classes',
    'school', 'academy', 'institute', 'college', 'university',
    'cbse', 'icse', 'igcse', 'ib', 'cambridge', 'neet', 'jee',
    'curriculum', 'pedagogy', 'learning', 'education', 'edtech',
    'tuition', 'teaching', 'instruction', 'mentoring', 'training',
    'mathematics', 'physics', 'chemistry', 'biology', 'english', 'science',
    'founder', 'ceo', 'coo', 'managing director'  # Only if combined with education context
]

NON_EDUCATION_KEYWORDS = [
    'software engineer', 'data scientist', 'product manager', 'marketing',
    'sales executive', 'business development', 'consultant', 'analyst',
    'recruiter', 'hr manager', 'finance', 'banking', 'real estate',
    'insurance', 'automotive', 'hospitality', 'retail'
]
```

Logic:
- Combine headline + about + current_role into single text
- Check for education keywords (at least 1 must match)
- Check for non-education keywords (if ONLY non-education keywords, reject)
- Founder/CEO/Director profiles need additional education context check
- Return (True/False, reason_string)

### 2. Brand Blacklist Filter
Create `is_blacklisted_brand(profile: dict) -> tuple[bool, str]`:

```python
BRAND_BLACKLIST = [
    # Big EdTech (reject)
    'Physics Wallah', 'PW', 'Unacademy', 'Vedantu', 'Byju', 'Allen',
    'Adda247', 'Sankalp', 'Magnet Brains', 'Xylem', 'Utkarsh',
    'Motion', 'Careerwill', 'Apna College', 'Infinity Learn', 'Doubtnut',
    'Mahendra', 'Wi-Fi Study', 'Exampur', 'Next Toppers',
    # Big Corp (reject)
    'Infosys', 'TCS', 'Wipro', 'HCL', 'Accenture', 'Cognizant',
    'Amazon', 'Google', 'Microsoft', 'Meta', 'Facebook', 'Apple',
    'Flipkart', 'Zomato', 'Swiggy', 'Paytm', 'Ola', 'Uber'
]
```

Check profile name, headline, current_company against blacklist.

### 3. Connection/Follower Filter
```python
MIN_CONNECTIONS = 100      # Too few = inactive/fake profile
MAX_CONNECTIONS = 30000    # Too many = likely a celebrity/influencer (not reachable)
```

For company pages:
```python
MIN_COMPANY_FOLLOWERS = 50
MAX_COMPANY_FOLLOWERS = 500000
```

### 4. Location Filter
Create `is_india_based(profile: dict) -> tuple[bool, str]`:

```python
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
```

Check location field. If location is empty, check headline and about for India indicators.
If still unclear, PASS (benefit of doubt — Gemini will verify later).

### 5. Completeness Filter
Reject profiles that are too sparse to be useful:
- Must have at least: name AND (headline OR current_role)
- If enrichment_status is "serpapi_only", must have at least: name AND snippet contains education keyword

### 6. Master Filter Function
Create `apply_hard_filters(profiles: list, status_container) -> tuple[list, dict]`:

Apply filters IN THIS ORDER (cheapest first):
1. Completeness filter
2. Brand blacklist
3. Location filter (India-based)
4. Connection/follower range
5. Education relevance

Return (filtered_profiles, rejection_stats_dict)

Log each rejection with reason to status_container:
```
🔍 Hard Filters Applied:
   Input: 150 | ✅ Passed: 45 | ❌ Rejected: 105
   📋 Rejections: Incomplete: 12 | Blacklisted: 8 | Non-India: 35 | Low connections: 15 | Non-education: 35
```

### 7. Update the Search Flow
After enrichment, apply hard filters before displaying results:
```
Discovery (SerpAPI) → Enrichment (Apify) → Hard Filters → Display
```

Update the results table to show only filtered profiles.
Show rejection summary in the status container.

IMPORTANT: 
- Hard filters should be FAST (no API calls, pure Python logic)
- Always give benefit of doubt for missing data (don't reject if field is empty, only reject if field clearly fails)
- Do NOT modify Phase 1 or Phase 2 code, only ADD Phase 3 functions and integrate them into the flow
```

---

# ============================================================
# PHASE 4: Gemini AI Classification
# ============================================================

## Prompt for Phase 4:

```
Continue building the LinkedIn Agent (app.py in linkedin_agent/ directory).

## CONTEXT:
Phase 1 (Discovery), Phase 2 (Enrichment), Phase 3 (Hard Filters) are complete. Now we classify filtered profiles using Gemini AI.

## PHASE 4 SCOPE — Gemini AI Classification:

### 1. Priority Chain (Same pattern as YouTube/Instagram agents)
Classification follows this STRICT priority order:
1. Brand Blacklist → Force reject as "Large Brand/Corporate" (already done in Phase 3, but double-check here)
2. Institute Keywords in name/company → Force classify as relevant type
3. Gemini AI → Full classification for unclear cases

### 2. Classification Function
Create `classify_linkedin_profile(profile: dict, api_key: str) -> dict`:

```python
# Return format:
{
    "persona_type": "Individual Tutor" | "Institute Leader" | "EdTech Decision-Maker" | "School Administrator" | "Coaching Institute Owner" | "Irrelevant",
    "subjects": ["Physics", "Mathematics"],  # Detected subjects
    "grades": ["11", "12"],  # Detected grades  
    "boards": ["CBSE", "IB"],  # Detected boards/curricula
    "organization_type": "School" | "Coaching Center" | "EdTech Company" | "Individual" | "University" | "Other",
    "seniority": "Owner/Founder" | "C-Level" | "Director" | "Principal" | "HOD" | "Teacher" | "Other",
    "collaboration_potential": "High" | "Medium" | "Low",
    "is_relevant": True | False,
    "reason": "Short explanation"
}
```

### 3. Gemini Prompt
```python
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
- Connections: {profile.get('connections', 0)}

Classify into ONE persona type:
- "Individual Tutor": Single teacher/tutor offering private or online classes
- "Institute Leader": Principal, VP, or director of a school or coaching center
- "EdTech Decision-Maker": Founder/CEO/COO/CXO of an edtech company
- "School Administrator": Admin staff, academic head, HOD at a school
- "Coaching Institute Owner": Owner of small-medium coaching center/academy
- "Irrelevant": Not related to education, or a big corporate employee

Also detect:
- subjects: from [Mathematics, Physics, Chemistry, Biology, Science, English, Computer Science, Economics, History, Geography, Hindi, Social Studies, Accountancy, Business Studies]
- grades: from [4,5,6,7,8,9,10,11,12]
- boards: from [CBSE, ICSE, IGCSE, IB, Cambridge, State Board, US Board, NEET, JEE]
- organization_type: "School", "Coaching Center", "EdTech Company", "Individual", "University", "Other"
- seniority: "Owner/Founder", "C-Level", "Director", "Principal", "HOD", "Teacher", "Other"
- collaboration_potential: "High" (decision-maker with reach), "Medium" (can influence), "Low" (limited scope)

Return ONLY this JSON (no markdown, no explanation):
{{"persona_type": "...", "subjects": [...], "grades": [...], "boards": [...], "organization_type": "...", "seniority": "...", "collaboration_potential": "...", "is_relevant": true, "reason": "..."}}"""
```

### 4. Gemini Quota Protection
```python
MAX_GEMINI_CALLS = 300  # Hard limit per search session

# Rate limiting
time.sleep(4)  # Between each Gemini call (free tier: ~15 req/min)
```

- Track gemini_calls counter
- Stop classification when limit reached
- Show warning in UI: "⚠️ Gemini limit reached (300 calls). Remaining profiles unclassified."
- Unclassified profiles: use keyword-based fallback (check headline for role keywords)

### 5. Fallback Classification (When Gemini fails or quota exhausted)
```python
def fallback_classify(profile: dict) -> dict:
    """Keyword-based classification when Gemini is unavailable"""
    headline_lower = (profile.get("headline", "") or "").lower()
    company_lower = (profile.get("current_company", "") or "").lower()
    
    # Check for institute keywords
    if any(kw.lower() in company_lower for kw in INSTITUTE_KEYWORDS):
        return {"persona_type": "Coaching Institute Owner", "is_relevant": True, ...}
    
    # Check for school roles
    if any(role in headline_lower for role in ["principal", "vice principal", "headmaster"]):
        return {"persona_type": "Institute Leader", "is_relevant": True, ...}
    
    # Check for founder/CEO
    if any(role in headline_lower for role in ["founder", "ceo", "co-founder"]):
        if any(kw in headline_lower + company_lower for kw in ["education", "edtech", "learn", "school", "academy"]):
            return {"persona_type": "EdTech Decision-Maker", "is_relevant": True, ...}
    
    # Check for teacher
    if any(role in headline_lower for role in ["teacher", "tutor", "educator", "faculty"]):
        return {"persona_type": "Individual Tutor", "is_relevant": True, ...}
    
    # Default
    return {"persona_type": "Individual Tutor", "is_relevant": True, "reason": "Fallback classification"}
```

### 6. Batch Classification Function
Create `classify_profiles(profiles: list, api_key: str, status_container) -> list`:

- Loop through profiles
- Call classify_linkedin_profile for each
- Track gemini_calls
- Apply rate limiting
- Use fallback when Gemini fails
- Log each classification result
- Add classification fields to profile dict
- Convert lists to strings: subjects_str, grades_str, boards_str

### 7. Update Search Flow
```
Discovery → Enrichment → Hard Filters → AI Classification → Display
```

Update results table to show: persona_type, subjects, seniority, collaboration_potential

IMPORTANT:
- Use model "gemini-2.5-flash" for classification
- Always parse Gemini response as JSON (strip markdown code blocks if present)
- NEVER let a Gemini error crash the app — always fallback gracefully
- Track and display Gemini call count in status container
```

---

# ============================================================
# PHASE 5: Contact Extraction + Tier Scoring
# ============================================================

## Prompt for Phase 5:

```
Continue building the LinkedIn Agent (app.py in linkedin_agent/ directory).

## CONTEXT:
Phases 1-4 are complete. Now we extract contact info from profiles and score them into tiers.

## PHASE 5 SCOPE — Contact Extraction + Tier Scoring:

### 1. Contact Extraction
Create `extract_linkedin_contacts(profile: dict) -> dict`:

Extract from: about section, headline, experience descriptions, website field

```python
contacts = {
    "email": "",
    "phone": "",
    "website": "",
    "twitter": "",
    "facebook": "",
    "instagram": "",
    "youtube": "",
    "whatsapp": "",
    "telegram": "",
    "other_links": ""
}
```

Regex patterns:
- Email: standard email pattern (same as YouTube/Instagram agents)
- Phone: Indian phone numbers (10 digit, with/without +91, with/without spaces/dashes)
  ```python
  phone_pattern = r'(?:\+91[\s-]?)?(?:0)?[6-9]\d{9}'
  ```
- WhatsApp: wa.me links, chat.whatsapp.com links
- Website: generic URLs excluding social media domains
- Telegram: t.me links
- Twitter/X: twitter.com or x.com links
- Instagram: instagram.com links
- YouTube: youtube.com or youtu.be links
- Linktree: linktr.ee links

IMPORTANT: LinkedIn "about" sections often contain contact info. Also check the external "website" field from Apify data.

### 2. Contact Confidence Level
```python
def calculate_contact_confidence(contacts: dict) -> str:
    has_email = bool(contacts.get("email"))
    has_phone = bool(contacts.get("phone"))
    has_website = bool(contacts.get("website"))
    has_social = any([contacts.get("twitter"), contacts.get("instagram"), 
                      contacts.get("facebook"), contacts.get("youtube")])
    has_messaging = any([contacts.get("whatsapp"), contacts.get("telegram")])
    
    if has_email and has_phone:
        return "High"
    elif has_email or has_phone:
        return "Medium"  
    elif has_website or has_messaging:
        return "Medium-Low"
    elif has_social:
        return "Low"
    else:
        return "LinkedIn Only"  # Can still reach via LinkedIn InMail/connection
```

### 3. Tier Scoring System
Create `calculate_linkedin_tier(profile: dict, contacts: dict, classification: dict) -> str`:

Scoring logic (adapted for B2B LinkedIn context):

```
Tier A (🟢 Immediate Outreach):
- Decision-maker (Founder/CEO/Principal/Director) 
- AND has direct contact (email or phone)
- AND collaboration_potential is "High"

Tier B (🔵 High Priority):
- Has some contact info (email OR phone OR website)
- AND is_relevant = True
- AND seniority is at least "HOD" level

Tier C (🟡 Standard):
- is_relevant = True
- AND has LinkedIn profile (can send connection request)
- BUT limited contact info

Tier D (🔴 Low Priority):
- Teacher/Tutor with no contact info
- OR very low connections (<200)
- OR classification uncertain
```

### 4. AI Collaboration Fit Summary
Create `generate_linkedin_fit_summary(profile: dict, api_key: str) -> str`:

Only for Tier A and Tier B leads (save Gemini quota):

```python
prompt = f"""Write a 2-sentence summary of why this LinkedIn professional would be a good collaboration partner for TuTrain (an online tutoring platform for Grade 4-12, CBSE/ICSE/IB/Cambridge).

Profile:
- Name: {profile.get('full_name', '')}
- Role: {profile.get('current_role', '')} at {profile.get('current_company', '')}
- Persona: {profile.get('persona_type', '')}
- Seniority: {profile.get('seniority', '')}
- Location: {profile.get('location', '')}
- Subjects: {profile.get('subjects_str', 'N/A')}
- Connections: {profile.get('connections', 0)}
- Contact Confidence: {profile.get('contact_confidence', '')}

Return ONLY the 2-sentence summary."""
```

For Tier C/D, auto-generate:
```python
f"{profile.get('persona_type', 'Professional')} at {profile.get('current_company', 'N/A')} in {profile.get('location', 'India')} with {profile.get('connections', 0)} connections."
```

### 5. Process All Profiles
Create `process_contacts_and_tiers(profiles: list, api_key: str, status_container) -> list`:

For each profile:
1. Extract contacts
2. Calculate contact confidence
3. Calculate tier
4. Generate AI summary (Tier A/B only)
5. Add all fields to profile dict

### 6. Update Search Flow
```
Discovery → Enrichment → Hard Filters → AI Classification → Contact Extraction + Tier Scoring → Display
```

IMPORTANT:
- Gemini calls for fit summaries count toward the same MAX_GEMINI_CALLS limit
- time.sleep(4) between Gemini calls
- Always handle Gemini failures gracefully with auto-generated fallback summaries
```

---

# ============================================================
# PHASE 6: Deep Filtering Loop (Target Count Guarantee)
# ============================================================

## Prompt for Phase 6:

```
Continue building the LinkedIn Agent (app.py in linkedin_agent/ directory).

## CONTEXT:
Phases 1-5 are complete. Now we need to wrap everything in a Deep Filtering Loop that keeps searching until the target lead count is reached — the same pattern used in our YouTube and Instagram agents.

## PHASE 6 SCOPE — Deep Filtering Loop:

### 1. Master Orchestrator Function
Create `smart_fetch_linkedin_profiles(subject, roles, cities, target_count, serpapi_key, apify_manager, google_api_key, status_container, existing_urls) -> list`:

This is the MAIN function that loops until target_count approved leads are found.

```python
def smart_fetch_linkedin_profiles(
    subject: str,
    roles: list,
    cities: list,
    target_count: int,
    serpapi_key: str,
    apify_manager,  # ApifyKeyManager instance
    google_api_key: str,
    status_container,
    existing_urls: set = None
) -> list:
    approved_leads = []
    seen_urls = existing_urls.copy() if existing_urls else set()
    
    # Counters
    gemini_calls = 0
    serpapi_calls = 0
    total_profiles_scraped = 0
    rejected_brand = 0
    rejected_filters = 0
    rejected_duplicate = 0
    search_round = 0
    max_rounds = 20
    consecutive_empty_rounds = 0
    
    while len(approved_leads) < target_count and search_round < max_rounds:
        search_round += 1
        
        # Safety limits check
        if gemini_calls >= MAX_GEMINI_CALLS:
            break
        if serpapi_calls >= MAX_SERPAPI_QUERIES:
            break
        
        # ===== DISCOVERY PHASE =====
        # SerpAPI with round-based query rotation
        discovered = discover_via_serpapi(subject, roles, cities, serpapi_key, status_container, round_num=search_round-1)
        serpapi_calls += len(queries_used)
        
        # Dedup against master CSV + already seen
        new_profiles = [p for p in discovered if p["url"].lower().rstrip("/") not in seen_urls]
        rejected_duplicate += len(discovered) - len(new_profiles)
        
        if not new_profiles:
            consecutive_empty_rounds += 1
            if consecutive_empty_rounds >= 4:
                break  # Exhausted discovery
            continue
        else:
            consecutive_empty_rounds = 0
        
        # Add to seen
        for p in new_profiles:
            seen_urls.add(p["url"].lower().rstrip("/"))
        
        # ===== ENRICHMENT PHASE =====
        # Batch size: min(remaining_needed * 4, 50, new_profiles count)
        remaining = target_count - len(approved_leads)
        batch_size = min(remaining * 4, 50, len(new_profiles))
        batch = new_profiles[:batch_size]
        
        enriched = enrich_discovered_profiles(batch, apify_manager, status_container)
        total_profiles_scraped += len(enriched)
        
        # ===== HARD FILTERS =====
        filtered, rejection_stats = apply_hard_filters(enriched, status_container)
        rejected_filters += len(enriched) - len(filtered)
        
        # ===== AI CLASSIFICATION + CONTACTS + TIERS =====
        for profile in filtered:
            if len(approved_leads) >= target_count:
                break
            if gemini_calls >= MAX_GEMINI_CALLS:
                break
            
            # Classify
            gemini_calls += 1
            classification = classify_linkedin_profile(profile, google_api_key)
            time.sleep(4)
            
            if not classification.get("is_relevant", True):
                rejected_brand += 1
                continue
            
            # Add classification to profile
            profile.update(classification)
            profile["subjects_str"] = ", ".join(classification.get("subjects", []))
            profile["grades_str"] = ", ".join(classification.get("grades", []))
            profile["boards_str"] = ", ".join(classification.get("boards", []))
            
            # Extract contacts
            contacts = extract_linkedin_contacts(profile)
            profile.update(contacts)
            profile["contact_confidence"] = calculate_contact_confidence(contacts)
            
            # Calculate tier
            tier = calculate_linkedin_tier(profile, contacts, classification)
            profile["tier"] = tier
            
            # AI Summary (Tier A/B only)
            if tier in ["A", "B"] and gemini_calls < MAX_GEMINI_CALLS:
                gemini_calls += 1
                profile["ai_summary"] = generate_linkedin_fit_summary(profile, google_api_key)
                time.sleep(4)
            else:
                profile["ai_summary"] = auto_generate_summary(profile)
            
            approved_leads.append(profile)
            status_container.write(f"✅ {profile['full_name'][:25]} → {classification['persona_type']} | Tier {tier}")
        
        # Round summary
        status_container.write(f"📈 Round {search_round}: {len(approved_leads)}/{target_count} approved")
    
    # Final summary
    status_container.write(f"🏁 Complete: {len(approved_leads)}/{target_count} | Rounds: {search_round} | Gemini: {gemini_calls}")
    
    return approved_leads
```

### 2. Adaptive Behaviors
Same patterns as Instagram agent:

- **High duplicate rate (>70%)**: Auto-broaden search queries (add more cities, alternate roles)
- **Low approval rate after round 8**: Relax hard filters slightly (lower min_connections from 100 to 50)
- **Consecutive empty rounds (4+)**: Stop searching, report to user
- **Gemini quota near limit**: Use fallback classification for remaining profiles

### 3. Safety Limits
```python
MAX_SERPAPI_QUERIES = 50
MAX_APIFY_SCRAPES = 300
MAX_GEMINI_CALLS = 300
MAX_SEARCH_ROUNDS = 20
```

### 4. Update Main Search Button Handler
Replace the current linear flow with the Deep Filtering Loop:

```python
if search_clicked:
    # Initialize ApifyKeyManager
    apify_manager = ApifyKeyManager([apify_key_1, apify_key_2, apify_key_3])
    
    # Get existing URLs from session state
    existing_urls = st.session_state.get("existing_urls", set())
    
    with st.status("🔍 Deep Filtering Search...", expanded=True) as status:
        results = smart_fetch_linkedin_profiles(
            subject, roles, cities, target_count,
            serpapi_key, apify_manager, google_api_key,
            status, existing_urls
        )
    
    if results:
        # Display dashboard
        ...
```

### 5. Progress Tracking
Show in status_container during each round:
```
🔄 Round 3/20 (Have: 12/25)
🔍 Discovery: 45 found, 12 new, 33 duplicates
👤 Enrichment: 12 profiles scraped
🔍 Filters: 8/12 passed
🤖 Classification: 6/8 relevant
📊 Round complete: 18/25 approved
```

IMPORTANT:
- The loop MUST respect all safety limits (SerpAPI, Apify, Gemini)
- The loop MUST handle API errors gracefully (don't crash, skip and continue)
- The loop MUST track and display ALL deduplication stats
- The loop MUST auto-rotate Apify keys when quota exhausts
```

---

# ============================================================
# PHASE 7: Dashboard + CSV Export + Final UI
# ============================================================

## Prompt for Phase 7:

```
Continue building the LinkedIn Agent (app.py in linkedin_agent/ directory).

## CONTEXT:
Phases 1-6 are complete. The Deep Filtering Loop works. Now we need a polished dashboard, charts, and CSV export — matching the quality of our YouTube and Instagram agents.

## PHASE 7 SCOPE — Dashboard + Export:

### 1. KPI Metrics Row (Top of Dashboard)
4 cards with gradient backgrounds:

```python
col1, col2, col3, col4 = st.columns(4)
# Card 1: Total Found (blue gradient)
# Card 2: Approved Leads (green gradient)  
# Card 3: Avg Connections (purple gradient)
# Card 4: Decision Makers (amber gradient) — count of Tier A leads
```

Use the same HTML/CSS card style as the YouTube agent (gradient backgrounds, shadow, centered text).

### 2. Quality Map (Scatter Plot)
Using Plotly:
- X-axis: Connections count
- Y-axis: Collaboration Potential score (map High=3, Medium=2, Low=1)
- Color: Tier (A=green, B=blue, C=amber, D=red)
- Hover: Name, Persona Type, Company, Connections
- Title: "🎯 Quality Map: Decision-Maker Reach vs Potential"

### 3. Pipeline Distribution Charts
Two donut charts side by side:

Chart 1: Persona Type Distribution
- Individual Tutor, Institute Leader, EdTech Decision-Maker, School Administrator, Coaching Institute Owner

Chart 2: Tier Distribution (Approved Only)
- A (green), B (blue), C (amber), D (red)

### 4. Data Table
Streamlit dataframe with these columns:
```python
display_df = pd.DataFrame({
    "Name": ...,
    "Persona": ...,  # persona_type
    "Seniority": ...,
    "Organization": ...,  # current_company
    "Location": ...,
    "Subjects": ...,  # subjects_str
    "Connections": ...,
    "Contact": ...,  # contact_confidence
    "Tier": ...,
    "LinkedIn": ...,  # linkedin_url as LinkColumn
})
```

Sort by Tier (A first), then by connections (descending).

### 5. Tier Metrics Row
```python
col1, col2, col3, col4 = st.columns(4)
st.metric("Tier A", count_a, help="Decision-makers with direct contact")
st.metric("Tier B", count_b, help="Relevant with some contact")
st.metric("Tier C", count_c, help="Relevant, LinkedIn-only contact")
st.metric("Tier D", count_d, help="Low priority")
```

### 6. CSV Export (FULL DATA)
Two download buttons:

Button 1: "📥 Download All Leads (CSV)" — all approved leads
Button 2: "📥 Download Tier A+B Only" — high priority leads

Export DataFrame columns (comprehensive):
```python
export_df = pd.DataFrame({
    "Subject Tag": ...,
    "Full Name": ...,
    "LinkedIn URL": ...,
    "Persona Type": ...,
    "Seniority": ...,
    "Organization": ...,
    "Organization Type": ...,
    "Location": ...,
    "Subjects": ...,
    "Grades": ...,
    "Boards": ...,
    "Connections": ...,
    "Followers": ...,
    "Experience Years": ...,
    "Email": ...,
    "Phone": ...,
    "Website": ...,
    "WhatsApp": ...,
    "Telegram": ...,
    "Twitter": ...,
    "Instagram": ...,
    "YouTube": ...,
    "Other Links": ...,
    "Contact Confidence": ...,
    "Collaboration Potential": ...,
    "Tier": ...,
    "AI Summary": ...,
    "Headline": ...,
    "About": ...,  # Truncated to 500 chars
    "Search Date": ...,
})
```

### 7. Sidebar — Final Polish
```python
with st.sidebar:
    st.subheader("🎯 Target Settings")
    target_count = st.slider("Target Lead Count", 5, 100, 25, step=5)
    
    st.divider()
    
    st.subheader("📋 Active Filters")
    st.markdown(f"""
    **Region:** India 🇮🇳
    **Connections:** {MIN_CONNECTIONS} - {MAX_CONNECTIONS}
    **AI Filter:** Education-relevant profiles
    **Blacklist:** Big EdTech + Big Corp
    **Max SerpAPI:** {MAX_SERPAPI_QUERIES}
    **Max Gemini:** {MAX_GEMINI_CALLS}
    """)
    
    st.divider()
    
    st.subheader("⭐ Tier Scoring")
    st.markdown("""
    **A** 🟢 Decision-maker + Direct contact + High potential
    **B** 🔵 Relevant + Has contact info
    **C** 🟡 Relevant + LinkedIn only
    **D** 🔴 Low priority / Uncertain
    """)
    
    st.divider()
    
    st.subheader("📂 Deduplication")
    master_csv = st.file_uploader("Upload Master Lead CSV", type=["csv"])
    
    st.divider()
    
    st.subheader("💼 Agent Info")
    st.markdown("""
    ✅ SerpAPI Google Dorking
    ✅ Apify LinkedIn Enrichment (3 keys)
    ✅ Hard Filters (Brand, Location, Education)
    ✅ Gemini AI Classification
    ✅ Contact Extraction
    ✅ Tier Scoring (A/B/C/D)
    ✅ Deep Filtering Loop
    ✅ CSV Deduplication
    ✅ Quality Map + Charts
    """)
```

### 8. Page Styling
Professional blue theme (LinkedIn-inspired):
```python
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #0077B5 0%, #004182 100%);
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
}
.main-header h1 { color: #ffffff !important; }
.main-header p { color: #cce5ff !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💼 TuTrain LinkedIn Discovery Engine</h1>
    <p>Discover Educators, Principals, Directors & EdTech Leaders for Collaboration</p>
</div>
""", unsafe_allow_html=True)
```

### 9. Final Flow
When search button is clicked:
1. Deep Filtering Loop runs (Discovery → Enrich → Filter → Classify → Contact → Tier)
2. Show status progress
3. When complete, show KPI cards
4. Show Quality Map + Pipeline charts
5. Show Data Table
6. Show Tier metrics
7. Show Download buttons

IMPORTANT:
- Match the UI quality of the YouTube agent (gradient cards, Plotly charts, clean layout)
- The CSV export must include ALL fields — this is the master sheet that gets re-uploaded for dedup
- Column names in export must be consistent so dedup works when re-uploaded
- "LinkedIn URL" column is the primary dedup key
```

---

# ============================================================
# PHASE 8: Testing, Edge Cases & Polish
# ============================================================

## Prompt for Phase 8:

```
Review and polish the LinkedIn Agent (app.py in linkedin_agent/ directory).

## PHASE 8 SCOPE — Testing & Edge Cases:

### 1. Error Handling Audit
Go through EVERY API call and ensure:
- SerpAPI calls: wrapped in try/except, handle invalid key, quota exceeded, network errors
- Apify calls: wrapped in try/except, handle 402/quota, invalid key, timeout (set timeout_secs=180)
- Gemini calls: wrapped in try/except, handle rate limit, invalid response, JSON parse errors
- File upload: wrapped in try/except, handle corrupt CSV, missing columns

### 2. Edge Cases to Handle
- Empty search results: Show "No results found, try different keywords"
- All profiles filtered out: Show "No profiles passed filters, try broader search"
- All Apify keys exhausted: Continue with SerpAPI-only data, show warning
- Gemini quota exhausted mid-loop: Use fallback classification for remaining
- Master CSV has no "LinkedIn URL" column: Show clear error message
- User enters empty subject: Show validation error
- User doesn't provide any API keys: Show clear instructions
- LinkedIn returns 0 results for some queries: Skip and try next query variant

### 3. Performance Optimizations
- Don't re-scrape profiles that failed in a previous round
- Cache SerpAPI results within session using st.session_state
- Batch Apify calls efficiently (groups of 30)
- Don't call Gemini for profiles that are obviously irrelevant (headline clearly non-education)

### 4. UI Polish
- All status messages should use emojis consistently (✅ ❌ ⚠️ 🔄 📊 🎯 etc.)
- Progress percentages where possible
- Final summary should match YouTube/Instagram agent format
- Charts should be responsive (use_container_width=True)
- Table should have proper column formatting (numbers, links)

### 5. Code Quality
- Add docstrings to all functions
- Add type hints to all function parameters
- Constants at the top of the file
- No hardcoded API keys in code
- Suppress all warnings (same as YouTube agent)

### 6. Test Scenarios
Mentally walk through these scenarios and fix any issues:

Scenario 1: Search "Physics Teacher" with no API keys → Should show clear error
Scenario 2: Search "Principal" with only SerpAPI key → Should work with discovery-only mode
Scenario 3: Search "EdTech Founder" with all keys → Full pipeline should work
Scenario 4: Upload CSV with 100 existing leads, search for 25 new → Should skip all 100 existing
Scenario 5: All Apify keys exhaust after 50 profiles → Should continue with SerpAPI data
Scenario 6: Gemini hits rate limit → Should fallback gracefully

### 7. Final README.md
Create a README.md in the linkedin_agent/ directory:

```markdown
# TuTrain LinkedIn Educator Discovery Agent

## Overview
AI-powered discovery engine to find educators, principals, directors, and edtech leaders on LinkedIn for collaboration opportunities.

## Features
- 🌐 Google dorking via SerpAPI (site:linkedin.com)
- 👤 Profile enrichment via Apify (3-key rotation)
- 🔍 Hard filters (education relevance, brand blacklist, location)
- 🤖 Gemini AI classification (persona type, subjects, grades, boards)
- 📞 Contact extraction (email, phone, social links)
- ⭐ Tier scoring (A/B/C/D)
- 📝 AI collaboration fit summaries
- 🎯 Deep Filtering Loop (searches until target met)
- 📂 CSV deduplication (master sheet upload)
- 📊 Quality Map + Pipeline charts
- 📥 Full CSV export

## Setup
1. pip install -r requirements.txt
2. Configure API keys in sidebar or .streamlit/secrets.toml
3. streamlit run app.py

## API Keys Needed
- SerpAPI (serpapi.com) — Google search, 100 free/month
- Apify x3 (apify.com) — LinkedIn scraping, $5 free each
- Google API Key (aistudio.google.com) — Gemini AI classification
```

Run through the entire codebase and ensure everything works as a cohesive unit. Fix any bugs, inconsistencies, or missing integrations between phases.
```

---

# ============================================================
# QUICK REFERENCE: KEY PATTERNS FROM YOUTUBE/INSTAGRAM AGENTS
# ============================================================

## Patterns to Reuse (Tell the AI agent about these):

### 1. Apify Key Rotation Pattern
```
When Apify returns error with "402", "quota", "credit", "limit" → switch to next key
Track exhausted keys in a set
Show active key count in sidebar
```

### 2. CSV Dedup Pattern
```
User uploads master CSV → extract primary key column → normalize → store in session_state
During discovery, check each new profile against existing set
Count and report duplicates
```

### 3. Deep Loop Pattern
```
while approved < target AND round < max_rounds:
    discover new profiles (different queries each round)
    dedup against master + seen
    enrich (Apify)
    filter (hard rules)
    classify (Gemini with fallback)
    extract contacts
    score tier
    append approved
    
    if consecutive_empty >= 4: break
    if gemini_calls >= MAX: break
```

### 4. Gemini Safety Pattern
```
MAX_GEMINI_CALLS = 300
time.sleep(4) between calls
Always try/except with fallback
Parse JSON response: strip markdown code blocks first
Track call count globally
```

### 5. Status Logging Pattern
```
status_container.write(f"✅ ...")  # Success
status_container.write(f"❌ ...")  # Rejection
status_container.write(f"⚠️ ...")  # Warning
status_container.write(f"🔄 ...")  # Progress
status_container.write(f"📊 ...")  # Stats
```
