"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

// maplibre touches window — load it only in the browser.
const MapExplorer = dynamic(() => import("./MapExplorer"), { ssr: false });

function Candidate({ c }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="candidate">
      <div className="head" onClick={() => setOpen((o) => !o)}>
        <span className={`pill ${c.passed ? "pass" : "fail"}`}>{c.passed ? "PASS" : "FAIL"}</span>
        <span className="name">{c.name}</span>
        {c.failure_class && <span className="pill cat">{c.failure_class}</span>}
        <span className="muted" style={{ marginLeft: "auto", fontSize: 12 }}>
          {open ? "▾" : "▸"} {c.solution_code ? "code" : "output"}
        </span>
      </div>
      {c.description && <div className="why">{c.description}</div>}
      {open && c.solution_code && <pre>{c.solution_code}</pre>}
      {open && <div className="detailtext">verifier: {c.detail}</div>}
    </div>
  );
}

export default function TaskDetail({ task }) {
  if (!task) return <div className="card muted">Select a task to inspect its candidates.</div>;
  return (
    <div className="card detail">
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
        <span className="pill cat">{task.category}</span>
        <span className="pill cat">{task.difficulty}</span>
        {!task.solvable && <span className="pill fail">unsolvable</span>}
      </div>
      <h2 style={{ marginTop: 0 }}>{task.id}</h2>
      <p style={{ marginTop: 0 }}>{task.prompt}</p>
      <p className="sub">
        golden: <code>{task.golden_summary}</code>
        {task.rejection_reason && <> · reason: {task.rejection_reason}</>}
      </p>

      {task.map && <MapExplorer mapPath={task.map} />}

      <h3 style={{ fontSize: 14, marginBottom: 4 }}>Candidates</h3>
      {task.candidates.map((c) => (
        <Candidate key={c.name} c={c} />
      ))}
    </div>
  );
}
