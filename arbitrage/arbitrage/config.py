import os

# —— 运行参数 ——
# config.py
DRY_RUN = True  # 先设成 True，保证不会下真实单

RUN_SECONDS = 60
POLL_INTERVAL = 0.6

# —— 风控阈值 ——
MAX_BOOK_SKEW_MS = 500
PAIR_TIMEOUT_SEC = 2.0
PAIR_POLL_INTERVAL = 0.2

# —— 入场策略 ——
AUTO_FROM_FRONTIER = True
MIN_V_USD = 5_000
EXECUTION_MODE = "taker"  # "taker" or "maker"

ENTER_BPS = 6.0
EXIT_BPS  = 2.0
STOP_BPS  = 12.0
MAX_HOLD_SEC = 30

V_USD = 10_000
MAX_SLIPPAGE_BPS_SPOT  = 1.0
MAX_SLIPPAGE_BPS_COINM = 2.0

ONLY_POSITIVE_CARRY = False
MAX_Q_BTC_FRONTIER = 0.5

# —— 资金费与保证金 ——
ENABLE_FUNDING_INFO = True
FUNDING_GAMMA = 0.8
FUNDING_BUFFER_SEC = 20

ENABLE_CM_RISK_CHECK = True
LIQ_DIST_MIN_PCT = 0.03
MARGIN_RATIO_MAX = 0.70

# —— 打印逐档 ——
PRINT_LEVELS = True
LEVELS_TO_PRINT = 5

# —— 交易对象 & 端点 ——（支持多币对：PAIR 推导，可由环境变量覆盖）
PAIR = os.environ.get("PAIR", "BTC").upper()
SPOT_SYMBOL  = os.environ.get("SPOT_SYMBOL",  f"{PAIR}USDT")
COINM_SYMBOL = os.environ.get("COINM_SYMBOL", f"{PAIR}USD_PERP")

SPOT_BASE = "https://api.binance.com"
DAPI_BASE = "https://dapi.binance.com"
#SPOT_BASE = "https://testnet.binance.vision"
#DAPI_BASE = "https://testnet.binancefuture.com"

SPOT_KEY    = os.environ.get("SPOT_KEY", "")
SPOT_SECRET = os.environ.get("SPOT_SECRET", "")
DAPI_KEY    = os.environ.get("DAPI_KEY", "")
DAPI_SECRET = os.environ.get("DAPI_SECRET", "")

# —— 交易日志 ——（按币种分文件）
TRADES_CSV = os.environ.get("TRADES_CSV", f"trades_{PAIR.lower()}.csv")
