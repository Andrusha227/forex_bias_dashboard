# Forex Bias Dashboard

Local Streamlit dashboard that collects EUR/USD context and converts it into a normalized macroeconomic and structural bias score.

## Features

- **Monthly Structure**: Monthly Opening Range analysis (dynamic D/W transition), CFTC Euro FX COT net position, and COT weekly change.
- **Weekly Structure**: Weekly Opening Range analysis (dynamic 4H/D transition) and DXY direction.
- **Rates & Yield Curve**: Fed policy rate direction, Yield Curve direction (average of 2Y, 5Y, 10Y, 30Y tenors), and Treasury Yield Spread (10Y − 2Y) direction.
- **Inflation**: CPI, PCE, and Sticky CPI directions.
- **Labor Market**: Payrolls, Unemployment (inverted), and Initial Claims (inverted) directions.
- **Liquidity**: Net Liquidity (calculated as WALCL − WTREGEN − RRPONTSYD) direction and SOFR direction.
- **Growth**: GDP, Retail Sales, and Industrial Production directions.
- **Economic Calendar**: Today's high-impact EUR/USD economic events (informational display only, excluded from scoring).

## Normalized Scoring Architecture

Each factor produces a signal in `[-1.0, +1.0]` (where `+1.0` supports EUR/USD and `-1.0` supports USD):
- Category Score = average of available factor signals in that category.
- Final Normalized Score = weighted average of available category scores, ranging from `-1.0` to `+1.0`.

### Category Weights
- **Monthly Structure**: weight 3
- **Weekly Structure**: weight 2
- **Rates & Yield Curve**: weight 2
- **Liquidity**: weight 2
- **Inflation**: weight 1.5
- **Labor**: weight 1.5
- **Growth**: weight 1

### Verdict Thresholds
- `≥ +0.70`: Strong Bullish EUR/USD
- `+0.50 to +0.69`: Bullish EUR/USD
- `−0.49 to +0.49`: Neutral / Mixed
- `−0.69 to −0.50`: Bearish EUR/USD
- `≤ −0.70`: Strong Bearish EUR/USD

## Graceful Degradation & Data Integrity
- **No Mock Data**: All mock datasets, fallback values, and synthetic placeholders have been removed. If data cannot be retrieved, the factor is marked as **Unavailable** and completely excluded from scoring.
- **Renormalization**: The scoring engine dynamically adjusts weights, dividing the sum of weighted scores of available categories by the sum of weights of those available categories.
- **Duplicate Factor Resolution**: Redundant treasury yield inputs and correlated policy rate/dollar index feeds have been consolidated or removed to avoid double-counting.

## Setup

Use Python 3.11+.

```bash
cd forex_bias_dashboard
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your local environment file:

```bash
cp .env.example .env
```

Define your FRED API Key (now required for macro and spread scoring):

```bash
FRED_API_KEY=your_fred_api_key_here
```

Define Twelve Data key (optional but recommended for real EUR/USD weekly/monthly structure):

```bash
TWELVE_DATA_API_KEY=your_twelve_data_key_here
TWELVE_DATA_SYMBOL=EUR/USD
```

## Run

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Project Structure

```text
forex_bias_dashboard/
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
      twelve_data.py
    engine/
      bias_engine.py
      macro_engine.py
      opening_engine.py
      scoring.py
    utils/
      time.py
```
