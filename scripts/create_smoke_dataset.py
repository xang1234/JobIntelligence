#!/usr/bin/env python3
"""Create a tiny SQLite dataset for Docker/ONNX smoke tests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mcf.database import MCFDatabase
from src.mcf.models import (
    Address,
    Category,
    Company,
    EmploymentType,
    Job,
    JobMetadata,
    PositionLevel,
    Salary,
    SalaryType,
    Skill,
)


def _job(
    *,
    uuid: str,
    title: str,
    company: str,
    description: str,
    skills: list[str],
    salary_min: int,
    salary_max: int,
) -> Job:
    return Job(
        uuid=uuid,
        title=title,
        description=description,
        salary=Salary(
            minimum=salary_min,
            maximum=salary_max,
            type=SalaryType(salaryType="Monthly"),
        ),
        postedCompany=Company(name=company, uen=f"{uuid[:8].upper()}A", description="Smoke test company"),
        skills=[Skill(skill=skill, isKeySkill=index < 3) for index, skill in enumerate(skills)],
        categories=[Category(category="Information Technology", id=1)],
        address=Address(
            block="1",
            street="Shenton Way",
            floor="10",
            unit="01",
            postalCode="068803",
            district="Downtown Core",
            region="Central",
        ),
        employmentTypes=[EmploymentType(employmentType="Full Time")],
        positionLevels=[PositionLevel(position="Senior")],
        minimumYearsExperience=3,
        metadata=JobMetadata(
            totalNumberJobApplication=7,
            newPostingDate="2026-03-01",
            originalPostingDate="2026-03-01",
            expiryDate="2026-04-01",
            isPostedOnBehalf=False,
        ),
    )


def build_smoke_jobs() -> list[Job]:
    return [
        _job(
            uuid="smoke-job-001",
            title="Python Platform Engineer",
            company="Smoke Systems",
            description=(
                "Build backend services for platform tooling, search relevance, and developer workflows "
                "using Python, FastAPI, Docker, and PostgreSQL."
            ),
            skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
            salary_min=8500,
            salary_max=11000,
        ),
        _job(
            uuid="smoke-job-002",
            title="Machine Learning Engineer",
            company="Vector Labs",
            description=(
                "Develop semantic search and ranking systems with transformers, ONNX Runtime, FAISS, "
                "and feature pipelines."
            ),
            skills=["Python", "ONNX Runtime", "FAISS", "Transformers"],
            salary_min=9500,
            salary_max=12500,
        ),
        _job(
            uuid="smoke-job-003",
            title="Data Engineer",
            company="Signal Analytics",
            description=(
                "Design ETL pipelines, analytics models, and batch processing systems with SQL, Spark, "
                "and cloud data services."
            ),
            skills=["SQL", "Spark", "ETL", "AWS"],
            salary_min=7800,
            salary_max=10200,
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a tiny SQLite dataset for smoke tests")
    parser.add_argument("--db", required=True, help="Output SQLite database path")
    args = parser.parse_args()

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = MCFDatabase(str(db_path))
    for job in build_smoke_jobs():
        db.upsert_job(job)

    print(f"Created smoke dataset at {db_path} with {len(build_smoke_jobs())} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
