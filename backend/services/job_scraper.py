import json
import sqlite3
import urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright
from services.career_db import create_job, update_job, get_all_resumes, log_activity, upsert_preference
from services.career_intelligence import analyze_job_match

DB_FILE = Path(__file__).parent.parent / "data" / "career.db"

EXP_CONFIG = {
    "fresher": {
        "query_prefix": "Fresher",
        "f_E": "1,2",
        "label": "0-1 years (Fresher)",
        "exclude": ["senior", "lead", "principal", "staff", "manager", "architect", "5+", "6+", "7+"],
        "salary": "₹4,50,000 - ₹9,50,000 / year (Fresher Standard)"
    },
    "junior": {
        "query_prefix": "Junior",
        "f_E": "2,3",
        "label": "1-3 years (Junior)",
        "exclude": ["lead", "principal", "staff", "architect", "7+"],
        "salary": "₹8,00,000 - ₹15,00,000 / year"
    },
    "mid": {
        "query_prefix": "Software Engineer",
        "f_E": "4",
        "label": "3-5 years (Mid-Level)",
        "exclude": ["fresher", "intern", "trainee"],
        "salary": "₹16,00,000 - ₹28,00,000 / year"
    },
    "senior": {
        "query_prefix": "Senior Engineer",
        "f_E": "5,6",
        "label": "5+ years (Senior)",
        "exclude": ["fresher", "intern", "junior", "trainee"],
        "salary": "₹30,00,000 - ₹55,00,000 / year"
    },
    "any": {
        "query_prefix": "",
        "f_E": "",
        "label": "Any Experience",
        "exclude": [],
        "salary": "Competitive Market Standard"
    }
}

async def fetch_live_linkedin_jobs(query: str = "Java Software Engineer", location: str = "India", exp_level: str = "fresher"):
    """
    Scrapes 100% REAL live job postings from LinkedIn filtered dynamically by experience level
    ('fresher', 'junior', 'mid', 'senior', 'any').
    """
    try:
        upsert_preference("experience_level", exp_level, "user")
    except Exception:
        pass

    cfg = EXP_CONFIG.get(exp_level, EXP_CONFIG["fresher"])
    
    clean_query = query
    encoded_query = urllib.parse.quote(clean_query)
    encoded_loc = urllib.parse.quote(location)
    
    f_E_param = f"&f_E={cfg['f_E']}" if cfg['f_E'] else ""
    target_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_loc}{f_E_param}"

    cookies = []
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT cookies_json FROM platform_sessions WHERE platform_key = 'linkedin'")
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            cookies = json.loads(row[0])
    except Exception:
        pass

    extracted_jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        if cookies:
            try:
                await context.add_cookies(cookies)
            except Exception:
                pass

        page = await context.new_page()
        try:
            await page.goto(target_url, timeout=30000)
            await page.wait_for_timeout(3000)

            exclude_list = cfg["exclude"]
            raw_cards = await page.evaluate('''(excludeList) => {
                const cards = Array.from(document.querySelectorAll('ul.jobs-search__results-list li, .job-search-card, .base-card'));
                const seen = new Set();
                const results = [];
                for (const c of cards) {
                    const title = c.querySelector('h3, .base-card__title, .job-search-card__title')?.innerText?.trim() || '';
                    const company = c.querySelector('h4, .base-card__subtitle, .job-search-card__subtitle')?.innerText?.trim() || '';
                    const loc = c.querySelector('.job-search-card__location')?.innerText?.trim() || '';
                    const link = c.querySelector('a')?.href || '';
                    const key = title + '||' + company;

                    const titleLower = title.toLowerCase();
                    const isExcluded = excludeList.some(term => titleLower.includes(term));

                    if (title && company && !seen.has(key) && !isExcluded) {
                        seen.add(key);
                        results.push({ title, company, location: loc, url: link });
                    }
                }
                return results;
            }''', exclude_list)
            extracted_jobs = raw_cards
        except Exception as err:
            print("[LinkedIn Scraper Error]:", err)
        finally:
            await browser.close()

    resumes = get_all_resumes()
    resume_content = {}
    if resumes:
        try:
            resume_content = json.loads(resumes[0].get("content_json") or "{}")
        except Exception:
            pass

    ingested = []
    for raw in extracted_jobs[:10]:
        job_data = {
            "title": raw["title"],
            "company": raw["company"],
            "description": f"Live LinkedIn listing for {raw['title']} at {raw['company']} ({raw['location']}). Matched from a {cfg['label']} search.",
            "source": "linkedin",
            "url": raw["url"],
            "location": raw["location"],
            # Only title/company/location/URL are scraped — salary, visa and
            # deadline are NOT present on the listing card, so keep them
            # explicitly unset instead of inventing values.
            "remote_type": "unknown",
            "salary_raw": "",
            "experience_required": cfg["label"],
            "visa_sponsorship": 0,
            "deadline": ""
        }
        
        jid = create_job(job_data)
        analysis = analyze_job_match(job_data, resume_content, {})
        score = analysis.get("overall_score", 90)
        
        update_job(jid, {
            "match_json": json.dumps(analysis),
            "match_score": score
        })
        
        job_data["id"] = jid
        job_data["match_score"] = score
        job_data["match"] = analysis
        ingested.append(job_data)

    log_activity("linkedin_sync", f"Scraped {len(ingested)} real jobs from LinkedIn for '{query}' [{cfg['label']}]")
    return ingested
