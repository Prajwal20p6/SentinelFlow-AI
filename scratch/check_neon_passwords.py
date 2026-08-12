import sys
sys.path.insert(0, 'backend')
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.models import User
from app.core.security import verify_password

db = SessionLocal()
users = db.query(User).all()
passwords_to_check = ['admin123', 'AdminPass123!', 'eng123', 'view123', 'JudgeDemo123!', 'EngineerPass123!', 'ViewerPass123!']

print(f"Total users in Neon DB: {len(users)}")
for u in users:
    print(f"User ID: {u.id} | Email: {u.email} | Hash prefix: {u.hashed_password[:30]}...")
    found = False
    for pw in passwords_to_check:
        if verify_password(pw, u.hashed_password):
            print(f"  ==> MATCH FOUND for {u.email}: password is '{pw}'")
            found = True
    if not found:
        print(f"  ❌ NO MATCH FOUND for {u.email} among test passwords")
