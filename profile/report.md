# Bitget USDT-M style profile (2026-09-19 → 2026-10-19, Asia/Saigon UTC+7)

Read-only analysis of **22 closed** hedge-mode positions (372 fills, 310 filled orders). Current equity ~384 USDT. Net realized **+459.9 USDT** (20W/2L, win rate **90.9%**). Gross PnL +541.9; fees **94.1 USDT (17.0% of gross)**. Net transfers in period ≈ −75.7 USDT (strategy/exchange/OTC), so trading PnL ≠ equity change alone.

## Style in numbers (median [p25–p75])

| Rule | Median | Range / notes |
|------|--------|----------------|
| Symbols | BTCUSDT (16), ETHUSDT (5), MAGIC (1) | Long 9 / short 13; **7** long+short overlaps same symbol |
| Leverage | 150x cross hedge | 25x only on MAGIC |
| First entry notional | **~10.3× equity** (~1.0–1.2k USDT BTC med) | p25–p75: 5.2–27.9×; Oct 19 spikes to 14k |
| DCA layers (incl. entry) | **3.5** | p90≈17; max 25; 9/22 single-shot |
| DCA spacing (adverse) | **0.18%** | p25–p75: 0.11–0.27% |
| DCA size vs prior | **0.87×** | Not strict martingale; p25–p75: 0.4–2.0× |
| Peak pos notional | **34× equity** | p90≈75×; account peak simultaneous **~18.8k (49×)** |
| Partial/final TP from avg | **~0.45%** (pos. reduces) | Often scale out; **11/22** also reduced while still red |
| MAE vs open avg | **0.39%** (BTC/ETH med) | Hold med **2.8h** (mean 29h; one ~12d) |
| Orders | **92% limit**, **86% maker** fills | SL triggers rare (6); no stable SL % |
| Entry context | **82% fade 1h** move | Free grid / mean-revert bias |

Suggested bot knobs are in `style_profile.json` → `suggested_bot_parameters`.

## Observations (risk appetite)

1. **Extreme notional vs tiny equity.** Median first clip is already ~10× equity at 150x; peaks 30–75×. Rough move-to-wipe at peak is only **~1.3–3%** — he accepts account-level risk, not tight stops.
2. **Neutral micro-grid, not trend.** Sub-0.2% add spacing, mostly limit/maker, entries fade the prior 1h, and he freely hedges both sides.
3. **Scale-out > stop-out.** Partials around +0.2–1.2% from avg; half of positions cut size while still underwater to recycle margin — matches his “recover balance on bounces” description.
4. **Activity and size ramped hard late period.** Sparse Sept/early Oct; **8 positions on 2026-10-19** alone with multi-k USDT clips — any bot should treat recent sizing as an upper regime, not the full-month median.
5. **Cannot infer a systematic stop-loss distance** from data (only 6 loss-trigger orders; distances inconsistent). Liquidation proximity must be treated as intentional risk, not an oversight.

Files: `positions_features.csv`, `style_profile.json`, raw pulls under `/workspace/bitget/profile/`.
