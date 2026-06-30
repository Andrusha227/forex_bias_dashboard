# EUR/USD Macro Bias Dashboard

Local Streamlit MVP that collects EUR/USD context and converts it into a simple Monthly -> Weekly -> Intraday bias score.

## Features

- Monthly Bias: current EUR/USD price, monthly open, price location, Euro FX COT net position, COT weekly change.
- Weekly Bias: weekly open, previous week high/low, DXY direction, US2Y direction, US10Y direction.
- Intraday Context: NY 4H daily open, yesterday high/low, Asia range, London and New York session opens, high-impact news.
- Macro Regime: Fed/rates, inflation, labor, liquidity/dollar, and growth context from FRED.
- Final score:
  - `>= +3`: Bullish EUR/USD
  - `<= -3`: Bearish EUR/USD
  - `-2` to `+2`: Neutral / Wait

This is a decision-support dashboard, not a trading signal.

## Setup

Use Python 3.11+.

```bash
cd eurusd-bias-dashboard
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your local environment file:

```bash
cp .env.example .env
```

Optional FRED key:

```bash
FRED_API_KEY=your_fred_api_key_here
```

Optional candle keys for automatic NY 4H Daily Open range:

```bash
TWELVE_DATA_API_KEY=your_twelve_data_key_here
TWELVE_DATA_SYMBOL=EUR/USD
TWELVE_DATA_DO_START_HOUR_NY=1

OANDA_API_TOKEN=your_oanda_token_here
OANDA_ENVIRONMENT=practice
OANDA_INSTRUMENT=EUR_USD
OANDA_DAILY_ALIGNMENT_HOUR_NY=17
```

## Run

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Chart-Level Overrides

Use the sidebar `Chart Levels` controls when TradingView has the correct live 4H level and the fallback feed is stale:

- `Override current EUR/USD`: manually set the current chart price.
- `Override Daily Open (DO range)`: manually set the Daily Open range from your 4H TradingView markup.

The Intraday `Daily open` block turns green when price is above the DO range, red when price is below the DO range, and neutral when price is inside the range. The DO range is a trade filter, not a score input.
The app cache refreshes every 15 minutes by default.

## Data Status

- EUR/USD daily OHLC: uses Twelve Data first when `TWELVE_DATA_API_KEY` is present, then falls back to Stooq/mock.
- EUR/USD daily open/range: uses Twelve Data 4H candles first, then OANDA H4 candles if configured, then intraday/daily fallback and manual override. It takes the first post-midnight NY H4 candle, default `01:00 NY`, and uses its open/high/low as the DO range.
- EUR/USD weekly open/ranges: displays Sunday session open range from `Sun 17:00 NY` and Monday first H4 range from `Mon 01:00 NY`.
- Opening range raids: a raid is any wick through the range high/low. Candle close does not matter.
- DXY direction: attempts to use Stooq daily CSV for `dx.f`, then falls back to mock data.
- US2Y and US10Y: uses FRED when `FRED_API_KEY` is present, then falls back to mock data.
- Macro Regime: uses FRED when `FRED_API_KEY` is present. If an individual series fails, that series falls back to mock data.
- Euro FX COT: attempts to parse the public CFTC legacy report, then falls back to mock data.
- Economic calendar: attempts to use ForexFactory/FairEconomy weekly XML, caches the last valid XML locally, then falls back to mock data.
- Asia/London/New York session levels: placeholder estimates until a dedicated intraday session feed is connected.
- Calendar warning logic: only high-impact EUR/USD events within the next 60 minutes reduce intraday score.

The app is designed to run even if every external API fails.

## Project Structure

```text
eurusd-bias-dashboard/
  app.py
  requirements.txt
  .env.example
  README.md
  src/
    data/
      market_data.py
      cot_data.py
      fred_data.py
      fred_catalog.py
      calendar_data.py
    engine/
      bias_engine.py
      macro_engine.py
    utils/
      time.py
```

## Macro Regime Layer

The macro layer is intentionally capped so it does not overwhelm price structure.
It adds a `Macro Tailwind`, `Macro Headwind`, or `Macro Mixed` filter and contributes a capped score from `-3` to `+3`.

Included FRED groups:

- Fed / rates: `DFF`, `EFFR`, `DFEDTARU`, `DFEDTARL`, `DGS3MO`, `DGS1`, `DGS2`, `DGS5`, `DGS10`, `DGS30`
- Inflation: `CPIAUCSL`, `PCEPI`, `CORESTICKM159SFRBATL`
- Labor: `PAYEMS`, `UNRATE`, `ICSA`
- Liquidity / dollar: `WALCL`, `SOFR`, `DTWEXBGS`
- Growth: `GDP`, `RSAFS`, `INDPRO`

The dashboard also shows the core score separately from the macro contribution.

## Next Development Steps

- Replace placeholder intraday levels with a true intraday EUR/USD feed.
- Replace mock economic calendar with a licensed calendar provider.
- Harden the COT parser against all CFTC layout variants or move to a structured CFTC dataset.
- Add unit tests for `src/engine/bias_engine.py`.
- Add unit tests for `src/engine/macro_engine.py`.
