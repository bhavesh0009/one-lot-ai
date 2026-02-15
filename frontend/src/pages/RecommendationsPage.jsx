import React, { useState, useEffect, useMemo } from 'react';
import { ChevronDown, RefreshCw } from 'lucide-react';
import { fetchRecommendations } from '../libs/api';

// Helper function to safely convert and format numbers
const toNumber = (val) => {
  const num = typeof val === 'string' ? parseFloat(val) : val;
  return !isNaN(num) && num !== null && num !== undefined ? num : null;
};

const formatCurrency = (val, decimals = 2) => {
  const num = toNumber(val);
  return num !== null ? `₹${num.toFixed(decimals)}` : 'N/A';
};

const formatConfidence = (val) => {
  const num = toNumber(val);
  // Confidence is already 0-100, no need to multiply
  return num !== null ? `${num.toFixed(0)}%` : 'N/A';
};

const formatRatio = (val) => {
  // Risk:reward ratio comes as a string like "1:2" or needs to be parsed
  if (!val) return 'N/A';
  if (typeof val === 'string') return val; // Already formatted as "1:X"
  const num = toNumber(val);
  return num !== null ? `${num.toFixed(2)}:1` : 'N/A';
};

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterTicker, setFilterTicker] = useState('');
  const [filterDirection, setFilterDirection] = useState('ALL');
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [expandedRow, setExpandedRow] = useState(null);

  useEffect(() => {
    loadRecommendations();
  }, []);

  const loadRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecommendations(100);
      setRecommendations(data || []);
    } catch (e) {
      console.error('Failed to load recommendations:', e);
      setError('Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  };

  // Extract unique tickers for filter dropdown
  const uniqueTickers = useMemo(() => {
    const tickers = new Set(recommendations.map((r) => r.ticker));
    return Array.from(tickers).sort();
  }, [recommendations]);

  // Filter and sort logic
  const filteredRecommendations = useMemo(() => {
    let filtered = recommendations.filter((rec) => {
      if (filterTicker && rec.ticker !== filterTicker) return false;
      if (filterDirection !== 'ALL' && rec.direction !== filterDirection) return false;
      return true;
    });

    // Sort
    filtered.sort((a, b) => {
      let aVal, bVal;

      switch (sortBy) {
        case 'date':
          aVal = new Date(a.timestamp || a.created_at || 0).getTime();
          bVal = new Date(b.timestamp || b.created_at || 0).getTime();
          break;
        case 'confidence':
          aVal = a.confidence || 0;
          bVal = b.confidence || 0;
          break;
        case 'risk_reward':
          aVal = a.risk_reward_ratio || 0;
          bVal = b.risk_reward_ratio || 0;
          break;
        case 'ticker':
          aVal = a.ticker;
          bVal = b.ticker;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [recommendations, filterTicker, filterDirection, sortBy, sortOrder]);

  const toggleExpand = (id) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', { year: '2-digit', month: 'short', day: 'numeric' });
  };

  const formatTime = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  };

  const getDirectionColor = (direction) => {
    switch (direction) {
      case 'BULLISH':
        return 'text-emerald-400 bg-emerald-500/10';
      case 'BEARISH':
        return 'text-red-400 bg-red-500/10';
      case 'NEUTRAL':
        return 'text-slate-300 bg-slate-500/10';
      default:
        return 'text-slate-300';
    }
  };

  return (
    <main className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">All AI Trade Recommendations</h1>
        <p className="text-slate-400">Historical recommendations for forward testing and analysis</p>
      </div>

      {/* Filters Row */}
      <div className="mb-6 flex flex-wrap gap-4 items-end">
        {/* Ticker Filter */}
        <div className="flex flex-col gap-2">
          <label className="text-xs uppercase text-slate-500 font-semibold">Ticker</label>
          <select
            value={filterTicker}
            onChange={(e) => setFilterTicker(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Tickers</option>
            {uniqueTickers.map((ticker) => (
              <option key={ticker} value={ticker}>
                {ticker}
              </option>
            ))}
          </select>
        </div>

        {/* Direction Filter */}
        <div className="flex flex-col gap-2">
          <label className="text-xs uppercase text-slate-500 font-semibold">Direction</label>
          <div className="flex gap-2">
            {['ALL', 'BULLISH', 'BEARISH', 'NEUTRAL'].map((dir) => (
              <button
                key={dir}
                onClick={() => setFilterDirection(dir)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filterDirection === dir
                    ? dir === 'BULLISH'
                      ? 'bg-emerald-500 text-white'
                      : dir === 'BEARISH'
                      ? 'bg-red-500 text-white'
                      : dir === 'NEUTRAL'
                      ? 'bg-slate-600 text-white'
                      : 'bg-slate-700 text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {dir}
              </button>
            ))}
          </div>
        </div>

        {/* Sort Dropdown */}
        <div className="flex flex-col gap-2">
          <label className="text-xs uppercase text-slate-500 font-semibold">Sort By</label>
          <div className="flex gap-2">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="date">Date</option>
              <option value="confidence">Confidence</option>
              <option value="risk_reward">Risk:Reward</option>
              <option value="ticker">Ticker</option>
            </select>

            <button
              onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800 transition-colors"
              title={`Sort ${sortOrder === 'desc' ? 'Ascending' : 'Descending'}`}
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>

        {/* Refresh Button */}
        <button
          onClick={loadRecommendations}
          disabled={loading}
          className="ml-auto px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-3" />
          Loading recommendations...
        </div>
      ) : error ? (
        <div className="bg-slate-900 border border-red-500/30 rounded-xl p-6 text-center text-red-400 bg-red-500/10">
          {error}
        </div>
      ) : filteredRecommendations.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400">
          No recommendations found
        </div>
      ) : (
        <div className="overflow-x-auto border border-slate-800 rounded-xl">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Ticker</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Direction</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Strategy</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Confidence</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Entry</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Target</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">SL</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">R:R</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecommendations.map((rec) => (
                <React.Fragment key={rec.id}>
                  {/* Main Row */}
                  <tr
                    onClick={() => toggleExpand(rec.id)}
                    className="border-b border-slate-800 hover:bg-slate-900/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm text-slate-300 font-mono">
                      <div>{formatDate(rec.timestamp || rec.created_at)}</div>
                      <div className="text-xs text-slate-500">{formatTime(rec.timestamp || rec.created_at)}</div>
                    </td>
                    <td className="px-4 py-3 text-sm font-bold text-white">{rec.ticker}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDirectionColor(rec.direction)}`}>
                        {rec.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300">{rec.strategy || 'N/A'}</td>
                    <td className="px-4 py-3 text-sm font-mono">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-amber-500 rounded-full"
                            style={{ width: `${Math.min((toNumber(rec.confidence) || 0), 100)}%` }}
                          ></div>
                        </div>
                        <span className="text-amber-400">{formatConfidence(rec.confidence)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-emerald-400">{formatCurrency(rec.entry_price, 2)}</td>
                    <td className="px-4 py-3 text-sm font-mono text-emerald-300">{formatCurrency(rec.target, 2)}</td>
                    <td className="px-4 py-3 text-sm font-mono text-red-400">{formatCurrency(rec.stop_loss, 2)}</td>
                    <td className="px-4 py-3 text-sm font-mono">
                      <span className="text-cyan-400">{formatRatio(rec.risk_reward_ratio)}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <button className="text-emerald-400 hover:text-emerald-300 font-medium text-xs">
                        {expandedRow === rec.id ? 'COLLAPSE' : 'EXPAND'}
                      </button>
                    </td>
                  </tr>

                  {/* Expanded Details Row */}
                  {expandedRow === rec.id && (
                    <tr className="border-b border-slate-800 bg-slate-900/30">
                      <td colSpan="10" className="px-4 py-4">
                        <div className="space-y-4">
                          {/* Trade Legs */}
                          {rec.trades && rec.trades.length > 0 && (
                            <div>
                              <h4 className="text-sm font-semibold text-emerald-400 mb-2">Trade Legs</h4>
                              <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="text-slate-500 border-b border-slate-700">
                                      <th className="px-2 py-2 text-left">Action</th>
                                      <th className="px-2 py-2 text-left">Strike</th>
                                      <th className="px-2 py-2 text-left">Option</th>
                                      <th className="px-2 py-2 text-left">Expiry</th>
                                      <th className="px-2 py-2 text-left">Price</th>
                                      <th className="px-2 py-2 text-left">Lots</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {rec.trades.map((trade, idx) => (
                                      <tr key={idx} className="border-b border-slate-800">
                                        <td className={`px-2 py-2 font-mono ${trade.action === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>
                                          {trade.action}
                                        </td>
                                        <td className="px-2 py-2 text-slate-300 font-mono">{trade.strike || 'N/A'}</td>
                                        <td className="px-2 py-2 text-slate-300 font-semibold">{trade.option_type || 'N/A'}</td>
                                        <td className="px-2 py-2 text-slate-300 font-mono">{trade.expiry || 'N/A'}</td>
                                        <td className="px-2 py-2 text-slate-300 font-mono">{formatCurrency(trade.price, 2)}</td>
                                        <td className="px-2 py-2 text-slate-300 font-mono">{trade.lots || 'N/A'}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {/* Rationale */}
                          {rec.rationale && (
                            <div>
                              <h4 className="text-sm font-semibold text-emerald-400 mb-2">Rationale</h4>
                              <p className="text-sm text-slate-300 bg-slate-950/50 p-3 rounded border border-slate-800">
                                {rec.rationale}
                              </p>
                            </div>
                          )}

                          {/* Risks */}
                          {rec.risks && rec.risks.length > 0 && (
                            <div>
                              <h4 className="text-sm font-semibold text-red-400 mb-2">Risks</h4>
                              <ul className="text-sm text-slate-300 space-y-1">
                                {rec.risks.map((risk, idx) => (
                                  <li key={idx} className="flex gap-2">
                                    <span className="text-red-500">•</span>
                                    <span>{risk}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Model Info */}
                          <div className="text-xs text-slate-500 pt-3 border-t border-slate-800">
                            <div className="grid grid-cols-2 gap-2">
                              {rec.model && <div>Model: <span className="text-slate-300">{rec.model}</span></div>}
                              {toNumber(rec.input_tokens) !== null && (
                                <div>Input tokens: <span className="text-slate-300">{toNumber(rec.input_tokens).toLocaleString()}</span></div>
                              )}
                              {toNumber(rec.output_tokens) !== null && (
                                <div>Output tokens: <span className="text-slate-300">{toNumber(rec.output_tokens).toLocaleString()}</span></div>
                              )}
                              {toNumber(rec.cost) !== null && <div>Cost: <span className="text-slate-300">${toNumber(rec.cost).toFixed(4)}</span></div>}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      {!loading && recommendations.length > 0 && (
        <div className="mt-6 text-sm text-slate-400 text-center">
          Showing {filteredRecommendations.length} of {recommendations.length} recommendations
        </div>
      )}
    </main>
  );
}
