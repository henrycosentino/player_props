## Project Overview

One challenge in trading on prediction markets is the sheer number of live and historical markets. From the perspective of a trader or researcher seeking edge, choosing which market segment to focus on can be difficult.

In this project, I examine bias in NBA, MLB, and NFL player proposition markets on Kalshi. I compare pre-game market pricing to realized hit rates using a paired-sample t-test to assess the accuracy of pre-game pricing. I also conduct a multivariable regression analysis to determine the effect that _side_, _market maturity_, _contract size_, _market size_,  and _order fill dispersion_ have on realized profit and loss for makers and takers. Sports markets were chosen due to the strong underlying bias observed in retail traders, along with my personal interest in sports.

This work builds on [the findings of Constantin Bürgi, Wanying Deng, and Karl Whelan](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5502658).

Each proposition market segment is analyzed through:

1. **Market Analysis**: Taker and maker PnL and returns are analyzed.
2. **Hit Rates**: Hit rates are compared to pre-game market implied probability of outcome.
3. **Regression Analysis**: Understanding how _side_, _market maturity_, _contract size_, _market size_,  and _order fill dispersion_ affect realized profit and loss for makers and takers.

## Key Findings

- **[MLB Prop Markets](https://github.com/henrycosentino/player_props/blob/main/mlb/analysis.ipynb)** 
    - Analysis in progress, check back later.
- **[NBA Prop Markets](https://github.com/henrycosentino/player_props/blob/main/nba/analysis.ipynb)**
    - Analysis in progress, check back later for more.
    - Total Maker PnL (after fees): $4,367,271.02.
    - Total Taker PnL (after fees): -$7,167,768.43.
    - Pre-game market implied probability of outcomes is structurally higher than observed hit rates.
    - Please refer to the [notebook](https://github.com/henrycosentino/player_props/blob/main/nfl/analysis.ipynb) for in-depth analysis, covering: Double Double, Triple Double, Threes, Steals, Blocks, Points, Assists, and Rebounds markets. 
- **[NFL Prop Markets](https://github.com/henrycosentino/player_props/blob/main/nfl/analysis.ipynb)** 
    - Total Maker PnL (after fees): $5,727,652.91.
    - Total Taker PnL (after fees): -$9,379,285.79.
    - Pre-game market implied probability of outcomes is structurally higher than observed hit rates.
    - Makers earn less on the 'Yes' outcome side; makers tend to earn more in markets with more trades, and larger trades (by trade count) are associated with lower maker profit. Regarding order fill dispersion, makers tend to profit modestly more when fills cut deeper through the order book, and modestly less when fills are spread across a wider breadth of prices. Market maturity has no observable effect on maker PnL.
    - Due to the strong relationship between maker and taker PnL, taker PnL dynamics nearly inversely mirror maker PnL dynamics. Takers earn less on the 'Yes' outcome side; takers tend to earn less in markets with more trades, and larger trades (by trade count) are associated with higher taker profit. Regarding order fill dispersion, takers tend to profit modestly less when fills cut deeper through the order book, and modestly more when fills are spread across a wider breadth of prices. Market maturity has no observable effect on taker PnL.
    - Please refer to the [notebook](https://github.com/henrycosentino/player_props/blob/main/nfl/analysis.ipynb) for in-depth analysis, covering: Anytime Touchdown, Two Plus Touchdown, Rushing Yard, Receiving Yard, Passing Yard, Passing Touchdown, and Receptions markets. 

### Data Sources

- **[Kalshi](https://kalshi.com/)**: Historical market and trade data
- **[NBA API](https://www.nba.com/)**: Basketball game data
- **[NFL API](https://www.nfl.com/)**: Football game data

## Setup

To fully view the analysis, you need to install the project and its dependencies.

### 1. Install Git LFS

```bash
brew install git-lfs
git lfs install
```

### 2. Clone the Repository

```bash
git clone https://github.com/henrycosentino/player_props.git
cd player_props
```

### 3. Install the Project

```bash
pip install -e .
```

### 4. Explore!