"""Authentication and member management API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    OrganizationResponse,
    InviteMemberRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & Members"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_organization(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new organization tenant and its initial administrator account."""
    return AuthService.register_organization(db=db, req=req)


@router.post("/login", response_model=TokenResponse)
def login_for_access_token(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate credentials and obtain a JWT access token."""
    return AuthService.authenticate(db=db, req=req)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve authenticated user profile and tenant identity."""
    return current_user


@router.get("/organization", response_model=OrganizationResponse)
def get_current_organization(current_user: User = Depends(get_current_user)):
    """Retrieve authenticated organization tenant details."""
    return current_user.organization


@router.get("/members", response_model=List[UserResponse])
def list_organization_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all members within the current user's organization."""
    return AuthService.list_members(db=db, organization_id=current_user.organization_id)


@router.post("/members", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    req: InviteMemberRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.SUPPORT_MANAGER])),
    db: Session = Depends(get_db),
):
    """Invite/create a new agent or manager in the organization (Requires Admin or Manager)."""
    return AuthService.invite_member(db=db, current_user=current_user, req=req)
