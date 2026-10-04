"""Demo login: the signed session cookie remembers which demo user was picked.
This is NOT real authentication (no passwords) - it is a prototype."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    return db.get(User, user_id) if user_id else None


def require_role(role: str):
    """Dependency factory: only lets in the logged-in demo user if they have this role."""
    def checker(user: User | None = Depends(get_current_user)) -> User:
        if user is None or user.role != role:
            # 303 redirect back to the sign-in page
            raise HTTPException(status_code=303, headers={"Location": "/"})
        return user
    return checker
