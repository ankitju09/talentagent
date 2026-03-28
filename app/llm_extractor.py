import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.schemas import CandidateProfile

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing in .env")


SYSTEM_PROMPT = """
You are a resume information extractor.

Extract information from the resume and return structured data
matching the CandidateProfile schema.

Rules:
- Use exact field names from the schema
- For missing scalar fields → return null
- For missing list fields → return []
- Do NOT add extra fields
- Do NOT hallucinate information
- Return ONLY valid JSON
"""


def build_resume_extractor():
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    structured_llm = llm.with_structured_output(CandidateProfile)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "Extract CandidateProfile from this resume:\n\n{resume_text}")
        ]
    )

    return prompt | structured_llm


def extract_candidate_profile(resume_text: str) -> CandidateProfile:
    if not resume_text or not resume_text.strip():
        raise ValueError("resume_text is empty")

    chain = build_resume_extractor()
    result = chain.invoke({"resume_text": resume_text})

    if not isinstance(result, CandidateProfile):
        raise ValueError("Extraction failed")

    return result