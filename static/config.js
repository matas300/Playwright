"use strict";

document.getElementById("btn-save-config").addEventListener("click", async () => {
  const status = document.getElementById("save-status");
  let parsed;
  try {
    parsed = JSON.parse(document.getElementById("config-json").value);
  } catch (e) {
    status.textContent = "JSON non valido: " + e.message;
    return;
  }
  const r = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed),
  });
  status.textContent = r.ok ? "Salvato ✓" : "Errore";
});
