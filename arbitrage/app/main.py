import time
import requests

from arbitrage.config import (
    RUN_SECONDS, POLL_INTERVAL, MAX_BOOK_SKEW_MS,
    SPOT_SYMBOL, COINM_SYMBOL
)
from arbitrage.exchanges.md_binance_rest import (
    get_spot_depth_with_ts, get_coinm_depth_with_ts, get_coinm_mark
)
from arbitrage.exchanges.rules import fetch_spot_rules, fetch_coinm_rules
from arbitrage.strategy.logic import (
    try_enter_from_frontier, try_enter, need_exit, do_exit,
    print_levels_if_needed
)
from arbitrage.config import (
    AUTO_FROM_FRONTIER, PRINT_LEVELS, LEVELS_TO_PRINT, ENTER_BPS
)

def main():
    spot_tick, spot_step = fetch_spot_rules(SPOT_SYMBOL)
    contract_size, cm_tick, cm_step = fetch_coinm_rules(COINM_SYMBOL)

    position = None
    t0 = time.time()
    placed_any = False

    while time.time() - t0 < RUN_SECONDS:
        try:
            spot_bids, spot_asks, t_spot = get_spot_depth_with_ts(limit=100)
            cm_bids,   cm_asks,   t_cm   = get_coinm_depth_with_ts(limit=100)

            if not (spot_bids and spot_asks and cm_bids and cm_asks):
                print("簿为空，等待..."); time.sleep(POLL_INTERVAL); continue

            skew_ms = abs(t_cm - t_spot) * 1000.0
            if skew_ms > MAX_BOOK_SKEW_MS:
                print(f"⏱️ 簿时间差 {skew_ms:.0f}ms > {MAX_BOOK_SKEW_MS}ms，丢弃本次信号")
                time.sleep(POLL_INTERVAL); continue

            spot_mid  = (spot_bids[0][0] + spot_asks[0][0]) / 2.0
            perp_mark = get_coinm_mark()
            spread_bps = (perp_mark - spot_mid) / spot_mid * 10000.0
            print(f"spread={spread_bps:.2f}bp | spot_mid={spot_mid:.2f} mark={perp_mark:.2f} | pos={None if not position else position['side']}")

            # 可选打印“逐档评估”
            print_levels_if_needed(
                PRINT_LEVELS, position, AUTO_FROM_FRONTIER,
                spot_bids, spot_asks, cm_bids, cm_asks, contract_size, LEVELS_TO_PRINT
            )

            if position is None:
                if AUTO_FROM_FRONTIER:
                    done, position = try_enter_from_frontier(
                        spot_bids, spot_asks, cm_bids, cm_asks,
                        contract_size, spot_step, cm_step
                    )
                else:
                    done, position = try_enter(
                        spread_bps, spot_mid,
                        spot_bids, spot_asks, cm_bids, cm_asks,
                        contract_size, spot_step, cm_step
                    )
                placed_any = placed_any or done
            else:
                should, reason = need_exit(spread_bps, position)
                if should:
                    print(f"平仓理由：{reason}")
                    do_exit(position)
                    position = None

            time.sleep(POLL_INTERVAL)

        except requests.HTTPError as e:
            print("HTTPError:", e.response.text); time.sleep(1.2)
        except Exception as e:
            print("Error:", e); time.sleep(1.0)

    print("== 结束 ==")
    print("是否曾下过单：", placed_any)

if __name__ == "__main__":
    main()
