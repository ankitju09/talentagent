from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.contact_finder import find_company_contact
from app.job_search_service import search_public_jobs
from app.llm_extractor import extract_candidate_profile
from app.resume_parser import clean_extracted_text, extract_text_from_pdf
from app.schemas import (
    CandidateProfile,
    CompanyContact,
    ContactSearchRequest,
    ContactSearchResponse,
    JobPost,
    ParseResumeResponse,
    SearchJobsRequest,
    SearchJobsResponse,
)
from pydantic import BaseModel


app = FastAPI(title="TalentAgent", version="0.4.0")


class RunAgentResponse(BaseModel):
    success: bool
    candidate_profile: CandidateProfile
    jobs: list[JobPost]
    contacts: list[CompanyContact]
    message: str


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "TalentAgent"}


@app.post("/parse-resume", response_model=ParseResumeResponse)
async def parse_resume(
    file: Optional[UploadFile] = File(default=None),
    resume_text: Optional[str] = Form(default=None),
):
    if file is None and resume_text is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'resume_text' or a PDF file."
        )

    if file is not None and resume_text is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide only one input: either 'resume_text' or a PDF file."
        )

    if resume_text is not None:
        cleaned_text = clean_extracted_text(resume_text)
        if not cleaned_text:
            raise HTTPException(
                status_code=400,
                detail="Resume text is empty after cleaning."
            )

        try:
            candidate_profile = extract_candidate_profile(cleaned_text)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract candidate profile: {str(exc)}"
            ) from exc

        return ParseResumeResponse(
            success=True,
            source_type="text",
            extracted_text=cleaned_text,
            candidate_profile=candidate_profile,
            message="Resume text parsed successfully."
        )

    extracted_text = await extract_text_from_pdf(file)

    try:
        candidate_profile = extract_candidate_profile(extracted_text)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract candidate profile: {str(exc)}"
        ) from exc

    return ParseResumeResponse(
        success=True,
        source_type="pdf",
        extracted_text=extracted_text,
        candidate_profile=candidate_profile,
        message="Resume PDF parsed successfully."
    )


@app.post("/search-jobs", response_model=SearchJobsResponse)
async def search_jobs(request: SearchJobsRequest):
    try:
        queries, jobs = search_public_jobs(
            candidate_profile=request.candidate_profile,
            country=request.country,
            city=request.city,
            field=request.field,
            limit=request.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Job search failed: {str(exc)}"
        ) from exc

    return SearchJobsResponse(
        success=True,
        jobs=jobs,
        generated_queries=queries,
        message=f"Found {len(jobs)} job posts."
    )


@app.post("/find-company-contact", response_model=ContactSearchResponse)
async def find_company_contact_endpoint(request: ContactSearchRequest):
    try:
        contact = find_company_contact(request.company)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Contact search failed: {str(exc)}"
        ) from exc

    return ContactSearchResponse(
        success=True,
        contact=contact,
        message="Company contact search completed."
    )


@app.post("/run-agent", response_model=RunAgentResponse)
async def run_agent(
    file: Optional[UploadFile] = File(default=None),
    resume_text: Optional[str] = Form(default=None),
    country: Optional[str] = Form(default=None),
    city: Optional[str] = Form(default=None),
    field: Optional[str] = Form(default=None),
    limit: int = Form(default=10),
):
    # 1) validate input
    if file is None and resume_text is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'resume_text' or a PDF file."
        )

    if file is not None and resume_text is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide only one input: either 'resume_text' or a PDF file."
        )

    if limit < 1 or limit > 25:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 25."
        )

    # 2) extract resume text
    if resume_text is not None:
        extracted_text = clean_extracted_text(resume_text)
        if not extracted_text:
            raise HTTPException(
                status_code=400,
                detail="Resume text is empty after cleaning."
            )
    else:
        extracted_text = await extract_text_from_pdf(file)

    # 3) build candidate profile
    try:
        candidate_profile = extract_candidate_profile(extracted_text)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract candidate profile: {str(exc)}"
        ) from exc

    # 4) search jobs
    try:
        _, jobs = search_public_jobs(
            candidate_profile=candidate_profile,
            country=country,
            city=city,
            field=field,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Job search failed: {str(exc)}"
        ) from exc

    # 5) find contacts for top unique companies
    contacts: list[CompanyContact] = []
    seen_companies = set()

    for job in jobs:
        if not job.company:
            continue

        company_key = job.company.strip().lower()
        if not company_key or company_key in seen_companies:
            continue

        seen_companies.add(company_key)

        try:
            contact = find_company_contact(job.company)
            contacts.append(contact)
        except Exception:
            # keep agent running even if one contact lookup fails
            continue

        if len(contacts) >= 5:
            break

    return RunAgentResponse(
        success=True,
        candidate_profile=candidate_profile,
        jobs=jobs,
        contacts=contacts,
        message="TalentAgent completed resume parsing, job search, and contact discovery."
    )