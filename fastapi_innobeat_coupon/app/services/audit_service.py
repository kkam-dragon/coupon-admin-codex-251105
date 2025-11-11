from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.domain import AuditLog


def log_action(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    success: bool = True,
    commit: bool = False,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
    )
    db.add(log)
    if commit:
        db.commit()
    else:
        db.flush()
    return log
