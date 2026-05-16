
import json
import time
import requests
from pathlib import Path

BASE = "https://ll.thespacedevs.com/2.3.0/launches/"

SEARCH_TERMS =  [

    # NATIONAL / STATE
    "China",
    "CNSA",
    "CASC",
    "CAST",
    "SAST",
    "CALT",

    # LONG MARCH FAMILY
    "Long March",
    "CZ-",
    "CZ-1",
    "CZ-2",
    "CZ-2C",
    "CZ-2D",
    "CZ-2F",
    "CZ-3",
    "CZ-3A",
    "CZ-3B",
    "CZ-3C",
    "CZ-4",
    "CZ-4B",
    "CZ-4C",
    "CZ-5",
    "CZ-5B",
    "CZ-6",
    "CZ-6A",
    "CZ-7",
    "CZ-7A",
    "CZ-8",
    "CZ-11",

    # HUMAN SPACEFLIGHT
    "Shenzhou",
    "Tianzhou",
    "Tiangong",

    # LUNAR / PLANETARY
    "Chang'e",
    "Tianwen",

    # EARLY / HISTORIC
    "Dong Fang Hong",
    "Fengyun",
    "Yaogan",
    "Beidou",

    # COMMERCIAL / MODERN
    "ExPace",
    "Kuaizhou",
    "i-Space",
    "Hyperbola",
    "LandSpace",
    "ZhuQue",
    "Galactic Energy",
    "Ceres-1",
    "CAS Space",
    "Space Pioneer",
    "Tianlong",

    # SEA LAUNCH / SPECIAL
    "Smart Dragon",
    "Jielong",

    # MILITARY / STRATEGIC
    "Yuanwang",

    # HEAVY PROGRAMS
    "Heavy Lift",

    # NATIONAL / AGENCIES
    "USA",
    "NASA",
    "USAF",
    "USSF",
    "NRO",

    # EARLY AMERICAN PROGRAMS
    "Mercury",
    "Gemini",
    "Apollo",
    "Skylab",
    "Apollo-Soyuz",

    # SHUTTLE PROGRAM
    "Shuttle",
    "STS-",
    "Space Shuttle",
    "Columbia",
    "Challenger",
    "Discovery",
    "Atlantis",
    "Endeavour",

    # ARTEMIS / MODERN HUMAN SPACEFLIGHT
    "Artemis",
    "Orion",
    "Crew Dragon",
    "Crew-1",
    "Crew-2",
    "Crew-3",
    "Crew-4",
    "Crew-5",
    "Crew-6",
    "Crew-7",
    "Demo-2",

    # SPACE STATION
    "ISS",
    "Skylab",

    # MARS
    "Viking",
    "Pathfinder",
    "Spirit",
    "Opportunity",
    "Phoenix",
    "Curiosity",
    "Perseverance",
    "Ingenuity",

    # DEEP SPACE / SCIENCE
    "Voyager",
    "Pioneer",
    "Galileo",
    "Cassini",
    "Juno",
    "New Horizons",
    "Hubble",
    "JWST",
    "James Webb",
    "Kepler",
    "TESS",
    "Chandra",
    "Spitzer",

    # SATURN FAMILY
    "Saturn I",
    "Saturn IB",
    "Saturn V",

    # ATLAS FAMILY
    "Atlas",
    "Atlas Agena",
    "Atlas Centaur",
    "Atlas II",
    "Atlas III",
    "Atlas V",

    # DELTA FAMILY
    "Delta",
    "Delta II",
    "Delta III",
    "Delta IV",
    "Delta IV Heavy",

    # TITAN FAMILY
    "Titan",
    "Titan II",
    "Titan III",
    "Titan IV",

    # OTHER HISTORIC ROCKETS
    "Thor",
    "Thor-Delta",
    "Redstone",
    "Little Joe",
    "Scout",
    "Pegasus",
    "Minotaur",

    # MODERN COMMERCIAL
    "Falcon 1",
    "Falcon 9",
    "Falcon Heavy",
    "Starship",
    "Dragon",
    "Starlink",

    # ULA / BOEING / LOCKHEED
    "ULA",

    # NORTHROP
    "Antares",

    # NASA HEAVY
    "SLS",

    # BLUE ORIGIN
    "New Shepard",
    "New Glenn",

    # VIRGIN ORBIT
    "LauncherOne",

    # RELATIVITY
    "Terran",

    # FIREFLY
    "Alpha",

    # MILITARY / STRATEGIC
    "DSP",
    "KH-",
    "Lacrosse",
    "Milstar",
    "Defense Support Program",

    # SPECIAL / HISTORIC
    "Apollo 11",
    "Apollo 13",
    "Challenger STS-51-L",
    "Columbia STS-107",
]

LIMIT = 100
MAX_REQUESTS_PER_RUN = 15
SLEEP_BETWEEN_REQUESTS = 180
RATE_LIMIT_SLEEP = 3600

ROOT = Path("historical_fetch")

RAW_DIR = ROOT / "raw_pages"
MERGED_DIR = ROOT / "merged"
STATE_DIR = ROOT / "state"

RAW_DIR.mkdir(parents=True, exist_ok=True)
MERGED_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "progress.json"

if STATE_FILE.exists():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
else:
    state = {
        "keyword_index": 0,
        "next_url": None,
        "page_number": 1,
        "completed_keywords": [],
    }

all_launches = []
seen_ids = set()

MERGED_FILE = MERGED_DIR / "all_launches.json"

if MERGED_FILE.exists():
    with open(MERGED_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)

    for launch in existing:
        lid = launch.get("id")
        if lid:
            seen_ids.add(lid)

    all_launches.extend(existing)

request_count = 0

for idx in range(state["keyword_index"], len(SEARCH_TERMS)):

    keyword = SEARCH_TERMS[idx]

    print("=" * 60)
    print(f"KEYWORD: {keyword}")
    print("=" * 60)

    url = state["next_url"] or BASE

    params = {
        "search": keyword,
        "ordering": "-net",
        "mode": "detailed",
        "limit": LIMIT,
    }

    page_number = state.get("page_number", 1)

    while url:

        if request_count >= MAX_REQUESTS_PER_RUN:

            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            with open(MERGED_FILE, "w", encoding="utf-8") as f:
                json.dump(all_launches, f, ensure_ascii=False, indent=2)

            raise SystemExit

        try:

            response = requests.get(
                url,
                params=params if page_number == 1 else None,
                timeout=60,
            )

            if response.status_code == 429:
                print("429 detected. Sleeping 1 hour...")
                time.sleep(RATE_LIMIT_SLEEP)
                continue

            response.raise_for_status()

            data = response.json()

        except requests.exceptions.RequestException as e:

            print("REQUEST ERROR:", e)

            state["keyword_index"] = idx
            state["next_url"] = url
            state["page_number"] = page_number

            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            with open(MERGED_FILE, "w", encoding="utf-8") as f:
                json.dump(all_launches, f, ensure_ascii=False, indent=2)

            raise SystemExit

        safe_keyword = keyword.replace(" ", "_").replace("/", "_")

        raw_file = RAW_DIR / f"{safe_keyword}_page_{page_number}.json"

        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        results = data.get("results", [])

        for launch in results:

            lid = launch.get("id")

            if not lid:
                continue

            if lid in seen_ids:
                continue

            seen_ids.add(lid)
            all_launches.append(launch)

        with open(MERGED_FILE, "w", encoding="utf-8") as f:
            json.dump(all_launches, f, ensure_ascii=False, indent=2)

        url = data.get("next")

        request_count += 1
        page_number += 1

        state["keyword_index"] = idx
        state["next_url"] = url
        state["page_number"] = page_number

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        if url:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    state["completed_keywords"].append(keyword)

    state["keyword_index"] = idx + 1
    state["next_url"] = None
    state["page_number"] = 1

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

all_launches.sort(
    key=lambda x: x.get("net", "")
)

FINAL_FILE = MERGED_DIR / "final_launches.json"

with open(FINAL_FILE, "w", encoding="utf-8") as f:
    json.dump(all_launches, f, ensure_ascii=False, indent=2)

print("DONE")
