const MLPanel = () => {
    const [trainingCode, setTrainingCode] = React.useState(`
# Example: Training a Random Forest Model
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np

# 1. Access the data (injected by backend if dates are selected)
if data.empty:
    print("Warning: No data loaded. Using dummy data for demonstration.")
    data = pd.DataFrame({
        'feature1': np.random.rand(100),
        'feature2': np.random.rand(100),
        'target': np.random.rand(100)
    })
else:
    print(f"Using {len(data)} rows of loaded data.")
    # Example: use 'price' as target and dummy feature
    if 'price' in data.columns:
        data['target'] = data['price'].shift(-1) # Predict next price
        data['feature1'] = data['price']
        data = data.dropna()

X = data[['feature1']]
y = data['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 2. Define Architecture
model = RandomForestRegressor(n_estimators=100)

# 3. Train
model.fit(X_train, y_train)

# 4. Save Model (save_model is injected by the backend)
save_model(model, "my_rf_model")

print("Model training complete.")
print("Test Score:", model.score(X_test, y_test))
`);
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
            cmInstance.current.setValue(trainingCode);
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
        let template = '';
        if (type === 'LSTM') {
            template = `
# LSTM Architecture (Requires TensorFlow/Keras)
import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Use 'data' variable provided by backend
if data.empty:
    dataset = np.random.rand(100, 1)
else:
    dataset = data[['price']].values

def create_dataset(dataset, look_back=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

look_back = 5
X, y = create_dataset(dataset, look_back)
X = np.reshape(X, (X.shape[0], 1, X.shape[1]))

# Define Architecture
model = Sequential([
    LSTM(4, input_shape=(1, look_back)),
    Dense(1)
])
model.compile(loss='mean_squared_error', optimizer='adam')

# Train
model.fit(X, y, epochs=5, batch_size=1, verbose=2)

# Save
save_model(model, "lstm_model")
`;
        } else if (type === 'Boosting') {
            template = `
# Gradient Boosting Example
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np

# Use 'data' variable provided by backend
if data.empty:
    X = np.random.rand(100, 2)
    y = np.random.rand(100)
else:
    # Example: Simple features from price
    data['prev_price'] = data['price'].shift(1)
    data = data.dropna()
    X = data[['prev_price']]
    y = data['price']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Architecture
model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1)

# Train
model.fit(X_train, y_train)

# Save
save_model(model, "boosting_model")
print("Trained Boosting model on actual data.")
`;
        } else {
            template = `
# Random Forest Example
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import numpy as np

# Use 'data' variable provided by backend
if not data.empty:
    X = data[['price']].shift(1).dropna()
    y = data['price'].iloc[1:]
else:
    X = np.random.rand(100, 1)
    y = np.random.rand(100)

# Architecture
model = RandomForestRegressor(n_estimators=50)

# Train
model.fit(X, y)

# Save
save_model(model, "rf_model")
`;
        }
        setTrainingCode(template.trim());
        if (cmInstance.current) cmInstance.current.setValue(template.trim());
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
