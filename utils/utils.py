import numpy as np
import pandas as pd


def _get_valid_pregame(
    df: pd.DataFrame, 
    trades: int, 
    dollar_volume: float
) -> pd.DataFrame | None:
    """
    Helper function used to create pre-game data frame that fits given criteria.

    Args:
        df: merged final data frame
        trades: strict minimum number of historical pre game trades observed
        dollar_volume: strict minimum pre game dollar volume observed
    """
    pregame = df[df['created_time'] < df['game_start_time']].copy()
    
    pregame_counts = pregame.groupby('ticker')['ticker'].transform('size')
    pregame_dollar_vol = pregame.groupby('ticker')['dollar_amt'].transform('sum')

    valid_pregame = pregame[
        (pregame_counts > trades) &
        (pregame_dollar_vol > dollar_volume)
    ].reset_index(drop=True).copy()

    return valid_pregame if len(valid_pregame) > 0 else None


def agg_probabilities(
    df: pd.DataFrame, 
    trades: int, 
    dollar_volume: float
) -> tuple[float | None, float | None, int | None]:
    """
    Computes aggregate pre-game and hit rate probabilities for sports prop markets.

    Args:
        df: merged final data frame
        trades: strict minimum number of historical pre game trades observed
        dollar_volume: strict minimum pre game dollar volume observed
    """
    valid_pregame = _get_valid_pregame(df, trades, dollar_volume)

    if valid_pregame is None:
        return None, None, None
    
    n = len(valid_pregame)

    # Dollar-weighted average pre-game implied probability
    pregame_prob = (
        (valid_pregame['yes_price_dollars'] * valid_pregame['dollar_amt']).sum() / 
        valid_pregame['dollar_amt'].sum()
    )

    # Hit rate of yes event outcomes
    hit_rate = valid_pregame.groupby('ticker')['result'].first().eq('yes').mean()

    return pregame_prob, hit_rate, n


def player_hit_rates(
    df: pd.DataFrame, 
    n_prop_markets: int = 30,
    trades: int = 5,
    dollar_volume: float = 50.0,
    round_output: bool = True
) -> pd.DataFrame | None:
    """
    Computes per-player hit rates and pre-game price statistics for sport prop markets.

    Args:
        df: merged final data frame
        n_prop_markets: strict minimum number of prop markets observed per player
        trades: strict minimum number of historical pre game trades observed
        dollar_volume: strict minimum pre game dollar volume observed
        round_ouput: rounds floats to two decimal places
    """
    valid_pregame = _get_valid_pregame(df, trades, dollar_volume)

    if valid_pregame is None:
        return None
    
    market_counts = valid_pregame.groupby('player')['ticker'].transform('nunique')
    players = valid_pregame[market_counts > n_prop_markets]

    if players.empty:
        return None

    players = players.groupby('player').apply(
        lambda x: pd.Series({
            'market_count'          : x['ticker'].nunique(),
            'pregame_trade_count'   : len(x),
            'dollar_volume'         : x['dollar_amt'].sum(),
            'hit_rate'              : x.groupby('ticker')['result'].first().eq('yes').mean(),
            'dvwa_pregame_yes_px'   : (x['yes_price_dollars'] * x['dollar_amt']).sum() / x['dollar_amt'].sum(),
            'median_pregame_yes_px' : x['yes_price_dollars'].median(),
        }),
        include_groups=False
    )

    players['hit_rate_dvwa_delta'] = players['hit_rate'] - players['dvwa_pregame_yes_px']
    players['hit_rate_median_delta'] = players['hit_rate'] - players['median_pregame_yes_px']

    if round_output:
        whole_cols  = ['market_count', 'pregame_trade_count']
        dollar_cols = ['dollar_volume']
        pct_cols    = ['hit_rate', 'dvwa_pregame_yes_px', 'median_pregame_yes_px', 'hit_rate_dvwa_delta', 'hit_rate_median_delta']

        players.loc[:, whole_cols]  = players[whole_cols].astype(int)
        players.loc[:, dollar_cols] = players[dollar_cols].round(2)
        players.loc[:, pct_cols]    = (players[pct_cols]).round(2)

    return players


def simulation(
    df: pd.DataFrame, 
    side: str = 'yes', 
    liquidity_amt: float = 1.0,
    fee: float = 0.07,
    by: str = 'dvwa', 
    trades: int = 5,
    dollar_volume: float = 50.0
) -> pd.DataFrame:
    """
    Simulates a fixed-dollar market-making strategy on prop markets.

    Args:
        df: merged final data frame
        side: 'yes' or 'no' side of market to provide liquidity on
        liquidity_amt: fixed dollar liquidity provided pre-game
        fee: percent fee when placing trades in decimal form
        by: 'median' or 'dvwa' (dollar volume weight average) pregame price
        trades: strict minimum number of historical pre game trades observed
        dollar_volume: strict minimum pre game dollar volume observed
    """
    valid_pregame = _get_valid_pregame(df, trades, dollar_volume)

    if valid_pregame is None:
        return None

    if side == 'yes' and by == 'median':
        prices = valid_pregame.groupby('ticker')['yes_price_dollars'].median()
    elif side == 'yes' and by == 'dvwa':
        prices = valid_pregame.groupby('ticker').apply(
            lambda x: (x['yes_price_dollars'] * x['dollar_amt']).sum() / x['dollar_amt'].sum(),
            include_groups=False
        )
    elif side == 'no' and by == 'median':
        prices = 1 - valid_pregame.groupby('ticker')['yes_price_dollars'].median()
    else:
        prices = 1 - valid_pregame.groupby('ticker').apply(
            lambda x: (x['yes_price_dollars'] * x['dollar_amt']).sum() / x['dollar_amt'].sum(),
            include_groups=False
        )

    market = valid_pregame.groupby('ticker').agg(
        result=('result', 'first'),
        close_time=('close_time', 'first'),
    )
    market['price'] = prices

    market['contracts_purchased'] = np.where(
        market['price'] > 0, np.floor(liquidity_amt / market['price']), 0
    ).astype(int)

    fees_per_contract = market['price'] * (1 - market['price']) * fee
    market['total_fees'] = np.ceil(np.round(market['contracts_purchased'] * fees_per_contract * 100, 6)) / 100

    market['net_winnings'] = (
        market['contracts_purchased'] * np.where(market['result'] == side, 1, 0)
        - market['contracts_purchased'] * market['price']
        - market['total_fees']
    )

    market['liquidity_amt'] = market['contracts_purchased'] * market['price'] + market['total_fees']

    market = market.sort_values('close_time')
    market['cum_net_winnings'] = market['net_winnings'].cumsum()

    return market


def simulation_statistics(
    df: pd.DataFrame,
    group_returns_by: str = 'weekly',
) -> dict:
    """
    Computes summary statistics on period returns from a simulation, where each
    period's return is defined as that period's net winnings divided by the
    capital risked that period (liquidity_amt * number of positions settled).

    Args:
        df: output of simulation()
        group_returns_by: 'annually', 'quarterly', 'monthly', or 'weekly'
    """
    time_period_map = {
        'annually'  : 'YE',
        'quarterly' : 'QE',
        'monthly'   : 'ME',
        'weekly'    : 'W-MON',
    }

    if group_returns_by not in time_period_map:
        raise ValueError(
            f"group_returns_by must be one of {list(time_period_map)}, got {group_returns_by!r}"
        )

    df = df.copy()
    df['close_time'] = pd.to_datetime(df['close_time'], format='ISO8601', utc=True)

    period = (
        df.set_index('close_time')
          .resample(time_period_map[group_returns_by])
          .agg(net_winnings=('net_winnings', 'sum'), liquidity_amt=('liquidity_amt', 'sum'))
    )
    period = period[period['liquidity_amt'] > 0]

    period_returns = period['net_winnings'] / period['liquidity_amt']

    return {
        'median' : period_returns.median(),
        'mean'   : period_returns.mean(),
        'std'    : period_returns.std(),
        'count'  : period_returns.count()
    }