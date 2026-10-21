from fastapi import APIRouter, HTTPException

from app.dependencies import Store
from app.models import CircuitMap, RaceDetail, RacePhotos, RaceWeather
from app.service import get_race_detail

router = APIRouter(tags=["race"])


@router.get("/race/{session_key}", response_model=RaceDetail)
async def race_detail(session_key: int, store: Store) -> RaceDetail:
    """Full per-driver luck breakdown for a single race session."""
    result = await get_race_detail(store, session_key)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Race session {session_key} not found.")
    return result


@router.get("/race/{session_key}/circuit", response_model=CircuitMap)
async def race_circuit(session_key: int, store: Store) -> CircuitMap:
    """One lap of the circuit (the weekend's fastest qualifying lap) with DRS zones."""
    session = await store.session(session_key)
    circuit = await store.circuit(session) if session else None
    if circuit is None:
        raise HTTPException(status_code=404, detail="No lap data to draw this circuit.")
    return circuit


@router.get("/race/{session_key}/weather", response_model=RaceWeather)
async def race_weather(session_key: int, store: Store) -> RaceWeather:
    """Weather station readings from the race."""
    session = await store.session(session_key)
    weather = await store.weather(session) if session else None
    if weather is None:
        raise HTTPException(status_code=404, detail="No weather data for this race.")
    return weather


@router.get("/race/{session_key}/photos", response_model=RacePhotos)
async def race_photos(session_key: int, store: Store) -> RacePhotos:
    """Freely licensed photos of the race weekend (or the circuit) from Wikimedia Commons."""
    session = await store.session(session_key)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Race session {session_key} not found.")
    return await store.photos(session)
