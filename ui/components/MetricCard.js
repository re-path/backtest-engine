const MetricCard = ({ label, value, subValue, positive }) => (
    <div className="bg-[#282828] p-4 rounded border border-[#504945] hover:border-[#fe8019] transition-colors">
        <p className="text-[#a89984] text-xs font-semibold uppercase tracking-wider mb-1">{label}</p>
        <p className={`text-2xl font-bold font-mono ${positive === true ? 'text-[#b8bb26]' : positive === false ? 'text-[#fb4934]' : 'text-[#ebdbb2]'}`}>
            {value}
        </p>
        {subValue && <p className="text-xs text-[#a89984] mt-1">{subValue}</p>}
    </div>
);
