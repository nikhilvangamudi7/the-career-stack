# backend/app.py
import os, csv, sqlite3, asyncio, re
from datetime import datetime, timedelta
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup

ROOT = os.path.dirname(__file__)
COMPANIES_CSV = os.getenv("COMPANIES_CSV", os.path.join(ROOT, "companies.csv"))
CACHE_DB = os.getenv("CACHE_DB", os.path.join(ROOT, "jobs_cache.db"))
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "60"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = FastAPI(title="The Career Stack - Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- Simple SQLite cache
def init_db():
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS jobs (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   company TEXT,
                   title TEXT,
                   url TEXT,
                   location TEXT,
                   scraped_at TEXT
                 )""")
    c.execute("""CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)""")
    conn.commit(); conn.close()
init_db()

def set_meta(k,v):
    conn = sqlite3.connect(CACHE_DB); c=conn.cursor(); c.execute("INSERT OR REPLACE INTO meta (key,value) VALUES (?,?)",(k,str(v))); conn.commit(); conn.close()
def get_meta(k):
    conn = sqlite3.connect(CACHE_DB); c=conn.cursor(); c.execute("SELECT value FROM meta WHERE key=?",(k,)); r=c.fetchone(); conn.close(); return r[0] if r else None
def clear_jobs():
    conn = sqlite3.connect(CACHE_DB); c=conn.cursor(); c.execute("DELETE FROM jobs"); conn.commit(); conn.close()
def add_job(company,title,url,location=""):
    conn = sqlite3.connect(CACHE_DB); c=conn.cursor(); c.execute("INSERT INTO jobs (company,title,url,location,scraped_at) VALUES (?,?,?,?,?)", (company,title,url,location,datetime.utcnow().isoformat())); conn.commit(); conn.close()
def read_jobs(limit=1000):
    conn = sqlite3.connect(CACHE_DB); c=conn.cursor(); c.execute("SELECT company,title,url,location,scraped_at FROM jobs ORDER BY scraped_at DESC LIMIT ?", (limit,)); rows=c.fetchall(); conn.close(); return [{"company":r[0],"title":r[1],"url":r[2],"location":r[3],"scraped_at":r[4]} for r in rows]

# --- load companies CSV
def load_companies(path=COMPANIES_CSV):
    rows=[]
    if not os.path.exists(path):
        return rows
    with open(path,newline="",encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

# --- heuristics for job extraction
JOB_LINK_PAT = re.compile(r'job|careers|openings|positions|apply', re.I)
def extract_jobs_from_html(company, base_url, html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    results=[]
    # anchors
    for a in soup.find_all("a", href=True):
        href=a["href"]; text=(a.get_text() or "").strip()
        if not text:
            text=a.get("aria-label","").strip()
        if (text and JOB_LINK_PAT.search(href + " " + text)) or JOB_LINK_PAT.search(text):
            full = href if href.startswith("http") else httpx.URL(base_url).join(href)
            results.append({"company":company, "title": text or href, "url": str(full), "location": ""})
    # containers
    selectors = ['[class*="job"]','[id*="job"]','[class*="opening"]','[class*="position"]','li','tr']
    for sel in selectors:
        for node in soup.select(sel):
            txt=node.get_text(separator=" ", strip=True)
            if len(txt)<15: continue
            if any(k in txt.lower() for k in ["engineer","developer","analyst","manager","intern","security","cyber"]):
                a=node.find("a", href=True)
                if a:
                    href=a["href"]; full = href if href.startswith("http") else httpx.URL(base_url).join(href)
                    results.append({"company":company, "title": (a.get_text(strip=True) or txt[:80]), "url": str(full), "location": ""})
    # dedupe
    seen=set(); out=[]
    for r in results:
        if r["url"] in seen: continue
        seen.add(r["url"]); out.append(r)
    return out

# --- async fetch
async def fetch_page(client, company_row):
    url = company_row.get("Career Page URL") or company_row.get("career") or company_row.get("career_page") or company_row.get("CareerPage")
    if not url:
        return []
    try:
        r = await client.get(url, follow_redirects=True, timeout=20.0)
        if r.status_code != 200:
            return []
        return extract_jobs_from_html(company_row.get("Company Name","Unknown"), r.url, r.text)
    except Exception:
        return []

@app.get("/api/fetch-latest")
async def fetch_latest(force: bool = Query(False)):
    last_run = get_meta("last_run")
    if last_run and not force:
        last = datetime.fromisoformat(last_run)
        if datetime.utcnow() - last < timedelta(minutes=CACHE_TTL_MINUTES):
            return {"status":"cached","last_run":last_run,"jobs":read_jobs(1000)}
    companies = load_companies()
    if not companies:
        raise HTTPException(400, "No companies CSV found on server.")
    clear_jobs()
    # polite concurrency
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(headers={"User-Agent":"TheCareerStackBot/1.0"}) as client:
        async def wrapped(c):
            async with sem:
                await asyncio.sleep(0.05)
                return await fetch_page(client, c)
        tasks=[wrapped(c) for c in companies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    count=0
    for res in results:
        if isinstance(res, list):
            for r in res:
                add_job(r["company"], r["title"], r["url"], r.get("location",""))
                count += 1
    set_meta("last_run", datetime.utcnow().isoformat())
    return {"status":"scraped","count":count,"last_run":get_meta("last_run"),"jobs": read_jobs(1000)}

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV allowed")
    contents = await file.read()
    with open(COMPANIES_CSV,"wb") as f:
        f.write(contents)
    return {"status":"ok","message":"uploaded"}

@app.post("/api/send-telegram")
async def send_telegram(title: str, company: str, url: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        raise HTTPException(400, "Telegram token/chat not set")
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    text = f"🚀 New Job: {title}\n🏢 {company}\n🔗 {url}"
    async with httpx.AsyncClient() as client:
        r = await client.post(send_url, json={"chat_id":TELEGRAM_CHAT_ID, "text": text})
    return {"ok": r.status_code == 200, "resp": await r.json()}

@app.get("/api/health")
def health():
    return {"status":"ok"}
