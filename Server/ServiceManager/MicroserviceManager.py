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


# Common constants for mounts
HOST_LOGS = "/home/ubuntu/fr_bot/logs"
HOST_SETTINGS = "/home/ubuntu/fr_bot/code/_settings"
IN_CONTAINER_LOGS_NEW = "/home/ubuntu/fr_bot/logs"
IN_CONTAINER_LOGS_OLD = "/app/logs"
IN_CONTAINER_SETTINGS_NEW = "/home/ubuntu/fr_bot/code/_settings"


class DockerController(MicroserviceController):
    """Quản lý một container Docker (create/start/stop/ping) qua Docker CLI.

    Dùng chung cho ADLControl, AssetControl và Discord relay — trước đây là 3 class
    gần như giống hệt nhau, chỉ khác container_name/image_name (và Discord cần tự
    build image nếu chưa có, xử lý qua `build_image`).
    """

    def __init__(self, host, name, container_name, image_name, build_image=None):
        super().__init__(host, name)
        self.container_name = container_name
        self.image_name = image_name
        self.build_image = build_image  # optional callable() -> {"error": ...} hoặc None nếu OK

    def ping(self):
        try:
            result = subprocess.run([
                "docker", "inspect", "-f", "{{.State.Running}}", self.container_name
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
                "docker", "inspect", self.container_name
            ], capture_output=True, text=True)
            need_create = False
            if result.returncode == 0:
                mounts = subprocess.run([
                    "docker", "inspect", "-f", "{{range .Mounts}}{{println .Destination}}{{end}}", self.container_name
                ], capture_output=True, text=True)
                destinations = mounts.stdout.strip().splitlines()
                has_logs = (IN_CONTAINER_LOGS_OLD in destinations) or (IN_CONTAINER_LOGS_NEW in destinations)
                has_settings = (IN_CONTAINER_SETTINGS_NEW in destinations)
                if not (has_logs and has_settings):
                    subprocess.run(["docker", "stop", self.container_name], check=False)
                    subprocess.run(["docker", "rm", self.container_name], check=True)
                    need_create = True
            else:
                need_create = True

            if need_create:
                if self.build_image is not None:
                    error = self.build_image()
                    if error is not None:
                        self.model.status = SERVICE_STATUS.STOPPED.value
                        return error

                create = subprocess.run([
                    "docker", "create",
                    "--name", self.container_name,
                    "-v", f"{HOST_LOGS}:{IN_CONTAINER_LOGS_NEW}",
                    "-v", f"{HOST_LOGS}:{IN_CONTAINER_LOGS_OLD}",
                    "-v", f"{HOST_SETTINGS}:{IN_CONTAINER_SETTINGS_NEW}",
                    self.image_name
                ], capture_output=True, text=True)
                if create.returncode != 0:
                    self.model.status = SERVICE_STATUS.STOPPED.value
                    return {"error": f"Failed to create container: {create.stderr}"}

            subprocess.run(["docker", "start", self.container_name], check=True)
            self.model.status = SERVICE_STATUS.RUNNING.value
            return {"success": True}
        except Exception as e:
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"error": str(e)}

    def stop(self):
        try:
            subprocess.run(["docker", "stop", self.container_name], check=True)
            self.model.status = SERVICE_STATUS.STOPPED.value
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}


def _build_discord_image_if_missing():
    img = subprocess.run(["docker", "images", "-q", "discord_shared_image"], capture_output=True, text=True)
    if img.returncode != 0 or not img.stdout.strip():
        build = subprocess.run(
            ["docker", "build", "-f", "Notification/Dockerfile", "-t", "discord_shared_image", "."],
            capture_output=True, text=True,
        )
        if build.returncode != 0:
            return {"error": f"Failed to build discord image: {build.stderr}"}
    return None


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
                self.microservices.append(DockerController(
                    host=ms["host"], name=ms["name"],
                    container_name="adlcontrol_container", image_name="adlprocess",
                ))
            elif name == "assetcontrol":
                self.microservices.append(DockerController(
                    host=ms["host"], name=ms["name"],
                    container_name="assetcontrol_container", image_name="assetprocess",
                ))
            elif name == "discord":
                self.microservices.append(DockerController(
                    host=ms["host"], name=ms["name"],
                    container_name="discord_shared_container", image_name="discord_shared_image",
                    build_image=_build_discord_image_if_missing,
                ))
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
