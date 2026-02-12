import React from 'react';
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const StockChart = ({ data, ticker }) => {
    if (!data || data.length === 0) {
        return (
            <div className="h-64 w-full bg-slate-800/50 flex items-center justify-center text-slate-500">
                No Data Available
            </div>
        );
    }

    return (
        <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                        dataKey="date"
                        stroke="#64748b"
                        tick={{ fontSize: 10 }}
                        tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis
                        yAxisId="left"
                        stroke="#64748b"
                        tick={{ fontSize: 10 }}
                        domain={['auto', 'auto']}
                    />
                    <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#475569"
                        tick={{ fontSize: 10 }}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f1f5f9' }}
                        itemStyle={{ color: '#f1f5f9' }}
                    />
                    <Legend />
                    <Bar yAxisId="right" dataKey="volume" fill="#3b82f6" opacity={0.3} name="Volume" />
                    <Line yAxisId="left" type="monotone" dataKey="close" stroke="#10b981" strokeWidth={2} dot={false} name="Price" />
                    {/* Add Technicals if present in data */}
                    {data[0].ema20 && <Line yAxisId="left" type="monotone" dataKey="ema20" stroke="#f59e0b" dot={false} strokeWidth={1} name="EMA 20" />}
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
};

export default StockChart;
