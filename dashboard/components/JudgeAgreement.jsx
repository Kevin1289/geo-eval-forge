export default function JudgeAgreement({ judge }) {
  const has = judge && judge.calibrated && judge.human_agreement !== null;
  return (
    <div className="card">
      <h2>LLM-as-judge agreement</h2>
      <div className="big">{has ? `${Math.round(judge.human_agreement * 100)}%` : "—"}</div>
      <div className="sub">
        {has
          ? `measured against ${judge.n_labels} hand-annotated labels`
          : "not calibrated — run `geoeval judge`"}
      </div>
      <p className="sub" style={{ marginTop: 10 }}>
        Reported, not assumed: the judge is only used where deterministic verifiers can't grade,
        and its agreement with humans is measured (cf. GeoBenchX 88–96%).
      </p>
    </div>
  );
}
