import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.settings import get_settings

from sqlalchemy import DateTime, String, Text, func, text, event, Integer, bindparam, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector
from pgvector.psycopg import register_vector


# --- SQLAlchemy base & engine ---
Base = declarative_base()


def get_database_url() -> str:
    # Prefer settings (.env) but allow env var override
    url = os.getenv("DATABASE_URL") or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL must be set")
    # Replace 'db' with 'postgres' in the URL if needed
    url = url.replace("db:5432", "postgres:5432")
    return url


_engine = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            pool_pre_ping=True,
            future=True,
            echo=True  # Add SQL logging for debugging
        )

        # Ensure pgvector is registered with psycopg3 connections
        @event.listens_for(_engine, "connect")
        def _on_connect(dbapi_conn, _):  # type: ignore[no-redef]
            try:
                register_vector(dbapi_conn)
            except Exception:
                # Safe to ignore; if registration fails, vector operations may error later
                pass

    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
            future=True,
            class_=Session
        )
    return _SessionLocal()


# --- Models ---
class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    candidate_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)

    skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    embedding: Mapped[List[float]] = mapped_column(Vector(384), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description_cleaned: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    embedding: Mapped[List[float]] = mapped_column(Vector(384), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# --- Initialization & helpers ---

def init_db() -> None:
    """Migrations-managed schema: no runtime DDL here. Ensure Alembic has been applied."""
    # Intentionally no-op: use Alembic migrations to manage schema and extensions.
    return None


# --- CRUD helpers ---

def insert_resume(
    *,
    resume_id: str,
    candidate_name: Optional[str],
    raw_text: Optional[str],
    cleaned_text: str,
    skills: Sequence[str],
    embedding: Sequence[float],
) -> str:
    with get_session() as s:
        obj = Resume(
            id=resume_id,
            candidate_name=candidate_name,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            skills=list(skills),
            embedding=list(embedding),
        )
        s.add(obj)
        s.commit()
        return obj.id


def insert_job(
    *,
    job_id: str,
    title: str,
    description_cleaned: str,
    required_skills: Sequence[str],
    embedding: Sequence[float],
) -> str:
    with get_session() as s:
        obj = Job(
            id=job_id,
            title=title,
            description_cleaned=description_cleaned,
            required_skills=list(required_skills),
            embedding=list(embedding),
        )
        s.add(obj)
        s.commit()
        return obj.id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with get_session() as s:
        j = s.get(Job, job_id)
        if not j:
            return None
        return {
            "id": j.id,
            "title": j.title,
            "description_cleaned": j.description_cleaned,
            "required_skills": j.required_skills or [],
            "embedding": j.embedding,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
        }


# --- Vector search ---

def search_resumes_by_embedding(
    *, job_embedding: Sequence[float], k: int = 20
) -> List[Tuple[str, Optional[str], List[str], float]]:
    """
    Returns top-k resumes by cosine distance (ascending distance).
    Output: list of (resume_id, candidate_name, skills, cosine_similarity)
    Note: cosine_similarity = 1 - cosine_distance
    """
    sql = text(
        """
        SELECT id, candidate_name, skills, (embedding <=> :job_vec) AS cos_dist
        FROM resumes
        ORDER BY embedding <=> :job_vec ASC
        LIMIT :k
        """
    ).bindparams(
        bindparam("job_vec", type_=Vector(384)),
        bindparam("k", type_=Integer()),
    )
    with get_session() as s:
        rows = s.execute(sql, {"job_vec": list(job_embedding), "k": int(max(1, k))}).all()
        results: List[Tuple[str, Optional[str], List[str], float]] = []
        for rid, cname, skills, cos_dist in rows:
            cos_sim = float(1.0 - float(cos_dist)) if cos_dist is not None else 0.0
            results.append((str(rid), cname, skills or [], cos_sim))
        return results
