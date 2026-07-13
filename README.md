## Project Overview

One problem in trading on prediction markets is the sheer number of live and historical markets. From the perspective of a trader or researcher seeking edge, choosing which market segment to focus on can be challenging. In this project I analyze NBA, MLB, and NFL player proposition markets on Kalshi, using historical pre-game pricing and market-maker economics to determine which sports proposition markets exhibit systematic favorite-longshot bias. Sports markets were chosen due to [a strong underlying bias observed in retail traders](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5502658), along with my personal interest in sports. The project is currently in-progress, check back soon for more!

Each player proposition market is analyzed through:
1. **Hit Rates**: Historical hit rates are compared against pre-game pricing
2. **Liquidity Simulation**: A market maker providing fixed-size liquidity is simulated at a naive fill price
3. **Market Size**: Dollar volume, trade count, and market count

## Findings

- **[NBA Prop Markets](https://github.com/henrycosentino/player_props/blob/main/nba/analysis.ipynb)** (complete)
  - **Double Double** (12-03-2025 – 06-13-2026): markets favor selling 'yes' contracts (buying 'no') pre-game
  - **Triple Double** (12-03-2025 – 06-13-2026): markets marginally favor selling 'yes' contracts pre-game
  - **Threes** (11-18-2025 – 06-13-2026): $2+$ markets favor selling 'yes' contracts pre-game, while other thresholds are mixed until the 2025-26 playoffs/finals, when they begin to exhibit a bias toward selling 'yes'
  - **Steals** (01-13-2026 – 06-13-2026): markets marginally favor selling 'yes' contracts pre-game, but have limited volume and markets
  - **Blocks** (01-13-2026 – 06-13-2026): markets, in aggregate, very marginally favor selling 'yes', but have limited volume and markets
  - **Points** (11-18-2025 – 06-13-2026): $10+$, $20+$, $25+$, and $30+$ markets favor selling 'yes' contracts pre-game; the remaining thresholds have limited volume and markets
  - **Assists** (11-18-2025 – 06-13-2026): markets, in aggregate, very marginally favor selling 'yes'
  - **Rebounds** (11-18-2025 – 06-13-2026): $6+$ and $10+$ markets favor selling 'yes'; the remaining thresholds are mixed, and some have limited volume and markets
- **[MLB Prop Markets](https://github.com/henrycosentino/player_props/blob/main/mlb/analysis.ipynb)** (complete)
  - **Home Run** (03-23-2026 – 07-11-2026): $1+$ markets display minimal bias, while $2+$ and $3+$ markets favor selling 'yes' but are skewed by orderbook sweeps
  - **Strikeout** (03-23-2026 – 07-11-2026): markets are mixed, with no clear bias
  - **Hit** (03-24-2026 – 07-11-2026): $2+$ markets are mixed, with no clear bias; $3+$ markets favor selling 'yes' but have limited dollar volume
  - **Hits + Runs + RBI** (03-24-2026 – 07-11-2026): $2+$, $3+$, $4+$, and $5+$ markets favor selling 'yes', while $1+$ markets show no clear bias
  - **Total Bases** (03-24-2026 – 07-11-2026): markets favor selling 'yes'; in particular, $2+$ markets exhibit a strong simulated upward wealth path with favorable statistics
  - **Outs** (06-22-2026 – 07-11-2026): markets have low trade count and thus low dollar volume; results are mixed, with no clear bias
  - **RBI** (06-22-2026 – 07-11-2026): $1+$ markets favor selling 'yes', but all three thresholds ($1+$, $2+$, $3+$) have low trade count and thus low dollar volume
  - **Stolen Base** (06-22-2026 – 07-11-2026): $1+$ markets favor selling 'yes', but have low trade count and thus low dollar volume
- **[NFL Prop Markets](https://github.com/henrycosentino/player_props/blob/main/nfl/analysis.ipynb)** (in-progress)

### Data Sources

- **[Kalshi](https://kalshi.com/)**: Historical market and trade data
- **[NBA API](https://www.nba.com/)**: Basketball game data

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