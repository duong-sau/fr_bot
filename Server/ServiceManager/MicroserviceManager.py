import json
import uuid
from enum import Enum
import subprocess
from Define import server_config_path
from pydantic import BaseModel, Field


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

    def get_model(self):
        return self.model

    def ping(self):
        raise NotImplementedError("gRPC microservice is no longer supported.")

    def start(self):
        raise NotImplementedError("gRPC microservice is no longer supported.")

    def stop(self):
        raise NotImplementedError("gRPC microservice is no longer supported.")


class ADLDockerController(MicroserviceController):
    def ping(self):
        try:
            result = subprocess.run([
                "docker", "inspect", "-f", "{{.State.Running}}", "adlcontrol_container"
            ], capture_output=True, text=True)
            running = result.stdout.strip() == "true"
            self.model.status = SERVICE_STATUS.RUNNING.value if running else SERVICE_STATUS.STOPPED.value
            return {"running": running}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def start(self):
        try:
            result = subprocess.run([
                "docker", "inspect", "adlcontrol_container"
            ], capture_output=True, text=True)
            need_create = False
            if result.returncode == 0:
                mounts = subprocess.run([
                    "docker", "inspect", "-f", "{{range .Mounts}}{{println .Destination}}{{end}}", "adlcontrol_container"
                ], capture_output=True, text=True)
                destinations = mounts.stdout.strip().splitlines()
                if "/app/logs" not in destinations and "/home/ubuntu/fr_bot/logs" not in destinations:
                    # Recreate with volume
                    subprocess.run(["docker", "stop", "adlcontrol_container"], check=False)
                    subprocess.run(["docker", "rm", "adlcontrol_container"], check=True)
                    need_create = True
            else:
                need_create = True

            if need_create:
                subprocess.run([
                    "docker", "create",
                    "--name", "adlcontrol_container",
                    "-v", "frbot_logs:/app/logs",
                    "-v", "frbot_logs:/home/ubuntu/fr_bot/logs",
                    "adlprocess"
                ], check=True)
            subprocess.run(["docker", "start", "adlcontrol_container"], check=True)
            self.model.status = SERVICE_STATUS.RUNNING.value
            return {"success": True}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def stop(self):
        try:
            subprocess.run(["docker", "stop", "adlcontrol_container"], check=True)
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}


class AssetDockerController(MicroserviceController):
    def ping(self):
        try:
            result = subprocess.run([
                "docker", "inspect", "-f", "{{.State.Running}}", "assetcontrol_container"
            ], capture_output=True, text=True)
            running = result.stdout.strip() == "true"
            self.model.status = SERVICE_STATUS.RUNNING.value if running else SERVICE_STATUS.STOPPED.value
            return {"running": running}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def start(self):
        try:
            result = subprocess.run([
                "docker", "inspect", "assetcontrol_container"
            ], capture_output=True, text=True)
            need_create = False
            if result.returncode == 0:
                mounts = subprocess.run([
                    "docker", "inspect", "-f", "{{range .Mounts}}{{println .Destination}}{{end}}", "assetcontrol_container"
                ], capture_output=True, text=True)
                destinations = mounts.stdout.strip().splitlines()
                if "/app/logs" not in destinations and "/home/ubuntu/fr_bot/logs" not in destinations:
                    subprocess.run(["docker", "stop", "assetcontrol_container"], check=False)
                    subprocess.run(["docker", "rm", "assetcontrol_container"], check=True)
                    need_create = True
            else:
                need_create = True

            if need_create:
                subprocess.run([
                    "docker", "create",
                    "--name", "assetcontrol_container",
                    "-v", "frbot_logs:/app/logs",
                    "-v", "frbot_logs:/home/ubuntu/fr_bot/logs",
                    "assetprocess"
                ], check=True)
            subprocess.run(["docker", "start", "assetcontrol_container"], check=True)
            self.model.status = SERVICE_STATUS.RUNNING.value
            return {"success": True}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def stop(self):
        try:
            subprocess.run(["docker", "stop", "assetcontrol_container"], check=True)
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}


class DiscordDockerController(MicroserviceController):
    def ping(self):
        try:
            result = subprocess.run([
                "docker", "inspect", "-f", "{{.State.Running}}", "discord_shared_container"
            ], capture_output=True, text=True)
            running = result.stdout.strip() == "true"
            self.model.status = SERVICE_STATUS.RUNNING.value if running else SERVICE_STATUS.STOPPED.value
            return {"running": running}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def start(self):
        try:
            subprocess.run(["docker", "start", "discord_shared_container"], check=True)
            self.model.status = SERVICE_STATUS.RUNNING.value
            return {"success": True}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def stop(self):
        try:
            subprocess.run(["docker", "stop", "discord_shared_container"], check=True)
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}


class MicroserviceManager:
    def __init__(self):
        self.microservices = []
        self.init_microservice()

    def init_microservice(self):
        with open(server_config_path, "r") as f:
            config = json.load(f)
        for ms in config.get("microservices", []):
            name = ms["name"].lower()
            if name == "adlcontrol":
                self.microservices.append(ADLDockerController(host=ms["host"], name=ms["name"]))
            elif name == "assetcontrol":
                self.microservices.append(AssetDockerController(host=ms["host"], name=ms["name"]))
            elif name == "discord":
                self.microservices.append(DiscordDockerController(host=ms["host"], name=ms["name"]))
            else:
                raise ValueError(f"Unknown microservice name: {name}")

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
