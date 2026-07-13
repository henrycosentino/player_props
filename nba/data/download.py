import time
import pandas as pd
from pathlib import Path
from api_stream.kalshi.rest.data import KalshiData  # Intentionally excluded from project GitHub
from nba_api.stats.endpoints import scheduleleaguev2


DATA_DIR = 'data/raw'

SERIES_TICKERS = {
    "points"         : "KXNBAPTS",    # NBA: 'Duncan Robinson scores 10+ points in a game'
    "assists"        : "KXNBAAST",    # NBA: 'Duncan Robinson has 2+ assists in a game'
    "rebounds"       : "KXNBAREB",    # NBA: 'Duncan Robinson has 2+ rebounds in a game'
    "threes"         : "KXNBA3PT",    # NBA: 'Duncan Robinson makes 3+ three point shots in a game'
    "steals"         : "KXNBASTL",    # NBA: 'Duncan Robinson has 2+ steals in a game'
    "blocks"         : "KXNBABLK",    # NBA: 'Rudy Gobert has 1+ blocks in a game'
    "double_double"  : "KXNBA2D",     # NBA: 'Anthony Edwards has a double-double in a game'
    "triple_double"  : "KXNBA3D",     # NBA: 'Anthony Edwards has a triple-double in a game'
}

START_DATE = 1729468800               # October 21, 2024 one day before 2024-25 NBA season starts


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

    # CHANGED: guard against empty result before writing to parquet
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


# ── NBA schedule ─────────────────────────────────────────────────────────
nba_schedule_path_str = DATA_DIR + "/nba_start_times.parquet"
nba_schedule_path = Path(nba_schedule_path_str)

if not nba_schedule_path.is_file():
    seasons = ['2024-25', '2025-26']

    schedule_frames = []
    for season in seasons:
        sched = scheduleleaguev2.ScheduleLeagueV2(season=season).get_data_frames()[0]
        schedule_frames.append(sched)
        time.sleep(0.6)

    schedule_df = pd.concat(schedule_frames, ignore_index=True)
    schedule_df.to_parquet(nba_schedule_path_str, index=False)