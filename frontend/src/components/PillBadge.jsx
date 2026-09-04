export function SensitivityPill({ level }) {
  const map = {
    public: "pill-green",
    internal: "pill-blue",
    confidential: "pill-yellow",
    highly_sensitive: "pill-red",
  };
  return <span className={`pill ${map[level] || ""}`} data-testid={`sens-${level}`}>{level}</span>;
}

export function ModePill({ mode }) {
  const map = {
    local: "pill-green",
    cloud: "pill-blue",
    both: "pill-yellow",
    auto: "",
    none: "",
  };
  return <span className={`pill ${map[mode] || ""}`}>{mode || "—"}</span>;
}
