const MLPanel = () => {
    const [trainingCode, setTrainingCode] = React.useState("");
    const [modelName, setModelName] = React.useState('my_rf_model');
    const [startDate, setStartDate] = React.useState('2012-01-01');
    const [endDate, setEndDate] = React.useState('2012-12-31');
    const [loading, setLoading] = React.useState(false);
    const [output, setOutput] = React.useState('');
    const [models, setModels] = React.useState([]);
    const editorRef = React.useRef(null);
    const cmInstance = React.useRef(null);

    const fetchModels = async () => {
        try {
            const res = await fetch('/models');
            if (res.ok) {
                const data = await res.json();
                setModels(data);
            }
        } catch (e) {
            console.error("Failed to fetch models", e);
        }
    };

    React.useEffect(() => {
        fetchModels();
        if (!cmInstance.current && editorRef.current) {
            cmInstance.current = CodeMirror.fromTextArea(editorRef.current, {
                mode: 'python',
                theme: 'dracula',
                keyMap: 'vim',
                lineNumbers: true,
                matchBrackets: true,
                autoCloseBrackets: true,
                indentUnit: 4,
                tabSize: 4,
                lineWrapping: true
            });
            cmInstance.current.on('change', (doc) => {
                setTrainingCode(doc.getValue());
            });

            // Fetch initial code
            fetch('/resources/ml_models/random_forest_initial.py')
                .then(res => res.text())
                .then(text => {
                    setTrainingCode(text);
                    if (cmInstance.current) cmInstance.current.setValue(text);
                })
                .catch(err => console.error("Failed to load initial ML code", err));
        }
    }, []);

    const runTraining = async () => {
        setLoading(true);
        setOutput('Training started...\n');
        try {
            const res = await fetch('/train', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: modelName,
                    code: trainingCode,
                    start_date: startDate,
                    end_date: endDate
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                setOutput(data.output);
                fetchModels();
            } else {
                setOutput(`ERROR: ${data.error}\n\n${data.traceback}\n\nConsole:\n${data.output}`);
            }
        } catch (e) {
            setOutput(`FAILED: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    const loadTemplate = (type) => {
        let resourcePath = '';
        if (type === 'LSTM') {
            resourcePath = '/resources/ml_models/lstm_template.py';
        } else if (type === 'Boosting') {
            resourcePath = '/resources/ml_models/boosting_template.py';
        } else {
            resourcePath = '/resources/ml_models/random_forest_template.py';
        }

        fetch(resourcePath)
            .then(res => {
                if (!res.ok) throw new Error(`Failed to load ${type} template`);
                return res.text();
            })
            .then(template => {
                setTrainingCode(template.trim());
                if (cmInstance.current) cmInstance.current.setValue(template.trim());
            })
            .catch(err => {
                console.error(err);
                setOutput(`Error loading template: ${err.message}`);
            });
    };

    return (
        <div className="flex flex-col h-full bg-[#1d2021] text-[#ebdbb2]">
            <div className="flex flex-grow overflow-hidden">
                {/* Left Panel: Code Editor */}
                <div className="w-2/3 flex flex-col border-r border-[#504945]">
                    <div className="bg-[#282828] px-4 py-2 text-xs font-mono border-b border-[#504945] flex justify-between items-center">
                        <div className="flex items-center space-x-4">
                            <span className="text-[#a89984]">ML STUDIO</span>
                            <div className="flex space-x-2">
                                <button onClick={() => loadTemplate('LSTM')} className="text-[10px] bg-[#3c3836] hover:bg-[#504945] px-2 py-0.5 rounded border border-[#504945]">LSTM</button>
                                <button onClick={() => loadTemplate('Boosting')} className="text-[10px] bg-[#3c3836] hover:bg-[#504945] px-2 py-0.5 rounded border border-[#504945]">BOOSTING</button>
                                <button onClick={() => loadTemplate('RF')} className="text-[10px] bg-[#3c3836] hover:bg-[#504945] px-2 py-0.5 rounded border border-[#504945]">RANDOM FOREST</button>
                            </div>
                        </div>
                        <div className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={modelName}
                                onChange={(e) => setModelName(e.target.value)}
                                className="bg-[#1d2021] border border-[#504945] text-xs px-2 py-0.5 rounded outline-none focus:border-[#fe8019]"
                                placeholder="Model Filename"
                            />
                        </div>
                    </div>
                    <div className="flex-grow overflow-hidden relative">
                        <textarea ref={editorRef} className="hidden"></textarea>
                    </div>
                    <div className="h-40 bg-[#1d2021] border-t border-[#504945] p-4 font-mono text-xs overflow-y-auto whitespace-pre-wrap">
                        <div className="text-[#fe8019] mb-1 font-bold">OUTPUT:</div>
                        {output || 'No output yet. Click TRAIN to start.'}
                    </div>
                </div>

                {/* Right Panel: Trained Models & Info */}
                <div className="w-1/3 flex flex-col bg-[#282828] p-6 space-y-6 overflow-y-auto">
                    <div>
                        <button
                            onClick={runTraining}
                            disabled={loading}
                            className={`w-full bg-[#fe8019] hover:bg-[#fabd2f] text-[#282828] py-3 rounded-sm font-bold text-sm flex items-center justify-center space-x-2 transition-colors ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {loading ? <span className="animate-spin h-4 w-4 border-2 border-[#282828]/30 border-t-[#282828] rounded-full"></span> : <IconPlay />}
                            <span>START TRAINING</span>
                        </button>
                    </div>

                    <div className="bg-[#1d2021] p-4 rounded border border-[#504945] space-y-4">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-[#ebdbb2] flex items-center space-x-2">
                            <IconSettings /> <span>Data Configuration</span>
                        </h3>
                        <div className="space-y-3">
                            <div>
                                <label className="block text-[10px] text-[#a89984] uppercase font-bold mb-1">Start Date</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="w-full bg-[#282828] border border-[#504945] rounded px-2 py-1 text-xs text-[#ebdbb2] focus:border-[#fe8019] outline-none"
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] text-[#a89984] uppercase font-bold mb-1">End Date</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="w-full bg-[#282828] border border-[#504945] rounded px-2 py-1 text-xs text-[#ebdbb2] focus:border-[#fe8019] outline-none"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-[#a89984] flex items-center space-x-2">
                            <IconModel /> <span>Trained Models (in data/)</span>
                        </h3>
                        <div className="bg-[#1d2021] border border-[#504945] rounded overflow-hidden">
                            {models.length === 0 ? (
                                <div className="p-4 text-xs text-[#a89984] italic">No models found in data/ folder.</div>
                            ) : (
                                models.map((m, i) => (
                                    <div key={i} className="px-4 py-2 border-b border-[#3c3836] last:border-0 text-xs flex justify-between items-center group hover:bg-[#3c3836]">
                                        <span className="font-mono text-[#ebdbb2]">{m}</span>
                                        <span className="text-[10px] text-[#a89984] opacity-0 group-hover:opacity-100 transition-opacity">PICKLE</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="bg-[#3c3836] p-4 rounded border border-[#504945] space-y-3">
                        <h4 className="text-xs font-bold text-[#ebdbb2] flex items-center space-x-2">
                            <IconCode /> <span>Integration Guide</span>
                        </h4>
                        <div className="text-[11px] text-[#a89984] space-y-2 leading-relaxed">
                            <p>To use your model in a strategy:</p>
                            <pre className="bg-[#1d2021] p-2 rounded text-[#b8bb26]">
                                {`class Strategy:
  def __init__(self, **params):
    self.model = context.load_model('${modelName}')

  def on_bar(self, context, bar):
    # Predict using your model
    pred = self.model.predict(...)
`}
                            </pre>
                            <p className="italic">Note: Model files are stored in <b>data/</b> and are git-ignored.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
