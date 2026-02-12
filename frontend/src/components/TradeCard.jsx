import React from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';

const TradeCard = ({ type, data, loading }) => {
    if (loading) return <div className="animate-pulse h-64 bg-slate-800 rounded-xl"></div>;
    if (!data) return null;

    const isCall = type === 'CALL';
    const isPut = type === 'PUT';
    const isAvoid = type === 'NO TRADE';

    return (
        <div className={`relative overflow-hidden rounded-xl border p-6 ${isCall
                ? 'bg-emerald-950/30 border-emerald-500/50'
                : isPut
                    ? 'bg-red-950/30 border-red-500/50'
                    : 'bg-slate-900 border-slate-700'
            }`}>
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">AI Recommendation</h3>
                    <div className="text-3xl font-bold mt-1 flex items-center gap-2">
                        {isCall ? <TrendingUp className="text-emerald-400" /> : isPut ? <TrendingDown className="text-red-400" /> : <Activity className="text-slate-400" />}
                        <span className={isCall ? 'text-emerald-400' : isPut ? 'text-red-400' : 'text-slate-200'}>
                            {isAvoid ? 'AVOID TRADE' : `BUY ${data.ticker} ${data.strike} ${type}`}
                        </span>
                    </div>
                </div>
                <div className="bg-slate-800 px-3 py-1 rounded-full text-xs font-mono text-slate-300">
                    Confidence: {data.confidence || '87%'}
                </div>
            </div>

            {!isAvoid && (
                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                        <div className="text-xs text-slate-500">Entry Zone</div>
                        <div className="text-xl font-mono font-semibold text-slate-200">₹{data.entry}</div>
                    </div>
                    <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                        <div className="text-xs text-slate-500">Stop Loss</div>
                        <div className="text-xl font-mono font-semibold text-red-400">₹{data.sl}</div>
                    </div>
                    <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                        <div className="text-xs text-slate-500">Target</div>
                        <div className="text-xl font-mono font-semibold text-emerald-400">₹{data.target}</div>
                    </div>
                </div>
            )}

            <div className="space-y-2">
                <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Lot Size</span>
                    <span className="text-slate-200 font-mono">{data.lotSize} Qty</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Est. Capital</span>
                    <span className="text-slate-200 font-mono">₹{(data.entry_price * data.lotSize).toLocaleString()}</span>
                </div>
            </div>
        </div>
    );
};

export default TradeCard;
