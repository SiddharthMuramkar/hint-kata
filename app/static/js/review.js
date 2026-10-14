(async () => {
  const items = Object.fromEntries(
    (await (await fetch("/api/review")).json()).map((x) => [x.card_id, x]));

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

  document.querySelectorAll("[data-review-card]").forEach((card) => {
    const item = items[card.dataset.reviewCard];
    const box = card.querySelector(".review-controls");
    if (!item) return;
    const t0 = Date.now();
    let answer = null;

    async function submit(payload) {
      const res = await fetch(`/api/review/${item.card_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ elapsed_ms: Date.now() - t0, ...payload }),
      });
      box.replaceChildren();
      if (!res.ok) return el("p", "Could not submit that answer.", "quiz-msg bad", box);
      const r = await res.json();
      const d = el("div", "", r.correct ? "quiz-msg ok" : "quiz-msg bad", box);
      el("strong", r.correct ? "Good." : "We will ask again soon.", "", d);
      if (r.feedback) el("p", r.feedback, "", d);
      el("p", `Next review: ${new Date(r.next_due).toLocaleString()}`, "muted", d);
    }

    if (item.kind === "criterion") {
      btn("I can explain this now", () => submit({ self_rating: "good" }), box);
      btn("Still shaky", () => submit({ self_rating: "again" }), box);
      return;
    }
    if (item.type === "single") {
      item.options.forEach((t, k) => {
        const b = btn(t, () => {
          answer = k;
          box.querySelectorAll(".quiz-opt").forEach((o) => o.classList.remove("sel"));
          b.classList.add("sel");
        }, box);
        b.classList.add("quiz-opt");
      });
    } else if (item.type === "order") {
      const pos = item.steps.map((_, k) => k);
      answer = pos;
      const list = el("div", "", "", box);
      const draw = () => {
        list.replaceChildren();
        const ol = el("ol", "", "", list);
        pos.forEach((p, k) => {
          const li = el("li", item.steps[p] + " ", "", ol);
          btn("Up", () => swap(k, k - 1), li).disabled = k === 0;
          btn("Down", () => swap(k, k + 1), li).disabled = k === pos.length - 1;
        });
      };
      const swap = (a, b) => ([pos[a], pos[b]] = [pos[b], pos[a]], draw());
      draw();
    } else {
      const input = el("input", "", "", box);
      input.type = "text";
      input.oninput = () => (answer = input.value);
    }
    const row = el("div", "", "quiz-conf", box);
    el("span", "How sure are you?", "muted", row);
    [["sure", "Sure"], ["thinkso", "Think so"], ["guessing", "Guessing"]].forEach(([c, label]) =>
      btn(label, () => answer !== null && answer !== "" && submit({ answer, confidence: c }), row));
  });
})();
