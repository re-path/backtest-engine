const AnalysisRow = ({ label, value, positive }) => (
    <div className="flex justify-between items-center py-2 border-b border-[#504945] last:border-0 hover:bg-[#3c3836] px-2 rounded">
        <span className="text-[#a89984] text-sm">{label}</span>
        <span className={`font-mono font-medium ${positive === true ? 'text-[#b8bb26]' : positive === false ? 'text-[#fb4934]' : 'text-[#d5c4a1]'}`}>
            {value}
        </span>
    </div>
);
