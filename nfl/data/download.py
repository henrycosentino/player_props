import pandas as pd
from pathlib import Path
from api_stream.kalshi.rest.data import KalshiData  # Intentionally excluded from project GitHub


DATA_DIR = 'data/raw'

SERIES_TICKERS = {
    "anytime_td"      : "KXNFLANYTD",     # NFL: 'CMC scores at least one touch down in a game'
    "two_plus_tds"    : "KXNFL2TD",       # NFL: 'CMC scores at least two touch downs in a game'
    "first_td"        : "KXNFLFIRSTTD",   # NFL: 'CMC scores the first touch down in a game'
    "rushing_yards"   : "KXNFLRSHYDS",    # NFL: 'Brock Purdy records 40+ rushing yards in a game'
    "receiving_yards" : "KXNFLRECYDS",    # NFL: 'CMC records 20+ receiving yards in a game'
    "passing_yards"   : "KXNFLPASSYDS",   # NFL: 'Brock Purdy records 200+ passing yards in a game'
    "passing_tds"     : "KXNFLPASSTDS",   # NFL: 'Brock Purdy throws 2+ touch downs in a game'
    "receptions"      : "KXNFLREC",       # NFL: 'CMC records 4+ receptions in a game'
    "sacks"           : "KXNFLGAMESACK",  # NFL: 'TEAM BASED, NOT PLAYER PROP, NOT CONSIDERED IN ANALYSIS'
    "field_goals"     : "KXNFLGAMEFG",    # NFL: 'Justin Tucker makes 2+ field goals in a game'
}

START_DATE = 1725408000                   # September 4, 2024 one day before 2024-25 NFL season starts


kh = KalshiData()


# ── Kalshi recent markets ────────────────────────────────────────────────────────────
rm_path_str = DATA_DIR + "/recent_markets.parquet"
rm_path = Path(rm_path_str)

if not rm_path.is_file():
    recent_markets = []
    for k, v in SERIES_TICKERS.items():

        params = {
            'limit'          : 1000,
            'min_settled_ts' : START_DATE,
            'series_ticker'  : v,
        }
        markets = kh.get_markets(params=params, historical=False)

        recent_markets.extend(markets)

    recent_markets_df = pd.DataFrame(recent_markets)

    if recent_markets_df.empty:
        print('No recent market data available (data is outside the recent markets lookback window).')
    else:
        recent_markets_df.to_parquet(rm_path_str, index=False)
else:
    recent_markets_df = pd.read_parquet(rm_path_str)


# ── Kalshi recent trades ─────────────────────────────────────────────────────────────
rt_path_str = DATA_DIR + "/recent_trades.parquet"
rt_path = Path(rt_path_str)

if not rt_path.is_file() and not recent_markets_df.empty:
    active_tickers = recent_markets_df[recent_markets_df['volume_fp'].astype(float) > 0]['ticker'].tolist()

    params = {'limit': 1000}
    recent_trades = kh.get_trades(
        tickers  = active_tickers,
        params   = params,
        endpoint = '/markets/trades'
    )
    pd.DataFrame([
        {**trade, 'ticker': ticker}
        for ticker, trades in recent_trades.items() if trades
        for trade in trades
    ]).to_parquet(rt_path_str, index=False)
else:
    print('Skipping recent trades, no recent markets in range.')


# ── Kalshi historical markets ────────────────────────────────────────────────────────
hm_path_str = DATA_DIR + "/historical_markets.parquet"
hm_path = Path(hm_path_str)

if not hm_path.is_file():
    historical_markets = []
    for k, v in SERIES_TICKERS.items():
        params = {
            'limit'         : 1000,
            'series_ticker' : v,
        }
        markets = kh.get_markets(params=params, historical=True)

        historical_markets.extend(markets)

    historical_markets_df = pd.DataFrame(historical_markets)

    if historical_markets_df.empty:
        print('No historical market data available.')
    else:
        print(f'Historical markets fetched: {len(historical_markets_df)}')
        historical_markets_df.to_parquet(hm_path_str, index=False)

else:
    historical_markets_df = pd.read_parquet(hm_path_str)


# ── Kalshi historical trades ─────────────────────────────────────────────────────────
ht_path_str = DATA_DIR + "/historical_trades.parquet"
ht_path = Path(ht_path_str)

if not ht_path.is_file() and not historical_markets_df.empty:
    active_historical_tickers = historical_markets_df[historical_markets_df['volume_fp'].astype(float) > 0]['ticker'].tolist()

    params = {
        'limit'  : 1000,
        'min_ts' : START_DATE,
    }
    historical_trades = kh.get_trades(
        tickers  = active_historical_tickers,
        params   = params,
        endpoint = '/historical/trades'
    )
    pd.DataFrame([
        {**trade, 'ticker': ticker}
        for ticker, trades in historical_trades.items() if trades
        for trade in trades
    ]).to_parquet(ht_path_str, index=False)
else:
    print('Skipping historical trades, no historical markets available.')