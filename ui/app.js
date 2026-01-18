const windowUrl = window.location.href;
const baseUrl = windowUrl.endsWith('/') ? windowUrl : windowUrl + '/';
const { useState, useEffect, useRef } = React;

function App() {
    const [activeTab, setActiveTab] = useState('backtest');
    const [strategies, setStrategies] = useState([]);
    const [selectedStrategy, setSelectedStrategy] = useState(null);
    const [pythonCode, setPythonCode] = useState('');
    const [parameters, setParameters] = useState({
        initial_capital: 100000,
        symbol: 'NEPSE',
        start_date: '2023-01-01',
        end_date: '2024-01-01',
        timeframe: '1d'
    });
    const [results, setResults] = useState(null);
    const [isRunning, setIsRunning] = useState(false);
    const [logs, setLogs] = useState([]);

    const handleRunBacktest = async () => {
        setIsRunning(true);
        setLogs(['Initializing backtest engine...', 'Compiling Python strategy...']);
        try {
            const response = await fetch(baseUrl + 'api/backtest/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: pythonCode,
                    params: parameters
                })
            });
            const data = await response.json();
            setResults(data.metrics);
            setLogs(prev => [...prev, 'Backtest completed successfully.']);
        } catch (err) {
            setLogs(prev => [...prev, 'Error: ' + err.message]);
        } finally {
            setIsRunning(false);
        }
    };

    const renderBacktestTab = () => (
        <div className="grid grid-cols-12 gap-6">
            <div className="col-span-12 lg:col-span-7">
                <div className="bg-gray-900 rounded-lg overflow-hidden shadow-inner">
                    <div className="bg-gray-800 px-4 py-2 flex justify-between items-center">
                        <span className="text-gray-300 text-sm font-mono uppercase">Strategy Editor (Python)</span>
                        <div className="flex space-x-2">
                            <div className="w-3 h-3 rounded-full bg-red-500"></div>
                            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                            <div className="w-3 h-3 rounded-full bg-green-500"></div>
                        </div>
                    </div>
                    <textarea
                        className="w-full h-[500px] bg-transparent text-green-400 font-mono p-4 focus:outline-none resize-none"
                        value={pythonCode}
                        onChange={(e) => setPythonCode(e.target.value)}
                        placeholder="class Strategy:
    def on_bar(self, bar):
        if bar.close > bar.sma(20):
            self.buy()"
                    />
                </div>
            </div>

            <div className="col-span-12 lg:col-span-5 space-y-6">
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                    <h3 className="text-lg font-bold mb-4 text-gray-800">Parameters</h3>
                    <div className="space-y-4">
                        {Object.keys(parameters).map(key => (
                            <div key={key}>
                                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">{key.replace('_', ' ')}</label>
                                <input
                                    type={typeof parameters[key] === 'number' ? 'number' : 'text'}
                                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                    value={parameters[key]}
                                    onChange={(e) => setParameters({...parameters, [key]: e.target.value})}
                                />
                            </div>
                        ))}
                        <button
                            onClick={handleRunBacktest}
                            disabled={isRunning}
                            className={`w-full py-3 rounded-lg font-bold text-white transition-all ${isRunning ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700 shadow-lg active:scale-95'}`}
                        >
                            {isRunning ? 'EXECUTING...' : 'RUN BACKTEST'}
                        </button>
                    </div>
                </div>

                {results && (
                    <div className="bg-blue-50 p-6 rounded-xl border border-blue-100">
                        <h3 className="text-lg font-bold mb-4 text-blue-800">Performance Metrics</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-white p-3 rounded shadow-sm">
                                <p className="text-xs text-gray-400 uppercase">Total Return</p>
                                <p className="text-xl font-bold text-green-600">{results.total_return}%</p>
                            </div>
                            <div className="bg-white p-3 rounded shadow-sm">
                                <p className="text-xs text-gray-400 uppercase">Sharpe Ratio</p>
                                <p className="text-xl font-bold text-blue-600">{results.sharpe_ratio}</p>
                            </div>
                            <div className="bg-white p-3 rounded shadow-sm">
                                <p className="text-xs text-gray-400 uppercase">Max Drawdown</p>
                                <p className="text-xl font-bold text-red-600">{results.max_drawdown}%</p>
                            </div>
                            <div className="bg-white p-3 rounded shadow-sm">
                                <p className="text-xs text-gray-400 uppercase">Win Rate</p>
                                <p className="text-xl font-bold text-gray-800">{results.win_rate}%</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div className="col-span-12">
                <div className="bg-gray-100 p-4 rounded-lg font-mono text-xs h-32 overflow-y-auto border border-gray-200">
                    {logs.map((log, i) => (
                        <div key={i} className="mb-1">
                            <span className="text-gray-400">[{new Date().toLocaleTimeString()}]</span> {log}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-50 p-4 md:p-8">
            <div className="max-w-7xl mx-auto">
                <header className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-4xl font-black text-gray-900 tracking-tight">KSAI ENGINE</h1>
                        <p className="text-gray-500 font-medium">Python-based Strategy Backtester</p>
                    </div>
                    <div className="flex bg-white rounded-lg p-1 shadow-sm border">
                        <button 
                            onClick={() => setActiveTab('backtest')}
                            className={`px-6 py-2 rounded-md text-sm font-bold transition-all ${activeTab === 'backtest' ? 'bg-gray-900 text-white' : 'text-gray-500'}`}
                        >
                            BACKTEST
                        </button>
                        <button 
                            onClick={() => setActiveTab('results')}
                            className={`px-6 py-2 rounded-md text-sm font-bold transition-all ${activeTab === 'results' ? 'bg-gray-900 text-white' : 'text-gray-500'}`}
                        >
                            HISTORY
                        </button>
                    </div>
                </header>

                <main>
                    {activeTab === 'backtest' ? renderBacktestTab() : (
                        <div className="bg-white p-12 rounded-2xl border border-dashed border-gray-300 text-center">
                            <p className="text-gray-400 font-medium">Historical backtest reports will appear here</p>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);