import React from 'react';
import { TrendingUp, TrendingDown, MinusCircle, Loader2 } from 'lucide-react';

const TradeCard = ({ data, loading }) => {
    if (loading) {
        return (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex items-center gap-3 text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Generating AI trade recommendation...</span>
            </div>
        );
    }

    if (!data) return null;
    if (data.error && !data.recommendation) return null;

    const rec = data.recommendation;
    if (!rec) return null;

    const isBullish = rec.direction === 'BULLISH';
    const isBearish = rec.direction === 'BEARISH';

    const DirectionIcon = isBullish ? TrendingUp : isBearish ? TrendingDown : MinusCircle;

    // Tailwind can't detect dynamic classes like `bg-${color}-500`.
    // Use full class names so Tailwind includes them in the build.
    const borderClass = isBullish
        ? 'bg-emerald-950/30 border-emerald-500/50'
        : isBearish
            ? 'bg-red-950/30 border-red-500/50'
            : 'bg-slate-900 border-slate-700';

    const dirTextClass = isBullish
        ? 'text-emerald-400'
        : isBearish
            ? 'text-red-400'
            : 'text-slate-300';

    const confidenceBadge = rec.confidence >= 70
        ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
        : rec.confidence >= 50
            ? 'bg-amber-500/20 border-amber-500/30 text-amber-400'
            : 'bg-red-500/20 border-red-500/30 text-red-400';

    return (
        <div className={`relative overflow-hidden rounded-xl border p-6 ${borderClass}`}>
            {/* Header */}
            <div className="flex justify-between items-start mb-5">
                <div>
                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-1">AI Recommendation</h3>
                    <div className="flex items-center gap-2">
                        <DirectionIcon className={`w-7 h-7 ${dirTextClass}`} />
                        <span className={`text-2xl font-bold ${dirTextClass}`}>
                            {rec.direction} — {rec.strategy}
                        </span>
                    </div>
                </div>
                <div className={`border px-3 py-1.5 rounded-full ${confidenceBadge}`}>
                    <span className="text-sm font-bold">
                        {rec.confidence}% confidence
                    </span>
                </div>
            </div>

            {/* Trade Legs */}
            {rec.trades && rec.trades.length > 0 && (
                <div className="mb-5">
                    <div className="text-xs text-slate-500 uppercase font-semibold mb-2 tracking-wider">Trade Legs</div>
                    <div className="space-y-2">
                        {rec.trades.map((trade, idx) => (
                            <div key={idx} className="bg-slate-900/60 border border-slate-700/50 rounded-lg px-4 py-3 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${trade.action === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                                        {trade.action}
                                    </span>
                                    <span className="text-slate-200 font-mono font-medium">
                                        {trade.strike} {trade.option_type}
                                    </span>
                                    <span className="text-slate-500 text-sm">{trade.expiry}</span>
                                </div>
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="text-slate-400">@ <span className="text-slate-200 font-mono">₹{trade.price}</span></span>
                                    <span className="text-slate-400">{trade.lots} lot{trade.lots > 1 ? 's' : ''}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Entry / SL / Target */}
            <div className="grid grid-cols-3 gap-4 mb-5">
                <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <div className="text-xs text-slate-500">Entry</div>
                    <div className="text-xl font-mono font-semibold text-slate-200">₹{rec.entry_price}</div>
                </div>
                <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <div className="text-xs text-slate-500">Stop Loss</div>
                    <div className="text-xl font-mono font-semibold text-red-400">₹{rec.stop_loss}</div>
                </div>
                <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <div className="text-xs text-slate-500">Target</div>
                    <div className="text-xl font-mono font-semibold text-emerald-400">₹{rec.target}</div>
                </div>
            </div>

            {/* Risk / Reward Row */}
            <div className="grid grid-cols-3 gap-4 mb-5">
                <div className="flex justify-between text-sm bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <span className="text-slate-500">Max Risk</span>
                    <span className="text-red-400 font-mono">₹{rec.max_risk?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <span className="text-slate-500">Max Reward</span>
                    <span className="text-emerald-400 font-mono">₹{rec.max_reward?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <span className="text-slate-500">R:R Ratio</span>
                    <span className="text-cyan-400 font-mono">{rec.risk_reward_ratio}</span>
                </div>
            </div>

            {/* Rationale */}
            {rec.rationale && (
                <div className="mb-4">
                    <div className="text-xs text-slate-500 uppercase font-semibold mb-1.5 tracking-wider">Rationale</div>
                    <p className="text-sm text-slate-300 leading-relaxed">{rec.rationale}</p>
                </div>
            )}

            {/* Risks */}
            {rec.risks && rec.risks.length > 0 && (
                <div>
                    <div className="text-xs text-slate-500 uppercase font-semibold mb-1.5 tracking-wider">Risks</div>
                    <ul className="space-y-1">
                        {rec.risks.map((risk, idx) => (
                            <li key={idx} className="text-sm text-slate-400 flex items-start gap-2">
                                <span className="text-red-500 mt-0.5">•</span>
                                {risk}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Usage info */}
            {data.usage && (
                <div className="mt-4 pt-3 border-t border-slate-800 flex items-center gap-4 text-[11px] text-slate-600">
                    <span>{data.usage.model}</span>
                    <span>{data.usage.input_tokens + data.usage.output_tokens} tokens</span>
                    <span>${data.usage.cost_usd?.toFixed(4)}</span>
                    <span>{(data.usage.latency_ms / 1000).toFixed(1)}s</span>
                </div>
            )}
        </div>
    );
};

export default TradeCard;
