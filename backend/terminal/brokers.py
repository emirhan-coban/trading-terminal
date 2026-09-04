from abc import ABC,abstractmethod
from dataclasses import dataclass
from .models import PaperOrderIn,Quote
@dataclass(frozen=True)
class BrokerCapabilities:
 market:bool;limit:bool;stop:bool;stop_limit:bool;bracket:bool;oco:bool;partial_fills:bool;live_money:bool
class BrokerAdapter(ABC):
 name:str;capabilities:BrokerCapabilities
 @abstractmethod
 async def submit(self,user_id:str,order:PaperOrderIn,quote:Quote):...
 @abstractmethod
 async def cancel(self,user_id:str,order_id:str):...
 @abstractmethod
 async def positions(self,user_id:str):...
class LiveBrokerDisabled(BrokerAdapter):
 name="live-disabled";capabilities=BrokerCapabilities(False,False,False,False,False,False,False,False)
 async def submit(self,user_id,order,quote):raise PermissionError("LIVE_TRADING_DISABLED")
 async def cancel(self,user_id,order_id):raise PermissionError("LIVE_TRADING_DISABLED")
 async def positions(self,user_id):return []
live_broker=LiveBrokerDisabled()
