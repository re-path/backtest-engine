const SQLSnippetsPanel = () => {
    const [snippets, setSnippets] = React.useState({});
    const [categories, setCategories] = React.useState([]);
    const [selectedCategory, setSelectedCategory] = React.useState("General");
    const [searchQuery, setSearchQuery] = React.useState("");

    // Create new snippet state
    const [isCreating, setIsCreating] = React.useState(false);
    const [newSnippetName, setNewSnippetName] = React.useState("");
    const [newSnippetCategory, setNewSnippetCategory] = React.useState("General");
    const [newSnippetCode, setNewSnippetCode] = React.useState("");

    const fetchSnippets = async () => {
        try {
            const res = await fetch('/sql-snippets');
            if (res.ok) {
                const data = await res.json();
                setSnippets(data);
                const cats = Object.keys(data).sort();
                setCategories(cats);
                if (!cats.includes(selectedCategory) && cats.length > 0) {
                    setSelectedCategory(cats[0]);
                } else if (cats.length === 0) {
                    setCategories(["General"]); // Default
                }
            }
        } catch (e) {
            console.error("Failed to load snippets", e);
        }
    };

    React.useEffect(() => {
        fetchSnippets();
    }, []);

    const handleCreate = async () => {
        if (!newSnippetName.trim() || !newSnippetCode.trim()) {
            alert("Name and Code are required");
            return;
        }

        try {
            const res = await fetch('/sql-snippets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newSnippetName,
                    category: newSnippetCategory || "General",
                    code: newSnippetCode
                })
            });

            if (res.ok) {
                setIsCreating(false);
                setNewSnippetName("");
                setNewSnippetCode("");
                fetchSnippets();
                setSelectedCategory(newSnippetCategory || "General");
            } else {
                const err = await res.json();
                alert(err.detail || "Failed to save snippet");
            }
        } catch (e) {
            alert(e.message);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text).then(() => {
            // Could show a toast here
            const btn = document.activeElement;
            const originalText = btn.innerText;
            btn.innerText = "COPIED!";
            setTimeout(() => btn.innerText = originalText, 1000);
        });
    };

    const filteredSnippets = (snippets[selectedCategory] || []).filter(s =>
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.code.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="flex h-full bg-[#1d2021] text-[#ebdbb2] overflow-hidden">
            {/* Sidebar (Categories) */}
            <div className="w-64 bg-[#282828] border-r border-[#504945] flex flex-col flex-shrink-0">
                <div className="p-4 border-b border-[#504945] flex justify-between items-center">
                    <h3 className="font-bold text-[#ebdbb2] uppercase tracking-wider text-sm">Categories</h3>
                    <button
                        onClick={() => setIsCreating(true)}
                        className="text-[#fe8019] hover:text-[#fabd2f]"
                        title="Add Snippet"
                    >
                        <IconUpload /> {/* Reusing icon or add plus icon */}
                    </button>
                </div>
                <div className="overflow-y-auto flex-grow">
                    {categories.map(cat => (
                        <div
                            key={cat}
                            onClick={() => setSelectedCategory(cat)}
                            className={`px-4 py-3 cursor-pointer hover:bg-[#3c3836] flex justify-between items-center transition-colors ${selectedCategory === cat ? 'bg-[#3c3836] border-l-4 border-[#fe8019]' : 'border-l-4 border-transparent'}`}
                        >
                            <span className="font-medium">{cat}</span>
                            <span className="text-xs bg-[#504945] px-2 py-0.5 rounded-full text-[#a89984]">
                                {(snippets[cat] || []).length}
                            </span>
                        </div>
                    ))}
                    {categories.length === 0 && (
                        <div className="p-4 text-[#a89984] text-sm italic">No categories</div>
                    )}
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-grow flex flex-col h-full overflow-hidden">
                {/* Search Bar */}
                <div className="bg-[#1d2021] p-4 border-b border-[#504945] flex items-center space-x-4">
                    <div className="relative flex-grow max-w-lg">
                        <input
                            type="text"
                            placeholder="Search snippets..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-[#282828] border border-[#504945] rounded pl-10 pr-4 py-2 text-sm text-[#ebdbb2] focus:border-[#fe8019] outline-none transition-colors"
                        />
                        <div className="absolute left-3 top-2.5 text-[#a89984]">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        </div>
                    </div>
                </div>

                {/* Snippets List */}
                <div className="flex-grow overflow-y-auto p-6 space-y-6">
                    {filteredSnippets.length === 0 ? (
                        <div className="text-center text-[#504945] mt-10">
                            <p className="text-lg font-bold">No snippets found</p>
                            <p className="text-sm">Select a category or add a new snippet.</p>
                        </div>
                    ) : (
                        filteredSnippets.map((snippet) => (
                            <div key={snippet.name} className="bg-[#282828] border border-[#504945] rounded overflow-hidden shadow-sm hover:border-[#7c6f64] transition-colors">
                                <div className="bg-[#3c3836] px-4 py-2 border-b border-[#504945] flex justify-between items-center">
                                    <h4 className="font-bold text-[#ebdbb2] text-sm">{snippet.name}</h4>
                                    <button
                                        onClick={(e) => copyToClipboard(snippet.code)}
                                        className="text-[#a89984] hover:text-[#fe8019] text-xs font-bold uppercase tracking-wider flex items-center space-x-1"
                                    >
                                        <span>COPY</span>
                                    </button>
                                </div>
                                <div className="p-0 relative group">
                                    <pre className="p-4 overflow-x-auto text-xs font-mono text-[#d5c4a1] bg-[#1d2021] m-0">
                                        <code>{snippet.code}</code>
                                    </pre>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Create Snippet Modal */}
            {isCreating && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
                    <div className="bg-[#282828] border border-[#504945] rounded-lg shadow-xl w-full max-w-2xl p-6">
                        <h2 className="text-xl font-bold text-[#fe8019] mb-4">Add New SQL Snippet</h2>

                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-xs font-bold text-[#a89984] uppercase mb-1">Name</label>
                                <input
                                    type="text"
                                    value={newSnippetName}
                                    onChange={(e) => setNewSnippetName(e.target.value)}
                                    className="w-full bg-[#1d2021] border border-[#504945] rounded px-3 py-2 text-[#ebdbb2] focus:border-[#fe8019] outline-none"
                                    placeholder="daily_stats"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-[#a89984] uppercase mb-1">Category</label>
                                <input
                                    type="text"
                                    value={newSnippetCategory}
                                    onChange={(e) => setNewSnippetCategory(e.target.value)}
                                    className="w-full bg-[#1d2021] border border-[#504945] rounded px-3 py-2 text-[#ebdbb2] focus:border-[#fe8019] outline-none"
                                    placeholder="General"
                                    list="category-suggestions"
                                />
                                <datalist id="category-suggestions">
                                    {categories.map(c => <option key={c} value={c} />)}
                                </datalist>
                            </div>
                        </div>

                        <div className="mb-6">
                            <label className="block text-xs font-bold text-[#a89984] uppercase mb-1">SQL Code</label>
                            <textarea
                                value={newSnippetCode}
                                onChange={(e) => setNewSnippetCode(e.target.value)}
                                className="w-full bg-[#1d2021] border border-[#504945] rounded px-3 py-2 text-[#ebdbb2] font-mono text-sm focus:border-[#fe8019] outline-none h-48 resize-none"
                                placeholder="SELECT * FROM table..."
                            ></textarea>
                        </div>

                        <div className="flex justify-end space-x-3">
                            <button
                                onClick={() => setIsCreating(false)}
                                className="px-4 py-2 text-[#a89984] hover:text-[#ebdbb2] font-medium transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreate}
                                className="px-6 py-2 bg-[#fe8019] hover:bg-[#fabd2f] text-[#282828] font-bold rounded transition-colors"
                            >
                                SAVE SNIPPET
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
