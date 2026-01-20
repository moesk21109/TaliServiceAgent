"""
Elektro-Planer API Router
Endpoints for floor plan projects, rooms, and electrical elements.
"""
import secrets
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import (
    FloorProject, ProjectFloor, ProjectRoom, ProjectElement,
    FloorProjectCreate, FloorProjectResponse,
    ProjectFloorCreate, ProjectFloorResponse,
    ProjectRoomCreate, ProjectRoomResponse,
    ProjectElementCreate, ProjectElementResponse,
    ProjectFullSave, ProjectFullResponse
)

router = APIRouter(prefix="/api/floor-planner", tags=["floor-planner"])


# ==========================================
# PROJECTS
# ==========================================

@router.get("/projects", response_model=List[FloorProjectResponse])
async def list_projects(session: Session = Depends(get_session)):
    """List all projects."""
    projects = session.exec(select(FloorProject).order_by(FloorProject.updated_at.desc())).all()
    return projects


@router.post("/projects", response_model=FloorProjectResponse)
async def create_project(data: FloorProjectCreate, session: Session = Depends(get_session)):
    """Create a new project."""
    project = FloorProject(
        name=data.name,
        customer_id=data.customer_id,
        address=data.address,
        notes=data.notes
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=FloorProjectResponse)
async def get_project(project_id: int, session: Session = Depends(get_session)):
    """Get project by ID."""
    project = session.get(FloorProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=FloorProjectResponse)
async def update_project(project_id: int, data: FloorProjectCreate, session: Session = Depends(get_session)):
    """Update project."""
    project = session.get(FloorProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.name = data.name
    project.customer_id = data.customer_id
    project.address = data.address
    project.notes = data.notes
    project.updated_at = datetime.utcnow()
    
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, session: Session = Depends(get_session)):
    """Delete project and all associated data."""
    project = session.get(FloorProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete all floors (cascades to rooms and elements)
    floors = session.exec(select(ProjectFloor).where(ProjectFloor.project_id == project_id)).all()
    for floor in floors:
        # Delete elements
        elements = session.exec(select(ProjectElement).where(ProjectElement.floor_id == floor.id)).all()
        for el in elements:
            session.delete(el)
        # Delete rooms
        rooms = session.exec(select(ProjectRoom).where(ProjectRoom.floor_id == floor.id)).all()
        for room in rooms:
            session.delete(room)
        session.delete(floor)
    
    session.delete(project)
    session.commit()
    return {"status": "deleted"}


# ==========================================
# SHARE FUNCTIONALITY
# ==========================================

@router.post("/projects/{project_id}/share")
async def enable_share(project_id: int, can_add: bool = True, can_move: bool = True, 
                       can_delete: bool = False, can_comment: bool = True,
                       session: Session = Depends(get_session)):
    """Enable sharing for a project."""
    project = session.get(FloorProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.share_token:
        project.share_token = secrets.token_urlsafe(16)
    
    project.share_enabled = True
    project.share_can_add = can_add
    project.share_can_move = can_move
    project.share_can_delete = can_delete
    project.share_can_comment = can_comment
    project.updated_at = datetime.utcnow()
    
    session.add(project)
    session.commit()
    session.refresh(project)
    
    return {
        "share_token": project.share_token,
        "share_url": f"/floor-planner?share={project.share_token}",
        "permissions": {
            "can_add": can_add,
            "can_move": can_move,
            "can_delete": can_delete,
            "can_comment": can_comment
        }
    }


@router.delete("/projects/{project_id}/share")
async def disable_share(project_id: int, session: Session = Depends(get_session)):
    """Disable sharing for a project."""
    project = session.get(FloorProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.share_enabled = False
    project.updated_at = datetime.utcnow()
    
    session.add(project)
    session.commit()
    return {"status": "sharing disabled"}


@router.get("/shared/{share_token}", response_model=ProjectFullResponse)
async def get_shared_project(share_token: str, session: Session = Depends(get_session)):
    """Get project by share token (public access)."""
    project = session.exec(
        select(FloorProject).where(
            FloorProject.share_token == share_token,
            FloorProject.share_enabled == True
        )
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Shared project not found or sharing disabled")
    
    # Get floor
    floor = session.exec(
        select(ProjectFloor).where(ProjectFloor.project_id == project.id)
    ).first()
    
    if not floor:
        raise HTTPException(status_code=404, detail="No floor plan found")
    
    # Get rooms and elements
    rooms = session.exec(select(ProjectRoom).where(ProjectRoom.floor_id == floor.id)).all()
    elements = session.exec(select(ProjectElement).where(ProjectElement.floor_id == floor.id)).all()
    
    return ProjectFullResponse(
        project=FloorProjectResponse.model_validate(project),
        floor=ProjectFloorResponse.model_validate(floor),
        rooms=[ProjectRoomResponse.model_validate(r) for r in rooms],
        elements=[ProjectElementResponse.model_validate(e) for e in elements]
    )


# ==========================================
# FLOORS
# ==========================================

@router.get("/projects/{project_id}/floors", response_model=List[ProjectFloorResponse])
async def list_floors(project_id: int, session: Session = Depends(get_session)):
    """List floors for a project."""
    floors = session.exec(
        select(ProjectFloor)
        .where(ProjectFloor.project_id == project_id)
        .order_by(ProjectFloor.order_index)
    ).all()
    return floors


@router.post("/floors", response_model=ProjectFloorResponse)
async def create_floor(data: ProjectFloorCreate, session: Session = Depends(get_session)):
    """Create a new floor."""
    floor = ProjectFloor(
        project_id=data.project_id,
        name=data.name,
        floor_plan_data=data.floor_plan_data,
        floor_plan_type=data.floor_plan_type,
        scale_pixels_per_meter=data.scale_pixels_per_meter
    )
    session.add(floor)
    session.commit()
    session.refresh(floor)
    return floor


@router.put("/floors/{floor_id}", response_model=ProjectFloorResponse)
async def update_floor(floor_id: int, data: ProjectFloorCreate, session: Session = Depends(get_session)):
    """Update floor."""
    floor = session.get(ProjectFloor, floor_id)
    if not floor:
        raise HTTPException(status_code=404, detail="Floor not found")
    
    floor.name = data.name
    floor.floor_plan_data = data.floor_plan_data
    floor.floor_plan_type = data.floor_plan_type
    floor.scale_pixels_per_meter = data.scale_pixels_per_meter
    
    session.add(floor)
    session.commit()
    session.refresh(floor)
    return floor


# ==========================================
# ROOMS
# ==========================================

@router.get("/floors/{floor_id}/rooms", response_model=List[ProjectRoomResponse])
async def list_rooms(floor_id: int, session: Session = Depends(get_session)):
    """List rooms for a floor."""
    rooms = session.exec(select(ProjectRoom).where(ProjectRoom.floor_id == floor_id)).all()
    return rooms


@router.post("/rooms", response_model=ProjectRoomResponse)
async def create_room(data: ProjectRoomCreate, session: Session = Depends(get_session)):
    """Create a new room."""
    room = ProjectRoom(
        floor_id=data.floor_id,
        name=data.name,
        color=data.color,
        category=data.category,
        x=data.x,
        y=data.y,
        width=data.width,
        height=data.height
    )
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


@router.delete("/rooms/{room_id}")
async def delete_room(room_id: int, session: Session = Depends(get_session)):
    """Delete room."""
    room = session.get(ProjectRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    session.delete(room)
    session.commit()
    return {"status": "deleted"}


# ==========================================
# ELEMENTS
# ==========================================

@router.get("/floors/{floor_id}/elements", response_model=List[ProjectElementResponse])
async def list_elements(floor_id: int, session: Session = Depends(get_session)):
    """List elements for a floor."""
    elements = session.exec(select(ProjectElement).where(ProjectElement.floor_id == floor_id)).all()
    return elements


@router.post("/elements", response_model=ProjectElementResponse)
async def create_element(data: ProjectElementCreate, session: Session = Depends(get_session)):
    """Create a new element."""
    element = ProjectElement(
        floor_id=data.floor_id,
        room_id=data.room_id,
        element_type=data.element_type,
        code=data.code,
        x=data.x,
        y=data.y,
        rotation=data.rotation,
        height=data.height,
        notes=data.notes
    )
    session.add(element)
    session.commit()
    session.refresh(element)
    return element


@router.put("/elements/{element_id}", response_model=ProjectElementResponse)
async def update_element(element_id: int, data: ProjectElementCreate, session: Session = Depends(get_session)):
    """Update element."""
    element = session.get(ProjectElement, element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Element not found")
    
    element.element_type = data.element_type
    element.code = data.code
    element.x = data.x
    element.y = data.y
    element.rotation = data.rotation
    element.height = data.height
    element.notes = data.notes
    element.room_id = data.room_id
    
    session.add(element)
    session.commit()
    session.refresh(element)
    return element


@router.delete("/elements/{element_id}")
async def delete_element(element_id: int, session: Session = Depends(get_session)):
    """Delete element."""
    element = session.get(ProjectElement, element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Element not found")
    session.delete(element)
    session.commit()
    return {"status": "deleted"}


# ==========================================
# FULL PROJECT SAVE/LOAD
# ==========================================

@router.post("/save-full", response_model=ProjectFullResponse)
async def save_full_project(data: ProjectFullSave, session: Session = Depends(get_session)):
    """Save complete project with floor, rooms, and elements in one request."""
    
    # Create or find project
    project = FloorProject(
        name=data.project.name,
        customer_id=data.project.customer_id,
        address=data.project.address,
        notes=data.project.notes
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    
    # Create floor
    floor = ProjectFloor(
        project_id=project.id,
        name=data.floor.name,
        floor_plan_data=data.floor.floor_plan_data,
        floor_plan_type=data.floor.floor_plan_type,
        scale_pixels_per_meter=data.floor.scale_pixels_per_meter
    )
    session.add(floor)
    session.commit()
    session.refresh(floor)
    
    # Create rooms
    saved_rooms = []
    for room_data in data.rooms:
        room = ProjectRoom(
            floor_id=floor.id,
            name=room_data.name,
            color=room_data.color,
            category=room_data.category,
            x=room_data.x,
            y=room_data.y,
            width=room_data.width,
            height=room_data.height
        )
        session.add(room)
        session.commit()
        session.refresh(room)
        saved_rooms.append(room)
    
    # Create elements
    saved_elements = []
    for el_data in data.elements:
        element = ProjectElement(
            floor_id=floor.id,
            room_id=el_data.room_id,
            element_type=el_data.element_type,
            code=el_data.code,
            x=el_data.x,
            y=el_data.y,
            rotation=el_data.rotation,
            height=el_data.height,
            notes=el_data.notes
        )
        session.add(element)
        session.commit()
        session.refresh(element)
        saved_elements.append(element)
    
    # Update project timestamp
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    
    return ProjectFullResponse(
        project=FloorProjectResponse.model_validate(project),
        floor=ProjectFloorResponse.model_validate(floor),
        rooms=[ProjectRoomResponse.model_validate(r) for r in saved_rooms],
        elements=[ProjectElementResponse.model_validate(e) for e in saved_elements]
    )


@router.get("/load-full/{project_id}", response_model=ProjectFullResponse)
async def load_full_project(project_id: int, session: Session = Depends(get_session)):
    """Load complete project with floor, rooms, and elements."""
    project = session.get(FloorProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get floor (assuming one floor per project for now)
    floor = session.exec(
        select(ProjectFloor).where(ProjectFloor.project_id == project_id)
    ).first()
    
    if not floor:
        raise HTTPException(status_code=404, detail="No floor found for project")
    
    # Get rooms and elements
    rooms = session.exec(select(ProjectRoom).where(ProjectRoom.floor_id == floor.id)).all()
    elements = session.exec(select(ProjectElement).where(ProjectElement.floor_id == floor.id)).all()
    
    return ProjectFullResponse(
        project=FloorProjectResponse.model_validate(project),
        floor=ProjectFloorResponse.model_validate(floor),
        rooms=[ProjectRoomResponse.model_validate(r) for r in rooms],
        elements=[ProjectElementResponse.model_validate(e) for e in elements]
    )


@router.put("/update-full/{project_id}", response_model=ProjectFullResponse)
async def update_full_project(project_id: int, data: ProjectFullSave, session: Session = Depends(get_session)):
    """Update complete project - deletes old data and saves new."""
    project = session.get(FloorProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update project info
    project.name = data.project.name
    project.customer_id = data.project.customer_id
    project.address = data.project.address
    project.notes = data.project.notes
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    
    # Get existing floor
    floor = session.exec(
        select(ProjectFloor).where(ProjectFloor.project_id == project_id)
    ).first()
    
    if floor:
        # Delete old elements and rooms
        old_elements = session.exec(select(ProjectElement).where(ProjectElement.floor_id == floor.id)).all()
        for el in old_elements:
            session.delete(el)
        old_rooms = session.exec(select(ProjectRoom).where(ProjectRoom.floor_id == floor.id)).all()
        for room in old_rooms:
            session.delete(room)
        
        # Update floor
        floor.name = data.floor.name
        floor.floor_plan_data = data.floor.floor_plan_data
        floor.floor_plan_type = data.floor.floor_plan_type
        floor.scale_pixels_per_meter = data.floor.scale_pixels_per_meter
        session.add(floor)
    else:
        # Create new floor
        floor = ProjectFloor(
            project_id=project.id,
            name=data.floor.name,
            floor_plan_data=data.floor.floor_plan_data,
            floor_plan_type=data.floor.floor_plan_type,
            scale_pixels_per_meter=data.floor.scale_pixels_per_meter
        )
        session.add(floor)
    
    session.commit()
    session.refresh(floor)
    
    # Create new rooms
    saved_rooms = []
    for room_data in data.rooms:
        room = ProjectRoom(
            floor_id=floor.id,
            name=room_data.name,
            color=room_data.color,
            category=room_data.category,
            x=room_data.x,
            y=room_data.y,
            width=room_data.width,
            height=room_data.height
        )
        session.add(room)
        session.commit()
        session.refresh(room)
        saved_rooms.append(room)
    
    # Create new elements
    saved_elements = []
    for el_data in data.elements:
        element = ProjectElement(
            floor_id=floor.id,
            room_id=el_data.room_id,
            element_type=el_data.element_type,
            code=el_data.code,
            x=el_data.x,
            y=el_data.y,
            rotation=el_data.rotation,
            height=el_data.height,
            notes=el_data.notes
        )
        session.add(element)
        session.commit()
        session.refresh(element)
        saved_elements.append(element)
    
    return ProjectFullResponse(
        project=FloorProjectResponse.model_validate(project),
        floor=ProjectFloorResponse.model_validate(floor),
        rooms=[ProjectRoomResponse.model_validate(r) for r in saved_rooms],
        elements=[ProjectElementResponse.model_validate(e) for e in saved_elements]
    )


# ==========================================
# MATERIAL LIST (Stückliste)
# ==========================================

# Element type to material mapping
ELEMENT_MATERIALS = {
    "steckdose_schuko": {"name": "Schuko-Steckdose UP", "unit": "Stück", "price": 12.50},
    "steckdose_doppelt": {"name": "Doppel-Steckdose UP", "unit": "Stück", "price": 18.90},
    "steckdose_usb": {"name": "Schuko-Steckdose mit USB", "unit": "Stück", "price": 29.90},
    "steckdose_cee16": {"name": "CEE 16A Steckdose", "unit": "Stück", "price": 45.00},
    "steckdose_cee32": {"name": "CEE 32A Steckdose", "unit": "Stück", "price": 65.00},
    "ausschalter": {"name": "Ausschalter UP", "unit": "Stück", "price": 9.90},
    "wechselschalter": {"name": "Wechselschalter UP", "unit": "Stück", "price": 12.90},
    "kreuzschalter": {"name": "Kreuzschalter UP", "unit": "Stück", "price": 18.50},
    "dimmer": {"name": "Dimmer UP", "unit": "Stück", "price": 39.90},
    "taster": {"name": "Taster UP", "unit": "Stück", "price": 11.90},
    "jalousietaster": {"name": "Jalousietaster UP", "unit": "Stück", "price": 16.90},
    "deckenauslass": {"name": "Deckenauslass", "unit": "Stück", "price": 8.50},
    "wandauslass": {"name": "Wandauslass", "unit": "Stück", "price": 8.50},
    "einbaustrahler": {"name": "Einbaustrahler-Dose", "unit": "Stück", "price": 5.90},
    "aussenleuchte": {"name": "Außenleuchten-Anschluss IP44", "unit": "Stück", "price": 15.90},
    "herdanschluss": {"name": "Herdanschlussdose", "unit": "Stück", "price": 24.90},
    "tv_anschluss": {"name": "Antennendose SAT/TV", "unit": "Stück", "price": 18.50},
    "netzwerk": {"name": "Netzwerkdose Cat.6 2-fach", "unit": "Stück", "price": 22.90},
    "telefon": {"name": "TAE-Dose", "unit": "Stück", "price": 12.50},
    "rauchmelder": {"name": "Rauchmelder 230V", "unit": "Stück", "price": 35.00},
}

# Element type to labor price mapping (installation cost)
ELEMENT_LABOR = {
    "steckdose_schuko": {"name": "Steckdose anschließen", "unit": "Stück", "price": 89.00},
    "steckdose_doppelt": {"name": "Doppelsteckdose anschließen", "unit": "Stück", "price": 109.00},
    "steckdose_usb": {"name": "USB-Steckdose anschließen", "unit": "Stück", "price": 99.00},
    "steckdose_cee16": {"name": "CEE 16A anschließen", "unit": "Stück", "price": 145.00},
    "steckdose_cee32": {"name": "CEE 32A anschließen", "unit": "Stück", "price": 175.00},
    "ausschalter": {"name": "Ausschalter anschließen", "unit": "Stück", "price": 79.00},
    "wechselschalter": {"name": "Wechselschalter anschließen", "unit": "Stück", "price": 95.00},
    "kreuzschalter": {"name": "Kreuzschalter anschließen", "unit": "Stück", "price": 115.00},
    "dimmer": {"name": "Dimmer anschließen", "unit": "Stück", "price": 110.00},
    "taster": {"name": "Taster anschließen", "unit": "Stück", "price": 85.00},
    "jalousietaster": {"name": "Jalousietaster anschließen", "unit": "Stück", "price": 95.00},
    "deckenauslass": {"name": "Deckenauslass setzen", "unit": "Stück", "price": 75.00},
    "wandauslass": {"name": "Wandauslass setzen", "unit": "Stück", "price": 75.00},
    "einbaustrahler": {"name": "Einbaustrahler vorbereiten", "unit": "Stück", "price": 45.00},
    "aussenleuchte": {"name": "Außenleuchte anschließen", "unit": "Stück", "price": 95.00},
    "herdanschluss": {"name": "Herdanschluss setzen", "unit": "Stück", "price": 185.00},
    "tv_anschluss": {"name": "Antennendose setzen", "unit": "Stück", "price": 85.00},
    "netzwerk": {"name": "Netzwerkdose setzen", "unit": "Stück", "price": 95.00},
    "telefon": {"name": "Telefondose setzen", "unit": "Stück", "price": 75.00},
    "rauchmelder": {"name": "Rauchmelder installieren", "unit": "Stück", "price": 65.00},
}


@router.get("/projects/{project_id}/materials")
async def get_materials_list(project_id: int, session: Session = Depends(get_session)):
    """Get material list (Stückliste) for a project."""
    # Get floor
    floor = session.exec(
        select(ProjectFloor).where(ProjectFloor.project_id == project_id)
    ).first()
    
    if not floor:
        return {"materials": [], "total": 0}
    
    # Get elements
    elements = session.exec(select(ProjectElement).where(ProjectElement.floor_id == floor.id)).all()
    
    # Count by type
    counts = {}
    for el in elements:
        if el.element_type not in counts:
            counts[el.element_type] = 0
        counts[el.element_type] += 1
    
    # Build material list
    materials = []
    total = 0
    for el_type, count in counts.items():
        if el_type in ELEMENT_MATERIALS:
            mat = ELEMENT_MATERIALS[el_type]
            subtotal = mat["price"] * count
            total += subtotal
            materials.append({
                "element_type": el_type,
                "name": mat["name"],
                "quantity": count,
                "unit": mat["unit"],
                "unit_price": mat["price"],
                "total_price": subtotal
            })
    
    return {"materials": materials, "total": total}


@router.get("/projects/{project_id}/quote-positions")
async def get_quote_positions(project_id: int, session: Session = Depends(get_session)):
    """Get quote positions (Angebotspositionen) for a project."""
    # Get floor
    floor = session.exec(
        select(ProjectFloor).where(ProjectFloor.project_id == project_id)
    ).first()
    
    if not floor:
        return {"positions": [], "total_net": 0, "vat": 0, "total_gross": 0}
    
    # Get elements
    elements = session.exec(select(ProjectElement).where(ProjectElement.floor_id == floor.id)).all()
    
    # Count by type
    counts = {}
    for el in elements:
        if el.element_type not in counts:
            counts[el.element_type] = 0
        counts[el.element_type] += 1
    
    # Build positions list
    positions = []
    total_net = 0
    
    # Add setup position
    positions.append({
        "pos": 1,
        "name": "Baustelleneinrichtung",
        "quantity": 1,
        "unit": "psch",
        "unit_price": 119.00,
        "total_price": 119.00
    })
    total_net += 119.00
    
    pos = 2
    for el_type, count in counts.items():
        if el_type in ELEMENT_LABOR:
            labor = ELEMENT_LABOR[el_type]
            subtotal = labor["price"] * count
            total_net += subtotal
            positions.append({
                "pos": pos,
                "element_type": el_type,
                "name": labor["name"],
                "quantity": count,
                "unit": labor["unit"],
                "unit_price": labor["price"],
                "total_price": subtotal
            })
            pos += 1
    
    # Add inspection
    positions.append({
        "pos": pos,
        "name": "Prüfprotokoll nach DIN VDE",
        "quantity": 1,
        "unit": "psch",
        "unit_price": 120.00,
        "total_price": 120.00
    })
    total_net += 120.00
    
    vat = total_net * 0.19
    total_gross = total_net + vat
    
    return {
        "positions": positions,
        "total_net": round(total_net, 2),
        "vat": round(vat, 2),
        "total_gross": round(total_gross, 2)
    }
