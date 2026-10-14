(() => {
  const root = document.getElementById("quiz");
  const box = document.getElementById("quiz-box");
  const api = `/api/quiz/${root.dataset.lesson}`;
  let items = [], i = 0, tryNo = 1, t0 = 0, prev = null;

  const el = (tag, text, cls, parent) => {
    const n = document.createElement(tag);
    if (text) n.textContent = text;
    if (cls) n.className = cls;
    if (parent) parent.append(n);
    return n;
  };
  const btn = (label, onclick, parent) => {
    const b = el("button", label, "", parent);
    b.type = "button";
    b.onclick = onclick;
    return b;
  };

  async function load() {
    const d = await (await fetch(api)).json();
    items = d.items;
    i = items.findIndex((x) => !x.answered || x.can_retry);
    if (i < 0) return finish(d);
    tryNo = items[i].can_retry ? 2 : 1;
    prev = null;
    render();
  }

  function finish(d) {
    box.replaceChildren();
    el("p", `Score: ${Math.round(d.score * 100)}% right on the first try.`, "quiz-score", box);
    const missed = d.items.filter((x) => x.correct_first_try === false);
    if (missed.length) {
      el("p", "Review misses:", "", box);
      const ul = el("ul", "", "", box);
      missed.forEach((x) => el("li", x.prompt, "", ul));
    }
  }

  function render() {
    const item = items[i];
    let answer = null;
    t0 = Date.now();
    box.replaceChildren();
    el("p", `Item ${i + 1} of ${items.length}`, "muted", box);
    el("p", item.prompt, "", box);
    if (prev) show(prev);
    const controls = el("div", "", "", box);
    if (item.type === "single") {
      item.options.forEach((t, k) => {
        const b = btn(t, () => {
          answer = k;
          controls.querySelectorAll(".quiz-opt").forEach((o) => o.classList.remove("sel"));
          b.classList.add("sel");
        }, controls);
        b.classList.add("quiz-opt");
      });
    } else if (item.type === "order") {
      const pos = item.steps.map((_, k) => k);
      answer = pos;
      const draw = () => {
        controls.replaceChildren();
        const ol = el("ol", "", "", controls);
        pos.forEach((p, k) => {
          const li = el("li", item.steps[p] + " ", "", ol);
          btn("Up", () => swap(k, k - 1), li).disabled = k === 0;
          btn("Down", () => swap(k, k + 1), li).disabled = k === pos.length - 1;
        });
      };
      const swap = (a, b) => ([pos[a], pos[b]] = [pos[b], pos[a]], draw());
      draw();
    } else {
      const input = el("input", "", "", controls);
      input.type = "text";
      input.oninput = () => (answer = input.value);
    }
    const row = el("div", "", "quiz-conf", box);
    el("span", "How sure are you?", "muted", row);
    [["sure", "Sure"], ["thinkso", "Think so"], ["guessing", "Guessing"]].forEach(([c, label]) =>
      btn(label, () => answer !== null && answer !== "" && submit(item, answer, c), row));
  }

  function show(r) {
    const d = el("div", "", r.correct ? "quiz-msg ok" : "quiz-msg bad", box);
    el("strong", r.correct ? "Correct." : "Not quite.", "", d);
    if (r.surprise) el("p", "Surprise! You were sure, and it was wrong. That is worth remembering.", "quiz-surprise", d);
    [r.feedback, r.misconception, r.explanation].forEach((t) => t && el("p", t, "", d));
  }

  async function submit(item, answer, confidence) {
    box.querySelectorAll("button").forEach((b) => (b.disabled = true));
    const res = await fetch(`${api}/${item.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer, confidence, try_no: tryNo, elapsed_ms: Date.now() - t0 }),
    });
    if (!res.ok) return el("p", "Could not submit that answer.", "quiz-msg bad", box);
    const r = await res.json();
    box.replaceChildren();
    el("p", `Item ${i + 1} of ${items.length}`, "muted", box);
    el("p", item.prompt, "", box);
    show(r);
    if (!r.correct && r.correct_answer !== null) {
      const ca = r.correct_answer;
      const text = item.type === "single" ? item.options[ca] : item.type === "order" ? ca.map((p) => item.steps[p]).join(" -> ") : ca;
      el("p", `Answer: ${text}`, "", box);
    }
    if (!r.correct && tryNo === 1) {
      btn("Try again", () => { tryNo = 2; prev = r; render(); }, box);
    } else {
      btn(i + 1 < items.length ? "Next" : "See score", async () => {
        if (i + 1 < items.length) { i++; tryNo = 1; prev = null; render(); }
        else finish(await (await fetch(api)).json());
      }, box);
    }
  }

  load();
})();
