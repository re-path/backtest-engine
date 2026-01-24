const OptimizationPanel = ({ params, onRun, loading, results, onApplyParams }) => {
    const [config, setConfig] = useState({
        ranges: {}, // param -> {min, max, step, type}
        algorithm: 'annealing',
        target_metric: 'total_net_profit'
    });

    // Helper to add a parameter to optimization
    const addParam = (key, value) => {
        if (config.ranges[key]) return;
        const isInt = Number.isInteger(value);
        setConfig(prev => ({
            ...prev,
            ranges: {
                ...prev.ranges,
                [key]: {
                    min: isInt ? value - 5 : value * 0.5,
                    max: isInt ? value + 5 : value * 1.5,
                    step: isInt ? 1 : value * 0.1,
                    type: isInt ? 'int' : 'float'
                }
            }
        }));
    };

    const removeParam = (key) => {
        const newRanges = { ...config.ranges };
        delete newRanges[key];
        setConfig(prev => ({ ...prev, ranges: newRanges }));
    };

    const updateRange = (key, field, val) => {
        setConfig(prev => ({
            ...prev,
            ranges: {
                ...prev.ranges,
                [key]: { ...prev.ranges[key], [field]: parseFloat(val) }
            }
        }));
    };

    return (
        <div className="flex flex-col h-full bg-[#1d2021] overflow-hidden">

            {/* Config Section */}
            <div className="flex-shrink-0 bg-[#282828] border-b border-[#504945] p-6">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h2 className="text-lg font-bold text-[#ebdbb2] flex items-center gap-2">
                            <IconSettings /> Optimization Configuration
                        </h2>
                        <p className="text-xs text-[#a89984] mt-1">Select parameters to optimize and define their ranges.</p>
                    </div>
                    <div className="flex gap-4">
                        <select
                            className="bg-[#3c3836] border border-[#504945] text-[#ebdbb2] text-xs p-2 rounded outline-none focus:border-[#fe8019]"
                            value={config.algorithm}
                            onChange={e => setConfig({ ...config, algorithm: e.target.value })}
                        >
                            <option value="annealing">Simulated Annealing</option>
                            <option value="hill_climb">Hill Climbing</option>
                        </select>
                        <select
                            className="bg-[#3c3836] border border-[#504945] text-[#ebdbb2] text-xs p-2 rounded outline-none focus:border-[#fe8019]"
                            value={config.target_metric}
                            onChange={e => setConfig({ ...config, target_metric: e.target.value })}
                        >
                            <option value="total_net_profit">Max Net Profit</option>
                            <option value="sharpe_ratio">Max Sharpe Ratio</option>
                            <option value="max_drawdown_pct">Min Drawdown (Not Impl)</option>
                        </select>
                        <button
                            onClick={() => onRun(config)}
                            disabled={loading || Object.keys(config.ranges).length === 0}
                            className={`bg-[#fe8019] hover:bg-[#fabd2f] text-[#282828] px-4 py-2 rounded font-bold text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                            {loading ? 'OPTIMIZING...' : 'START OPTIMIZATION'}
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Available Params */}
                    <div className="bg-[#1d2021] border border-[#504945] rounded p-4">
                        <h3 className="text-xs font-bold text-[#a89984] uppercase mb-3">Available Parameters</h3>
                        <div className="flex flex-wrap gap-2">
                            {Object.entries(params.strategy_params).map(([k, v]) => (
                                <button
                                    key={k}
                                    onClick={() => addParam(k, v)}
                                    disabled={!!config.ranges[k]}
                                    className={`px-2 py-1 text-xs rounded border border-[#504945] transition-colors ${config.ranges[k] ? 'opacity-50 cursor-not-allowed bg-[#3c3836]' : 'hover:border-[#fe8019] hover:text-[#fe8019] bg-[#282828]'}`}
                                >
                                    {k}
                                </button>
                            ))}
                            {Object.keys(params.strategy_params).length === 0 && <span className="text-xs text-[#504945] italic">No strategy params defined.</span>}
                        </div>
                    </div>

                    {/* Active Ranges */}
                    <div className="bg-[#1d2021] border border-[#504945] rounded p-4 md:col-span-2 overflow-y-auto max-h-48">
                        <h3 className="text-xs font-bold text-[#a89984] uppercase mb-3">Optimization Ranges</h3>
                        <div className="space-y-2">
                            {Object.entries(config.ranges).map(([k, range]) => (
                                <div key={k} className="flex items-center gap-4 bg-[#282828] p-2 rounded border border-[#3c3836]">
                                    <span className="text-xs font-mono font-bold text-[#fe8019] w-24 truncate" title={k}>{k}</span>
                                    <div className="flex items-center gap-2 flex-1">
                                        <div className="flex flex-col">
                                            <label className="text-[10px] text-[#a89984]">MIN</label>
                                            <input type="number" className="bg-[#3c3836] text-[#ebdbb2] text-xs p-1 rounded w-20 border border-transparent focus:border-[#fe8019] outline-none"
                                                value={range.min} onChange={(e) => updateRange(k, 'min', e.target.value)} />
                                        </div>
                                        <div className="flex flex-col">
                                            <label className="text-[10px] text-[#a89984]">MAX</label>
                                            <input type="number" className="bg-[#3c3836] text-[#ebdbb2] text-xs p-1 rounded w-20 border border-transparent focus:border-[#fe8019] outline-none"
                                                value={range.max} onChange={(e) => updateRange(k, 'max', e.target.value)} />
                                        </div>
                                        <div className="flex flex-col">
                                            <label className="text-[10px] text-[#a89984]">STEP</label>
                                            <input type="number" className="bg-[#3c3836] text-[#ebdbb2] text-xs p-1 rounded w-20 border border-transparent focus:border-[#fe8019] outline-none"
                                                value={range.step} onChange={(e) => updateRange(k, 'step', e.target.value)} />
                                        </div>
                                    </div>
                                    <button onClick={() => removeParam(k)} className="text-[#fb4934] hover:bg-[#3c3836] p-1 rounded">✕</button>
                                </div>
                            ))}
                            {Object.keys(config.ranges).length === 0 && <p className="text-xs text-[#504945] italic">Add parameters from the left to configure ranges.</p>}
                        </div>
                    </div>
                </div>
            </div>

            {/* Results Table */}
            <div className="flex-grow overflow-auto bg-[#1d2021] p-6 relative">
                <h3 className="text-xs font-bold text-[#a89984] uppercase mb-3 sticky top-0 bg-[#1d2021] py-2">Optimization Results ({results ? results.length : 0} runs)</h3>

                {!results && <div className="text-center mt-20 text-[#504945]">Run optimization to see results here.</div>}

                {results && (
                    <table className="w-full text-left border-collapse">
                        <thead className="sticky top-8 bg-[#282828] text-[#a89984] text-xs uppercase font-bold z-10">
                            <tr>
                                <th className="p-3 border-b border-[#504945]">Score</th>
                                <th className="p-3 border-b border-[#504945]">Net Profit</th>
                                <th className="p-3 border-b border-[#504945]">Returns</th>
                                <th className="p-3 border-b border-[#504945]">Sharpe</th>
                                <th className="p-3 border-b border-[#504945]">Drawdown</th>
                                <th className="p-3 border-b border-[#504945]">Parameters</th>
                                <th className="p-3 border-b border-[#504945]">Action</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm font-mono">
                            {results.sort((a, b) => b.score - a.score).map((res, i) => (
                                <tr key={i} className="border-b border-[#3c3836] hover:bg-[#282828] transition-colors">
                                    <td className="p-3 text-[#fe8019] font-bold">{res.score.toFixed(4)}</td>
                                    <td className={`p-3 ${res.metrics.total_net_profit >= 0 ? 'text-[#b8bb26]' : 'text-[#fb4934]'}`}>
                                        {res.metrics.total_net_profit?.toFixed(2)}
                                    </td>
                                    <td className="p-3">{res.metrics.total_return_pct?.toFixed(2)}%</td>
                                    <td className="p-3">{res.metrics.sharpe_ratio?.toFixed(2)}</td>
                                    <td className="p-3 text-[#fb4934]">{res.metrics.max_drawdown_pct?.toFixed(2)}%</td>
                                    <td className="p-3 text-[#ebdbb2] text-xs">
                                        {JSON.stringify(res.params).replace(/["{}]/g, '').replace(/,/g, ', ')}
                                    </td>
                                    <td className="p-3">
                                        <button
                                            onClick={() => onApplyParams(res.params)}
                                            className="text-[#83a598] hover:text-[#ebdbb2] hover:underline text-xs"
                                        >
                                            Apply
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};
