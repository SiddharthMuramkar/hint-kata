// "Check my work": POST the lesson's check, show the output. textContent only, never innerHTML.
(() => {
  const task = document.getElementById("task");
  const btn = document.getElementById("check-btn");
  const out = document.getElementById("check-output");
  if (!task || !btn || !out) return;
  const url = "/api/check/" + encodeURIComponent(task.dataset.lesson);
  const show = (r) => {
    if (r.passed === null) return;
    out.textContent = (r.passed ? "✓ Passed" : "✗ Not yet") + "\n\n" + r.output;
  };
  fetch(url).then((r) => r.json()).then(show).catch(() => {});
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    out.textContent = "Running…";
    try {
      show(await (await fetch(url, { method: "POST" })).json());
    } catch (e) {
      out.textContent = "✗ Could not run the check: " + e;
    } finally {
      btn.disabled = false;
    }
  });
})();
