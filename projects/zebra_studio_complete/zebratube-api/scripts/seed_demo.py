#!/usr/bin/env python3
from app.db import SessionLocal
from app.models.schema import User
db = SessionLocal()
if not db.get(User, "demo-user"):
    db.add(User(id="demo-user", username="demo-user", points=0)); db.commit(); print("seeded demo-user")
else:
    print("demo-user already exists")
db.close()
