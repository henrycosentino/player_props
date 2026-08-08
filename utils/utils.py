import pandas as pd
from scipy import stats
import statsmodels.api as sm
import plotly.graph_objects as go


# --- Preprocessing Helpers ---
def find_teams(
    teams: str
) -> tuple[str | None, str | None]:
    """Data processing function used to extract NFL teams from Kalshi tickers."""
    valid_3 = {
        'ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET',
        'HOU','IND','JAC','LAC','MIA','MIN','NYG','NYJ','PHI','PIT','SEA','TEN','WAS'
    }
    valid_2 = {'GB','KC','LV','NE','NO','SF','TB','LA'}

    if len(teams) == 4:
        away, home = teams[:2], teams[2:]
    elif len(teams) == 5:
        if teams[:3] in valid_3 and teams[3:] in valid_2:
            away, home = teams[:3], teams[3:]
        elif teams[:2] in valid_2 and teams[2:] in valid_3:
            away, home = teams[:2], teams[2:]
        else:
            away, home = None, None
    elif len(teams) == 6:
        away, home = teams[:3], teams[3:]
    else:
        away, home = None, None

    return away, home


# --- Analysis Helpers ---
def market_analysis(
    df: pd.DataFrame,
    n_req_trades: int = 500,
    series_thresholds: bool = False
) -> pd.DataFrame:
    """
    Computes aggregate trading statistics (volume, PnL, net returns,
    variance, and fee economics for makers and takers) for a sports
    prop market. If the series has thresholds (e.g. rushing yard
    thresholds), statistics are broken out per series threshold; otherwise
    a single row is returned for the whole series.
 
    Args:
        df: kalshi DataFrame.
        n_req_trades: Minimum number of required trades per series threshold, default 500.
        series_thresholds: Whether this series has thresholds (e.g. rushing yard
            thresholds) that stats should be broken out by, keyed on the
            'series_threshold' column. Default False.
 
    Returns:
        Data Frame with series or series threshold analytics.
    """
    if series_thresholds:
        trade_counts   = df['series_threshold'].value_counts()
        valid_groups   = sorted(trade_counts[trade_counts >= n_req_trades].index)
        invalid_groups = sorted(trade_counts[trade_counts < n_req_trades].index)
 
        if invalid_groups:
            print(f"Invalid Series Threshold: {invalid_groups} do not have {n_req_trades:,.0f} required trades.")
 
        if not valid_groups:
            print(f"No valid Series Thresholds with {n_req_trades:,.0f} required trades.")
            return None
 
        df = df[df['series_threshold'].isin(valid_groups)].reset_index(drop=True).copy()
        group_col = 'series_threshold'
    else:
        if len(df) < n_req_trades:
            print(f"Only {len(df):,.0f} out of {n_req_trades:,.0f} required trades.")
            return None
        df = df.assign(_group=1)
        group_col = '_group'
 
    def _agg(g: pd.DataFrame) -> pd.Series:
        n_trades_g    = len(g)
        n_markets_g   = g['ticker'].nunique()
        maker_edge_g  = (g['maker_revenue'] - g['maker_dollar_amt']).sum()
 
        return pd.Series(dict(
            start_date              = g['created_time'].min(),               
            end_date                = g['created_time'].max(),
            n_trades                = n_trades_g,
            n_markets               = n_markets_g,
            contract_volume         = g['count_fp'].sum(),               
            avg_taker_trade_size    = g['taker_dollar_amt'].mean(),
            median_taker_trade_size = g['taker_dollar_amt'].median(),
            trades_per_market       = n_trades_g / n_markets_g,
            total_taker_pnl         = g['taker_pnl'].sum(),
            taker_pct_net_ret       = g['taker_pnl'].sum() / (g['taker_dollar_amt'] + g['taker_fee']).sum() * 100,
            taker_pct_winning       = (g['taker_pnl'] > 0).mean() * 100,
            taker_win_avg_pct_ret   = g.loc[g['taker_pnl'] > 0, 'taker_net_return'].mean() * 100,       
            taker_loss_avg_pct_ret  = g.loc[g['taker_pnl'] <= 0, 'taker_net_return'].mean() * 100,      
            total_maker_pnl         = g['maker_pnl'].sum(),
            maker_pct_net_ret       = g['maker_pnl'].sum() / (g['maker_dollar_amt'] + g['maker_fee']).sum() * 100,
            maker_pct_winning       = (g['maker_pnl'] > 0).mean() * 100,
            maker_win_avg_pct_ret   = g.loc[g['maker_pnl'] > 0, 'maker_net_return'].mean() * 100,        
            maker_loss_avg_pct_ret  = g.loc[g['maker_pnl'] <= 0, 'maker_net_return'].mean() * 100,     
            maker_fee_pct_of_edge   = g['maker_fee'].sum() / maker_edge_g * 100,
        ))
 
    market_analytics_df = df.groupby(group_col).apply(_agg, include_groups=False).reset_index()
 
    if group_col == '_group':
        market_analytics_df = market_analytics_df.drop(columns='_group')
 
    return market_analytics_df

def graph_comparison(
    df: pd.DataFrame,
    graph_title: str,
    n_req_trades: int = 500,
    ci: float = 0.95,
) -> None:
    """
    Computes the aggregate pre-game implied probability and hit rate for
    a sports prop market, runs a paired t-test between them at the market
    level, and plots a bar chart comparing the two.

    Args:
        df: kalshi DataFrame.
        graph_title: Graph title for series.
        n_req_trades: Strict minimum number of required trades, default 500.
        ci: Confidence level for confidence interval.

    Returns:
        None. Displays the resulting plotly figure.
    """
    n_trades = len(df)

    if n_trades < n_req_trades:
        print(f"Only {n_trades:,.0f} out of {n_req_trades:,.0f} required trades.")
        return None

    pregame_df = df[df['created_time'] < df['game_start_time']]

    if pregame_df.empty:
        print("No pre-game trade data available for this market.")
        return None

# Per-market pregame probability and outcome
    pregame_df = pregame_df.assign(
        _weighted_price=pregame_df['yes_price_dollars'] * pregame_df['count_fp']
    )
    market_stats = pregame_df.groupby('ticker').agg(
        _weighted_sum=('_weighted_price', 'sum'),
        _contract_sum=('count_fp', 'sum'),
        _outcome=('result', 'first'),
    )
    market_stats['pregame_prob_k'] = 100 * market_stats['_weighted_sum'] / market_stats['_contract_sum']
    market_stats['outcome_k'] = 100 * market_stats['_outcome'].eq('yes')
    
    # Average of per-market pregame probabilities (each market counted once)
    pregame_prob = market_stats['pregame_prob_k'].mean()

    # Hit rate across all markets
    hitrate = market_stats['outcome_k'].mean()

    # Paired t-test 
    diffs = market_stats['pregame_prob_k'] - market_stats['outcome_k']
    n_paired = len(diffs)
    t_stat, p_value = stats.ttest_1samp(diffs, popmean=0)

    # Confidence interval
    t_crit  = stats.t.ppf(ci + (1 - ci) / 2, df=n_paired - 1)
    prob_ci = t_crit * market_stats['pregame_prob_k'].sem()
    hit_ci  = t_crit * market_stats['outcome_k'].sem()

    max_height = max(pregame_prob + prob_ci, hitrate + hit_ci)

    hover_info = (
        f"<b>Pre-Game:</b> {pregame_prob:,.2f}%<br>"
        f"<b>Hit Rate:</b> {hitrate:,.2f}%<br>"
        f"<b>Paired t-test:</b><br>"
        f"&nbsp;&nbsp;• t = {t_stat:.2f}<br>"
        f"&nbsp;&nbsp;• p = {p_value:.4f}<br>"
        f"&nbsp;&nbsp;• n (markets) = {n_paired:,.0f}<extra></extra>"
    )

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=['Pre-Game'],
        y=[pregame_prob],
        name='Pre-Game',
        marker=dict(color="#E29A4A"),
        hovertemplate=hover_info,
        error_y=dict(type='data', array=[prob_ci], visible=True)
    ))

    fig.add_trace(go.Bar(
        x=['Hit Rate'],
        y=[hitrate],
        name='Hit Rate',
        marker=dict(color="#9096ED"),
        hovertemplate=hover_info,
        error_y=dict(type='data', array=[hit_ci], visible=True)
    ))

    fig.update_layout(
        template='plotly_dark',
        showlegend=False,
        barmode='group',
        title={
            'text': (
                "<b>Pre-Game Market Implied Probability of Outcome vs. Hit Rate</b><br>"
                f"<span style='font-size: 15px; color: #b0b0b0;'>{graph_title} Prop Market</span>"
            ),
            'font': {'size': 20, 'color': '#ffffff'},
            'x': 0.5,
            'xanchor': 'center'
        },
        yaxis_title='Probability (%)',
        yaxis_range=[0, max_height + 15],
        paper_bgcolor='#111111',
        plot_bgcolor='#111111',
        legend_title_text=''
    )

    fig.show()
    return None

def graph_comparison_by_threshold(
    df: pd.DataFrame,
    graph_title: str,
    n_req_trades: int = 500,
    n_req_markets: int = 10,
    ci: float = 0.95,
) -> None:
    """
    Computes aggregate pre-game implied probabilities and hit rates for
    sports prop markets, broken out by series threshold, runs a paired
    t-test per threshold at the market level, and plots a grouped bar
    chart comparing pre-game implied probability vs. hit rate for each
    threshold.

    Args:
        df: kalshi DataFrame.
        graph_title: Graph title for series.
        n_req_trades: Minimum number of required trades per series threshold, default 500.
        n_req_markets: Minimum number of required markets per series threshold, default 10.
        ci: Confidence level for confidence interval.

    Returns:
        None. Displays the resulting plotly figure.
    """
    counts_df = pd.DataFrame({
        'trade_count': df['series_threshold'].value_counts(),
        'market_count': df.groupby('series_threshold')['ticker'].nunique(),
    }).fillna(0)

    valid_series_thresholds = sorted(
        counts_df[(counts_df['trade_count'] >= n_req_trades) & (counts_df['market_count'] >= n_req_markets)].index
    )

    if not valid_series_thresholds:
        print(f"No valid series thresholds with {n_req_trades:,.0f} required trades and {n_req_markets:,.0f} required markets.")
        return None

    series_threshold_df = df[df['series_threshold'].isin(valid_series_thresholds)]
    pregame_df = series_threshold_df[series_threshold_df['created_time'] < series_threshold_df['game_start_time']]

    if pregame_df.empty:
        return None

    # Per-market pregame probability and outcome
    pregame_df = pregame_df.assign(
        _weighted_price=pregame_df['yes_price_dollars'] * pregame_df['taker_dollar_amt']
    )
    market_stats = pregame_df.groupby(['series_threshold', 'ticker']).agg(
        _weighted_sum=('_weighted_price', 'sum'),
        _dollar_sum=('taker_dollar_amt', 'sum'),
        _outcome=('result', 'first'),
    )
    market_stats['pregame_prob_k'] = 100 * market_stats['_weighted_sum'] / market_stats['_dollar_sum']
    market_stats['outcome_k'] = 100 * market_stats['_outcome'].eq('yes')
    market_stats['diff_k'] = market_stats['pregame_prob_k'] - market_stats['outcome_k']

    # Average of per-market probabilities within each threshold
    pregame_prob = market_stats.groupby(level='series_threshold')['pregame_prob_k'].mean()

    # Hit rate across all markets
    hit_rate = market_stats.groupby(level='series_threshold')['outcome_k'].mean()

    # Paired t-test per threshold
    def _paired_ttest(g):
        t_stat, p_value = stats.ttest_1samp(g, popmean=0)
        return pd.Series({'t_stat': t_stat, 'p_value': p_value, 'n_paired': len(g)})

    ttest_results = market_stats.groupby(level='series_threshold')['diff_k'].apply(_paired_ttest).unstack()

    def _ci(g):
        t_crit = stats.t.ppf(ci + (1 - ci) / 2, df=len(g) - 1)
        return t_crit * g.sem()

    prob_ci = market_stats.groupby(level='series_threshold')['pregame_prob_k'].apply(_ci)
    hit_ci  = market_stats.groupby(level='series_threshold')['outcome_k'].apply(_ci)

    results_df = pd.DataFrame({'pregame_prob': pregame_prob, 'hit_rate': hit_rate})
    results_df = (
        results_df
        .join(ttest_results)
        .join(prob_ci.rename('prob_ci'))
        .join(hit_ci.rename('hit_ci'))
    )

    results_df = results_df.loc[[sm for sm in valid_series_thresholds if sm in results_df.index]]
    results_df = results_df.reset_index().rename(columns={'series_threshold': 'series_threshold_raw'})
    results_df['series_threshold'] = results_df['series_threshold_raw'].astype(str) + '+'

    hover_text_list = [
        f"<b>Pre-Game:</b> {r['pregame_prob']:,.2f}%<br>"
        f"<b>Hit Rate:</b> {r['hit_rate']:,.2f}%<br>"
        f"<b>Paired t-test:</b><br>"
        f"&nbsp;&nbsp;• t = {r['t_stat']:.2f}<br>"
        f"&nbsp;&nbsp;• p = {r['p_value']:.4f}<br>"
        f"&nbsp;&nbsp;• n (markets) = {r['n_paired']:,.0f}<extra></extra>"
        for _, r in results_df.iterrows()
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=results_df['series_threshold'],
        y=results_df['pregame_prob'],
        name='Pre-Game',
        marker=dict(color="#E29A4A"),
        hovertemplate=hover_text_list,
        error_y=dict(type='data', array=results_df['prob_ci'], visible=True)
    ))

    fig.add_trace(go.Bar(
        x=results_df['series_threshold'],
        y=results_df['hit_rate'],
        name='Hit Rate',
        marker=dict(color="#9096ED"),
        hovertemplate=hover_text_list,
        error_y=dict(type='data', array=results_df['hit_ci'], visible=True)
    ))

    max_height = max(
        (results_df['pregame_prob'] + results_df['prob_ci']).max(),
        (results_df['hit_rate'] + results_df['hit_ci']).max()
    )
    fig.update_layout(
        template='plotly_dark',
        barmode='group',
        title={
            'text': (
                "<b>Pre-Game Market Implied Probability of Outcome vs. Hit Rate</b><br>"
                f"<span style='font-size: 15px; color: #b0b0b0;'>{graph_title} Prop Markets, by Threshold</span>"
            ),
            'font': {'size': 20, 'color': '#ffffff'},
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title=f"{graph_title} Threshold",
        yaxis_title='Probability (%)',
        yaxis_range=[0, max_height + 15],
        paper_bgcolor='#111111',
        plot_bgcolor='#111111',
        legend_title_text=''
    )

    fig.show()
    return None

def _variable_color(
    var_name: str
) -> str:
    """
    Maps an independent variable name to the color used for it in the
    analysis markdown legend, so the regression chart's bars visually
    match the written variable definitions.
    """
    if 'outcome_side' in var_name:
        return '#FDFD96'    # Price level and side
    if any(key in var_name for key in ('market_completion_pct', 'is_post_kickoff_dummy')):
        return '#5A99E0'    # Market maturity
    if 'log_n_trades_in_market' in var_name:
        return '#FF6B6B'    # Market size
    if 'log_count_fp' in var_name:
        return '#50E3C2'    # Trade size
    return '#888888'        # Constant

def graph_regression(
    df: pd.DataFrame,
    side: str,
    graph_title: str,
    n_req_trades: int = 500,
    show_const: bool = False,
    ci: float = 0.95,
) -> None:
    """
    Standardizes 'log_n_trades_in_market', 'log_count_fp', and 'market_completion_pct'
    Then performs a multivariable regression with covariance clustered by ticker, and 
    plots the coefficients with confidence interval error bars.
 
    Args:
        df: DataFrame containing the data.
        side: 'maker' or 'taker'.
        graph_title: Graph title for series.
        n_req_trades: Strict minimum number of required trades, default 500.
        show_const: Whether to include the regression constant as its own bar, default False.
        ci: Confidence level for the coefficient error bars, default 0.95.
 
    Returns:
        None. Displays plotly figure.
    """
    if side not in ('maker', 'taker'):
        raise ValueError("side must be 'maker' or 'taker'")
 
    variables_to_scale = ['log_n_trades_in_market', 'log_count_fp', 'market_completion_pct']
    scaled_variable_names = ["scaled_" + var for var in variables_to_scale]
 
    X_vars = scaled_variable_names + ['is_post_kickoff_dummy', f'{side}_outcome_side_dummy']
    y_var  = f'{side}_pnl_per_contract'
 
    clean_df = df[variables_to_scale + ['is_post_kickoff_dummy', f'{side}_outcome_side_dummy', y_var, 'ticker']].dropna(how='any').copy()
 
    n_trades = len(clean_df)
    if n_trades < n_req_trades:
        print(f"Only {n_trades:,.0f} out of {n_req_trades:,.0f} required trades.")
        return None
 
    # Standardize
    clean_df[scaled_variable_names] = (
        (clean_df[variables_to_scale] - clean_df[variables_to_scale].mean())
        / clean_df[variables_to_scale].std(ddof=0)
    )
 
    y = clean_df[y_var]
    X = clean_df[X_vars]
 
    X = sm.add_constant(X, has_constant='add')
 
    model = sm.OLS(endog=y, exog=X)

    # Clustered and naive regressions
    results_clustered = model.fit(cov_type="cluster", cov_kwds={"groups": clean_df["ticker"]})
    results_naive     = model.fit(cov_type="nonrobust")
 
    coef_df = pd.DataFrame(
        {
            "independent_variable" : results_clustered.params.index,
            "beta"                 : results_clustered.params.values,
            "p_value"              : results_clustered.pvalues.values,
            "std_err"              : results_clustered.bse.values,
            "t_stat"               : results_clustered.tvalues.values,
            "std_err_naive"        : results_naive.bse.values,
            "t_stat_naive"         : results_naive.tvalues.values,
            "p_value_naive"        : results_naive.pvalues.values,
        }
    )
    coef_df["se_inflation"] = coef_df["std_err"] / coef_df["std_err_naive"]
 
    if not show_const:
        coef_df = coef_df[coef_df["independent_variable"] != "const"].reset_index(drop=True)
 
    if coef_df.empty:
        return None
 
    # Confidence interval error bars, using the clustered SE
    n_clusters = clean_df["ticker"].nunique()
    t_crit = stats.t.ppf(ci + (1 - ci) / 2, df=n_clusters - 1)
    coef_df["ci_margin"] = t_crit * coef_df["std_err"]
    coef_df["ci_lower"]  = coef_df["beta"] - coef_df["ci_margin"]
    coef_df["ci_upper"]  = coef_df["beta"] + coef_df["ci_margin"]
 
    hovertemplate = (
        "<b>Independent Variable:</b> %{y}<br>"
        "<b>Beta:</b> %{x:.4f}<br>"
        f"<b>{ci * 100:.0f}% CI:</b> [" + "%{customdata[7]:.4f}, %{customdata[8]:.4f}]<br>"
        "<br><b>Clustered (by ticker):</b><br>"
        "p-value: %{customdata[0]:.4f}<br>"
        "Std Error: %{customdata[1]:.4f}<br>"
        "t-statistic: %{customdata[2]:.2f}<br>"
        "<br><b>Naive (non-clustered):</b><br>"
        "p-value: %{customdata[3]:.4f}<br>"
        "Std Error: %{customdata[4]:.4f}<br>"
        "t-statistic: %{customdata[5]:.2f}<br>"
        "<br><b>SE inflation (clustered / naive):</b> %{customdata[6]:.2f}x"
        "<extra></extra>"
    )
 
    def _significance_symbol(p: float) -> str:
        if p < 0.01:
            return "star"
        elif p < 0.05:
            return "square"
        elif p < 0.10:
            return "circle"
        else:
            return "circle-open"

    fig = go.Figure()

    for _, row in coef_df.iterrows():
        var = row["independent_variable"]
        var_color = _variable_color(var)
        symbol = _significance_symbol(row["p_value"])

        fig.add_trace(
            go.Scatter(
                x=[row["beta"]],
                y=[var],
                mode="markers",
                marker=dict(color=var_color, size=11, symbol=symbol),
                hovertemplate=hovertemplate,
                error_x=dict(type='data', array=[row["ci_margin"]], visible=True, color=var_color),
                customdata=[[
                    row["p_value"], row["std_err"], row["t_stat"],
                    row["p_value_naive"], row["std_err_naive"], row["t_stat_naive"],
                    row["se_inflation"], row["ci_lower"], row["ci_upper"],
                ]],
                showlegend=False,
            )
        )

    significance_legend = [
        ("p < 0.01", "star"),
        ("p < 0.05", "square"),
        ("p < 0.10", "circle"),
        ("p \u2265 0.10", "circle-open"),
    ]
    for label, symbol in significance_legend:
        fig.add_trace(
            go.Scatter(
                name=label,
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(color="#dddddd", size=11, symbol=symbol),
                hoverinfo="skip",
                showlegend=True,
            )
        )
 
    fig.update_yaxes(showticklabels=False)
    max_label_len = max(len(str(var)) for var in coef_df["independent_variable"])
    left_margin = 60 + max_label_len * 7
    for var in coef_df["independent_variable"]:
        fig.add_annotation(
            xref="paper", yref="y",
            x=-0.01, y=var,
            xanchor="right", yanchor="middle",
            text=var,
            showarrow=False,
            font=dict(color=_variable_color(var), size=12),
        )
 
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        title={
            "text": (
                f"<b>OLS Regression Summary Results</b><br>"
                f"<span style='font-size: 15px; color: #b0b0b0;'>{graph_title} Prop Market | Dependent Variable = <b>{y_var}</b> | Covariance Clustered by Market (ticker)</span>"
            ),
            "font": {"size": 20, "color": "#ffffff"},
            "x": 0.5,
            "xanchor": "center",
        },
        xaxis=dict(
            title="Beta Coefficient",
            zeroline=True,
            zerolinecolor="#888888",
            zerolinewidth=1.5,
        ),
        yaxis_title=None,
        legend=dict(
            title="Significance",
            x=1.02, y=1,
            xanchor="left", yanchor="top",
            bgcolor="rgba(0,0,0,0.35)",
            bordercolor="#444444",
            borderwidth=1,
        ),
        margin=dict(l=left_margin, r=220),
        height=400 + (len(X_vars) * 35),
    )
 
    fig.show()
    return None

def graph_regression_by_threshold(
    df: pd.DataFrame,
    side: str,
    graph_title: str,
    n_req_trades: int = 500,
    show_const: bool = False,
    ci: float = 0.95,
) -> None:
    """
    Standardizes 'log_n_trades_in_market', 'log_count_fp', and 'market_completion_pct'.
    Then performs a multivariable regression with covariance clustered by ticker, and 
    plots the coefficients by series threshold.
 
    Args:
        df: DataFrame containing the data.
        side: 'maker' or 'taker'.
        graph_title: Graph title for series.
        n_req_trades: Strict minimum number of required trades, default 500.
        show_const: Whether to include the regression constant as its own bar, default False.
        ci: Confidence level for the coefficient error bars, default 0.95.
 
    Returns:
        None. Displays forest plot using plotly figure.
    """
    variables_to_scale = ['log_n_trades_in_market', 'log_count_fp', 'market_completion_pct']
    scaled_variable_names = ["scaled_" + var for var in variables_to_scale]

    X_vars = scaled_variable_names + ['is_post_kickoff_dummy', f'{side}_outcome_side_dummy']
    y_var = f'{side}_pnl_per_contract'

    required_cols = (
        variables_to_scale
        + ['is_post_kickoff_dummy', f'{side}_outcome_side_dummy', y_var, 'ticker', "series_threshold"]
    )

    all_thresholds = sorted(df["series_threshold"].dropna().unique())
    invalid_thresholds = []
    all_coef_dfs = []
    passed_thresholds = []

    for threshold in all_thresholds:
        sub_df = df[df["series_threshold"] == threshold]
        clean_df = sub_df[required_cols].dropna(how='any').copy()

        n_trades = len(clean_df)
        if n_trades < n_req_trades:
            invalid_thresholds.append(threshold)
            continue

        clean_df[scaled_variable_names] = (
            (clean_df[variables_to_scale] - clean_df[variables_to_scale].mean())
            / clean_df[variables_to_scale].std(ddof=0)
        )

        y = clean_df[y_var]
        X = clean_df[X_vars]
        X = sm.add_constant(X, has_constant='add')

        model = sm.OLS(endog=y, exog=X)
        results_clustered = model.fit(cov_type="cluster", cov_kwds={"groups": clean_df["ticker"]})
        results_naive = model.fit(cov_type="nonrobust")

        coef_df = pd.DataFrame(
            {
                "independent_variable": results_clustered.params.index,
                "beta": results_clustered.params.values,
                "p_value": results_clustered.pvalues.values,
                "std_err": results_clustered.bse.values,
                "t_stat": results_clustered.tvalues.values,
                "std_err_naive": results_naive.bse.values,
                "t_stat_naive": results_naive.tvalues.values,
                "p_value_naive": results_naive.pvalues.values,
            }
        )
        coef_df["se_inflation"] = coef_df["std_err"] / coef_df["std_err_naive"]

        if not show_const:
            coef_df = coef_df[coef_df["independent_variable"] != "const"].reset_index(drop=True)

        if coef_df.empty:
            continue

        n_clusters = clean_df["ticker"].nunique()
        t_crit = stats.t.ppf(ci + (1 - ci) / 2, df=n_clusters - 1)
        coef_df["ci_margin"] = t_crit * coef_df["std_err"]
        coef_df["ci_lower"] = coef_df["beta"] - coef_df["ci_margin"]
        coef_df["ci_upper"] = coef_df["beta"] + coef_df["ci_margin"]
        coef_df["threshold"] = threshold
        coef_df["n_trades"] = n_trades

        all_coef_dfs.append(coef_df)
        passed_thresholds.append(threshold)

    if not all_coef_dfs:
        print("No thresholds met the minimum trade requirement.")
        return None

    full_df = pd.concat(all_coef_dfs, ignore_index=True)

    var_order = [v for v in (['const'] + X_vars if show_const else X_vars) if v in full_df["independent_variable"].unique()]
    threshold_labels = [str(t) for t in passed_thresholds]

    fig = go.Figure()

    hovertemplate = (
        "<b>Independent Variable:</b> %{customdata[9]}<br>"
        "<b>Series Threshold:</b> %{customdata[11]}<br>"
        "<b>N trades:</b> %{customdata[10]:,}<br>"
        "<b>Beta:</b> %{x:.4f}<br>"
        f"<b>{ci * 100:.0f}% CI:</b> [" + "%{customdata[7]:.4f}, %{customdata[8]:.4f}]<br>"
        "<br><b>Clustered (by ticker):</b><br>"
        "p-value: %{customdata[0]:.4f}<br>"
        "Std Error: %{customdata[1]:.4f}<br>"
        "t-statistic: %{customdata[2]:.2f}<br>"
        "<br><b>Naive (non-clustered):</b><br>"
        "p-value: %{customdata[3]:.4f}<br>"
        "Std Error: %{customdata[4]:.4f}<br>"
        "t-statistic: %{customdata[5]:.2f}<br>"
        "<br><b>SE inflation (clustered / naive):</b> %{customdata[6]:.2f}x"
        "<extra></extra>"
    )

    row_labels = []
    for var in reversed(var_order):
        for t_label in threshold_labels:
            row_labels.append(f"{var}  |  {t_label}")

    band_shapes = []
    n_thr = len(threshold_labels)
    for i, var in enumerate(reversed(var_order)):
        if i % 2 == 1:
            continue
        y0 = i * n_thr - 0.5
        y1 = (i + 1) * n_thr - 0.5
        band_shapes.append(
            dict(
                type="rect",
                xref="paper", yref="y",
                x0=0, x1=1, y0=y0, y1=y1,
                fillcolor="rgba(255,255,255,0.03)",
                line=dict(width=0),
                layer="below",
            )
        )

    def _significance_symbol(p: float) -> str:
        if p < 0.01:
            return "star"
        elif p < 0.05:
            return "square"
        elif p < 0.10:
            return "circle"
        else:
            return "circle-open"

    for var in var_order:
        v_df = (
            full_df[full_df["independent_variable"] == var]
            .set_index("threshold")
            .reindex(passed_thresholds)
            .reset_index()
        )
        v_df["threshold_label"] = v_df["threshold"].apply(lambda t: str(t) if pd.notna(t) else None)
        v_df = v_df.dropna(subset=["beta"])
        if v_df.empty:
            continue

        v_df["row_label"] = v_df["threshold_label"].apply(lambda t: f"{var}  |  {t}")
        marker_symbols = v_df["p_value"].apply(_significance_symbol)

        fig.add_trace(
            go.Scatter(
                name=var,
                x=v_df["beta"],
                y=v_df["row_label"],
                mode="markers",
                marker=dict(color=_variable_color(var), size=11, symbol=marker_symbols),
                error_x=dict(
                    type="data",
                    symmetric=False,
                    array=v_df["ci_upper"] - v_df["beta"],
                    arrayminus=v_df["beta"] - v_df["ci_lower"],
                    color=_variable_color(var),
                    thickness=1.5,
                    width=4,
                ),
                hovertemplate=hovertemplate,
                customdata=v_df.assign(independent_variable=var)[[
                    "p_value", "std_err", "t_stat",
                    "p_value_naive", "std_err_naive", "t_stat_naive",
                    "se_inflation", "ci_lower", "ci_upper", "independent_variable", "n_trades",
                    "threshold_label",
                ]].values,
                showlegend=False,
            )
        )

    significance_legend = [
        ("p < 0.01", "star"),
        ("p < 0.05", "square"),
        ("p < 0.10", "circle"),
        ("p \u2265 0.10", "circle-open"),
    ]
    for label, symbol in significance_legend:
        fig.add_trace(
            go.Scatter(
                name=label,
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(color="#dddddd", size=11, symbol=symbol),
                hoverinfo="skip",
                showlegend=True,
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        title={
            "text": (
                f"<b>OLS Regression Summary Results by Series Threshold</b><br>"
                f"<span style='font-size: 15px; color: #b0b0b0;'>{graph_title} Prop Market | Dependent Variable = <b>{y_var}</b> | Covariance Clustered by Market (ticker)</span>"
            ),
            "font": {"size": 20, "color": "#ffffff"},
            "x": 0.5,
            "xanchor": "center",
        },
        xaxis=dict(
            title="Beta Coefficient",
            zeroline=True,
            zerolinecolor="#888888",
            zerolinewidth=1.5,
        ),
        yaxis=dict(
            title="Independent Variable  |  Series Threshold",
            type="category",
            categoryorder="array",
            categoryarray=row_labels,
        ),
        shapes=band_shapes,
        legend=dict(
            title="Significance",
            x=1.02, y=1,
            xanchor="left", yanchor="top",
            bgcolor="rgba(0,0,0,0.35)",
            bordercolor="#444444",
            borderwidth=1,
        ),
        margin=dict(r=220, l=260),
        height=max(600, 40 * len(row_labels) + 200),
    )

    if invalid_thresholds:
        print(f"Invalid Series Threshold: {invalid_thresholds} do not have {n_req_trades} required trades.")

    fig.show()
    return None