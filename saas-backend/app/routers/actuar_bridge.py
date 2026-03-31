from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import clear_current_gym_id, get_db, set_current_gym_id
from app.models import ActuarBridgeDevice
from app.schemas.actuar_bridge import (
    ActuarBridgeClaimedJobRead,
    ActuarBridgeHeartbeatResponse,
    ActuarBridgeJobCompleteInput,
    ActuarBridgeJobFailInput,
    ActuarBridgePairRequest,
    ActuarBridgePairResponse,
)
from app.services.actuar_bridge_service import (
    authenticate_actuar_bridge_device,
    claim_next_actuar_bridge_job,
    complete_actuar_bridge_job,
    fail_actuar_bridge_job,
    heartbeat_actuar_bridge_device,
    pair_actuar_bridge_device,
)


router = APIRouter(prefix="/actuar-bridge", tags=["actuar-bridge"])


def get_current_bridge_device(
    db: Annotated[Session, Depends(get_db)],
    bridge_token: Annotated[str, Header(alias="X-Actuar-Bridge-Token")],
):
    device = authenticate_actuar_bridge_device(db, device_token=bridge_token)
    set_current_gym_id(device.gym_id)
    try:
        yield device
    finally:
        clear_current_gym_id()


@router.post("/pair", response_model=ActuarBridgePairResponse)
def pair_actuar_bridge_endpoint(
    payload: ActuarBridgePairRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ActuarBridgePairResponse:
    result = pair_actuar_bridge_device(db, payload=payload)
    db.commit()
    return result


@router.post("/heartbeat", response_model=ActuarBridgeHeartbeatResponse)
def heartbeat_actuar_bridge_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_device: Annotated[ActuarBridgeDevice, Depends(get_current_bridge_device)],
) -> ActuarBridgeHeartbeatResponse:
    result = heartbeat_actuar_bridge_device(db, device=current_device)
    db.commit()
    return result


@router.post("/jobs/claim", response_model=ActuarBridgeClaimedJobRead | None)
def claim_next_actuar_bridge_job_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_device: Annotated[ActuarBridgeDevice, Depends(get_current_bridge_device)],
) -> ActuarBridgeClaimedJobRead | None:
    result = claim_next_actuar_bridge_job(db, device=current_device)
    if result is None:
        db.commit()
        return None
    db.commit()
    return result


@router.post("/jobs/{job_id}/complete")
def complete_actuar_bridge_job_endpoint(
    job_id: UUID,
    payload: ActuarBridgeJobCompleteInput,
    db: Annotated[Session, Depends(get_db)],
    current_device: Annotated[ActuarBridgeDevice, Depends(get_current_bridge_device)],
) -> dict[str, str]:
    complete_actuar_bridge_job(db, device=current_device, job_id=job_id, payload=payload)
    db.commit()
    return {"status": "ok"}


@router.post("/jobs/{job_id}/fail")
def fail_actuar_bridge_job_endpoint(
    job_id: UUID,
    payload: ActuarBridgeJobFailInput,
    db: Annotated[Session, Depends(get_db)],
    current_device: Annotated[ActuarBridgeDevice, Depends(get_current_bridge_device)],
) -> dict[str, str]:
    fail_actuar_bridge_job(db, device=current_device, job_id=job_id, payload=payload)
    db.commit()
    return {"status": "ok"}
