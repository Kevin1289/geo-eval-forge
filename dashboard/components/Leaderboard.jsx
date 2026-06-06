function pct(v) {
  return v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
}

function rowClass(model) {
  if (model === "expert") return "model-expert";
  if (model === "naive-llm") return "model-naive";
  return "";
}

export default function Leaderboard({ leaderboard, categories }) {
  return (
    <div className="card">
      <h2>Leaderboard</h2>
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th className="num">Overall</th>
            {categories.map((c) => (
              <th key={c} className="num">{c}</th>
            ))}
            <th className="num">Rejection</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard.map((row) => (
            <tr key={row.model} className={rowClass(row.model)}>
              <td>{row.model}</td>
              <td className="num">{pct(row.overall)}</td>
              {categories.map((c) => (
                <td key={c} className="num">{pct(row.by_category?.[c])}</td>
              ))}
              <td className="num">{pct(row.rejection_accuracy)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="sub" style={{ marginTop: 10 }}>
        <code>expert</code> always picks the correct solution; <code>naive-llm</code> falls into the
        documented trap on every task that has one. Live model rows appear above these when you run{" "}
        <code>geoeval run --adapter vertex</code>.
      </p>
    </div>
  );
}
