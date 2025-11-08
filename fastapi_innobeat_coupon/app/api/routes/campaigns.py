from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.campaigns import CampaignCreate, CampaignRead
from app.schemas.dispatch import DispatchSummary, DispatchSyncSummary
from app.services.campaign_service import create_campaign
from app.services.dispatch_result_service import sync_dispatch_results
from app.services.dispatch_service import dispatch_campaign_messages

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign_endpoint(payload: CampaignCreate, db: Session = Depends(get_db)):
    """
    sendCoupon 화면의 발송 등록에서 캠페인을 생성한다.
    """
    try:
        campaign = create_campaign(db, payload)
        return CampaignRead.model_validate(campaign)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{campaign_id}/dispatch/results/sync",
    response_model=DispatchSyncSummary,
)
def sync_dispatch_results_endpoint(
    campaign_id: int,
    year_month: str | None = Query(default=None, description="UMS_LOG_YYYYMM 접미사"),
    db: Session = Depends(get_db),
):
    """
    SNAP Agent 결과 로그(UMS_LOG_YYYYMM)를 읽어 dispatch_results를 갱신한다.
    """
    try:
        return sync_dispatch_results(db, campaign_id, year_month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{campaign_id}/dispatch", response_model=DispatchSummary)
def dispatch_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """
    VALIDATED 상태 수신자를 SNAP Agent UMS_MSG에 INSERT 하여 발송 큐에 적재.
    """
    try:
        return dispatch_campaign_messages(db, campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
