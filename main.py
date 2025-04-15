from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uuid
import random
from typing import List, Dict

app = FastAPI()

# Монтируем статические файлы (для frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Модели данных
class CaseItem(BaseModel):
    name: str
    rarity: str
    chance: float

class Case(BaseModel):
    id: str
    name: str
    price: int
    items: List[CaseItem]

class UserInventory(BaseModel):
    user_id: int
    items: List[Dict]

# База данных (в памяти, в реальном проекте используйте БД)
cases_db = [
    Case(
        id="basic_case",
        name="Обычный кейс",
        price=100,
        items=[
            CaseItem(name="Glock-18 | Groundwater", rarity="common", chance=0.5),
            CaseItem(name="USP-S | Forest Leaves", rarity="common", chance=0.3),
            CaseItem(name="P250 | Sand Dune", rarity="common", chance=0.15),
            CaseItem(name="Desert Eagle | Midnight Storm", rarity="rare", chance=0.04),
            CaseItem(name="AWP | Lightning Strike", rarity="legendary", chance=0.01)
        ]
    )
]

# "База данных" пользователей и инвентаря
users_db = {}
inventory_db = {}

# Функция для открытия кейса
def open_case(case_id: str) -> Dict:
    case = next((c for c in cases_db if c.id == case_id), None)
    if not case:
        return None
    
    rand = random.random()
    cumulative = 0.0
    
    for item in case.items:
        cumulative += item.chance
        if rand <= cumulative:
            return {
                "id": str(uuid.uuid4()),
                "name": item.name,
                "rarity": item.rarity,
                "unboxed_at": "now"  # В реальном приложении используйте datetime
            }
    
    return case.items[0].dict()  # fallback

# API endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/api/cases")
async def get_cases():
    return [case.dict() for case in cases_db]

@app.post("/api/open_case")
async def open_case_endpoint(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    case_id = data.get("case_id")
    
    if not user_id or not case_id:
        return JSONResponse({"error": "Missing parameters"}, status_code=400)
    
    # Проверяем, есть ли у пользователя достаточно денег
    user = users_db.get(user_id, {"balance": 1000})  # По умолчанию баланс 1000
    
    case = next((c for c in cases_db if c.id == case_id), None)
    if not case:
        return JSONResponse({"error": "Case not found"}, status_code=404)
    
    if user["balance"] < case.price:
        return JSONResponse({"error": "Not enough balance"}, status_code=400)
    
    # Открываем кейс
    item = open_case(case_id)
    if not item:
        return JSONResponse({"error": "Failed to open case"}, status_code=500)
    
    # Обновляем баланс пользователя
    user["balance"] -= case.price
    users_db[user_id] = user
    
    # Добавляем предмет в инвентарь
    if user_id not in inventory_db:
        inventory_db[user_id] = []
    inventory_db[user_id].append(item)
    
    return JSONResponse({
        "success": True,
        "item": item,
        "new_balance": user["balance"]
    })

@app.get("/api/inventory/{user_id}")
async def get_inventory(user_id: int):
    return JSONResponse({
        "items": inventory_db.get(user_id, [])
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)