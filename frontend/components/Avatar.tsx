function initialsFor(nameOrId: string) {
  const parts = nameOrId.replace(/_/g, " ").trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export default function Avatar({ name, size = 28 }: { name: string; size?: number }) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-teal-600 text-white font-medium"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {initialsFor(name)}
    </span>
  );
}
