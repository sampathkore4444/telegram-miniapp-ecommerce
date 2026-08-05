import httpx
from fastapi import APIRouter, Query

from app.core.errors import AppError

router = APIRouter(prefix="/geocode", tags=["geocode"])

USER_AGENT = "ShopTrolleyMiniapp/1.0 (https://minishop.khmerhomeservices.com)"


async def _nominatim(lat: float, lon: float) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "format": "jsonv2",
                    "lat": lat,
                    "lon": lon,
                    "zoom": 18,
                    "addressdetails": 1,
                    "accept-language": "en",
                },
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data or data.get("error"):
                return None
            a = data.get("address", {})
            parts = []
            road = a.get("road") or a.get("pedestrian") or a.get("footway")
            house = a.get("house_number")
            if road and house:
                parts.append(f"{house} {road}")
            elif road:
                parts.append(road)
            elif house:
                parts.append(house)
            for key in (
                "suburb",
                "neighbourhood",
                "quarter",
                "hamlet",
                "city_district",
                "village",
                "town",
                "city",
                "municipality",
                "state",
                "country",
            ):
                value = a.get(key)
                if value and value not in parts:
                    parts.append(value)
            if parts:
                return ", ".join(parts)
            return data.get("display_name")
    except Exception:
        return None


async def _bigdatacloud(lat: float, lon: float) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.bigdatacloud.net/data/reverse-geocode-client",
                params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            parts = []
            for key in ("locality", "city", "principalSubdivision", "countryName"):
                value = data.get(key)
                if value and value not in parts:
                    parts.append(value)
            if parts:
                return ", ".join(parts)
            return data.get("formattedAddress")
    except Exception:
        return None


@router.get("/reverse", response_model=dict)
async def reverse_geocode(lat: float = Query(...), lon: float = Query(...)):
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise AppError("Invalid coordinates", code="invalid_coordinates")
    address = await _nominatim(lat, lon) or await _bigdatacloud(lat, lon)
    if not address:
        raise AppError(
            "Could not resolve an address for those coordinates",
            code="geocode_failed",
            status_code=502,
        )
    return {"address": address, "latitude": lat, "longitude": lon}
