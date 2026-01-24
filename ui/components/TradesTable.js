const TradesTable = ({ events }) => {
    const [searchTerm, setSearchTerm] = useState('');

    const filteredEvents = events.filter(ev => {
        const searchLower = searchTerm.toLowerCase();
        return (
            (ev.ticker && ev.ticker.toLowerCase().includes(searchLower)) ||
            (ev.event_type && ev.event_type.toLowerCase().includes(searchLower))
        );
    });

    return (
        <div className="flex flex-col h-full overflow-hidden">
            <div className="p-2 border-b border-[#504945] bg-[#1d2021] flex items-center gap-2">
                <IconSettings /> {/* Reusing an icon for the search bar prefix or just a search icon if I had one */}
                <input
                    type="text"
                    placeholder="Search by Ticker or Event Type..."
                    className="bg-[#282828] border border-[#504945] text-[#ebdbb2] text-xs p-1.5 rounded w-64 outline-none focus:border-[#fe8019] transition-colors"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
                <span className="text-[10px] text-[#a89984] font-mono uppercase">
                    Showing {filteredEvents.length} of {events.length} events
                </span>
            </div>
            <div className="overflow-auto flex-grow">
                <table className="w-full text-left border-collapse font-mono text-xs">
                    <thead className="sticky top-0 bg-[#282828] text-[#a89984] uppercase font-bold z-10">
                        <tr>
                            <th className="p-2 border-b border-[#504945]">Time</th>
                            <th className="p-2 border-b border-[#504945]">Event</th>
                            <th className="p-2 border-b border-[#504945]">Ticker</th>
                            <th className="p-2 border-b border-[#504945]">Price</th>
                            <th className="p-2 border-b border-[#504945]">Change</th>
                            <th className="p-2 border-b border-[#504945]">Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredEvents.map((ev, i) => (
                            <tr key={i} className="border-b border-[#3c3836] hover:bg-[#282828] transition-colors">
                                <td className="p-2 text-[#ebdbb2] whitespace-nowrap">{ev.timestamp.split('.')[0]}</td>
                                <td className="p-2">
                                    <span className={`px-1.5 py-0.5 rounded-sm font-bold ${ev.event_type === 'BUY' ? 'bg-[#b8bb26] text-[#282828]' :
                                        ev.event_type.startsWith('SELL') ? 'bg-[#fb4934] text-[#282828]' :
                                            'bg-[#3c3836] text-[#a89984]'
                                        }`}>
                                        {ev.event_type}
                                    </span>
                                </td>
                                <td className="p-2 text-[#83a598]">{ev.ticker || '-'}</td>
                                <td className="p-2 text-[#fabd2f]">{ev.price ? parseFloat(ev.price).toFixed(2) : '-'}</td>
                                <td className={`p-2 ${parseFloat(ev.money_change) > 0 ? 'text-[#b8bb26]' : parseFloat(ev.money_change) < 0 ? 'text-[#fb4934]' : 'text-[#a89984]'}`}>
                                    {ev.money_change !== '0.0' ? parseFloat(ev.money_change).toFixed(2) : '-'}
                                </td>
                                <td className="p-2 text-[#ebdbb2] font-bold">{parseFloat(ev.portfolio_balance).toFixed(2)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
