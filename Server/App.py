import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

from Server.AppCore import AppCore, Position
from Server.ServiceManager.MicroserviceManager import Microservice

app = FastAPI()

# CORS for development (React dev server on 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/bot1api/positions", response_model=List[Position])
def get_positions():
    return app_core.get_positions()


class PositionPayLoad(BaseModel):
    symbol: str
    size: float

@app.post("/bot1api/positions/open")
def update_position_status(payload: PositionPayLoad):
    result, e = app_core.open_position(payload.symbol, payload.size)
    if not result:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Position on {payload.symbol} opened"}


@app.post("/bot1api/positions/estimate")
def estimate_position_status(payload: PositionPayLoad):
    result, e = app_core.estimate_position(payload.symbol, payload.size)
    if not result:
        raise HTTPException(status_code=400, detail=str(e))
    return e


if __name__ == "__main__":
    uvicorn.run("App:app", host="127.0.0.1", port=8000, reload=True)