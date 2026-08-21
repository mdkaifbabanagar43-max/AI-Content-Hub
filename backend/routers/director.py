from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from typing import List, Optional

from core.auth import get_current_user
from core.models.blueprint import ProductionBlueprint
from core.repositories.blueprint_repo import BlueprintRepository
from core.services.production_director import ProductionDirector

router = APIRouter(prefix="/projects", tags=["AI Production Director"])
repo = BlueprintRepository()

VALID_STATUS_TRANSITIONS = {
    "DRAFT": ["READY_FOR_APPROVAL", "INVALID", "DRAFT"],
    "READY_FOR_APPROVAL": ["APPROVED", "DRAFT", "INVALID", "READY_FOR_APPROVAL"],
    "APPROVED": ["IN_PRODUCTION", "SUPERSEDED", "DRAFT", "APPROVED"],
    "IN_PRODUCTION": ["COMPLETED", "SUPERSEDED", "IN_PRODUCTION"],
    "SUPERSEDED": ["DRAFT", "SUPERSEDED"],
    "INVALID": ["DRAFT", "INVALID"],
    "COMPLETED": ["COMPLETED"]
}

class BlueprintGenerateRequest(BaseModel):
    user_idea: str
    target_duration_seconds: float = 30.0

@router.post("/{project_id}/blueprint", response_model=ProductionBlueprint)
def generate_blueprint(
    project_id: str,
    request: BlueprintGenerateRequest,
    user_id: str = Depends(get_current_user)
):
    """Generates a new ProductionBlueprint based on user idea and existing Bibles."""
    try:
        director = ProductionDirector(user_id, project_id)
        blueprint = director.generate_blueprint(request.user_idea, request.target_duration_seconds)
        return blueprint
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{project_id}/blueprints/{blueprint_id}/version", response_model=ProductionBlueprint)
def create_blueprint_version(
    project_id: str,
    blueprint_id: str,
    blueprint_update: ProductionBlueprint,
    user_id: str = Depends(get_current_user)
):
    """Creates a new version revision for an existing blueprint identity without overwriting previous versions."""
    existing = repo.get(user_id, project_id, blueprint_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Original blueprint not found.")
        
    try:
        new_bp = repo.create_version(user_id, project_id, blueprint_id, blueprint_update)
        return new_bp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/blueprints", response_model=List[ProductionBlueprint])
def list_blueprints(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Lists all blueprints for a project."""
    try:
        return repo.list_all(user_id, project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/blueprints/{blueprint_id}", response_model=ProductionBlueprint)
def get_blueprint(
    project_id: str,
    blueprint_id: str,
    version: Optional[int] = Query(None, description="Optional specific version number"),
    user_id: str = Depends(get_current_user)
):
    """Gets a specific blueprint identity, optionally requesting an exact version."""
    try:
        bp = repo.get(user_id, project_id, blueprint_id, version=version)
        if not bp:
            raise HTTPException(status_code=404, detail="Blueprint not found.")
        return bp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/blueprints/{blueprint_id}/versions", response_model=List[ProductionBlueprint])
def list_blueprint_versions(
    project_id: str,
    blueprint_id: str,
    user_id: str = Depends(get_current_user)
):
    """Lists all revisions for a specific blueprint."""
    try:
        versions = repo.list_versions(user_id, project_id, blueprint_id)
        if not versions:
            raise HTTPException(status_code=404, detail="No versions found for blueprint.")
        return versions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{project_id}/blueprints/{blueprint_id}/status")
def update_blueprint_status(
    project_id: str,
    blueprint_id: str,
    status: str = Body(..., embed=True),
    version: Optional[int] = Query(None, description="Optional specific version number to update"),
    user_id: str = Depends(get_current_user)
):
    """
    Updates blueprint status with state transition enforcement.
    Requires explicit action (e.g. READY_FOR_APPROVAL -> APPROVED).
    """
    bp = repo.get(user_id, project_id, blueprint_id, version=version)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
        
    allowed = VALID_STATUS_TRANSITIONS.get(bp.status, [])
    if status not in allowed:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid state transition from '{bp.status}' to '{status}'. Allowed transitions: {allowed}"
        )
        
    bp.status = status
    repo.save(user_id, bp)
    return {
        "message": "Status updated successfully",
        "blueprint_id": bp.blueprint_id,
        "blueprint_version": bp.blueprint_version,
        "status": bp.status
    }
