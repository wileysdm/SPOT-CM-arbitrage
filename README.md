# SPOT-CM-arbitrage
# README — BTC 现货 × 币本位永续 对冲 / 套利原型（Binance Testnet）

> **目标**：通过「现货 BTCUSDT」与「币本位永续 BTCUSD_PERP（逆向合约）」的对冲，力图让账户中的 **BTC 数量**随时间**净增加**（以 BTC 作为唯一结算口径）。  
> **场景**：**Binance 测试网（Testnet）**。  
> **特点**：逐档 **VWAP/前沿** 评估、两腿 **配对监控与救援**、**保证金风控**、**资金费（Funding）提示**、模块化接口。

---

## 1. 套利/对冲原理

### 1.1 为什么两边价格会联动？
- **同一标的**：现货 BTCUSDT 与币本位永续 BTCUSD_PERP 都在定价“比特币”。只是结算单位不同（USDT vs BTC）、形态不同（现货 vs 永续合约）。

- **资金费（Funding）的“慢回拉”**：永续无交割日，交易所通过资金费将其锚在现货指数附近：
  - 永续价 **高于** 现货 ⇒ 资金费 **为正**：多头付钱给空头，鼓励 **做空永续 / 做多现货**，把永续压回去；
  - 永续价 **低于** 现货 ⇒ 资金费 **为负**：空头付钱给多头，鼓励 **做多永续 / 做空现货**，把永续拉回去。


### 1.2 为什么还会产生价差？
即使长期联动，短时间内仍会“错位”，常见原因：
1) **撮合与延迟**：两个订单簿在不同引擎，信息传播有毫秒级延迟；单侧大单冲击时，另一侧来不及同步。
2) **流动性与库存**：杠杆偏好常令永续更受追捧而溢价；做市/套利的库存与保证金有限，无法瞬间吃光差价。
3) **资金费预期**：若市场预期未来资金费持续为正（或为负），愿意短期接受偏高（或偏低）的永续价格，形成方向性“基差”。
4) **口径差异**：信号多用 **Mark Price**（指数+保护机制），与最新成交价并非同一数；剧烈波动/强平时差异被放大。
5) **被动/非理性交易**：强平、被动减仓、资金再平衡、跟单盘，都可能短暂把一侧价格推离另一侧。

### 1.3 为何通常会回归？
> “回归”不是保证，但**机制上**存在回拉力，使价差有较高概率回到合理区间。

- **可赚套利=资金会行动**：当差价超出“手续费 + 滑点 + 资金成本”，套利者会：  
  - 永续 **偏高**：**空永续 / 多现货**（cash-and-carry）→ 卖压打低永续、买盘抬升现货 → **差价缩小**；  
  - 永续 **偏低**：反向操作，差价同样被压缩。
- **资金费的慢回拉**：若永续长期高于现货，资金费常 **为正**，空头持续 **收取** 资金费，吸引更多资金参与，促进回归；反之亦然。
- **做市库存均衡**：做市商围绕现货指数价双边报价，库存偏离会促使其调整报价到更合理位置，拉近两边价格。

### 1.4 但也可能长时间不回归（风险）
- **趋势市**：牛市里**正基差**、熊市里**负基差**可长期存在；
- **资金费“站队”**：若市场一致看涨，资金费或长期为正；做“空永续/多现货”在等待回归时需要承受资金费与价格波动；
- **约束与冲击**：保证金/库存限制、流动性骤降、强平链，会让差价先扩大再修复，甚至久不回归。

> 因此系统需要：**入场阈值（ENTER_BPS）**、**退出阈值（EXIT_BPS/STOP_BPS）**、**持仓超时（MAX_HOLD_SEC）**、**保证金与强平距离检查**等工程化保护。

### 1.5 一眼看懂的小结
- **联动**：同一标的 + 套保/做市传动带 + 资金费回拉；
- **价差**：延迟、流动性/库存、资金费预期、口径差异、被动交易；
- **回归**：套利/做市与资金费共同施力；但**不保证立刻**，需风控与退出机制配合。

## 2.与 Binance 文档的一致性（Spot + COIN-M Futures / Testnet）
## 2.1) 端点与签名
现货与交割合约均使用 Binance 官方 REST 端点；r_signed() 采用 HMAC-SHA256 对 timestamp/recvWindow 等参数签名，符合 Binance 对 TRADE/USER_DATA 安全类型的签名要求与示例流程（COIN-M 文档“SIGNED Endpoint Examples”，以及通用安全说明）。

## 2.2) 交易规则与单位
现货（Spot）：通过 /api/v3/exchangeInfo 读取 PRICE_FILTER.tickSize 与 LOT_SIZE.stepSize 并在下单前作步长取整，完全符合现货过滤器定义与通过示例（quantity%stepSize==0 等）。

COIN-M 永续（交割合约）：通过 /dapi/v1/exchangeInfo 读取 contractSize（单位：USD/张）与 baseAsset/quoteAsset（BTC/USD），下单数量以“合约张数”为口径与文档一致。代码据此在簿间用“名义USD”对齐两腿容量，符合 COIN-M 的合约面值与计价方式。

## 2.3) 行情口径与基差定义
深度：现货用 /api/v3/depth，COIN-M 用 /dapi/v1/depth，与文档的市场数据端点一致。
标记价格 & 资金费相关：用 /dapi/v1/premiumIndex 获取 markPrice/lastFundingRate/nextFundingTime；策略用标记价算 spread_bps、用结算时间做“是否跨资金费”判断，契合 Binance 将资金费、触发等逻辑锚定在 Mark Price 的做法。

## 2.4) 订单类型与参数
现货：入场/撤退时使用 LIMIT_MAKER（只做挂单，不能吃单）或 MARKET，与现货文档对 LIMIT_MAKER 的定义一致。

COIN-M：
限价单 timeInForce=GTX 用作 Post-Only（Good-Till-Crossing），与 COIN-M「Common Definition」对 GTX 的官方定义完全一致；市价单用于紧急对冲。

reduceOnly：平仓市价单显式带 reduceOnly=true，与 COIN-M POST /dapi/v1/order 的参数规范一致（文档明确 reduceOnly 为合法参数并在响应示例中返回该字段）。

## 2.5) 成交回报与手续费/资金费记账
现货成交：使用 GET /api/v3/myTrades 汇总 qty/price 做 VWAP，并依据返回中的 commission 与 commissionAsset 将手续费统一折算至 BTC 口径，这与现货账户交易列表端点的用途相符（手续费细项可结合 GET /api/v3/account/commission 获取费率配置）。

COIN-M 成交：使用 GET /dapi/v1/userTrades 汇总成交与 commission（COIN-M 手续费以标的币计，如 BTC），与期货成交列表端点功能一致。资金费与已实现盈亏采用 GET /dapi/v1/income 拉取，并仅计入 incomeType in {"FUNDING_FEE","REALIZED_PNL"}，完全符合官方给出的类型枚举。

## 2.6) 保证金与强平风控
通过 GET /dapi/v1/positionRisk 获取逐品种强平价等信息以计算“距强平比例”，并用 GET /dapi/v1/account 读取 totalMaintMargin/totalWalletBalance 评估维护保证金占比，严格对应 COIN-M 的账户/风险查询端点。

## 2.7) 下单/查询的返回与权重
下单走 POST /dapi/v1/order（COIN-M），并使用官方 newOrderRespType="RESULT" 语义；订单/成交/撤单等查询端点与权重、参数均按 Binance 文档实现

## 2.8) Testnet 与主网的等价性
代码使用 https://testnet.binance.vision（Spot）与 https://testnet.binancefuture.com（COIN-M），其 API 结构与主网一致，对应的 Testnet 文档与示例亦指向同一套接口/签名规范。

## 3. 账户与结算（BTC 唯一口径）
- **现货腿**：买入 `+Q_btc`、卖出 `−Q_btc`；手续费若以 USDT 计，按成交 VWAP 换算为 BTC 扣减。  
- **合约腿**：开/平仓手续费为 BTC；通过收益端点拉取 **Funding/Realized PnL（BTC）** 并累计。  
- **结果展示**：每笔交易结束（双腿都平）后，统计 **ΔBTC** = 现货变动 + 合约手续费/收益 + Funding。

---

## 4. 行情与规则获取（Testnet API）
- **现货深度**：`/api/v3/depth` → 价格 `USDT/BTC`、数量 `BTC`  
- **COIN‑M 深度**：`/dapi/v1/depth` → 价格 `USD/BTC`、数量 `contracts`  
- **标记价/资金费**：`/dapi/v1/premiumIndex` → `markPrice`、`lastFundingRate`、`nextFundingTime`  
- **交易所规则**：
  - 现货：`/api/v3/exchangeInfo` → `tickSize`、`stepSize`
  - COIN‑M：`/dapi/v1/exchangeInfo` → `contractSize`、`tickSize`、`stepSize`
- **错位簿防护**：比较两侧抓取的**本地时间**差，超过 `MAX_BOOK_SKEW_MS` 则丢弃该次信号。

---

## 5. 交易流程（入场/对冲/退出）

### 5.1 入场两模式
1) **前沿（逐档 VWAP）模式**（默认）：
   - 沿两侧订单簿累计 USD 容量，取**瓶颈名义** `V`；
   - 求两腿 VWAP 得 `arb_ratio / edge_usd`，过滤 `ENTER_BPS` 和 `MIN_V_USD`；
   - 触发 **现货腿上限**（`MAX_Q_BTC_FRONTIER`）时，两腿按比例缩放后按步进取整；
   - `EXECUTION_MODE` 可选 `taker/maker`。

2) **固定名义模式**：
   - 使用 `V_USD` 计算 `Q_btc / N_cntr`，在簿上模拟 VWAP 与滑点；
   - 满足 `ENTER_BPS` 和滑点阈值后（如 `MAX_SLIPPAGE_BPS_*`）执行。

### 5.2 配对监控与单腿救援（安全阀）
- 两腿下单后，在 `PAIR_TIMEOUT_SEC` 内轮询成交；若仅**一腿**成交：
  - 仅**现货**成交 → 立即**市价**反向平现货；
  - 仅**合约**成交 → 立即 **reduceOnly 市价**平合约。

### 5.3 退出条件（择一即触发）
- **回归**：`|spread_bps| ≤ EXIT_BPS`  
- **止损**：`|spread_bps| ≥ STOP_BPS`  
- **超时**：持仓时间 `≥ MAX_HOLD_SEC`  
- 触发后以市价平仓（合约腿 `reduceOnly`）。

---

## 6. 费用与滑点（统一折算 BTC）
- **现货手续费**：来自 `myTrades` 的 `commission/commissionAsset`；若为 USDT：`fee_BTC = fee_USDT / spot_vwap`。  
- **合约手续费**：`userTrades.commission`，天然是 BTC。  
- **资金费 / Realized PnL**：从 `/dapi/v1/income` 拉取 `FUNDING_FEE/REALIZED_PNL`（单位 BTC）累加。  
- **滑点控制**：用簿上 VWAP 与顶档价偏离（bp）做阈值；实际按真实成交计入盈亏。

---

## 7. 风险控制（硬阈值 + 建议）
## 7.2 入场前硬阈值（严格拦截）

A. 盘口时间一致性（数据质量）

规则：skew_ms = |t_cm - t_spot| × 1000 ≤ MAX_BOOK_SKEW_MS（默认 500ms）

不满足：丢弃当次信号

代码：主循环 skew_ms 判断

B. 账户保证金/强平（COIN-M）

强平距离：dist ≥ LIQ_DIST_MIN_PCT（默认 3%）

维护保证金比：totalMaintMargin / totalWalletBalance ≤ MARGIN_RATIO_MAX（默认 70%）

任一不满足：拒绝入场

代码：check_cm_margin_ok()

C. 收益与名义门槛（前沿入场）

最小套利幅度：ENTER_BPS（默认 6bp）

最小名义（USD）：MIN_V_USD（默认 $5,000）

代码：collect_frontier_candidates(..., min_bp=ENTER_BPS, min_vusd=MIN_V_USD)

D. 数量/价格合法性（交易所过滤器）

现货数量按 LOT_SIZE.stepSize 向下取整；COIN-M 张数按合约 stepSize 向下取整

否则会触发 PRICE_FILTER/LOT_SIZE 拒单

代码：fetch_spot_rules()/fetch_coinm_rules() + round_step(...)

E. 现货腿规模上限（防过度放大）

MAX_Q_BTC_FRONTIER（默认 0.5 BTC）：候选超过上限时按比例缩小两腿

代码：place_entry_from_row()（打印 [CAP]）

## 7.3 执行期风险（下单→成交）

A. 单腿成交风控 & 紧急对冲（强约束）

监控窗口：PAIR_TIMEOUT_SEC（默认 2s），轮询间隔 PAIR_POLL_INTERVAL（默认 0.2s）

分支：

只现货成 → 立刻市价反向平现货

只合约成 → 立刻市价 + reduceOnly 平合约

代码：monitor_and_rescue_single_leg()

B. 滑点与可成交性（固定名义入场路径）

逐档 VWAP 预估不可接受则放弃入场：

现货 MAX_SLIPPAGE_BPS_SPOT（默认 1bp）

COIN-M MAX_SLIPPAGE_BPS_COINM（默认 2bp）

代码：try_enter() → vwap_slippage_bps()

C. Post-Only 语义

Maker：现货 LIMIT_MAKER；COIN-M LIMIT + timeInForce=GTX（Post-Only，可能被拒）

Taker：两腿直接市价（用于前沿入场或紧急对冲）

## 7.4 持有与平仓（风控型退出）

触发条件（任一成立即平仓）：

回归：

∣spreadb​ps∣≤ EXITBPS（默认 2bp）

止损：

∣spreadbps∣≥STOPBPS（默认 12bp）

超时：age ≥ MAX_HOLD_SEC（默认 30s）

平仓方式：现货市价；合约市价 + reduceOnly

代码：need_exit() + do_exit()

## 7.5 资金费率（信息提示）

打印 lastFundingRate（换算 bp）与 nextFundingTime，并判断在 MAX_HOLD_SEC 内是否大概率跨结算（缓冲 FUNDING_BUFFER_SEC，默认 20s）

仅提示，不直接参与入场/退出决策

## 8. 运行说明（Testnet）

### 8.1 安装依赖
```bash
pip install requests

### 8.2 设置环境变量（测试网 API）
```bash
# 现货
export SPOT_KEY=your_spot_key
export SPOT_SECRET=your_spot_secret
# 币本位永续
export DAPI_KEY=your_dapi_key
export DAPI_SECRET=your_dapi_secret
```

### 8.3 运行
```bash
python -m app.main
```
> 首次建议在 `arbitrage/config.py` 将 `DRY_RUN = True`（只打印，不下单）。

---

## 9. 关键参数（常用）
| 参数 | 含义 | 典型值 |
|---|---|---|
| `DRY_RUN` | 只打印不下单 | `True`（首次） |
| `RUN_SECONDS` | 主循环时长（秒） | `60` |
| `POLL_INTERVAL` | 拉簿频率（秒） | `0.6`–`1.0` |
| `ENTER_BPS / EXIT_BPS / STOP_BPS` | 入/回归/止损阈值（bp） | `6 / 2 / 12` |
| `MAX_HOLD_SEC` | 持仓超时（秒） | `30`–`120` |
| `AUTO_FROM_FRONTIER` | 用前沿筛选 | `True` |
| `MIN_V_USD` | 最小名义（USD） | `5000` |
| `MAX_Q_BTC_FRONTIER` | 前沿现货腿上限（BTC） | `0.2`–`0.5` |
| `EXECUTION_MODE` | 执行模式 | `taker / maker` |

---

## 10. 输出文件（对账）
- **`trades_log.csv`**：
```
ts_ms, ts_iso, event, trade_id, side, Q_btc, N_cntr, spot_vwap, perp_vwap,
spot_orderId, cm_orderId, fee_btc_spot, fee_btc_cm, income_btc, delta_btc
```
- **ΔBTC** = 现货腿（±Q − 现货费_BTC） + 合约腿（−合约费_BTC + Realized PnL + Funding）。

---

## 11. 目录结构（模块化）
```
app/            # 程序入口（主循环）
arbitrage/
  config.py     # 运行参数与阈值（Testnet端点、API密钥）
  models.py     # 数据模型（Position等）
  utils.py      # 工具函数 & 交易CSV写入
  exchanges/    # 行情/下单/账户/规则/配对监控
  strategy/     # 前沿评估、风控、入场/退出编排
```

---

## 12. 风险与免责声明
- 本原型面向**测试网**。接入真实资金前，请务必补齐：
  1) 结构化日志与告警；  
  2) 重试/熔断/限流；  
  3) 手续费/滑点/资金费后的**净收益评估**；  
  4) 全局账户与仓位风控；  
  5) 持仓持久化与异常恢复。

---
