"""Authentication and user management business logic."""

import re
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.team import Team
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, InviteMemberRequest
from app.services.audit_service import AuditService


class AuthService:
    @staticmethod
    def _generate_slug(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
        return slug or "org"

    @classmethod
    def register_organization(cls, db: Session, req: UserRegisterRequest) -> dict:
        """Register a new tenant organization and its primary administrator."""
        # Check if email is already taken
        existing_user = db.query(User).filter(User.email == req.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        # Generate unique organization slug
        base_slug = cls._generate_slug(req.organization_name)
        slug = base_slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(name=req.organization_name, slug=slug)
        db.add(org)
        db.flush()  # assign org.id

        # Create default support teams
        tier1_team = Team(organization_id=org.id, name="Tier 1 Support", description="General customer inquiries and initial triage")
        billing_team = Team(organization_id=org.id, name="Billing & Finance", description="Payments, refunds, and subscription queries")
        tech_team = Team(organization_id=org.id, name="Technical Escalations", description="Bugs, API issues, and platform errors")
        db.add_all([tier1_team, billing_team, tech_team])

        # Create primary administrator
        admin_user = User(
            organization_id=org.id,
            email=req.email.lower(),
            password_hash=get_password_hash(req.password),
            full_name=req.full_name,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        db.flush()

        AuditService.log_event(
            db=db,
            organization_id=org.id,
            actor_id=admin_user.id,
            action="organization.registered",
            entity_type="organization",
            entity_id=org.id,
            details={"name": org.name, "slug": org.slug},
        )

        db.commit()
        db.refresh(org)
        db.refresh(admin_user)

        # Generate access token
        access_token = create_access_token(
            data={"sub": admin_user.id, "org_id": org.id, "role": admin_user.role}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": admin_user,
            "organization": org,
        }

    @staticmethod
    def authenticate(db: Session, req: UserLoginRequest) -> dict:
        """Authenticate user credentials and issue a verified JWT access token."""
        user = db.query(User).filter(User.email == req.email.lower()).first()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact your organization administrator.",
            )

        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization tenant not found.",
            )

        access_token = create_access_token(
            data={"sub": user.id, "org_id": org.id, "role": user.role}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
            "organization": org,
        }

    @staticmethod
    def invite_member(db: Session, current_user: User, req: InviteMemberRequest) -> User:
        """Add a team member to the current user's organization."""
        existing_user = db.query(User).filter(User.email == req.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        new_user = User(
            organization_id=current_user.organization_id,
            email=req.email.lower(),
            password_hash=get_password_hash(req.password),
            full_name=req.full_name,
            role=req.role,
            is_active=True,
        )
        db.add(new_user)
        db.flush()

        AuditService.log_event(
            db=db,
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
            action="user.invited",
            entity_type="user",
            entity_id=new_user.id,
            details={"email": new_user.email, "role": new_user.role},
        )

        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def list_members(db: Session, organization_id: str) -> List[User]:
        """List all users within an organization boundary."""
        return db.query(User).filter(User.organization_id == organization_id).order_by(User.created_at.desc()).all()
