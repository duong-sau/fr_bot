import threading
import time

from pydantic import BaseModel

from Server.PositionCreator.PositionCreator import PositionCreator
from Server.ServiceManager.MicroserviceManager import MicroserviceManager
from Server.PositionView.PositionView import PositionView



class Position(BaseModel):
    symbol: str
    amount: float
    entry: float
    unrealpnl: float
    funding1: float
    funding2: float
    exchange1: str = "Bitget"
    exchange2: str = "Gate.io"

class AppCore:
    def __init__(self):
        self.microservice_manager = MicroserviceManager()
        self.position_manager = PositionView()
        self.position_creator = PositionCreator()
        self.run()

    def get_microservices(self):
        services =  self.microservice_manager.get_microservices()
        return [ms.get_model() for ms in services]

    def start_microservice(self, service_id):
        return self.microservice_manager.start_microservice(service_id)

    def stop_microservice(self, service_id):
        return self.microservice_manager.stop_microservice(service_id)

    def main_loop(self):
        while True:
            for microservice in self.microservice_manager.get_microservices():
                microservice.ping()
            time.sleep(5)

    def run(self):
        main_thread = threading.Thread(target=self.main_loop)
        main_thread.start()

    def get_positions(self):
        self.position_manager.refresh()
        self.position_manager.refresh_unreal_pnl()
        position =  self.position_manager.get_core_positions()
        result = []
        for pos in position:
            result.append(Position(
                symbol=pos.long_position.symbol,
                amount=pos.long_position.amount_,
                entry=round(float(pos.long_position.entry_price), 2),
                unrealpnl=pos.unreal_pnl,
                funding1=round(float(pos.long_position.funding_fee), 2),
                funding2=round(float(pos.short_position.funding_fee), 2),
                exchange1=pos.long_position.exchange,
                exchange2=pos.short_position.exchange,
            ))

        return result

    def open_position(self, symbol, size):
        symbol = symbol + "/USDT:USDT"
        result, e = self.estimate_position(symbol, size)
        if not result:
            print("Cannot open position:", symbol)
            return False, e
        self.position_creator.open_position(symbol, e)
        return True, e

    def estimate_position(self, symbol, size):
        symbol = symbol + "/USDT:USDT"
        return self.position_creator.estimate_position(symbol, size)
