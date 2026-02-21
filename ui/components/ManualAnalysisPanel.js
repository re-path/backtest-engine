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

    const renameNotebook = async (e, oldName) => {
        e.stopPropagation();
        const newName = prompt("Enter new name for the notebook:", oldName);
        if (!newName || newName === oldName) return;

        try {
            const res = await fetch('/notebooks/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_name: oldName, new_name: newName })
            });
            if (res.ok) {
                fetchNotebooks();
            } else {
                const err = await res.json();
                alert(err.detail || "Failed to rename notebook");
            }
        } catch (e) {
            alert(e.message);
        }
    };

    const openNotebook = (name) => {
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
                            className="bg-[#282828] border border-[#504945] p-4 rounded cursor-pointer hover:border-[#fe8019] transition-all group relative"
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div className="font-bold text-lg text-[#ebdbb2] group-hover:text-[#fe8019]">{nb.name}</div>
                                <span className="text-xs text-[#a89984]">{new Date(nb.date).toLocaleDateString()}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <div className="text-sm text-[#a89984]">
                                    Python Notebook
                                </div>
                                <button
                                    onClick={(e) => renameNotebook(e, nb.name)}
                                    className="text-xs bg-[#504945] px-2 py-1 rounded hover:bg-[#665c54] text-[#ebdbb2] opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                    RENAME
                                </button>
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
