// Think-deeper: POST the answer, show per-criterion results. textContent only, never innerHTML.
(() => {
  const root = document.getElementById("deeper");
  if (!root) return;
  const base = "/api/deeper/" + encodeURIComponent(root.dataset.lesson) + "/";
  const el = (tag, text, cls) => {
    const e = document.createElement(tag);
    e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
  const render = (box, r) => {
    const out = box.querySelector(".result");
    out.replaceChildren(el("p", "Attempt " + r.attempt_no + ": " + r.feedback));
    const ul = document.createElement("ul");
    for (const c of r.criteria) {
      const mark = c.met ? "✓" : c.uncertain ? "?" : "✗";
      const li = el("li", mark + " " + c.name + (c.uncertain ? " (not sure)" : ""));
      if (c.evidence) li.append(el("div", "“" + c.evidence + "”", "muted"));
      if (c.feedback_hint) li.append(el("div", "Hint: " + c.feedback_hint));
      ul.append(li);
    }
    out.append(ul);
    if (r.model_answer) out.append(el("p", "Model answer: " + r.model_answer));
    box.querySelector(".submit").hidden = r.attempt_no > 0;
    box.querySelector(".revise").hidden = !r.can_retry;
    box.querySelector("textarea").readOnly = !r.can_retry;
  };
  for (const box of root.querySelectorAll(".deeper-q")) {
    const url = base + encodeURIComponent(box.dataset.question);
    const area = box.querySelector("textarea");
    const result = box.querySelector(".result");
    const submit = async (btn) => {
      btn.disabled = true;
      result.textContent = "Grading…";
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answer: area.value }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || res.status);
        render(box, await res.json());
      } catch (e) {
        result.textContent = "Could not grade: " + e;
      } finally {
        btn.disabled = false;
      }
    };
    for (const btn of box.querySelectorAll(".submit, .revise")) {
      btn.addEventListener("click", () => submit(btn));
    }
    fetch(url)
      .then((r) => r.json())
      .then((rows) => {
        if (rows.length) render(box, rows[rows.length - 1]);
      })
      .catch(() => {});
  }
})();
