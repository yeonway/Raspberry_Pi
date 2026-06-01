from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.kiwoom.client import KiwoomClient
from app.schemas import ConditionRunRequest, ConditionRunResponse, ConditionSummary
from app.services import condition_service

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


def get_client() -> KiwoomClient:
    from app.main import kiwoom_client

    return kiwoom_client


@router.get("", response_model=list[ConditionSummary])
async def list_conditions(
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[ConditionSummary]:
    return await condition_service.list_conditions(client, settings)


@router.post("/{seq}/run", response_model=ConditionRunResponse)
async def run_condition(
    seq: str,
    payload: ConditionRunRequest,
    client: Annotated[KiwoomClient, Depends(get_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConditionRunResponse:
    return await condition_service.run_condition(seq, payload, client, settings)
