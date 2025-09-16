import time
import requests
import argparse

from arbitrage.config import (
    RUN_SECONDS, POLL_INTERVAL, MAX_BOOK_SKEW_MS,
    SPOT_SYMBOL, COINM_SYMBOL,
    AUTO_FROM_FRONTIER, PRINT_LEVELS, LEVELS_TO_PRINT
)
from arbitrage.exchanges.md_binance_rest import (
    get_spot_depth_with_ts, get_coinm_depth_with_ts, get_coinm_mark
)
from arbitrage.exchanges.rules import fetch_spot_rules, fetch_coinm_rules
from arbitrage.strategy.logic import (
    try_enter_from_frontier, try_enter, need_exit, do_exit,
    print_levels_if_needed
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spot",  type=str, default=SPOT_SYMBOL, help="现货交易对，如 BTCUSDT / ETHUSDT")
    parser.add_argument("--coinm", type=str, default=COINM_SYMBOL, help="币本位永续，如 BTCUSD_PERP / ETHUSD_PERP")
    args = parser.parse_args()

    spot_symbol  = args.spot
    coinm_symbol = args.coinm

    spot_tick, spot_step = fetch_spot_rules(spot_symbol)
    contract_size, cm_tick, cm_step = fetch_coinm_rules(coinm_symbol)

    position = None
    t0 = time.time()
    placed_any = False

    while time.time() - t0 < RUN_SECONDS:
        try:
            spot_bids, spot_asks, t_spot = get_spot_depth_with_ts(limit=100, symbol=spot_symbol)
            cm_bids,   cm_asks,   t_cm   = get_coinm_depth_with_ts(limit=100, symbol=coinm_symbol)

            if not (spot_bids and spot_asks and cm_bids and cm_asks):
                print("簿为空，等待..."); time.sleep(POLL_INTERVAL); continue

            skew_ms = abs(t_cm - t_spot) * 1000.0
            if skew_ms > MAX_BOOK_SKEW_MS:
                print(f"⏱️ 簿时间差 {skew_ms:.0f}ms > {MAX_BOOK_SKEW_MS}ms，丢弃本次信号")
                time.sleep(POLL_INTERVAL); continue

            spot_mid  = (spot_bids[0][0] + spot_asks[0][0]) / 2.0
            perp_mark = get_coinm_mark(coinm_symbol)
            spread_bps = (perp_mark - spot_mid) / spot_mid * 10000.0
            pos_side = None if position is None else position.side
            print(f"spread={spread_bps:.2f}bp | spot_mid={spot_mid:.2f} mark={perp_mark:.2f} | pos={pos_side}")

            # 可选打印“逐档评估”
            print_levels_if_needed(
                PRINT_LEVELS, position, AUTO_FROM_FRONTIER,
                spot_bids, spot_asks, cm_bids, cm_asks, contract_size, LEVELS_TO_PRINT
            )

            if position is None:
                if AUTO_FROM_FRONTIER:
                    done, position = try_enter_from_frontier(
                        spot_bids, spot_asks, cm_bids, cm_asks,
                        contract_size, spot_step, cm_step,
                        spot_symbol, coinm_symbol
                    )
                else:
                    done, position = try_enter(
                        spread_bps, spot_mid,
                        spot_bids, spot_asks, cm_bids, cm_asks,
                        contract_size, spot_step, cm_step,
                        spot_symbol, coinm_symbol
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
