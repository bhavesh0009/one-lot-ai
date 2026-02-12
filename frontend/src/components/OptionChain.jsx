import React, { useState } from 'react';

const OptionChain = ({ data }) => {
    const [showGreeks, setShowGreeks] = useState(false);

    if (!data || !data.chain) return <div style={{ color: '#64748b', textAlign: 'center', padding: '1rem' }}>No Option Chain Data</div>;

    const { underlying_price, expiry, chain } = data;

    const isATM = (strike) => Math.abs(strike - underlying_price) < (underlying_price * 0.005);
    const fmt = (val, dec = 2) => val && val > 0 ? val.toFixed(dec) : '-';
    const fmtOI = (val) => {
        if (!val || val === 0) return '-';
        if (val >= 100000) return (val / 100000).toFixed(1) + 'L';
        if (val >= 1000) return (val / 1000).toFixed(1) + 'K';
        return val.toString();
    };

    return (
        <div style={{
            background: '#1e293b',
            padding: '1rem',
            borderRadius: '12px',
            border: '1px solid #334155',
            marginTop: '1.5rem'
        }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f1f5f9', margin: 0 }}>Option Chain</h3>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                        Spot: <span style={{ color: '#fff', fontFamily: 'monospace' }}>{underlying_price}</span>
                    </span>
                    <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                        Expiry: <span style={{ color: '#fbbf24', fontFamily: 'monospace' }}>{expiry}</span>
                    </span>
                    <button
                        onClick={() => setShowGreeks(!showGreeks)}
                        style={{
                            background: showGreeks ? '#3b82f6' : '#334155',
                            color: '#fff',
                            border: 'none',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            cursor: 'pointer'
                        }}
                    >
                        {showGreeks ? 'Hide Greeks' : 'Show Greeks'}
                    </button>
                </div>
            </div>

            {/* Table */}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: '0.8rem', textAlign: 'center', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid #475569' }}>
                            {/* CALLS side */}
                            {showGreeks && <th style={{ padding: '8px 4px', color: '#86efac', fontSize: '0.7rem' }}>Δ</th>}
                            {showGreeks && <th style={{ padding: '8px 4px', color: '#86efac', fontSize: '0.7rem' }}>θ</th>}
                            <th style={{ padding: '8px 4px', color: '#86efac' }}>IV%</th>
                            <th style={{ padding: '8px 4px', color: '#86efac' }}>VOL</th>
                            <th style={{ padding: '8px 4px', color: '#86efac' }}>OI</th>
                            <th style={{ padding: '8px 4px', color: '#4ade80', fontWeight: 700 }}>CE LTP</th>
                            {/* Strike */}
                            <th style={{ padding: '8px 4px', color: '#e2e8f0', fontWeight: 700 }}>STRIKE</th>
                            {/* PUTS side */}
                            <th style={{ padding: '8px 4px', color: '#f87171', fontWeight: 700 }}>PE LTP</th>
                            <th style={{ padding: '8px 4px', color: '#fca5a5' }}>OI</th>
                            <th style={{ padding: '8px 4px', color: '#fca5a5' }}>VOL</th>
                            <th style={{ padding: '8px 4px', color: '#fca5a5' }}>IV%</th>
                            {showGreeks && <th style={{ padding: '8px 4px', color: '#fca5a5', fontSize: '0.7rem' }}>Δ</th>}
                            {showGreeks && <th style={{ padding: '8px 4px', color: '#fca5a5', fontSize: '0.7rem' }}>θ</th>}
                        </tr>
                    </thead>
                    <tbody>
                        {chain.map((row) => {
                            const atm = isATM(row.strike);
                            const rowStyle = {
                                borderBottom: '1px solid rgba(71, 85, 105, 0.3)',
                                background: atm ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                                transition: 'background 0.15s'
                            };
                            const cellBase = { padding: '6px 4px', fontFamily: 'monospace', fontSize: '0.8rem' };

                            return (
                                <tr key={row.strike} style={rowStyle}
                                    onMouseEnter={(e) => e.currentTarget.style.background = atm ? 'rgba(59, 130, 246, 0.2)' : 'rgba(71, 85, 105, 0.2)'}
                                    onMouseLeave={(e) => e.currentTarget.style.background = atm ? 'rgba(59, 130, 246, 0.1)' : 'transparent'}
                                >
                                    {/* CALL side — Greeks */}
                                    {showGreeks && <td style={{ ...cellBase, color: '#86efac' }}>{fmt(row.ceDelta, 3)}</td>}
                                    {showGreeks && <td style={{ ...cellBase, color: '#86efac' }}>{fmt(row.ceTheta, 2)}</td>}
                                    <td style={{ ...cellBase, color: '#86efac' }}>{fmt(row.ceIV, 1)}</td>
                                    <td style={{ ...cellBase, color: '#94a3b8' }}>{fmtOI(row.ceVolume)}</td>
                                    <td style={{ ...cellBase, color: '#86efac', fontWeight: row.ceOI > 0 ? 600 : 400 }}>{fmtOI(row.ceOI)}</td>
                                    <td style={{ ...cellBase, color: '#4ade80', fontWeight: 700 }}>{fmt(row.cePrice)}</td>

                                    {/* Strike */}
                                    <td style={{
                                        ...cellBase,
                                        fontWeight: 700,
                                        color: atm ? '#60a5fa' : '#e2e8f0',
                                        background: 'rgba(30, 41, 59, 0.8)',
                                        borderLeft: '1px solid #475569',
                                        borderRight: '1px solid #475569',
                                        position: 'relative'
                                    }}>
                                        {row.strike}
                                        {atm && <span style={{ color: '#fbbf24', fontSize: '0.6rem', marginLeft: '4px' }}>ATM</span>}
                                    </td>

                                    {/* PUT side */}
                                    <td style={{ ...cellBase, color: '#f87171', fontWeight: 700 }}>{fmt(row.pePrice)}</td>
                                    <td style={{ ...cellBase, color: '#fca5a5', fontWeight: row.peOI > 0 ? 600 : 400 }}>{fmtOI(row.peOI)}</td>
                                    <td style={{ ...cellBase, color: '#94a3b8' }}>{fmtOI(row.peVolume)}</td>
                                    <td style={{ ...cellBase, color: '#fca5a5' }}>{fmt(row.peIV, 1)}</td>
                                    {showGreeks && <td style={{ ...cellBase, color: '#fca5a5' }}>{fmt(row.peDelta, 3)}</td>}
                                    {showGreeks && <td style={{ ...cellBase, color: '#fca5a5' }}>{fmt(row.peTheta, 2)}</td>}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default OptionChain;
