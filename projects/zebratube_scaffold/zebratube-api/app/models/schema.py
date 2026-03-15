
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    title = Column(String)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    title = Column(String)
    projection = Column(String)
    assembly_weight = Column(Float)
    project_id = Column(String, ForeignKey("projects.id"))
