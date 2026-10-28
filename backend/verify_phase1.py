"""
Self-contained verification script for Phase 1: Multi-Tenancy Foundation
"""
from app.database import SessionLocal, engine
from app import models
from app.models import User, Organization, OrganizationMember, AuditLog
from app.auth import create_token, verify_token, ROLE_PERMISSIONS
from app.services.audit_service import audit_service
from app.services.data_access_service import data_access_service
from passlib.context import CryptContext

# Ensure tables are built
models.Base.metadata.create_all(bind=engine)

def verify_multi_tenancy():
    db = SessionLocal()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
    
    try:
        print("1. Creating Test Organizations (Org Alpha & Org Beta)...")
        # Cleanup previous test records if existing
        test_orgs = db.query(Organization).filter(Organization.name.in_(["Org Alpha", "Org Beta"])).all()
        test_org_ids = [o.id for o in test_orgs]
        if test_org_ids:
            db.query(AuditLog).filter(AuditLog.organization_id.in_(test_org_ids)).delete(synchronize_session=False)
            db.query(OrganizationMember).filter(OrganizationMember.organization_id.in_(test_org_ids)).delete(synchronize_session=False)
            db.query(Organization).filter(Organization.id.in_(test_org_ids)).delete(synchronize_session=False)
            db.commit()

        org_a = Organization(
            name="Org Alpha",
            email="alpha@test.org",
            mission="Alpha Basin Conservation",
            status="active"
        )
        org_b = Organization(
            name="Org Beta",
            email="beta@test.org",
            mission="Beta River Network",
            status="active"
        )
        db.add_all([org_a, org_b])
        db.commit()
        db.refresh(org_a)
        db.refresh(org_b)
        print(f"   [OK] Created Org Alpha (ID: {org_a.id}) & Org Beta (ID: {org_b.id})")

        print("2. Creating Test Users & Memberships...")
        user_a = db.query(User).filter(User.email == "user_a@alpha.org").first()
        if not user_a:
            user_a = User(name="Alpha Admin", email="user_a@alpha.org", password=pwd_context.hash("Alpha@123"), role="ngo")
            db.add(user_a)
            db.commit()
            db.refresh(user_a)

        user_b = db.query(User).filter(User.email == "user_b@beta.org").first()
        if not user_b:
            user_b = User(name="Beta Admin", email="user_b@beta.org", password=pwd_context.hash("Beta@1234"), role="ngo")
            db.add(user_b)
            db.commit()
            db.refresh(user_b)

        # Clear existing test memberships
        db.query(OrganizationMember).filter(OrganizationMember.user_id.in_([user_a.id, user_b.id])).delete(synchronize_session=False)
        db.commit()

        mem_a = OrganizationMember(organization_id=org_a.id, user_id=user_a.id, role="admin", status="active")
        mem_b = OrganizationMember(organization_id=org_b.id, user_id=user_b.id, role="field_worker", status="active")
        db.add_all([mem_a, mem_b])
        db.commit()
        print("   [OK] User A linked to Org Alpha (role: admin), User B linked to Org Beta (role: field_worker)")

        print("3. Testing JWT Token Encoding & Context Extraction...")
        token_a = create_token({
            "sub": user_a.email,
            "role": user_a.role,
            "user_id": user_a.id,
            "organization_id": org_a.id,
            "org_role": "admin"
        })
        payload_a = verify_token(token_a)
        assert payload_a["organization_id"] == org_a.id, "Organization ID mismatch in token"
        assert payload_a["org_role"] == "admin", "Org role mismatch in token"
        print("   [OK] JWT token correctly encoded and verified with organization context")

        print("4. Testing Audit Logging Service...")
        log_entry = audit_service.log(
            db=db,
            action="CREATE",
            user_id=user_a.id,
            organization_id=org_a.id,
            resource_type="organization_test",
            resource_id=org_a.id,
            metadata={"secret_token": "SHOULD_BE_REDACTED", "test_field": "visible_value"}
        )
        assert log_entry is not None, "Audit log creation failed"
        assert "[REDACTED]" in log_entry.metadata_json, "Sensitive field was not sanitized"
        print("   [OK] Audit log recorded and sanitized sensitive fields safely")

        print("5. Testing Multi-Tenant Data Access Policies...")
        # A) Private resource belonging to Org Alpha
        data_access_service.set_policy(
            db=db,
            resource_type="incident",
            resource_id=901,
            owner_organization_id=org_a.id,
            visibility="private"
        )
        can_a_access = data_access_service.can_access(db, "incident", 901, user_organization_id=org_a.id)
        can_b_access = data_access_service.can_access(db, "incident", 901, user_organization_id=org_b.id)
        assert can_a_access is True, "Owner Org Alpha should have access"
        assert can_b_access is False, "Org Beta should NOT have access to private resource"
        print("   [OK] Private policy enforced: Org Alpha = True, Org Beta = False")

        # B) Partner resource shared from Org Alpha to Org Beta
        data_access_service.set_policy(
            db=db,
            resource_type="incident",
            resource_id=902,
            owner_organization_id=org_a.id,
            visibility="partner",
            partner_organization_ids=[org_b.id]
        )
        can_b_access_partner = data_access_service.can_access(db, "incident", 902, user_organization_id=org_b.id)
        assert can_b_access_partner is True, "Partner Org Beta should have read access"
        print("   [OK] Partner policy enforced: Shared Org Beta = True")

        # C) Public resource
        data_access_service.set_policy(
            db=db,
            resource_type="report",
            resource_id=903,
            owner_organization_id=org_a.id,
            visibility="public"
        )
        can_anyone_access = data_access_service.can_access(db, "report", 903, user_organization_id=None)
        assert can_anyone_access is True, "Public resource must be viewable by anyone"
        print("   [OK] Public policy enforced: Unauthenticated / citizen = True")

        print("\nALL PHASE 1 MULTI-TENANCY FOUNDATION CHECKS PASSED SUCCESSFULLY!")

    finally:
        db.close()

if __name__ == "__main__":
    verify_multi_tenancy()
