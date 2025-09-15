import time
from arbitrage.config import PAIR_TIMEOUT_SEC, PAIR_POLL_INTERVAL, DRY_RUN
from arbitrage.exchanges.exec_binance_rest import (
    get_spot_order_status, get_coinm_order_status,
    place_spot_market, place_coinm_market
)

def monitor_and_rescue_single_leg(side: str, spot_order: dict, cm_order: dict,
                                  expect_Q: float, expect_N: int,
                                  timeout_sec: float = PAIR_TIMEOUT_SEC,
                                  poll_interval: float = PAIR_POLL_INTERVAL):
    if DRY_RUN:
        print("[DRY] 单腿监控跳过")
        return

    soid = spot_order.get("orderId")
    coid = cm_order.get("orderId")
    if not soid or not coid:
        print("⚠ 订单ID缺失，跳过监控");  return

    deadline = time.time() + timeout_sec
    spot_filled = cm_filled = 0.0

    while time.time() < deadline:
        _, s_exec = get_spot_order_status(soid)
        _, c_exec = get_coinm_order_status(coid)
        spot_filled = max(spot_filled, s_exec)
        cm_filled   = max(cm_filled,   c_exec)
        if (spot_filled > 0.0) and (cm_filled > 0.0):
            return
        time.sleep(poll_interval)

    # 超时：单腿处理
    if (spot_filled > 0.0) and (cm_filled == 0.0):
        qty = spot_filled if spot_filled > 0 else expect_Q
        print(f"‼ 单腿：仅现货成交 {qty:.6f} BTC → 市价平掉")
        place_spot_market("SELL" if side=="POS" else "BUY", qty)
    elif (cm_filled > 0.0) and (spot_filled == 0.0):
        n = int(cm_filled if cm_filled > 0 else expect_N)
        print(f"‼ 单腿：仅合约成交 {n} 张 → reduceOnly 市价平掉")
        if side == "POS":
            place_coinm_market("BUY",  n, reduce_only=True)
        else:
            place_coinm_market("SELL", n, reduce_only=True)
