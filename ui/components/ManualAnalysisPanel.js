const ManualAnalysisPanel = () => {
    const [notebooks, setNotebooks] = React.useState([]);
    const [newNotebookName, setNewNotebookName] = React.useState('');

    const fetchNotebooks = async () => {
        try {
            const res = await fetch('/notebooks');
            if (res.ok) {
                const data = await res.json();
                setNotebooks(data);
            }
        } catch (e) {
            console.error("Failed to load notebooks", e);
        }
    };

    React.useEffect(() => {
        fetchNotebooks();
    }, []);

    const createNotebook = async () => {
        if (!newNotebookName.trim()) return;
        try {
            const res = await fetch('/notebooks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newNotebookName })
            });
            if (res.ok) {
                setNewNotebookName('');
                fetchNotebooks();
            } else {
                const err = await res.json();
                alert(err.detail || "Failed to create notebook");
            }
        } catch (e) {
            alert(e.message);
        }
    };

    const openNotebook = (name) => {
        // Construct URL to open simple edit mode for the specific file
        // Marimo URL format: http://host:port/?file=path/to/file.py
        // We serve resources/notebooks at root of marimo
        // So file path is just name.py
        const url = `http://${window.location.hostname}:2718/?file=${name}.py`;
        window.open(url, '_blank');
    };

    return (
        <div className="p-8 h-full bg-[#1d2021] text-[#ebdbb2] overflow-y-auto">
            <div className="max-w-4xl mx-auto">
                <h2 className="text-2xl font-bold mb-6 text-[#fe8019]">Manual Analysis (Marimo)</h2>

                <div className="bg-[#282828] p-6 rounded border border-[#504945] mb-8">
                    <h3 className="text-sm font-bold uppercase tracking-wider mb-4 text-[#a89984]">Create New Notebook</h3>
                    <div className="flex space-x-4">
                        <input
                            type="text"
                            value={newNotebookName}
                            onChange={(e) => setNewNotebookName(e.target.value)}
                            placeholder="notebook_name"
                            className="bg-[#1d2021] border border-[#504945] px-4 py-2 rounded text-[#ebdbb2] flex-grow focus:border-[#fe8019] outline-none"
                        />
                        <button
                            onClick={createNotebook}
                            className="bg-[#fe8019] text-[#282828] px-6 py-2 rounded font-bold hover:bg-[#fabd2f] transition-colors"
                        >
                            CREATE
                        </button>
                    </div>
                </div>

                <h3 className="text-sm font-bold uppercase tracking-wider mb-4 text-[#a89984]">Existing Notebooks</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {notebooks.map((nb) => (
                        <div
                            key={nb.name}
                            onClick={() => openNotebook(nb.name)}
                            className="bg-[#282828] border border-[#504945] p-4 rounded cursor-pointer hover:border-[#fe8019] transition-all group"
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div className="font-bold text-lg text-[#ebdbb2] group-hover:text-[#fe8019]">{nb.name}</div>
                                <span className="text-xs text-[#a89984]">{new Date(nb.date).toLocaleDateString()}</span>
                            </div>
                            <div className="text-sm text-[#a89984]">
                                Python Notebook
                            </div>
                        </div>
                    ))}
                    {notebooks.length === 0 && (
                        <p className="text-[#a89984] italic">No notebooks found.</p>
                    )}
                </div>
            </div>
        </div>
    );
};
