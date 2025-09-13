import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from Server.AppCore import AppCore
from Server.MicroserviceManager import Microservice

app = FastAPI()
app_core = AppCore()

@app.get("/bot1api/microservices", response_model=List[Microservice])
def get_microservices():
    return app_core.get_microservices()

class StatusUpdate(BaseModel):
    status: str  # "start" or "stop"

@app.put("/bot1api/microservices/{id}/start")
def update_microservice_status(id: str):
    if app_core.start_microservice(id):
        return {"message": f"{id} started"}
    raise HTTPException(status_code=404, detail="Microservice not found")

@app.put("/bot1api/microservices/{id}/stop")
def update_microservice_status(id: str):
    if app_core.stop_microservice(id):
        return {"message": f"{id} stopped"}
    raise HTTPException(status_code=404, detail="Microservice not found")

class Position(BaseModel):
    symbol: str
    name: str
    status: str  # "open" or "closed"

positions = [
    Position(symbol="BTCUSD", name="BTCUSD", status="closed"),
    Position(symbol="ETHUSD", name="ETHUSD", status="open"),
]
@app.get("/bot1api/positions", response_model=List[Position])
def get_positions():
    return positions

class PositionAction(BaseModel):
    action: str  # "open" or "close"

@app.post("/bot1api/positions/{symbol}")
def update_position_status(symbol: str, action: PositionAction):
    for pos in positions:
        if pos.symbol == symbol:
            if action.action not in ["open", "close"]:
                raise HTTPException(status_code=400, detail="Invalid action")
            pos.status = "open" if action.action == "open" else "closed"
            return {"message": f"Position {symbol} {action.action}ed"}
    raise HTTPException(status_code=404, detail="Position not found")

if __name__ == "__main__":
    uvicorn.run("App:app", host="127.0.0.1", port=8000, reload=True)