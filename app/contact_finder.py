import re
from typing import Optional
from urllib.parse import urlparse

from ddgs import DDGS

from app.schemas import CompanyContact


EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_REGEX = r"(\+?\d[\d\-\s()]{7,}\d)"

CAREERS_KEYWORDS = ["career", "careers", "jobs", "join-us", "work-with-us"]
CONTACT_KEYWORDS = ["contact", "contact-us", "get-in-touch", "support"]

RECRUITER_TITLE_KEYWORDS = [
    "recruiter",
    "talent acquisition",
    "hr",
    "human resources",
    "hiring",
    "staffing",
    "talent partner",
]


def _extract_email(text: str) -> Optional[str]:
    if not text:
        return None

    matches = re.findall(EMAIL_REGEX, text)
    if not matches:
        return None

    blocked_parts = ["noreply", "no-reply", "donotreply"]
    for email in matches:
        email_lower = email.lower()
        if not any(part in email_lower for part in blocked_parts):
            return email

    return matches[0]


def _extract_phone(text: str) -> Optional[str]:
    if not text:
        return None

    matches = re.findall(PHONE_REGEX, text)
    if not matches:
        return None

    for match in matches:
        cleaned = re.sub(r"\s+", " ", match).strip()
        if len(re.sub(r"\D", "", cleaned)) >= 8:
            return cleaned

    return None


def _is_careers_url(url: str) -> bool:
    url_lower = url.lower()
    return any(keyword in url_lower for keyword in CAREERS_KEYWORDS)


def _is_contact_url(url: str) -> bool:
    url_lower = url.lower()
    return any(keyword in url_lower for keyword in CONTACT_KEYWORDS)


def _is_public_profile_url(url: str) -> bool:
    url_lower = url.lower()
    return "linkedin.com/in/" in url_lower or "linkedin.com/pub/" in url_lower


def _is_same_company_result(company: str, title: str, snippet: str, url: str) -> bool:
    blob = f"{title} {snippet} {url}".lower()
    company_tokens = [token for token in company.lower().split() if len(token) > 2]

    if not company_tokens:
        return True

    matched = sum(1 for token in company_tokens if token in blob)
    return matched >= 1


def _extract_recruiter_name(title: str) -> Optional[str]:
    """
    Very simple heuristic:
    'John Smith - Recruiter - Company | LinkedIn'
    -> John Smith
    """
    if not title:
        return None

    separators = [" - ", " | ", " – "]
    parts = [title]
    for sep in separators:
        if sep in title:
            parts = [p.strip() for p in title.split(sep) if p.strip()]
            break

    if not parts:
        return None

    first = parts[0].strip()
    if len(first.split()) <= 5:
        return first

    return None


def _extract_recruiter_title(title: str, snippet: str) -> Optional[str]:
    text = f"{title} {snippet}".lower()

    for keyword in RECRUITER_TITLE_KEYWORDS:
        if keyword in text:
            return keyword.title()

    return None


def find_company_contact(company: str) -> CompanyContact:
    if not company or not company.strip():
        raise ValueError("company is required")

    company = company.strip()

    company_queries = [
        f"{company} careers",
        f"{company} contact",
        f"{company} hr email",
        f"{company} hr phone",
    ]

    recruiter_queries = [
        f'site:linkedin.com/in "{company}" recruiter',
        f'site:linkedin.com/in "{company}" "talent acquisition"',
        f'site:linkedin.com/in "{company}" HR',
    ]

    careers_page = None
    contact_page = None
    hr_email = None
    hr_phone = None
    recruiter_name = None
    recruiter_title = None
    recruiter_profile_url = None

    source_urls: list[str] = []
    seen_urls = set()

    with DDGS() as ddgs:
        # Step 1: company pages first
        for query in company_queries:
            try:
                results = ddgs.text(query, max_results=5)
            except Exception:
                continue

            for item in results:
                url = item.get("href") or item.get("url")
                title = item.get("title") or ""
                snippet = item.get("body") or item.get("snippet") or ""

                if not url:
                    continue

                if url in seen_urls:
                    continue

                if not _is_same_company_result(company, title, snippet, url):
                    continue

                seen_urls.add(url)
                source_urls.append(url)

                if careers_page is None and _is_careers_url(url):
                    careers_page = url

                if contact_page is None and _is_contact_url(url):
                    contact_page = url

                if hr_email is None:
                    found_email = _extract_email(f"{title}\n{snippet}\n{url}")
                    if found_email:
                        hr_email = found_email

                if hr_phone is None:
                    found_phone = _extract_phone(f"{title}\n{snippet}")
                    if found_phone:
                        hr_phone = found_phone

        # Step 2: recruiter / HR public profile search
        for query in recruiter_queries:
            if recruiter_profile_url is not None:
                break

            try:
                results = ddgs.text(query, max_results=5)
            except Exception:
                continue

            for item in results:
                url = item.get("href") or item.get("url")
                title = item.get("title") or ""
                snippet = item.get("body") or item.get("snippet") or ""

                if not url:
                    continue

                if url in seen_urls:
                    continue

                if not _is_public_profile_url(url):
                    continue

                if not _is_same_company_result(company, title, snippet, url):
                    continue

                extracted_title = _extract_recruiter_title(title, snippet)
                if extracted_title is None:
                    continue

                seen_urls.add(url)
                source_urls.append(url)

                recruiter_profile_url = url
                recruiter_name = _extract_recruiter_name(title)
                recruiter_title = extracted_title

                if hr_email is None:
                    hr_email = _extract_email(f"{title}\n{snippet}")

                if hr_phone is None:
                    hr_phone = _extract_phone(f"{title}\n{snippet}")

                break

    return CompanyContact(
        company=company,
        careers_page=careers_page,
        contact_page=contact_page,
        hr_email=hr_email,
        hr_phone=hr_phone,
        recruiter_name=recruiter_name,
        recruiter_title=recruiter_title,
        recruiter_profile_url=recruiter_profile_url,
        source_urls=source_urls[:10],
    )