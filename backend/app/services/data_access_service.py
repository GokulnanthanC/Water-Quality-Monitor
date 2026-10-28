import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import DataAccessPolicy, DataAccessPartner

logger = logging.getLogger(__name__)

class DataAccessService:
    @staticmethod
    def set_policy(
        db: Session,
        resource_type: str,
        resource_id: int,
        owner_organization_id: int,
        visibility: str = "private",
        partner_organization_ids: Optional[List[int]] = None,
        created_by: Optional[int] = None
    ) -> DataAccessPolicy:
        """
        Create or update access policy for a resource (e.g. report, incident, equipment).
        Visibility options: 'private', 'partner', 'public'
        """
        policy = db.query(DataAccessPolicy).filter(
            DataAccessPolicy.resource_type == resource_type,
            DataAccessPolicy.resource_id == resource_id
        ).first()

        if not policy:
            policy = DataAccessPolicy(
                resource_type=resource_type,
                resource_id=resource_id,
                owner_organization_id=owner_organization_id,
                visibility=visibility,
                created_by=created_by
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
        else:
            policy.visibility = visibility
            policy.owner_organization_id = owner_organization_id
            db.commit()

        # Update partner sharing list if partner visibility
        if partner_organization_ids is not None:
            # Delete existing partners
            db.query(DataAccessPartner).filter(DataAccessPartner.policy_id == policy.id).delete()
            for partner_org_id in partner_organization_ids:
                if partner_org_id != owner_organization_id:
                    partner = DataAccessPartner(
                        policy_id=policy.id,
                        organization_id=partner_org_id,
                        permission="read"
                    )
                    db.add(partner)
            db.commit()
            db.refresh(policy)

        return policy

    @staticmethod
    def can_access(
        db: Session,
        resource_type: str,
        resource_id: int,
        user_organization_id: Optional[int],
        user_system_role: str = "citizen",
        required_permission: str = "read"
    ) -> bool:
        """
        Check if user or organization can access the specified resource.
        Admins and system authorities have overriding visibility for compliance.
        """
        if user_system_role in ["admin", "authority"]:
            return True

        policy = db.query(DataAccessPolicy).filter(
            DataAccessPolicy.resource_type == resource_type,
            DataAccessPolicy.resource_id == resource_id
        ).first()

        # If no explicit policy exists, default is open/public
        if not policy:
            return True

        # Public visibility is viewable by anyone
        if policy.visibility == "public" and required_permission == "read":
            return True

        # If user has no organization and resource is not public, deny
        if not user_organization_id:
            return False

        # Owner organization always has full access
        if policy.owner_organization_id == user_organization_id:
            return True

        # If partner visibility, check if user's organization is in partners list
        if policy.visibility == "partner":
            partner_match = db.query(DataAccessPartner).filter(
                DataAccessPartner.policy_id == policy.id,
                DataAccessPartner.organization_id == user_organization_id
            ).first()
            if partner_match:
                if required_permission == "read":
                    return True
                if required_permission in ["write", "edit"] and partner_match.permission in ["write", "full"]:
                    return True
                if required_permission == "admin" and partner_match.permission == "full":
                    return True

        return False

data_access_service = DataAccessService()
