from concurrent import futures
import grpc
import microservices_pb2
import microservices_pb2_grpc
from MainProcess.Controller import BotController

log_file = "~/fr_bot/logs/syslog.txt"
status_file = "~/fr_bot/data/status.json"

class GRPCServicer(microservices_pb2_grpc.MicroserviceControllerServicer):
    def __init__(self):
        self.controller = BotController(log_file=log_file, status_file=status_file)

    def Ping(self, request, context):
        print(f"Received ping from {request.client_id}")
        dt = self.controller.get_status()
        return microservices_pb2.PingResponse(data=dt)


    def StartService(self, request, context):
        print(f"Received start command for {request.client_id}")
        self.controller.start_bot()
        return microservices_pb2.Result(success=True)

    def StopService(self, request, context):
        print(f"Received stop command for {request.client_id}")
        # Logic stop bot
        self.controller.stop_bot()
        return microservices_pb2.Result(success=True)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=11))
    microservices_pb2_grpc.add_MicroserviceControllerServicer_to_server(GRPCServicer(), server)
    server.add_insecure_port('[::]:4953')
    server.start()
    print("🚀 gRPC server started on port 4953")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
