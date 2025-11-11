from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.roles import DEFAULT_READ_ROLES
from app.db.session import get_db
from app.schemas.send_query import CampaignQueryFilters, CampaignQueryResponse, CampaignDetail
from app.services.send_query_service import get_campaign_detail, list_campaigns

router = APIRouter(prefix="/send-query", tags=["send-query"])


@router.get("/campaigns", response_model=CampaignQueryResponse)
def list_campaigns_endpoint(
    filters: CampaignQueryFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_READ_ROLES)),
):
    return list_campaigns(db, filters)


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetail)
def get_campaign_detail_endpoint(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: deps.AuthenticatedUser = Depends(deps.require_roles(DEFAULT_READ_ROLES)),
):
    try:
        return get_campaign_detail(db, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
