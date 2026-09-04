from terminal.market_stream import DepthBook,normalize_binance
def test_trade_and_kline_normalization():
 trade=normalize_binance({"data":{"e":"trade","E":1,"t":2,"p":"100.5","q":".2","m":False}},"x");assert trade["type"]=="trade" and trade["price"]==100.5
 candle=normalize_binance({"data":{"e":"kline","E":2,"k":{"i":"1m","t":1,"T":2,"o":"1","h":"2","l":".5","c":"1.5","v":"10","x":True}}},"x");assert candle["closed"] and candle["close"]==1.5
def test_depth_sequence_gap_requires_resync():
 book=DepthBook();book.snapshot({"lastUpdateId":10,"bids":[["100","1"]],"asks":[["101","1"]]});assert book.apply({"first_update_id":11,"final_update_id":12,"bids":[[100,0],[99,2]],"asks":[]})=="applied";assert book.top()["bids"][0]==(99,2);assert book.apply({"first_update_id":20,"final_update_id":21,"bids":[],"asks":[]})=="gap"
