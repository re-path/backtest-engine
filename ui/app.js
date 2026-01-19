const { useState, useEffect, useRef, useCallback } = React;

// --- Icons ---
const IconPlay = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
);
const IconCode = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
);
const IconSettings = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
);
const IconChart = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
);
const IconList = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
);
const IconSave = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
);
const IconFolder = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
);
const IconUpload = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
);


// --- Defaults ---
const DEFAULT_STRATEGY = `class Strategy:
    def __init__(self, **kwargs):
        # Strategy parameters are passed to __init__
        self.params = kwargs

    def on_bar(self, context, bar):
        """
        Main Strategy Logic
        
        API Documentation:
        ------------------
        Accessing Data:
          bar.price       (float) : Current close price of the asset
          bar.timestamp   (params): Current timestamp (pandas Timestamp)
          bar.ticker      (str)   : Ticker symbol
          
        Context (State & Actions):
          context.get_balance()           : Current available cash (Affected by fees & interest)
          context.get_positions()         : Dictionary of active positions {ticker: Position}
          
          # NOTE: Broker fees and Interest rates are configured in the right panel
          # and applied automatically by the engine.
          
          # STATE MANAGEMENT (CRITICAL):
          # Do NOT use self.variable = x. Use context.get/set instead.
          context.set(key, value)         : Store a value
          context.get(key, default=None)  : Retrieve a value, returns default if not found
          
          # TRADING ACTIONS:
          context.buy(ticker, money_amount, price, time)
          context.sell(ticker, share_fraction, price, time, reason="SELL")
          context.close(ticker, price, time, reason="CLOSE") # Close entire position
          
        """
        
        # Example 1: Use context.get() to manage state
        # Let's count how many bars we've seen for this ticker
        ticker_count_key = f"{bar.ticker}_count"
        current_count = context.get(ticker_count_key, 0)
        context.set(ticker_count_key, current_count + 1)
        
        # Example 2: Accessing Parameters
        # params are populated from the Configuration panel on the right
        buy_probability = self.params.get('buy_prob', 0.10) 
        
        # Example 3: Trading Logic
        import random
        if random.random() < buy_probability:
             if context.get_balance() > 0:
                 amount = context.get_balance() * 0.20
                 # NOTE: context.buy handles logging and slippage automatically
                 context.buy(bar.ticker, amount, bar.price, bar.timestamp)
        
        # Example 4: Risk Management
        positions = context.get_positions()
        if bar.ticker in positions:
             pos = positions[bar.ticker]
             # Check for 5% profit
             if bar.price > pos.entry_price * 1.05:
                 context.sell(bar.ticker, pos.share_units, bar.price, bar.timestamp, "TakeProfit")
`;

// --- Components ---

const MetricCard = ({ label, value, subValue, positive }) => (
    <div className="bg-[#252526] p-4 rounded border border-[#454545] hover:border-[#007acc] transition-colors">
        <p className="text-[#a1a1a1] text-xs font-semibold uppercase tracking-wider mb-1">{label}</p>
        <p className={`text-2xl font-bold font-mono ${positive === true ? 'text-[#4ec9b0]' : positive === false ? 'text-[#f14c4c]' : 'text-[#d4d4d4]'}`}>
            {value}
        </p>
        {subValue && <p className="text-xs text-[#a1a1a1] mt-1">{subValue}</p>}
    </div>
);

const AnalysisRow = ({ label, value, positive }) => (
    <div className="flex justify-between items-center py-2 border-b border-[#333333] last:border-0 hover:bg-[#2a2d2e] px-2 rounded">
        <span className="text-[#a1a1a1] text-sm">{label}</span>
        <span className={`font-mono font-medium ${positive === true ? 'text-[#4ec9b0]' : positive === false ? 'text-[#f14c4c]' : 'text-[#cccccc]'}`}>
            {value}
        </span>
    </div>
);

const App = () => {
    const [activeTab, setActiveTab] = useState('strategies'); // strategies, results, analysis
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);
    const [code, setCode] = useState(DEFAULT_STRATEGY);
    const [strategyName, setStrategyName] = useState('My Strategy');
    const [savedStrategies, setSavedStrategies] = useState([]);

    // Resizable State
    const [leftPanelWidth, setLeftPanelWidth] = useState(60);
    const [isDragging, setIsDragging] = useState(false);
    const containerRef = useRef(null);

    // Editor Ref
    const editorRef = useRef(null);
    const cmInstance = useRef(null);

    // File Input Ref
    const fileInputRef = useRef(null);

    const triggerFileSelect = () => {
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const handleFileSelect = (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            setCode(content);
            if (cmInstance.current) {
                cmInstance.current.setValue(content);
            }
            // Set name from filename without extension
            const name = file.name.replace(/\.[^/.]+$/, "");
            setStrategyName(name);
        };
        reader.readAsText(file);
        // Reset value so same file can be selected again
        event.target.value = '';
    };

    const [params, setParams] = useState({
        start_date: '2025-01-01',
        end_date: '2025-12-31',
        initial_balance: 10000,
        slippage: 0.001,
        broker_fee: 0.001,
        annual_interest_rate: 0.0,
        strategy_params: {}
    });

    // Load saved strategies on mount
    // Load saved strategies on mount
    useEffect(() => {
        fetchStrategies();
    }, []);

    // Initialize CodeMirror (Only once!)
    useEffect(() => {
        if (!cmInstance.current && editorRef.current) {
            cmInstance.current = CodeMirror.fromTextArea(editorRef.current, {
                mode: 'python',
                theme: 'dracula', // Using dracula as base, overridden by CSS
                lineNumbers: true,
                matchBrackets: true,
                autoCloseBrackets: true,
                indentUnit: 4,
                tabSize: 4,
                lineWrapping: true,
                viewportMargin: Infinity
            });

            cmInstance.current.on('change', (doc) => {
                setCode(doc.getValue());
            });

            cmInstance.current.setValue(DEFAULT_STRATEGY);
        }
    }, []);

    // Resize Chart on Tab Switch
    useEffect(() => {
        if (activeTab === 'results' && results?.plot_json) {
            setTimeout(() => {
                Plotly.react('chart-container-full', results.plot_json.data, results.plot_json.layout, {
                    responsive: true,
                    paper_bgcolor: '#1e1e1e',
                    plot_bgcolor: '#1e1e1e',
                    font: { color: '#d4d4d4' },
                    xaxis: { gridcolor: '#333333' },
                    yaxis: { gridcolor: '#333333' }
                });
            }, 50);
        }
        // Force refresh codemirror when strategy tab becomes active to prevent visual glitches
        if (activeTab === 'strategies' && cmInstance.current) {
            setTimeout(() => cmInstance.current.refresh(), 50);
        }
    }, [activeTab, results]);


    // Resize Logic
    const startResize = useCallback((e) => {
        setIsDragging(true);
        e.preventDefault();
    }, []);

    const stopResize = useCallback(() => {
        setIsDragging(false);
    }, []);

    const resize = useCallback((e) => {
        if (isDragging && containerRef.current) {
            const containerRect = containerRef.current.getBoundingClientRect();
            const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
            if (newWidth > 15 && newWidth < 85) {
                setLeftPanelWidth(newWidth);
            }
        }
    }, [isDragging]);

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', resize);
            window.addEventListener('mouseup', stopResize);
        } else {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResize);
        }
        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResize);
        };
    }, [isDragging, resize, stopResize]);


    const runBacktest = async () => {
        setLoading(true);
        setError(null);
        try {
            const payload = { ...params, code };

            const response = await fetch('/run-backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Backtest failed');
            }

            const data = await response.json();
            setResults(data);
            setActiveTab('results'); // Auto switch to results
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const saveStrategy = async () => {
        try {
            const payload = { name: strategyName, code, params };
            const response = await fetch('/strategies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) throw new Error("Failed to save strategy");

            alert(`Saved strategy: ${strategyName}`);
            fetchStrategies(); // Refresh list
        } catch (e) {
            alert(e.message);
        }
    };

    const fetchStrategies = async () => {
        try {
            const res = await fetch('/strategies');
            if (res.ok) {
                const data = await res.json();
                setSavedStrategies(data);
            }
        } catch (e) {
            console.error("Failed to load strategies", e);
        }
    };

    const loadStrategy = async (stratMeta) => {
        if (window.confirm(`Load strategy "${stratMeta.name}"? Unsaved changes will be lost.`)) {
            try {
                const res = await fetch(`/strategies/${stratMeta.name}`);
                if (!res.ok) throw new Error("Failed to load strategy details");

                const strat = await res.json();

                setStrategyName(strat.name);
                setCode(strat.code);
                setParams(strat.params);
                if (cmInstance.current) cmInstance.current.setValue(strat.code);
            } catch (e) {
                alert(e.message);
            }
        }
    };


    const handleChange = (e) => {
        const { name, value } = e.target;
        setParams(prev => ({
            ...prev,
            [name]: ['initial_balance', 'slippage', 'broker_fee', 'annual_interest_rate'].includes(name) ? parseFloat(value) : value
        }));
    };

    // --- Renderers ---

    return (
        <div className="min-h-screen flex flex-col h-screen bg-[#1e1e1e] text-[#d4d4d4]">

            {/* Header */}
            <header className="bg-[#252526] border-b border-[#333333] h-12 flex items-center px-4 justify-between flex-shrink-0 select-none z-20">
                <div className="flex items-center space-x-6">
                    <div className="flex items-center space-x-2 text-[#007acc]">
                        <IconCode />
                        <span className="font-bold text-sm tracking-tight hidden md:inline text-[#d4d4d4]">Backtest<span className="text-[#007acc]">Engine</span></span>
                    </div>

                    {/* Navigation Tabs - VSCode Style */}
                    <div className="flex space-x-1 h-full items-end">
                        {['strategies', 'results', 'analysis'].map(tab => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`px-4 py-2 text-xs font-medium border-t-2 transition-all h-full ${activeTab === tab
                                    ? 'bg-[#1e1e1e] text-[#d4d4d4] border-[#007acc]'
                                    : 'text-[#969696] hover:bg-[#2a2d2e] hover:text-[#d4d4d4] border-transparent'}`}
                            >
                                {tab.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <button
                        onClick={runBacktest}
                        disabled={loading}
                        className={`bg-[#007acc] hover:bg-[#0062a3] text-white px-4 py-1.5 rounded-sm font-medium text-xs flex items-center space-x-2 transition-colors ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {loading ? <span className="animate-spin h-3 w-3 border-2 border-white/30 border-t-white rounded-full"></span> : <IconPlay />}
                        <span>RUN STRATEGY</span>
                    </button>
                </div>
            </header>

            {/* Main Content Area */}
            <div className="flex-grow overflow-hidden relative flex flex-col">

                {/* 
                    STRATEGIES TAB 
                    Using logic to keep it in DOM but hidden to preserve CodeMirror instance 
                */}
                <div
                    className="flex-grow flex flex-col md:flex-row overflow-hidden absolute inset-0"
                    style={{ visibility: activeTab === 'strategies' ? 'visible' : 'hidden', zIndex: activeTab === 'strategies' ? 10 : 0 }}
                    ref={containerRef}
                >
                    {/* Left Panel: Code Editor */}
                    <div
                        className="flex flex-col border-r border-[#333333] bg-[#1e1e1e] h-full"
                        style={{ width: `${leftPanelWidth}%` }}
                    >
                        <div className="bg-[#252526] px-4 py-2 text-xs font-mono border-b border-[#333333] flex justify-between items-center select-none">
                            <div className="flex items-center space-x-2">
                                <span className="text-[#969696]">FILE:</span>
                                <input
                                    type="text"
                                    className="bg-transparent border-b border-transparent focus:border-[#007acc] outline-none text-[#d4d4d4] w-48 transition-colors hover:bg-[#2a2d2e]"
                                    value={strategyName}
                                    onChange={(e) => setStrategyName(e.target.value)}
                                />
                            </div>
                            <span className="text-[#007acc] text-xs">Python 3.13</span>
                        </div>
                        <div className="flex-grow overflow-hidden relative">
                            <textarea ref={editorRef} className="hidden"></textarea>
                        </div>
                    </div>

                    {/* Resizer Handle */}
                    <div
                        className="w-1 bg-[#333333] hover:bg-[#007acc] cursor-col-resize z-20 flex items-center justify-center transition-colors"
                        onMouseDown={startResize}
                    >
                    </div>

                    {/* Right Panel: Controls */}
                    <div
                        className="flex flex-col bg-[#1e1e1e] overflow-y-auto h-full"
                        style={{ width: `${100 - leftPanelWidth}%` }}
                    >
                        <div className="p-6 border-b border-[#333333]">
                            <div className="flex items-center space-x-2 mb-4 text-[#d4d4d4]">
                                <IconSettings />
                                <h3 className="text-xs font-bold uppercase tracking-wider">Configuration</h3>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                <div>
                                    <label className="label-text">Start Date</label>
                                    <input type="date" name="start_date" value={params.start_date} onChange={handleChange} className="input-field" />
                                </div>
                                <div>
                                    <label className="label-text">End Date</label>
                                    <input type="date" name="end_date" value={params.end_date} onChange={handleChange} className="input-field" />
                                </div>
                                <div>
                                    <label className="label-text">Capital ($)</label>
                                    <input type="number" name="initial_balance" value={params.initial_balance} onChange={handleChange} className="input-field font-mono" />
                                </div>
                                <div>
                                    <label className="label-text">Slippage (%)</label>
                                    <input type="number" step="0.001" name="slippage" value={params.slippage} onChange={handleChange} className="input-field font-mono" />
                                </div>
                                <div>
                                    <label className="label-text">Broker Fee (%)</label>
                                    <input type="number" step="0.001" name="broker_fee" value={params.broker_fee || 0} onChange={handleChange} className="input-field font-mono" />
                                </div>
                                <div>
                                    <label className="label-text">Interest Rate (%)</label>
                                    <input type="number" step="0.01" name="annual_interest_rate" value={params.annual_interest_rate || 0} onChange={handleChange} className="input-field font-mono" />
                                </div>
                            </div>

                            <div className="mt-6 flex space-x-2">
                                <button
                                    onClick={saveStrategy}
                                    className="bg-[#3c3c3c] hover:bg-[#4a4a4a] text-[#d4d4d4] px-4 py-1.5 rounded-sm font-medium text-xs flex items-center space-x-2 transition-colors flex-1 justify-center border border-[#454545]"
                                >
                                    <IconSave /> <span>SAVE</span>
                                </button>
                                <div className="relative group flex-1">
                                    <button className="bg-[#3c3c3c] hover:bg-[#4a4a4a] text-[#d4d4d4] px-4 py-1.5 rounded-sm font-medium text-xs flex items-center space-x-2 transition-colors w-full justify-center border border-[#454545]">
                                        <IconFolder /> <span>LOAD</span>
                                    </button>
                                    {/* Saved Strategies Dropdown */}
                                    <div className="absolute top-full left-0 right-0 mt-1 bg-[#252526] border border-[#454545] shadow-xl hidden group-hover:block z-50 max-h-48 overflow-y-auto">
                                        {savedStrategies.length === 0 && <div className="p-2 text-xs text-[#969696]">No saved strategies</div>}
                                        {savedStrategies.map((s, i) => (
                                            <div
                                                key={i}
                                                className="p-2 text-xs text-[#d4d4d4] hover:bg-[#007acc] hover:text-white cursor-pointer border-b border-[#333333] last:border-0"
                                                onClick={() => loadStrategy(s)}
                                            >
                                                <div className="font-bold">{s.name}</div>
                                                <div className="opacity-70">{new Date(s.date).toLocaleDateString()}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="mt-2 text-center">
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileSelect}
                                    style={{ display: 'none' }}
                                    accept=".py"
                                />
                                <button
                                    onClick={triggerFileSelect}
                                    className="text-[#007acc] hover:underline text-xs flex items-center justify-center space-x-1 w-full"
                                >
                                    <IconUpload /> <span>Import .py File</span>
                                </button>
                            </div>

                        </div>

                        {error && (
                            <div className="p-4 bg-[#5a1d1d] border-b border-[#8a2c2c] text-[#ffcccc] text-xs font-mono break-words">
                                &gt; {error}
                            </div>
                        )}

                        <div className="p-6 flex-grow flex items-center justify-center text-center text-[#5a5a5a]">
                            <div className="max-w-xs">
                                <p className="mb-2 text-sm font-medium">Strategy & Parameters</p>
                                <p className="text-xs">Adjust your settings and code logic here.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 
                   RESULTS TAB
                */}
                {activeTab === 'results' && (
                    <div className="h-full flex flex-col bg-[#1e1e1e] absolute inset-0 z-10">
                        {!results ? (
                            <div className="flex-grow flex flex-col items-center justify-center text-[#5a5a5a] p-8">
                                <IconChart />
                                <p className="mt-4 font-bold text-lg">No Results</p>
                                <p className="text-sm">Run a strategy first.</p>
                                <button onClick={() => setActiveTab('strategies')} className="mt-6 text-[#007acc] hover:underline text-sm">Return to Strategies</button>
                            </div>
                        ) : (
                            <>
                                <div className="bg-[#252526] border-b border-[#333333] px-6 py-3 flex justify-between items-center shadow-sm">
                                    <div className="flex space-x-8">
                                        <div>
                                            <p className="text-[10px] text-[#969696] uppercase font-bold tracking-wider">Return</p>
                                            <p className={`text-lg font-bold font-mono ${results.metrics.total_return_pct >= 0 ? 'text-[#4ec9b0]' : 'text-[#f14c4c]'}`}>
                                                {results.metrics.total_return_pct.toFixed(2)}%
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-[#969696] uppercase font-bold tracking-wider">Net Profit</p>
                                            <p className={`text-lg font-bold font-mono ${results.metrics.total_net_profit >= 0 ? 'text-[#4ec9b0]' : 'text-[#f14c4c]'}`}>
                                                {results.metrics.total_net_profit.toFixed(0)}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-[#969696] uppercase font-bold tracking-wider">Drawdown</p>
                                            <p className="text-lg font-bold font-mono text-[#f14c4c]">
                                                {results.metrics.max_drawdown_pct.toFixed(2)}%
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-xs text-[#969696] font-mono border border-[#333333] px-2 py-1 rounded">
                                        {results.metrics.total_trades} TRADES
                                    </div>
                                </div>
                                <div className="flex-grow p-0">
                                    <div id="chart-container-full" className="w-full h-full bg-[#1e1e1e]"></div>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {/* 
                   ANALYSIS TAB
                */}
                {activeTab === 'analysis' && (
                    <div className="h-full overflow-y-auto bg-[#1e1e1e] p-8 absolute inset-0 z-10">
                        {!results ? (
                            <div className="flex-grow flex flex-col items-center justify-center text-[#5a5a5a] pt-20">
                                <IconList />
                                <p className="mt-4 font-bold text-lg">No Analysis Data</p>
                            </div>
                        ) : (
                            <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">

                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                    <MetricCard label="Profit Factor" value={results.metrics.profit_factor.toFixed(2)} />
                                    <MetricCard label="Win Rate" value={`${results.metrics.pct_profitable.toFixed(2)}%`} positive={results.metrics.pct_profitable > 50} />
                                    <MetricCard label="Sharpe (Est)" value={(results.metrics.daily_two_sigma_pct / 100).toFixed(2)} />
                                    <MetricCard label="Total Trades" value={results.metrics.total_trades} />
                                </div>

                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    <div className="bg-[#252526] rounded border border-[#333333] overflow-hidden">
                                        <div className="px-4 py-3 border-b border-[#333333] bg-[#2d2d2e]">
                                            <h3 className="font-bold text-sm text-[#cccccc] uppercase tracking-wide">Trade Statistics</h3>
                                        </div>
                                        <div className="p-4">
                                            <AnalysisRow label="Total Net Profit" value={results.metrics.total_net_profit.toFixed(2)} positive={results.metrics.total_net_profit >= 0} />
                                            <AnalysisRow label="Gross Profit" value={results.metrics.gross_profit.toFixed(2)} positive={true} />
                                            <AnalysisRow label="Gross Loss" value={results.metrics.gross_loss.toFixed(2)} positive={false} />
                                            <AnalysisRow label="Avg Trade" value={results.metrics.avg_trade_net_profit.toFixed(2)} positive={results.metrics.avg_trade_net_profit >= 0} />
                                            <AnalysisRow label="Avg Win" value={results.metrics.avg_winning_trade.toFixed(2)} positive={true} />
                                            <AnalysisRow label="Avg Loss" value={results.metrics.avg_losing_trade.toFixed(2)} positive={false} />
                                            <AnalysisRow label="Largest Win" value={results.metrics.largest_winning_trade.toFixed(2)} positive={true} />
                                            <AnalysisRow label="Largest Loss" value={results.metrics.largest_losing_trade.toFixed(2)} positive={false} />
                                        </div>
                                    </div>

                                    <div className="bg-[#252526] rounded border border-[#333333] overflow-hidden">
                                        <div className="px-4 py-3 border-b border-[#333333] bg-[#2d2d2e]">
                                            <h3 className="font-bold text-sm text-[#cccccc] uppercase tracking-wide">Drawdown & Risk</h3>
                                        </div>
                                        <div className="p-4">
                                            <AnalysisRow label="Max Drawdown %" value={`${results.metrics.max_drawdown_pct.toFixed(2)}%`} positive={false} />
                                            <AnalysisRow label="Drawdown Depth" value={results.metrics.drawdown_depth_money.toFixed(2)} />
                                            <AnalysisRow label="Decline Duration" value={`${results.metrics.decline_duration_days} Days`} />
                                            <AnalysisRow label="Recovery Status" value={results.metrics.recovery_status_str} />
                                            <AnalysisRow label="Max Win Streak" value={results.metrics.max_consec_winning} />
                                            <AnalysisRow label="Max Loss Streak" value={results.metrics.max_consec_losing} />
                                            <AnalysisRow label="Daily VaR (5%)" value={`${results.metrics.daily_var_5pct.toFixed(2)}%`} />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);