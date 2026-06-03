export interface User {
  name: string
  username: string
}

export interface IndexData {
  index: number
  change_val: number
  change_rate: number
  open: number
  high: number
  low: number
  volume: number
}

export interface StockPrice {
  stock_code: string
  stock_name: string
  price: number
  change_rate: number
  volume: number
  high: number
  low: number
  open: number
  error?: boolean
}

export interface MarketPricesResponse {
  mode: string
  indices: {
    kospi: IndexData | null
    kosdaq: IndexData | null
  }
  stocks: StockPrice[]
}

export interface BalanceItem {
  stock_code: string
  stock_name: string
  quantity: number
  avg_price: number
  current_price: number
  eval_profit_loss: number
  profit_loss_rate: number
  exchange?: string
  currency?: string
}

export interface RankItem {
  rank: number
  stock_code: string
  stock_name: string
  name?: string
  price: number
  change_rate: number
  change_val: number
  volume: number
  change_sign: string
}

export interface OverseasStock {
  stock_code: string
  exchange: string
  name: string
  price: number
  change_rate: number
  open: number
  high: number
  low: number
  volume: number
}

export interface Strategy {
  id: number
  name: string
  stock_code: string
  stock_name: string
  exchange: string
  strategy_type: string
  params: Record<string, unknown>
  is_active: boolean
  mode: string
  created_at: string
}

export interface ChartCandle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  ma_short: number
  ma_long: number
  ma60: number
  rsi: number
  macd: number
  macd_signal: number
  macd_hist: number
  vol_ma20: number
}

export interface ChartData {
  candles: ChartCandle[]
  params: Record<string, number>
  error?: string
}

export interface ChartEvent {
  time: string
  direction: string
  change_pct: number
  price: number
  news: string[]
  reason: string
}

export interface BacktestTrade {
  time: string
  type: string
  price: number
  qty: number
  reason: string
  pnl: number
}

export interface BacktestResult {
  stock_name: string
  strategy_type: string
  period: string
  total_return: number
  buy_hold_return: number
  win_rate: number
  total_trades: number
  max_drawdown: number
  final_equity: number
  equity_curve: { time: string; value: number }[]
  buy_hold_curve: { time: string; value: number }[]
  trades: BacktestTrade[]
  error?: string
}

export interface Order {
  id: number
  strategy_id: number | null
  stock_code: string
  order_type: string
  price: number
  quantity: number
  status: string
  trigger: string
  mode: string
  kis_order_no: string
  created_at: string
}

export interface AuctionAlert {
  id: number | null
  stock_code: string
  stock_name: string
  suggested_action: string
  suggested_price: number
  suggested_qty: number
  ai_confidence: number
  ai_score: number
  ai_summary: string
  ai_factors: AiFactor[]
  expires_at: string
}

export interface AiFactor {
  name: string
  score: number
  reason: string
}

export interface EsgScore {
  stock_code: string
  stock_name: string
  total_grade: string
  env_grade: string
  social_grade: string
  gov_grade: string
  score: number
  data_year: number
  available: boolean
}

export interface AuditLog {
  id: number
  action: string
  stock_code: string
  stock_name: string
  price: number
  quantity: number
  mode: string
  reason: string
  ai_score: number | null
  ai_summary: string
  esg_grade: string
  user: string
  created_at: string
}

export interface InvestLimit {
  daily_limit: number
  monthly_limit: number
  per_order_limit: number
  esg_min_grade: string
}
