from arbitrage.config import SPOT_SYMBOL, COINM_SYMBOL
from arbitrage.exchanges.binance_rest import spot_get, dapi_get

def get_spot_depth(limit=100):
    d = spot_get("/api/v3/depth", {"symbol": SPOT_SYMBOL, "limit": limit})
    bids = [(float(p), float(q)) for p,q in d["bids"]]
    asks = [(float(p), float(q)) for p,q in d["asks"]]
    return bids, asks

def get_coinm_depth(limit=100):
    d = dapi_get("/dapi/v1/depth", {"symbol": COINM_SYMBOL, "limit": limit})
    bids = [(float(p), float(q)) for p,q in d["bids"]]
    asks = [(float(p), float(q)) for p,q in d["asks"]]
    return bids, asks

def get_coinm_mark():
    rows = dapi_get("/dapi/v1/premiumIndex", {"symbol": COINM_SYMBOL})
    if isinstance(rows, list):
        for it in rows:
            if it.get("symbol") == COINM_SYMBOL:
                return float(it["markPrice"])
    else:
        if rows.get("symbol") == COINM_SYMBOL:
            return float(rows["markPrice"])
    raise RuntimeError("premiumIndex: symbol not found")

def get_coinm_funding():
    rows = dapi_get("/dapi/v1/premiumIndex", {"symbol": COINM_SYMBOL})
    if isinstance(rows, list):
        for it in rows:
            if it.get("symbol") == COINM_SYMBOL:
                fr = float(it.get("lastFundingRate", 0.0) or 0.0) * 10000.0
                nxt = it.get("nextFundingTime")
                nxt = int(nxt) if nxt not in (None, "") else None
                return fr, nxt
    else:
        if rows.get("symbol") == COINM_SYMBOL:
            fr = float(rows.get("lastFundingRate", 0.0) or 0.0) * 10000.0
            nxt = rows.get("nextFundingTime")
            nxt = int(nxt) if nxt not in (None, "") else None
            return fr, nxt
    return 0.0, None

# with timestamp
import time
def get_spot_depth_with_ts(limit=100):
    t0 = time.time()
    bids, asks = get_spot_depth(limit)
    return bids, asks, t0

def get_coinm_depth_with_ts(limit=100):
    t0 = time.time()
    bids, asks = get_coinm_depth(limit)
    return bids, asks, t0
