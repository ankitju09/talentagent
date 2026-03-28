from typing import List

from app.schemas import CandidateProfile


def _pick_role_terms(profile: CandidateProfile, field: str | None) -> List[str]:
    terms: List[str] = []

    if field and field.strip():
        terms.append(field.strip())

    if profile.preferred_job_titles:
        terms.extend(profile.preferred_job_titles[:3])

    if profile.current_title:
        terms.append(profile.current_title)

    if not terms and profile.roles:
        terms.extend(profile.roles[:3])

    if not terms:
        terms.append("Software Engineer")

    seen = set()
    result = []
    for term in terms:
        key = term.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(term.strip())

    return result[:3]


def _pick_skill_terms(profile: CandidateProfile) -> List[str]:
    terms = []
    terms.extend(profile.skills[:3])
    terms.extend(profile.tools[:2])

    seen = set()
    result = []
    for term in terms:
        key = term.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(term.strip())

    return result[:4]


def build_job_search_queries(
    profile: CandidateProfile,
    country: str | None = None,
    city: str | None = None,
    field: str | None = None,
) -> List[str]:
    role_terms = _pick_role_terms(profile, field)
    skill_terms = _pick_skill_terms(profile)

    location_parts = []
    if city:
        location_parts.append(city.strip())
    if country:
        location_parts.append(country.strip())

    location_text = ", ".join([p for p in location_parts if p])

    queries: List[str] = []
    for role in role_terms:
        base = f"{role} jobs"
        if location_text:
            base += f" in {location_text}"

        queries.append(f"site:linkedin.com/jobs/view {base}")
        queries.append(f"{base} careers")
        queries.append(f"{base} job opening")

        if skill_terms:
            skill_text = " ".join(skill_terms[:2])
            queries.append(f"{base} {skill_text}")

    seen = set()
    final_queries = []
    for q in queries:
        key = q.lower().strip()
        if key not in seen:
            seen.add(key)
            final_queries.append(q)

    return final_queries[:6]