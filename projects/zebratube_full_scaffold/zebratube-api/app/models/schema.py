from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text, DateTime, Boolean

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
    points = Column(Integer, default=0)

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    title = Column(String)
    project_type = Column(String)

class ProjectVersion(Base):
    __tablename__ = "project_versions"
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"))
    version_label = Column(String)
    graph_path = Column(String)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    project_version_id = Column(String, ForeignKey("project_versions.id"))
    title = Column(String)
    projection = Column(String)
    difficulty = Column(String)
    assembly_weight = Column(Float, default=1.0)
    status = Column(String, default="open")
    submission_count = Column(Integer, default=0)

class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    depends_on_task_id = Column(String, ForeignKey("tasks.id"))

class Claim(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    user_id = Column(String, ForeignKey("users.id"))
    status = Column(String, default="active")

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    claim_id = Column(String, ForeignKey("claims.id"))
    user_id = Column(String, ForeignKey("users.id"))
    media_path = Column(String)
    status = Column(String, default="under_review")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(String, primary_key=True)
    submission_id = Column(String, ForeignKey("submissions.id"))
    reviewer_id = Column(String, ForeignKey("users.id"))
    verdict = Column(String)
    notes = Column(Text)

class Assembly(Base):
    __tablename__ = "assemblies"
    id = Column(String, primary_key=True)
    project_version_id = Column(String, ForeignKey("project_versions.id"))
    status = Column(String, default="draft")

class AssemblySegment(Base):
    __tablename__ = "assembly_segments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    assembly_id = Column(String, ForeignKey("assemblies.id"))
    submission_id = Column(String, ForeignKey("submissions.id"))
    segment_order = Column(Integer)

class PointLedger(Base):
    __tablename__ = "point_ledger"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    reason = Column(String)
    delta = Column(Integer)

class SearchIndex(Base):
    __tablename__ = "search_index"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_version_id = Column(String, ForeignKey("project_versions.id"))
    kind = Column(String)
    label = Column(String)
    payload = Column(Text)

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    role = Column(String)

class MediaArtifact(Base):
    __tablename__ = "media_artifacts"
    id = Column(String, primary_key=True)
    submission_id = Column(String, ForeignKey("submissions.id"))
    artifact_type = Column(String)
    path = Column(String)
