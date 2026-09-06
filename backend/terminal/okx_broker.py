from __future__ import annotations

import asyncio,base64,hashlib,hmac,json,os
from decimal import Decimal,ROUND_DOWN
from datetime import datetime,timezone
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from uuid import uuid4

from .brokers import BrokerAdapter,BrokerCapabilities


class OkxHTTPError(RuntimeError):
    def __init__(self,status,message):
        self.status=status
        super().__init__(f"OKX_HTTP_{status}:{message}")


class OkxDemoBroker(BrokerAdapter):
    """OKX spot demo adapter. It cannot be switched to real-money mode."""

    name="okx-demo"
    capabilities=BrokerCapabilities(True,True,False,False,False,False,True,False)
    default_base="https://openapi.okx.com"
    allowed_bases={
        "https://openapi.okx.com",
        "https://www.okx.com",
        "https://tr.okx.com",
        "https://eea.okx.com",
        "https://us.okx.com",
    }

    def __init__(self,api_key=None,secret=None,passphrase=None,base_url=None):
        self.api_key=api_key or os.getenv("OKX_API_KEY","")
        self.secret=secret or os.getenv("OKX_API_SECRET","")
        self.passphrase=passphrase or os.getenv("OKX_API_PASSPHRASE","")
        self.base=(base_url or os.getenv("OKX_API_BASE_URL") or self.default_base).rstrip("/")
        if self.base not in self.allowed_bases:raise ValueError("OKX_API_BASE_URL_NOT_ALLOWED")

    @property
    def configured(self):return bool(self.api_key and self.secret and self.passphrase)

    def _request(self,method,path,body=None):
        if not self.configured:raise RuntimeError("OKX_DEMO_NOT_CONFIGURED")
        stamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
        raw=json.dumps(body,separators=(",",":")) if body is not None else ""
        signature=base64.b64encode(hmac.new(self.secret.encode(),f"{stamp}{method}{path}{raw}".encode(),hashlib.sha256).digest()).decode()
        headers={"Content-Type":"application/json","OK-ACCESS-KEY":self.api_key,"OK-ACCESS-SIGN":signature,"OK-ACCESS-TIMESTAMP":stamp,"OK-ACCESS-PASSPHRASE":self.passphrase,"x-simulated-trading":"1"}
        try:
            with urlopen(Request(self.base+path,data=raw.encode() if raw else None,headers=headers,method=method),timeout=10) as response:payload=json.loads(response.read())
        except HTTPError as error:
            raw_error=error.read().decode("utf-8","replace")[:500]
            try:
                error_payload=json.loads(raw_error)
                message=error_payload.get("msg") or error_payload.get("message") or "request rejected"
            except (json.JSONDecodeError,AttributeError):
                message=raw_error.strip() or "request rejected"
            raise OkxHTTPError(error.code,message) from error
        except URLError as error:
            raise RuntimeError(f"OKX_CONNECTION_ERROR:{error.reason}") from error
        if str(payload.get("code","0"))!="0":raise RuntimeError(f"OKX_{payload.get('code')}:{payload.get('msg','request failed')}")
        return payload.get("data",[])

    def _public_request(self,path):
        with urlopen(Request(self.base+path,headers={"User-Agent":"NEXUS/1.0","x-simulated-trading":"1"}),timeout=10) as response:payload=json.loads(response.read())
        if str(payload.get("code","0"))!="0":raise RuntimeError(f"OKX_{payload.get('code')}:{payload.get('msg','request failed')}")
        return payload.get("data",[])

    async def instrument_rules(self,inst_id):
        rows=await asyncio.to_thread(self._public_request,f"/api/v5/public/instruments?instType=SPOT&instId={inst_id}")
        if not rows or rows[0].get("state")!="live":raise RuntimeError("OKX_INSTRUMENT_NOT_LIVE")
        return {"lot_size":Decimal(rows[0]["lotSz"]),"min_size":Decimal(rows[0]["minSz"]),"tick_size":Decimal(rows[0]["tickSz"])}

    async def normalize_size(self,inst_id,quantity):
        rules=await self.instrument_rules(inst_id);value=Decimal(str(quantity));steps=(value/rules["lot_size"]).to_integral_value(rounding=ROUND_DOWN);size=steps*rules["lot_size"]
        if size<rules["min_size"]:raise RuntimeError("OKX_SIZE_BELOW_MINIMUM")
        return format(size,"f")

    async def normalize_price(self,inst_id,price):
        rules=await self.instrument_rules(inst_id);value=Decimal(str(price));steps=(value/rules["tick_size"]).to_integral_value(rounding=ROUND_DOWN)
        return format(steps*rules["tick_size"],"f")

    async def submit(self,user_id,order,quote=None,client_order_id=None):
        inst_id=order.instrument_id.rsplit(":",1)[-1].upper()
        client_order_id=client_order_id or f"nx{uuid4().hex[:24]}"
        size=await self.normalize_size(inst_id,order.quantity)
        payload={"instId":inst_id,"tdMode":"cash","clOrdId":client_order_id,"side":order.side,"ordType":order.order_type,"sz":size}
        if order.order_type=="market":payload["tgtCcy"]="base_ccy"
        if order.order_type=="limit":payload["px"]=str(order.limit_price)
        if order.order_type not in {"market","limit"}:raise ValueError("OKX demo adapter supports market and limit orders")
        try:rows=await asyncio.to_thread(self._request,"POST","/api/v5/trade/order",payload)
        except OkxHTTPError as error:
            if 400<=error.status<500:raise
            recovered=await asyncio.to_thread(self._request,"GET",f"/api/v5/trade/order?instId={inst_id}&clOrdId={client_order_id}")
            if not recovered:raise
            rows=[{"ordId":recovered[0].get("ordId"),"clOrdId":client_order_id,"sCode":"0","sMsg":""}]
        except (RuntimeError,TimeoutError):
            recovered=await asyncio.to_thread(self._request,"GET",f"/api/v5/trade/order?instId={inst_id}&clOrdId={client_order_id}")
            if not recovered:raise
            rows=[{"ordId":recovered[0].get("ordId"),"clOrdId":client_order_id,"sCode":"0","sMsg":""}]
        if not rows:raise RuntimeError("OKX_EMPTY_ORDER_RESPONSE")
        row=rows[0]
        if str(row.get("sCode","0"))!="0":raise RuntimeError(f"OKX_{row.get('sCode')}:{row.get('sMsg','order rejected')}")
        result={"broker":"okx-demo","order_id":row.get("ordId"),"client_order_id":row.get("clOrdId"),"status":"submitted"}
        for _ in range(10):
            await asyncio.sleep(.5)
            details=await asyncio.to_thread(self._request,"GET",f"/api/v5/trade/order?instId={inst_id}&ordId={row.get('ordId')}")
            if details:
                result.update({"status":details[0].get("state"),"filled_quantity":float(details[0].get("accFillSz") or 0),"fill_price":float(details[0].get("avgPx") or 0)})
                if result["status"] in {"filled","canceled"}:break
        return result

    async def place_stop(self,inst_id,quantity,trigger_price,client_order_id):
        size=await self.normalize_size(inst_id,quantity);trigger=await self.normalize_price(inst_id,trigger_price)
        rows=await asyncio.to_thread(self._request,"POST","/api/v5/trade/order-algo",{"instId":inst_id,"tdMode":"cash","side":"sell","ordType":"trigger","sz":size,"triggerPx":trigger,"triggerPxType":"last","orderPx":"-1","algoClOrdId":client_order_id})
        if not rows or str(rows[0].get("sCode","0"))!="0":raise RuntimeError(f"OKX_STOP_REJECTED:{rows[0].get('sMsg') if rows else 'empty response'}")
        return {"algo_id":rows[0].get("algoId"),"client_order_id":client_order_id}

    async def cancel_stop(self,inst_id,algo_id):
        if not algo_id:return []
        return await asyncio.to_thread(self._request,"POST","/api/v5/trade/cancel-algos",[{"instId":inst_id,"algoId":algo_id}])

    async def balances(self,currencies=("USDT","BTC","ETH")):
        rows=await asyncio.to_thread(self._request,"GET",f"/api/v5/account/balance?ccy={','.join(currencies)}")
        details=rows[0].get("details",[]) if rows else []
        return {x["ccy"]:float(x.get("cashBal") or 0) for x in details}

    async def cancel(self,user_id,order_id):
        inst_id,_,broker_id=order_id.partition("|")
        return await asyncio.to_thread(self._request,"POST","/api/v5/trade/cancel-order",{"instId":inst_id,"ordId":broker_id})

    async def positions(self,user_id):
        return await asyncio.to_thread(self._request,"GET","/api/v5/account/balance")


okx_demo_broker=OkxDemoBroker()
