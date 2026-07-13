import pandas as pd
from pathlib import Path
from api_stream.kalshi.rest.data import KalshiData  # Intentionally excluded from project GitHub


DATA_DIR = 'data/raw'

SERIES_TICKERS = {
    "homeruns"         : "KXMLBHR",    # MLB: 'Buster Posey records n+ home runs in a game'
    "strikeouts"       : "KXMLBKS",    # MLB: 'Tim Lincecum records n+ strike outs in a game'
    "hits"             : "KXMLBHIT",   # MLB: 'Buster Posey records n+ hits in a game'
    "hits_runs_rbi"    : "KXMLBHRR",   # MLB: 'Buster Posey records n+ combined hits, runs, or RBIs in a game'
    "total_bases"      : "KXMLBTB",    # MLB: 'Buster Posey records n+ total bases in a game'
    "outs"             : "KXMLBOUTS",  # MLB: 'Tim Lincecum records n+ total outs'
    "rbi"              : "KXMLBRBI",   # MLB: 'Buster Posey records n+ total RBIs in a game'
    "stolen_bases"     : "KXMLBSB",    # MLB: 'Buster Posey records n+ stolen bases in a game'
}

START_DATE = 1774310400 # March 24, 2026 day before MLB season starts


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