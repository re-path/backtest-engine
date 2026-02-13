const { useState, useEffect } = React;

const LiveStrategiesPanel = () => {
    const [strategies, setStrategies] = useState([]);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState(null);

    const fetchLiveStrategies = async () => {
        setLoading(true);
        try {
            const res = await fetch('/live/strategies');
            if (res.ok) {
                const data = await res.json();
                setStrategies(data);
            }
        } catch (e) {
            console.error("Failed to fetch live strategies", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLiveStrategies();
        const interval = setInterval(fetchLiveStrategies, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    const startStrategy = async (name) => {
        setActionLoading(name);
        try {
            const res = await fetch('/live/strategies/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ strategy_name: name })
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(data.message);
            } else {
                alert(`Warning: ${data.message}`);
            }
            fetchLiveStrategies();
        } catch (e) {
            alert(`Error: ${e.message}`);
        } finally {
            setActionLoading(null);
        }
    };

    const stopStrategy = async (name) => {
        setActionLoading(name);
        try {
            const res = await fetch('/live/strategies/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ strategy_name: name })
            });
            if (res.ok) {
                alert(`Strategy ${name} stop signal sent.`);
            } else {
                alert(`Failed to stop strategy ${name}`);
            }
            fetchLiveStrategies();
        } catch (e) {
            alert(`Error: ${e.message}`);
        } finally {
            setActionLoading(null);
        }
    };

    return (
        <div className="p-8 bg-[#1d2021] h-full overflow-y-auto">
            <div className="max-w-6xl mx-auto">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h2 className="text-xl font-bold text-[#ebdbb2]">Live Strategies</h2>
                        <p className="text-sm text-[#a89984]">Monitor and manage your strategy processes in real-time.</p>
                    </div>
                    <button
                        onClick={fetchLiveStrategies}
                        className="bg-[#3c3836] hover:bg-[#504945] text-[#ebdbb2] px-4 py-2 rounded border border-[#504945] text-xs font-bold transition-all"
                    >
                        REFRESH
                    </button>
                </div>

                <div className="bg-[#282828] border border-[#504945] rounded-md overflow-hidden shadow-xl">
                    <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-[#3c3836] text-[#a89984] uppercase">
                            <tr>
                                <th className="px-6 py-3">Strategy Name</th>
                                <th className="px-6 py-3">Last Modified</th>
                                <th className="px-6 py-3">Status</th>
                                <th className="px-6 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#504945]">
                            {strategies.map((strat) => (
                                <tr key={strat.name} className="hover:bg-[#32302f] transition-colors">
                                    <td className="px-6 py-4 font-bold text-[#ebdbb2]">{strat.name}</td>
                                    <td className="px-6 py-4 text-[#a89984]">{new Date(strat.date).toLocaleString()}</td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${strat.status === 'running' ? 'bg-[#b8bb26]/20 text-[#b8bb26]' :
                                                strat.status === 'stopping' ? 'bg-[#fe8019]/20 text-[#fe8019]' :
                                                    'bg-[#fb4934]/20 text-[#fb4934]'
                                            }`}>
                                            {strat.status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex justify-end space-x-2">
                                            {strat.status === 'stopped' || !strat.status ? (
                                                <button
                                                    onClick={() => startStrategy(strat.name)}
                                                    disabled={actionLoading === strat.name}
                                                    className="bg-[#b8bb26] hover:bg-[#8ec07c] text-[#282828] px-3 py-1 rounded-sm font-bold flex items-center space-x-1 disabled:opacity-50"
                                                >
                                                    <IconPlay small />
                                                    <span>START</span>
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={() => stopStrategy(strat.name)}
                                                    disabled={actionLoading === strat.name}
                                                    className="bg-[#fb4934] hover:bg-[#cc241d] text-[#ebdbb2] px-3 py-1 rounded-sm font-bold flex items-center space-x-1 disabled:opacity-50"
                                                >
                                                    <IconStop small />
                                                    <span>STOP</span>
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {strategies.length === 0 && !loading && (
                                <tr>
                                    <td colSpan="4" className="px-6 py-10 text-center text-[#a89984]">
                                        No strategies found in resources/strategies.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                    {loading && (
                        <div className="p-4 text-center text-[#fe8019] animate-pulse">
                            Syncing with Redis...
                        </div>
                    )}
                </div>

                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-[#282828] p-6 rounded border border-[#504945]">
                        <h3 className="text-[#fe8019] font-bold text-sm mb-4">Process Management Info</h3>
                        <ul className="text-xs text-[#a89984] space-y-2 list-disc pl-4">
                            <li>Strategies are managed via <code className="text-[#ebdbb2]">ksai_proc</code>.</li>
                            <li>Status is synchronized using a dedicated Redis instance on port 6380.</li>
                            <li>Starting a strategy spawns a new process that runs <code className="text-[#ebdbb2]">core.live_runner</code>.</li>
                            <li>Stopping sends a SIGTERM and updates the Redis status to "stopping".</li>
                        </ul>
                    </div>
                    <div className="bg-[#282828] p-6 rounded border border-[#504945]">
                        <h3 className="text-[#83a598] font-bold text-sm mb-4">Live Context Stats</h3>
                        <p className="text-xs text-[#a89984]">
                            Redis keys are used for real-time balance, positions, and order monitoring.
                            These details will be expanded in future updates.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};
