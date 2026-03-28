from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlparse

from ddgs import DDGS

from app.job_query_builder import build_job_search_queries
from app.schemas import CandidateProfile, JobPost


COMPANY_PATTERNS = [
    r"\bat\s+([A-Z][A-Za-z0-9&.\- ]+)",
    r"\bjoin\s+([A-Z][A-Za-z0-9&.\- ]+)",
]


LOCATION_HINTS = [
    "Dubai",
    "Abu Dhabi",
    "UAE",
    "United Arab Emirates",
    "Germany",
    "India",
    "Remote",
]


def _infer_source(url: str) -> str:
    hostname = urlparse(url).netloc.lower()
    if "linkedin.com" in hostname:
        return "linkedin"
    return hostname or "web"


def _extract_company(title: str, snippet: str) -> Optional[str]:
    text = f"{title} {snippet}".strip()

    for sep in [" - ", " | ", " @ ", " at "]:
        if sep in title:
            parts = [p.strip() for p in title.split(sep) if p.strip()]
            if len(parts) >= 2:
                return parts[-1]

    for pattern in COMPANY_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return None


def _extract_location(
    snippet: str,
    preferred_city: str | None,
    preferred_country: str | None,
) -> Optional[str]:
    if preferred_city and preferred_city.lower() in snippet.lower():
        if preferred_country:
            return f"{preferred_city}, {preferred_country}"
        return preferred_city

    if preferred_country and preferred_country.lower() in snippet.lower():
        return preferred_country

    for hint in LOCATION_HINTS:
        if hint.lower() in snippet.lower():
            return hint

    return None


def _looks_like_job_result(title: str, snippet: str, url: str) -> bool:
    blob = f"{title} {snippet} {url}".lower()
    job_terms = ["job", "jobs", "career", "careers", "hiring", "opening", "position", "apply"]
    role_terms = ["engineer", "developer", "architect", "scientist", "manager", "analyst"]
    return any(t in blob for t in job_terms) or any(t in blob for t in role_terms)


def search_public_jobs(
    candidate_profile: CandidateProfile,
    country: str | None = None,
    city: str | None = None,
    field: str | None = None,
    limit: int = 10,
) -> tuple[list[str], list[JobPost]]:
    queries = build_job_search_queries(
        profile=candidate_profile,
        country=country,
        city=city,
        field=field,
    )

    jobs: List[JobPost] = []
    seen_urls = set()

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=limit)
            except Exception:
                continue

            for item in results:
                url = item.get("href") or item.get("url")
                title = item.get("title")
                snippet = item.get("body") or item.get("snippet") or ""

                if not url or not title:
                    continue

                if url in seen_urls:
                    continue

                if not _looks_like_job_result(title, snippet, url):
                    continue

                seen_urls.add(url)

                jobs.append(
                    JobPost(
                        source=_infer_source(url),
                        title=title.strip(),
                        company=_extract_company(title, snippet),
                        location=_extract_location(snippet, city, country),
                        job_url=url,
                        description=snippet.strip() or None,
                        posted_date=None,
                        search_query=query,
                    )
                )

                if len(jobs) >= limit:
                    return queries, jobs

    return queries, jobs