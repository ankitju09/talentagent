from typing import List, Optional

from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

    total_experience_years: Optional[float] = None
    current_title: Optional[str] = None
    roles: List[str] = []
    seniority_level: Optional[str] = None

    skills: List[str] = []
    tools: List[str] = []
    domains: List[str] = []
    preferred_job_titles: List[str] = []
    locations: List[str] = []

    education: List[str] = []
    projects: List[str] = []
    summary: Optional[str] = None


class ParseResumeResponse(BaseModel):
    success: bool
    source_type: str
    extracted_text: str
    candidate_profile: CandidateProfile
    message: str


class SearchJobsRequest(BaseModel):
    candidate_profile: CandidateProfile
    country: Optional[str] = None
    city: Optional[str] = None
    field: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=25)


class JobPost(BaseModel):
    source: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    search_query: Optional[str] = None


class SearchJobsResponse(BaseModel):
    success: bool
    jobs: List[JobPost]
    generated_queries: List[str]
    message: str

from typing import List, Optional
from pydantic import BaseModel

class CompanyContact(BaseModel):
    company: str
    careers_page: Optional[str] = None
    contact_page: Optional[str] = None
    hr_email: Optional[str] = None
    hr_phone: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_title: Optional[str] = None
    recruiter_profile_url: Optional[str] = None
    source_urls: List[str] = []


class ContactSearchRequest(BaseModel):
    company: str


class ContactSearchResponse(BaseModel):
    success: bool
    contact: CompanyContact
    message: str