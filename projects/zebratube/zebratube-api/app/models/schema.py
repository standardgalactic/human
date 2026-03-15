"""
schema.py — SQLAlchemy ORM models for ZebraTube

Tables:
    users
    projects
    project_versions
    tasks
    task_dependencies
    claims
    submissions
    submission_reviews
    assemblies
    assembly_segments
    point_ledger

Design principles:
    - Every point event is immutable (ledger not balance)
    - Tasks reference versioned script artifacts, not mutable rows
    - Reviews are records, not overwrites
    - Branches are preserved; convergence is assembler-driven
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ── Enumerations ──────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    observer    = "observer"
    contributor = "contributor"
    producer    = "producer"
    assembler   = "assembler"
    admin       = "admin"


class ProjectType(str, enum.Enum):
    research    = "research"
    essay       = "essay"
    software    = "software"
    personal    = "personal"
    fiction     = "fiction"
    mixed       = "mixed"


class TaskDifficulty(str, enum.Enum):
    simple   = "simple"
    standard = "standard"
    complex  = "complex"


class TaskStatus(str, enum.Enum):
    open       = "open"
    claimed    = "claimed"
    submitted  = "submitted"
    in_review  = "in_review"
    accepted   = "accepted"
    saturated  = "saturated"   # enough alternatives exist


class ClaimStatus(str, enum.Enum):
    active   = "active"
    expired  = "expired"
    withdrawn= "withdrawn"
    fulfilled= "fulfilled"


class SubmissionStatus(str, enum.Enum):
    pending   = "pending"
    in_review = "in_review"
    accepted  = "accepted"
    rejected  = "rejected"
    branch    = "branch"    # preserved as alternative


class ReviewVerdict(str, enum.Enum):
    approve         = "approve"
    reject          = "reject"
    request_revision= "request_revision"
    preserve_branch = "preserve_branch"


class PointEventType(str, enum.Enum):
    submission_accepted  = "submission_accepted"
    submission_reviewed  = "submission_reviewed"
    selector_comparison  = "selector_comparison"
    assembly_accepted    = "assembly_accepted"
    first_submission_bonus = "first_submission_bonus"
    admin_adjustment     = "admin_adjustment"


class OutputFormat(str, enum.Enum):
    video            = "video"
    audio            = "audio"
    animation        = "animation"
    diagram_animation= "diagram_animation"
    diagram          = "diagram"
    screencast       = "screencast"
    voiceover        = "voiceover"


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(UUID, primary_key=True, default=new_uuid)
    username      = Column(String(80), unique=True, nullable=False, index=True)
    email         = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), nullable=False, default=UserRole.observer)
    point_balance = Column(Integer, nullable=False, default=0)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, onupdate=func.now())

    # Optional: public person graph artifact path
    person_graph_path = Column(String(512), nullable=True)
    person_graph_public = Column(Boolean, default=False)

    claims      = relationship("Claim",        back_populates="user")
    submissions = relationship("Submission",   back_populates="user")
    reviews     = relationship("SubmissionReview", back_populates="reviewer")
    ledger      = relationship("PointLedger",  back_populates="user")


# ── Projects ──────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id           = Column(UUID, primary_key=True, default=new_uuid)
    slug         = Column(String(120), unique=True, nullable=False, index=True)
    title        = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    project_type = Column(Enum(ProjectType), nullable=False, default=ProjectType.mixed)
    source_url   = Column(String(512), nullable=True)   # original repo/text URL
    is_public    = Column(Boolean, default=True)
    created_at   = Column(DateTime, server_default=func.now())
    owner_id     = Column(UUID, ForeignKey("users.id"), nullable=True)

    versions    = relationship("ProjectVersion", back_populates="project",
                               order_by="ProjectVersion.created_at")


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id              = Column(UUID, primary_key=True, default=new_uuid)
    project_id      = Column(UUID, ForeignKey("projects.id"), nullable=False, index=True)
    version_number  = Column(Integer, nullable=False, default=1)
    crawl_timestamp = Column(DateTime, nullable=False)
    source_commit   = Column(String(64), nullable=True)   # git hash if available
    source_snapshot = Column(String(512), nullable=True)  # path to source archive

    # Artifact paths (relative to artifact root)
    graph_path        = Column(String(512), nullable=True)
    projections_dir   = Column(String(512), nullable=True)
    wiki_dir          = Column(String(512), nullable=True)
    scripts_dir       = Column(String(512), nullable=True)
    corpus_stats      = Column(JSONB, nullable=True)      # entity/event/claim counts

    # Extraction metadata for auditability
    extraction_prompt_hash = Column(String(64), nullable=True)
    model_name             = Column(String(64), nullable=True)
    model_version          = Column(String(64), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    is_active  = Column(Boolean, default=True)

    project  = relationship("Project",     back_populates="versions")
    tasks    = relationship("Task",        back_populates="project_version")
    assemblies = relationship("Assembly",  back_populates="project_version")

    __table_args__ = (
        UniqueConstraint("project_id", "version_number"),
    )


# ── Tasks ─────────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id                 = Column(String(128), primary_key=True)  # stable content-addressed id
    project_version_id = Column(UUID, ForeignKey("project_versions.id"), nullable=False, index=True)

    projection_type    = Column(String(60), nullable=False)
    label              = Column(String(255), nullable=False)
    difficulty         = Column(Enum(TaskDifficulty), nullable=False, default=TaskDifficulty.standard)
    output_format      = Column(Enum(OutputFormat), nullable=False, default=OutputFormat.video)
    duration_estimate_s= Column(Integer, nullable=True)
    assembly_weight    = Column(Float, nullable=False, default=1.0)

    script_path        = Column(String(512), nullable=True)   # path to script artifact dir
    bundle_path        = Column(String(512), nullable=True)   # path to .zip bundle
    graph_nodes        = Column(JSONB, nullable=True)         # list of node ids
    style_hint         = Column(Text, nullable=True)
    output_spec        = Column(JSONB, nullable=True)

    status             = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.open)
    submission_count   = Column(Integer, nullable=False, default=0)
    accepted_count     = Column(Integer, nullable=False, default=0)

    # Computed bounty components (recalculated live, cached here)
    base_value         = Column(Integer, nullable=False, default=100)
    scarcity           = Column(Float, nullable=False, default=1.0)
    current_bounty     = Column(Float, nullable=False, default=100.0)

    created_at         = Column(DateTime, server_default=func.now())
    updated_at         = Column(DateTime, onupdate=func.now())

    project_version = relationship("ProjectVersion",  back_populates="tasks")
    claims          = relationship("Claim",           back_populates="task")
    submissions     = relationship("Submission",      back_populates="task")
    outgoing_deps   = relationship("TaskDependency",  foreign_keys="TaskDependency.from_task_id",
                                   back_populates="from_task")
    incoming_deps   = relationship("TaskDependency",  foreign_keys="TaskDependency.to_task_id",
                                   back_populates="to_task")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id           = Column(UUID, primary_key=True, default=new_uuid)
    from_task_id = Column(String(128), ForeignKey("tasks.id"), nullable=False)
    to_task_id   = Column(String(128), ForeignKey("tasks.id"), nullable=False)
    via          = Column(String(128), nullable=True)   # shared node id or "narrative_sequence"

    from_task = relationship("Task", foreign_keys=[from_task_id], back_populates="outgoing_deps")
    to_task   = relationship("Task", foreign_keys=[to_task_id],   back_populates="incoming_deps")

    __table_args__ = (UniqueConstraint("from_task_id", "to_task_id"),)


# ── Claims ────────────────────────────────────────────────────────────────────

class Claim(Base):
    __tablename__ = "claims"

    id         = Column(UUID, primary_key=True, default=new_uuid)
    user_id    = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    task_id    = Column(String(128), ForeignKey("tasks.id"), nullable=False, index=True)
    status     = Column(Enum(ClaimStatus), nullable=False, default=ClaimStatus.active)
    claimed_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)     # claimed_at + 72h default
    withdrawn_at = Column(DateTime, nullable=True)

    user        = relationship("User",        back_populates="claims")
    task        = relationship("Task",        back_populates="claims")
    submissions = relationship("Submission",  back_populates="claim")


# ── Submissions ───────────────────────────────────────────────────────────────

class Submission(Base):
    __tablename__ = "submissions"

    id            = Column(UUID, primary_key=True, default=new_uuid)
    claim_id      = Column(UUID, ForeignKey("claims.id"), nullable=False)
    task_id       = Column(String(128), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id       = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)

    status        = Column(Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.pending)
    branch_label  = Column(String(120), nullable=True)   # user-supplied branch name

    # Media artifact
    original_path = Column(String(512), nullable=True)
    preview_path  = Column(String(512), nullable=True)   # transcoded preview
    thumbnail_path= Column(String(512), nullable=True)
    media_metadata= Column(JSONB, nullable=True)         # duration, codec, dims, waveform
    file_hash     = Column(String(64), nullable=True)    # sha256 of original

    notes         = Column(Text, nullable=True)
    submitted_at  = Column(DateTime, server_default=func.now())
    reviewed_at   = Column(DateTime, nullable=True)

    claim   = relationship("Claim",       back_populates="submissions")
    task    = relationship("Task",        back_populates="submissions")
    user    = relationship("User",        back_populates="submissions")
    reviews = relationship("SubmissionReview", back_populates="submission")


# ── Reviews ───────────────────────────────────────────────────────────────────

class SubmissionReview(Base):
    __tablename__ = "submission_reviews"

    id            = Column(UUID, primary_key=True, default=new_uuid)
    submission_id = Column(UUID, ForeignKey("submissions.id"), nullable=False, index=True)
    reviewer_id   = Column(UUID, ForeignKey("users.id"), nullable=False)
    verdict       = Column(Enum(ReviewVerdict), nullable=False)
    notes         = Column(Text, nullable=True)
    reviewed_at   = Column(DateTime, server_default=func.now())

    submission = relationship("Submission",     back_populates="reviews")
    reviewer   = relationship("User",           back_populates="reviews")


# ── Assemblies ────────────────────────────────────────────────────────────────

class Assembly(Base):
    __tablename__ = "assemblies"

    id                 = Column(UUID, primary_key=True, default=new_uuid)
    project_version_id = Column(UUID, ForeignKey("project_versions.id"), nullable=False, index=True)
    assembler_id       = Column(UUID, ForeignKey("users.id"), nullable=True)
    title              = Column(String(255), nullable=True)
    description        = Column(Text, nullable=True)

    spec_path          = Column(String(512), nullable=True)   # assembly spec JSON
    output_path        = Column(String(512), nullable=True)   # rendered preview video
    status             = Column(String(40), nullable=False, default="draft")
    created_at         = Column(DateTime, server_default=func.now())
    updated_at         = Column(DateTime, onupdate=func.now())

    project_version = relationship("ProjectVersion", back_populates="assemblies")
    segments        = relationship("AssemblySegment", back_populates="assembly",
                                   order_by="AssemblySegment.position")


class AssemblySegment(Base):
    __tablename__ = "assembly_segments"

    id             = Column(UUID, primary_key=True, default=new_uuid)
    assembly_id    = Column(UUID, ForeignKey("assemblies.id"), nullable=False, index=True)
    task_id        = Column(String(128), ForeignKey("tasks.id"), nullable=False)
    submission_id  = Column(UUID, ForeignKey("submissions.id"), nullable=True)  # null = gap
    position       = Column(Integer, nullable=False)
    is_canonical   = Column(Boolean, default=True)
    branch_label   = Column(String(120), nullable=True)
    notes          = Column(Text, nullable=True)

    assembly    = relationship("Assembly",    back_populates="segments")
    submission  = relationship("Submission")


# ── Point Ledger ──────────────────────────────────────────────────────────────

class PointLedger(Base):
    __tablename__ = "point_ledger"

    id           = Column(UUID, primary_key=True, default=new_uuid)
    user_id      = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    event_type   = Column(Enum(PointEventType), nullable=False)
    delta        = Column(Integer, nullable=False)   # positive or negative
    balance_after= Column(Integer, nullable=False)

    # Context references
    task_id      = Column(String(128), ForeignKey("tasks.id"), nullable=True)
    submission_id= Column(UUID, ForeignKey("submissions.id"), nullable=True)
    assembly_id  = Column(UUID, ForeignKey("assemblies.id"), nullable=True)

    description  = Column(Text, nullable=True)
    created_at   = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="ledger")
