// Tutor chat: POST, read the SSE stream, show tokens as text, then swap in the server-rendered HTML.
(() => {
  const root = document.getElementById("tutor");
  if (!root) return;
  const base = "/api/tutor/" + encodeURIComponent(root.dataset.lesson);
  const log = document.getElementById("tutor-log");
  const form = document.getElementById("tutor-form");
  const level = document.getElementById("tutor-level");
  const answer = document.getElementById("tutor-answer");

  const bubble = (role) => {
    const el = document.createElement("article");
    el.className = "markdown-body tutor-" + role;
    log.append(el);
    return el;
  };
  const cites = (el, list) => {
    if (!list.length) return;
    const p = document.createElement("p");
    p.append("Sources: ");
    list.forEach((c) => {
      const a = document.createElement("a");
      a.href = c.href;
      a.textContent = "§" + c.title;
      p.append(a, " ");
      if (c.source_url) {
        const s = document.createElement("a");
        s.href = c.source_url;
        s.textContent = "(docs)";
        p.append(s, " ");
      }
    });
    el.append(p);
  };

  fetch(base + "/history").then((r) => r.json()).then((turns) => {
    for (const t of turns) {
      const el = bubble(t.role);
      if (t.role === "user") el.textContent = t.text;
      else {
        el.innerHTML = t.html; // server-rendered with html=False
        cites(el, t.citations);
        level.textContent = t.ceiling;
      }
    }
  }).catch(() => {});

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = form.elements.namedItem("message");
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    bubble("user").textContent = message;
    const reply = bubble("assistant");
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const res = await fetch(base, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ message, active_item: root.dataset.activeItem || null }),
      });
      if (!res.ok || !res.body) throw new Error("HTTP " + res.status);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut;
        while ((cut = buffer.indexOf("\n\n")) !== -1) {
          const block = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);
          let type = "message", data = "";
          for (const line of block.split("\n")) {
            if (line.startsWith("event: ")) type = line.slice(7);
            else if (line.startsWith("data: ")) data += line.slice(6);
          }
          if (!data) continue; // ': ping' keep-alives
          const v = JSON.parse(data);
          if (type === "token") reply.textContent += v;
          else if (type === "html") reply.innerHTML = v; // server-rendered with html=False
          else if (type === "ceiling") level.textContent = v;
          else if (type === "citations") cites(reply, v);
          else if (type === "error") reply.textContent += "\n[error] " + v;
        }
      }
    } catch (err) {
      reply.textContent += "\n[connection error: " + err.message + "]";
    } finally {
      button.disabled = false;
    }
  });

  const reveal = document.getElementById("tutor-reveal");
  if (reveal) {
    reveal.addEventListener("click", async () => {
      if (!window.confirm("This is logged and you will be re-tested on it later. Continue?")) return;
      const item_id = document.getElementById("tutor-item").value;
      const res = await fetch(base + "/reveal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id }),
      });
      answer.textContent = res.ok ? (await res.json()).answer : "Could not reveal that item.";
      answer.hidden = false;
      if (res.ok) level.textContent = "L6";
    });
  }
})();
