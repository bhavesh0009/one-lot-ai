import React, { useState } from 'react';
import { Brain, Clock, RefreshCw, ShieldAlert, CheckCircle2, Activity, Target, Newspaper } from 'lucide-react';
import { useStockData } from './hooks/useStockData';
import TradeCard from './components/TradeCard';
import StockChart from './components/StockChart';
import OptionChain from './components/OptionChain';
import TickerSearch from './components/TickerSearch';

export default function App() {
  const { data, loading, error, logs, loadStockData } = useStockData();

  const handleSelect = (symbol) => {
    loadStockData(symbol);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-emerald-500/30">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-cyan-600 rounded-lg flex items-center justify-center">
              <Brain className="text-white w-5 h-5" />
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
              One Lot AI
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-400">
            {/* Mock Market Status for now */}
            <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> Market Open</span>
            <div className="w-px h-4 bg-slate-800"></div>
            <span className="text-emerald-500 font-medium">NIFTY (Live)</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Search Section */}
        <div className="flex justify-center mb-12">
          <TickerSearch onSelect={handleSelect} loading={loading} />
        </div>

        {/* Loading / Status State */}
        {loading && (
          <div className="max-w-2xl mx-auto mb-12">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl">
              <h3 className="text-lg font-medium text-emerald-400 mb-4 flex items-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin" />
                AI Analysis in Progress
              </h3>
              <div className="space-y-2 font-mono text-sm max-h-48 overflow-y-auto">
                {logs.map((log, idx) => (
                  <div key={idx} className="flex gap-3 text-slate-400 animate-in fade-in slide-in-from-left-2">
                    <span className="text-slate-600">{log.time}</span>
                    <span>{log.msg}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto mb-12 text-center text-red-500 bg-red-500/10 p-4 rounded-xl border border-red-500/20">
            {error}
          </div>
        )}

        {/* Main Dashboard */}
        {!loading && data && (
          <div className="grid grid-cols-12 gap-6 animate-in fade-in zoom-in-95 duration-500">

            {/* Left Column: Ticker Info & Technicals */}
            <div className="col-span-12 lg:col-span-3 space-y-6">
              {/* Ticker Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-bold text-white">{data.basic.symbol}</h2>
                    <span className="text-slate-500 text-sm">{data.basic.sector}</span>
                  </div>
                  {/* Ban Status Logic: Check if there's a recent ban entry */}
                  {/* Note: data.banStatus is the row from fno_ban_period. If it exists, check date. 
                       For now, if it's there, we assume it might be banned. 
                       Ideally backend filters by date. check endpoints.py logic again. */}
                  {data.banStatus ? (
                    <span className="px-3 py-1 bg-red-500/20 text-red-400 text-xs font-bold rounded-full flex items-center gap-1 border border-red-500/30">
                      <ShieldAlert className="w-3 h-3" /> F&O BAN
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 text-xs font-bold rounded-full flex items-center gap-1 border border-emerald-500/30">
                      <CheckCircle2 className="w-3 h-3" /> ACTIVE
                    </span>
                  )}
                </div>
                <div className="flex items-end gap-3 mb-2">
                  <span className="text-4xl font-bold text-white">₹{data.latest_ohlcv.close}</span>
                  {data.change !== undefined && (
                    <div className="flex items-center gap-1 mb-1">
                      <span className={`text-sm font-medium ${data.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data.change >= 0 ? '+' : ''}{data.change}
                      </span>
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${data.change_pct >= 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                        {data.change_pct >= 0 ? '+' : ''}{data.change_pct}%
                      </span>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4 mt-6 pt-6 border-t border-slate-800">
                  <div>
                    <div className="text-slate-500 text-xs uppercase">Lot Size</div>
                    <div className="text-slate-200 font-mono">{data.basic.lot_size}</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-xs uppercase">Volume</div>
                    <div className="text-slate-200 font-mono">{(data.latest_ohlcv.volume / 100000).toFixed(2)}L</div>
                  </div>
                </div>
              </div>

              {/* Technicals Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-slate-400 font-medium mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4" /> Technical Indicators
                </h3>
                {data.technicals && (
                  <div className="space-y-5">
                    {/* Momentum */}
                    <div>
                      <div className="text-xs text-slate-600 uppercase font-semibold mb-2 tracking-wider">Momentum</div>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-slate-500">RSI (14)</span>
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.min(data.technicals.rsi || 0, 100)}%` }}></div>
                            </div>
                            <span className={`text-sm font-mono ${data.technicals.rsi > 70 ? 'text-red-400' : data.technicals.rsi < 30 ? 'text-emerald-400' : 'text-slate-300'}`}>
                              {data.technicals.rsi?.toFixed(1)}
                            </span>
                          </div>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-slate-500">MACD</span>
                          <span className={`text-sm font-mono ${data.technicals.macd > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {data.technicals.macd?.toFixed(2)}
                          </span>
                        </div>
                        {data.technicals.supertrend && (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-slate-500">Supertrend</span>
                            <span className={`text-sm font-mono ${data.latest_ohlcv.close > data.technicals.supertrend ? 'text-emerald-400' : 'text-red-400'}`}>
                              {data.technicals.supertrend?.toFixed(2)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Trend - SMAs */}
                    <div className="border-t border-slate-800 pt-4">
                      <div className="text-xs text-slate-600 uppercase font-semibold mb-2 tracking-wider">Moving Averages</div>
                      <div className="space-y-3">
                        {[{ label: 'SMA 20', key: 'sma_20' }, { label: 'SMA 50', key: 'sma_50' }, { label: 'SMA 200', key: 'sma_200' }].map(({ label, key }) => {
                          const sma = data.technicals[key];
                          const above = sma ? data.latest_ohlcv.close > sma : null;
                          return sma ? (
                            <div key={key} className="flex justify-between items-center">
                              <span className="text-sm text-slate-500">{label}</span>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-mono text-slate-300">₹{sma.toFixed(1)}</span>
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${above ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                                  {above ? '▲' : '▼'}
                                </span>
                              </div>
                            </div>
                          ) : null;
                        })}
                      </div>
                    </div>

                    {/* 52-Week */}
                    <div className="border-t border-slate-800 pt-4">
                      <div className="text-xs text-slate-600 uppercase font-semibold mb-2 tracking-wider">52-Week Range</div>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-slate-500">From 52W High</span>
                          <span className={`text-sm font-mono ${data.technicals.dist_52w_high >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {data.technicals.dist_52w_high?.toFixed(1)}%
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-slate-500">From 52W Low</span>
                          <span className={`text-sm font-mono ${data.technicals.dist_52w_low >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            +{data.technicals.dist_52w_low?.toFixed(1)}%
                          </span>
                        </div>
                        {/* Visual range bar */}
                        {data.technicals.low_52w && data.technicals.high_52w && (
                          <div>
                            <div className="flex justify-between text-[10px] text-slate-600 mb-1">
                              <span>₹{data.technicals.low_52w}</span>
                              <span>₹{data.technicals.high_52w}</span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-800 rounded-full relative">
                              <div
                                className="absolute h-3 w-1 bg-cyan-400 rounded-full top-1/2 -translate-y-1/2"
                                style={{ left: `${Math.min(Math.max(((data.latest_ohlcv.close - data.technicals.low_52w) / (data.technicals.high_52w - data.technicals.low_52w)) * 100, 0), 100)}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Volume */}
                    <div className="border-t border-slate-800 pt-4">
                      <div className="text-xs text-slate-600 uppercase font-semibold mb-2 tracking-wider">Volume</div>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-slate-500">Delivery %</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-mono text-slate-300">{data.technicals.delivery_pct?.toFixed(1)}%</span>
                            {data.technicals.avg_delivery_pct_20 && (
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${data.technicals.delivery_pct > data.technicals.avg_delivery_pct_20
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : 'bg-amber-500/20 text-amber-400'
                                }`}>
                                avg {data.technicals.avg_delivery_pct_20?.toFixed(1)}%
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Middle Column: Visuals & Trade Logic */}
            <div className="col-span-12 lg:col-span-9 space-y-6">
              {/* Chart */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden relative group p-4">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-slate-400 font-medium flex items-center gap-2">
                    <Activity className="w-4 h-4" /> Price Action (Last Year)
                  </h3>
                </div>
                <StockChart data={data.history || []} ticker={data.basic.symbol} />
              </div>

              {/* Option Chain */}
              <OptionChain data={data.chain} />

              {/* AI Trade Card (Mocked) */}
              <TradeCard
                type={data.recommendation.type}
                data={data.recommendation}
              />

              {/* LLM Reasoning (Placeholder) */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-slate-400 font-medium mb-4 flex items-center gap-2">
                  <Target className="w-4 h-4" /> AI Reasoning
                </h3>
                <div className="text-sm text-slate-300 space-y-3 leading-relaxed">
                  Analysis based on latest data... (LLM integration pending in next phase).
                  <br />
                  RSI is {data.technicals.rsi?.toFixed(2)}, indicating {data.technicals.rsi > 70 ? 'Overbought' : data.technicals.rsi < 30 ? 'Oversold' : 'Neutral'} territory.
                </div>
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}
