import json
import uuid
from enum import Enum

import grpc
from pydantic import BaseModel, Field

import microservices_pb2
import microservices_pb2_grpc
from Define import server_config_path


class Microservice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: str  # "start" or "stop"

class SERVICE_STATUS(Enum):
    RUNNING = "running"
    STOPPED = "stopped"


class MicroserviceController:
    def __init__(self, host, name):
        self.host = host
        self.model = Microservice(name=name, status=SERVICE_STATUS.STOPPED.value)
        self.channel = grpc.insecure_channel(f"{self.host}")
        self.stub = microservices_pb2_grpc.MicroserviceControllerStub(self.channel)

    def get_model(self):
        return self.model

    def ping(self):
        try:
            response = self.stub.Ping(microservices_pb2.PingMessage(client_id=self.model.id))
            dt = response.data
            print(dt)
            if dt['status'] == 'alive':
                self.model.status = SERVICE_STATUS.RUNNING.value
            else:
                self.model.status = SERVICE_STATUS.STOPPED.value
            return {"success": True}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def start(self):
        try:
            response = self.stub.StartService(microservices_pb2.StartAndStopCommand(client_id=self.model.id))
            print(response.data)
            return {"success": True}
        except Exception as e:
            return {"error": str(e), "started": False}

    def stop(self):
        try:
            response = self.stub.StopService(microservices_pb2.StartAndStopCommand(client_id=self.model.id))
            print(response.data)
            return {"success": True}
        except Exception as e:
            return {"error": str(e), "stopped": False}


class MicroserviceManager:
    def __init__(self):
        self.microservices = []
        self.init_microservice()

    def init_microservice(self):

        with open(server_config_path, "r") as f:
            config = json.load(f)
        for ms in config.get("microservices", []):
            self.microservices.append(MicroserviceController(host=ms["host"], name=ms["name"]))


    def get_microservices(self):
        return self.microservices

    def start_microservice(self, service_id):
        for ms in self.microservices:
            if ms.get_model().id == service_id:
                ms.start()
                return True
        return False
    def stop_microservice(self, service_id):
        for ms in self.microservices:
            if ms.get_model().id == service_id:
                ms.stop()
                return True
        return False
