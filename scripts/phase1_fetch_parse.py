# Phase 1: SEC EDGAR N-PX Data Fetcher (Google Colab)
# Run in Google Colab with Drive mounted at /content/drive
# First time: from google.colab import drive; drive.mount('/content/drive')

import requests, sqlite3, json, time
import xml.etree.ElementTree as ET
from pathlib import Path

HEADERS = {"User-Agent": "Kamran Ali kamibaigal62@gmail.com"}
NS      = "http://www.sec.gov/edgar/document/npxproxy/informationtable"
DATA_DIR = Path("/content/drive/MyDrive/proxy_voting_2025")
RAW_DIR  = DATA_DIR / "raw_xml"
DB_PATH  = DATA_DIR / "proxy_2025.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Direct CIK lookup (2025 mandatory structured XML year) ──────────────────
TO_LOAD = [
    ("StateStreet", "1107414", "State Street Institutional Investment Trust"),
    ("Vanguard",    "36405",   "Vanguard Index Funds"),
    ("BlackRock",   "927971",  "iShares Inc"),
]

def get_2025_npx_accession(cik):
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json",
                     headers=HEADERS, timeout=30)
    if r.status_code != 200: return None, None
    filings = r.json().get("filings", {}).get("recent", {})
    for form, acc, date in zip(filings.get("form",[]),
                               filings.get("accessionNumber",[]),
                               filings.get("filingDate",[])):
        if form == "N-PX" and date >= "2025-07-01":
            return acc.replace("-",""), date
    return None, None

def find_pvt_file(cik, accession):
    r = requests.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json",
                     headers=HEADERS, timeout=30)
    if r.status_code != 200: return None, 0
    for item in r.json().get("directory",{}).get("item",[]):
        name = item.get("name","")
        size = int(item.get("size") or 0)
        if name.lower().endswith(".xml") and "proxy" in name.lower() and size > 10000:
            return name, size
    return None, 0

def download(cik, accession, xml_name, out_path):
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{xml_name}"
    r = requests.get(url, headers=HEADERS, timeout=120, stream=True)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(65536): f.write(chunk)
    print(f"  Downloaded: {out_path.name} ({out_path.stat().st_size/1024/1024:.1f} MB)")

def parse(path, institution, fund_name, filer_id, conn):
    def g(el, tag):
        child = el.find(f"{{{NS}}}{tag}")
        return child.text.strip() if child is not None and child.text else ""
    count, buf = 0, []
    for event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != f"{{{NS}}}proxyTable": continue
        issuer   = g(elem,"issuerName"); cusip = g(elem,"cusip"); date = g(elem,"meetingDate")
        desc     = g(elem,"voteDescription")
        cat_el   = elem.find(f".//{{{NS}}}categoryType")
        category = cat_el.text.strip() if cat_el is not None and cat_el.text else "OTHER"
        for vr in elem.findall(f".//{{{NS}}}voteRecord"):
            how  = g(vr,"howVoted"); mgmt = g(vr,"managementRecommendation")
            sh   = g(vr,"sharesVoted")
            try: shares = float(sh.replace(",",""))
            except: shares = None
            buf.append((filer_id,institution,fund_name,issuer,cusip,date,category,desc,how,mgmt,shares))
            count += 1
        elem.clear()
        if len(buf) >= 500:
            conn.executemany("INSERT INTO votes VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?)", buf)
            conn.commit(); buf.clear()
    if buf:
        conn.executemany("INSERT INTO votes VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?)", buf)
        conn.commit()
    return count

# ── Database setup ──────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.executescript("""
    CREATE TABLE IF NOT EXISTS filers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        institution TEXT, fund_name TEXT, cik TEXT UNIQUE, accession TEXT
    );
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filer_id INTEGER, institution TEXT, fund_name TEXT,
        issuer_name TEXT, cusip TEXT, meeting_date TEXT,
        category_type TEXT, vote_description TEXT,
        how_voted TEXT, mgmt_recommendation TEXT, shares_voted REAL
    );
    CREATE INDEX IF NOT EXISTS idx_inst ON votes(institution);
    CREATE INDEX IF NOT EXISTS idx_cat  ON votes(category_type);
    CREATE INDEX IF NOT EXISTS idx_vote ON votes(how_voted);
""")
conn.commit()

# ── Fetch & parse each institution ─────────────────────────────────────────
for institution, cik, fund_name in TO_LOAD:
    print(f"\n{'='*55}")
    print(f"[{institution}] CIK={cik}  {fund_name}")

    accession, date = get_2025_npx_accession(cik)
    if not accession:
        print("  No 2025 N-PX found — skipping"); continue
    print(f"  Filing date: {date}  accession: {accession}")

    xml_name, size = find_pvt_file(cik, accession)
    if not xml_name:
        print("  No ProxyVotingTable.xml found — skipping"); continue
    print(f"  XML file: {xml_name}  ({size/1024/1024:.1f} MB)")

    out_path = RAW_DIR / f"{institution}_{accession}_{xml_name}"
    if not out_path.exists():
        time.sleep(0.5)
        download(cik, accession, xml_name, out_path)

    conn.execute("INSERT OR IGNORE INTO filers (institution,fund_name,cik,accession) VALUES (?,?,?,?)",
                 (institution, fund_name, cik, accession))
    conn.commit()
    filer_id = conn.execute("SELECT id FROM filers WHERE cik=?", (cik,)).fetchone()[0]

    existing = conn.execute("SELECT COUNT(*) FROM votes WHERE institution=?", (institution,)).fetchone()[0]
    if existing:
        print(f"  Already parsed: {existing:,} votes in DB — skipping parse"); continue

    n = parse(out_path, institution, fund_name, filer_id, conn)
    print(f"  Stored {n:,} votes")

# ── Normalize case ──────────────────────────────────────────────────────────
conn.execute("UPDATE votes SET how_voted=UPPER(how_voted)")
conn.commit()

# ── Summary ─────────────────────────────────────────────────────────────────
print("\n=== SUMMARY ===")
for row in conn.execute("SELECT institution, COUNT(*) FROM votes GROUP BY institution"):
    print(f"  {row[0]}: {row[1]:,} votes")
total = conn.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
print(f"  TOTAL: {total:,} votes")
print(f"\nDB saved to: {DB_PATH}")
