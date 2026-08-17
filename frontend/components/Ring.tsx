export default function Ring({ percent, size = 44, label }: { percent: number; size?: number; label?: string }) {
  const stroke = Math.max(3, size * 0.09);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (percent / 100) * c;
  const color = percent >= 75 ? "#0d9488" : percent >= 45 ? "#d97706" : "#64748b";

  return (
    <span className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        />
      </svg>
      <span className="absolute font-semibold text-slate-800" style={{ fontSize: size * 0.24 }}>
        {label ?? `${Math.round(percent)}%`}
      </span>
    </span>
  );
}
