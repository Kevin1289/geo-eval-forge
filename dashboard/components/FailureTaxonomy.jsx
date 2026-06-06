export default function FailureTaxonomy({ taxonomy }) {
  const max = Math.max(1, ...taxonomy.map((t) => t.count));
  return (
    <div className="card">
      <h2>Failure taxonomy</h2>
      {taxonomy.length === 0 && <p className="muted">No failures recorded.</p>}
      <div className="tax">
        {taxonomy.map((t) => (
          <div className="row" key={t.failure_class}>
            <div>
              <div className="label">
                {t.failure_class} <small>· e.g. {t.example_task}</small>
              </div>
              <div className="bar"><span style={{ width: `${(t.count / max) * 100}%` }} /></div>
            </div>
            <div className="num">{t.count}</div>
          </div>
        ))}
      </div>
      <p className="sub" style={{ marginTop: 10 }}>
        Each class is a plausible-but-wrong "AI-rot" pattern the verifiers caught.
      </p>
    </div>
  );
}
