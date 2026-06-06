"use client";

import { useEffect, useState } from "react";
import Leaderboard from "../components/Leaderboard";
import FailureTaxonomy from "../components/FailureTaxonomy";
import JudgeAgreement from "../components/JudgeAgreement";
import TaskDetail from "../components/TaskDetail";

export default function Page() {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    fetch("results.json")
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setSelected(d.tasks?.[0]?.id ?? null);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div className="wrap"><p className="muted">Could not load results.json — run <code>make run</code> first. ({err})</p></div>;
  if (!data) return <div className="wrap"><p className="muted">Loading…</p></div>;

  const task = data.tasks.find((t) => t.id === selected);

  return (
    <div className="wrap">
      <header className="hero">
        <h1>geo-eval-forge</h1>
        <p>A reproducible GeoAI benchmark + eval harness — every pass/fail proven by the real geo stack.</p>
        <div className="badges">
          <span className="badge">suite: {data.suite}</span>
          <span className="badge">mode: {data.mode}</span>
          <span className="badge">{data.tasks.length} tasks</span>
          <span className="badge">categories: {data.categories.join(", ")}</span>
        </div>
      </header>

      <div className="grid">
        <Leaderboard leaderboard={data.leaderboard} categories={data.categories} />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 2fr" }}>
        <JudgeAgreement judge={data.judge} />
        <FailureTaxonomy taxonomy={data.failure_taxonomy} />
      </div>

      <h2 style={{ marginTop: 28, marginBottom: 10 }}>Tasks</h2>
      <div className="grid" style={{ gridTemplateColumns: "minmax(240px, 1fr) 2fr", alignItems: "start" }}>
        <div className="tasklist">
          {data.tasks.map((t) => {
            const correct = t.candidates.find((c) => c.label === "correct");
            return (
              <div
                key={t.id}
                className={`taskrow ${t.id === selected ? "active" : ""}`}
                onClick={() => setSelected(t.id)}
              >
                <span className={`pill ${correct?.passed ? "pass" : "fail"}`}>
                  {correct?.passed ? "✓" : "✗"}
                </span>
                <span className="title">
                  {t.id}
                  <small>{t.category} · {t.candidates.length} candidates</small>
                </span>
              </div>
            );
          })}
        </div>
        <TaskDetail task={task} />
      </div>

      <p className="sub" style={{ marginTop: 32 }}>
        Built by <code>geoeval run</code> → <code>results/results.json</code>. Code MIT · data CC BY 4.0.
      </p>
    </div>
  );
}
