// Trace player: one step at a time, pauses at a checkpoint until the learner answers.
(async () => {
  const root = document.getElementById("trace");
  if (!root) return;
  const $ = (id) => document.getElementById(id);
  const api = `/api/trace/${encodeURIComponent(root.dataset.lesson)}`;
  const res = await fetch(api);
  if (!res.ok) { $("trace-step").textContent = "No trace for this lesson."; return; }
  const trace = await res.json();
  let i = 0;
  const answered = new Set();

  const el = (tag, text, cls) => {
    const e = document.createElement(tag);
    e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };

  function render() {
    const s = trace.steps[i];
    const card = $("trace-step");
    card.replaceChildren(el("h3", `${i + 1}/${trace.steps.length}  ${s.title}`), el("p", s.summary, "trace-meta"));
    if (s.payload_excerpt) card.append(el("pre", s.payload_excerpt));
    const m = Object.entries(s.metrics || {}).map(([k, v]) => `${k}: ${v}`).join(" · ");
    if (m) card.append(el("p", m, "trace-meta"));
    // Annotation stays hidden while a checkpoint is unanswered: it may give the answer away.
    const locked = s.checkpoint && !answered.has(i);
    if (s.annotation && !locked) {
      card.append(el("p", s.annotation.why), el("p", s.annotation.concept_tags.join(", "), "trace-meta"));
      for (const c of s.annotation.citations) {
        const a = el("a", c.title);
        a.href = c.url;
        card.append(a, " ");
      }
    }
    $("trace-progress").max = trace.steps.length;
    $("trace-progress").value = i + 1;
    $("trace-prev").disabled = i === 0;
    $("trace-next").disabled = i === trace.steps.length - 1 || locked;
    const box = $("trace-checkpoint");
    box.hidden = !s.checkpoint;
    $("trace-result").textContent = "";
    $("trace-options").replaceChildren();
    if (!s.checkpoint) return;
    $("trace-prompt").textContent = s.checkpoint.prompt;
    s.checkpoint.options.forEach((opt, n) => {
      const b = el("button", opt);
      b.type = "button";
      b.disabled = answered.has(i);
      b.onclick = () => choose(s.idx, n);
      $("trace-options").append(b);
    });
  }

  async function choose(idx, n) {
    const r = await fetch(`${api}/${idx}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ choice: n }),
    });
    if (!r.ok) return;
    const out = await r.json();
    answered.add(i);
    render();
    $("trace-checkpoint").hidden = false;
    $("trace-result").textContent = `${out.correct ? "✓" : "✗"} ${out.explanation}`;
  }

  $("trace-prev").onclick = () => { i -= 1; render(); };
  $("trace-next").onclick = () => { i += 1; render(); };
  render();
})();
