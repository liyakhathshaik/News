import json
import time
import atexit
import traceback
import requests

from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────
# STARTUP
# ─────────────────────────────────────

print("=" * 60, flush=True)
print("HISTORICAL FETCHER STARTED", flush=True)
print("=" * 60, flush=True)

# ─────────────────────────────────────
# CONFIG
# ─────────────────────────────────────

BASE = "https://ll.thespacedevs.com/2.3.0/launches/"

SEARCH_TERMS = [

    # CHINA
    "China",
    "CNSA",
    "CASC",
    "CAST",
    "SAST",
    "CALT",
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
    "Shenzhou",
    "Tianzhou",
    "Tiangong",
    "Chang'e",
    "Tianwen",
    "Dong Fang Hong",
    "Fengyun",
    "Yaogan",
    "Beidou",
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
    "Smart Dragon",
    "Jielong",
    "Yuanwang",

    # USA
    "NASA",
    "Mercury",
    "Gemini",
    "Apollo",
    "Skylab",
    "Apollo-Soyuz",
    "Shuttle",
    "STS-",
    "Space Shuttle",
    "Columbia",
    "Challenger",
    "Discovery",
    "Atlantis",
    "Endeavour",
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
    "ISS",
    "Viking",
    "Pathfinder",
    "Spirit",
    "Opportunity",
    "Phoenix",
    "Curiosity",
    "Perseverance",
    "Ingenuity",
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
    "Saturn I",
    "Saturn IB",
    "Saturn V",
    "Atlas",
    "Atlas Agena",
    "Atlas Centaur",
    "Atlas II",
    "Atlas III",
    "Atlas V",
    "Delta",
    "Delta II",
    "Delta III",
    "Delta IV",
    "Delta IV Heavy",
    "Titan",
    "Titan II",
    "Titan III",
    "Titan IV",
    "Thor",
    "Thor-Delta",
    "Redstone",
    "Little Joe",
    "Scout",
    "Pegasus",
    "Minotaur",
    "Falcon 1",
    "Falcon 9",
    "Falcon Heavy",
    "Starship",
    "Dragon",
    "Starlink",
    "ULA",
    "Antares",
    "SLS",
    "New Shepard",
    "New Glenn",
    "LauncherOne",
    "Terran",
    "Alpha",
    "DSP",
    "KH-",
    "Lacrosse",
    "Milstar",
    "Defense Support Program",
    "Apollo 11",
    "Apollo 13",
    "Challenger STS-51-L",
    "Columbia STS-107",
]

print(f"TOTAL KEYWORDS: {len(SEARCH_TERMS)}", flush=True)

if not SEARCH_TERMS:
    print("NO SEARCH TERMS PROVIDED", flush=True)
    raise SystemExit

LIMIT = 100

# HARD LIMIT PER WORKFLOW RUN
MAX_REQUESTS_PER_RUN = 15

# 15 requests/hour safe spacing
SLEEP_BETWEEN_REQUESTS = 240

# If API rate limits
RATE_LIMIT_SLEEP = 3600

REQUEST_TIMEOUT = 60

# ─────────────────────────────────────
# PATHS
# ─────────────────────────────────────

ROOT = Path("historical_fetch")

RAW_DIR = ROOT / "raw_pages"
MERGED_DIR = ROOT / "merged"
STATE_DIR = ROOT / "state"
LOG_DIR = ROOT / "logs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
MERGED_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "progress.json"
MERGED_FILE = MERGED_DIR / "all_launches.json"
FINAL_FILE = MERGED_DIR / "final_launches.json"

# ─────────────────────────────────────
# LOAD STATE
# ─────────────────────────────────────

if STATE_FILE.exists():

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    print("Loaded previous state", flush=True)

else:

    state = {
        "keyword_index": 0,
        "next_url": None,
        "page_number": 1,
        "completed_keywords": [],
        "total_requests": 0,
        "started_at": datetime.utcnow().isoformat(),
    }

    print("Created new state", flush=True)

# ─────────────────────────────────────
# STORAGE
# ─────────────────────────────────────

all_launches = []
seen_ids = set()

if MERGED_FILE.exists():

    print("Loading existing launches...", flush=True)

    with open(MERGED_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)

    for launch in existing:

        lid = launch.get("id")

        if lid:
            seen_ids.add(lid)

    all_launches.extend(existing)

    print(f"Loaded existing launches: {len(all_launches)}", flush=True)

# ─────────────────────────────────────
# EMERGENCY SAVE
# ─────────────────────────────────────

def emergency_save():

    try:

        with open(MERGED_FILE, "w", encoding="utf-8") as f:
            json.dump(
                all_launches,
                f,
                ensure_ascii=False,
                indent=2,
            )

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print("Emergency save completed", flush=True)

    except Exception as e:

        print("Emergency save failed:", e, flush=True)

atexit.register(emergency_save)

# ─────────────────────────────────────
# REQUEST COUNTER
# ─────────────────────────────────────

request_count = 0

# ─────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────

try:

    for idx in range(state["keyword_index"], len(SEARCH_TERMS)):

        keyword = SEARCH_TERMS[idx]

        print("\n" + "=" * 60, flush=True)
        print(f"KEYWORD: {keyword}", flush=True)
        print("=" * 60, flush=True)

        url = state["next_url"] or BASE

        params = {
            "search": keyword,
            "ordering": "-net",
            "mode": "detailed",
            "limit": LIMIT,
        }

        page_number = state.get("page_number", 1)

        while url:

            # ─────────────────────────────────────
            # HARD REQUEST LIMIT
            # ─────────────────────────────────────

            if request_count >= MAX_REQUESTS_PER_RUN:

                print(
                    "SAFE STOP AFTER REQUEST LIMIT",
                    flush=True,
                )

                emergency_save()

                raise SystemExit

            print("\n" + "-" * 60, flush=True)
            print(f"REQUEST #{request_count + 1}", flush=True)
            print(f"KEYWORD: {keyword}", flush=True)
            print(f"PAGE: {page_number}", flush=True)
            print(f"URL: {url}", flush=True)

            try:

                response = requests.get(
                    url,
                    params=params if page_number == 1 else None,
                    timeout=REQUEST_TIMEOUT,
                )

                # ─────────────────────────────────────
                # RATE LIMIT
                # ─────────────────────────────────────

                if response.status_code == 429:

                    print(
                        "429 RATE LIMIT DETECTED",
                        flush=True,
                    )

                    print(
                        "Sleeping 1 hour...",
                        flush=True,
                    )

                    emergency_save()

                    time.sleep(RATE_LIMIT_SLEEP)

                    continue

                response.raise_for_status()

                try:

                    data = response.json()

                except json.JSONDecodeError as e:

                    print(
                        "JSON ERROR:",
                        e,
                        flush=True,
                    )

                    emergency_save()

                    time.sleep(300)

                    continue

            except requests.exceptions.RequestException as e:

                print(
                    "REQUEST ERROR:",
                    e,
                    flush=True,
                )

                state["keyword_index"] = idx
                state["next_url"] = url
                state["page_number"] = page_number

                emergency_save()

                raise SystemExit

            # ─────────────────────────────────────
            # SAVE RAW PAGE
            # ─────────────────────────────────────

            safe_keyword = (
                keyword
                .replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_")
                .replace(":", "_")
            )

            raw_file = RAW_DIR / (
                f"{safe_keyword}_page_{page_number}.json"
            )

            with open(raw_file, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(
                f"Saved raw page: {raw_file.name}",
                flush=True,
            )

            # ─────────────────────────────────────
            # PROCESS RESULTS
            # ─────────────────────────────────────

            results = data.get("results", [])

            added_this_page = 0

            for launch in results:

                lid = launch.get("id")

                if not lid:
                    continue

                if lid in seen_ids:
                    continue

                seen_ids.add(lid)

                all_launches.append(launch)

                added_this_page += 1

            print(
                f"Results in page: {len(results)}",
                flush=True,
            )

            print(
                f"New launches added: {added_this_page}",
                flush=True,
            )

            print(
                f"Total unique launches: {len(all_launches)}",
                flush=True,
            )

            # ─────────────────────────────────────
            # SAVE MERGED FILE
            # ─────────────────────────────────────

            with open(MERGED_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    all_launches,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            # ─────────────────────────────────────
            # NEXT PAGE
            # ─────────────────────────────────────

            url = data.get("next")

            request_count += 1

            state["total_requests"] += 1

            page_number += 1

            # ─────────────────────────────────────
            # SAVE STATE
            # ─────────────────────────────────────

            state["keyword_index"] = idx
            state["next_url"] = url
            state["page_number"] = page_number

            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    state,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            # ─────────────────────────────────────
            # RATE LIMIT SPACING
            # ─────────────────────────────────────

            if url:

                print(
                    f"Sleeping {SLEEP_BETWEEN_REQUESTS} sec...",
                    flush=True,
                )

                time.sleep(SLEEP_BETWEEN_REQUESTS)

        # ─────────────────────────────────────
        # KEYWORD COMPLETE
        # ─────────────────────────────────────

        state["completed_keywords"].append(keyword)

        state["keyword_index"] = idx + 1
        state["next_url"] = None
        state["page_number"] = 1

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(
            f"Completed keyword: {keyword}",
            flush=True,
        )

    # ─────────────────────────────────────
    # FINAL SORT
    # ─────────────────────────────────────

    all_launches.sort(
        key=lambda x: x.get("net", "")
    )

    with open(FINAL_FILE, "w", encoding="utf-8") as f:
        json.dump(
            all_launches,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n" + "=" * 60, flush=True)
    print("FETCH COMPLETE", flush=True)
    print("=" * 60, flush=True)

    print(
        f"Final launches: {len(all_launches)}",
        flush=True,
    )

    print(
        f"Total requests overall: {state['total_requests']}",
        flush=True,
    )

except Exception as e:

    print("\nFATAL ERROR", flush=True)
    print(str(e), flush=True)

    traceback.print_exc()

    emergency_save()

    raise
