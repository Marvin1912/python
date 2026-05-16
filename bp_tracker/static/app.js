(() => {
  const form = document.getElementById("reading-form");
  const formMessage = document.getElementById("form-message");
  const latestReading = document.getElementById("latest-reading");

  const statsButton = document.getElementById("stats-button");
  const statsRange = document.getElementById("stats-range");
  const statsOutput = document.getElementById("stats-output");

  const historyRange = document.getElementById("history-range");
  const historyOutput = document.getElementById("history-output");
  const historyMessage = document.getElementById("history-message");
  const exportPdf = document.getElementById("export-pdf");

  const chartRange = document.getElementById("chart-range");
  const chartMessage = document.getElementById("chart-message");
  const chartCanvas = document.getElementById("bp-chart");

  const timesScatterCanvas = document.getElementById("bp-times-scatter");
  const timesScatterMessage = document.getElementById("times-scatter-message");

  let chart = null;
  let timesScatter = null;

  const CATEGORY_COLORS = {
    Normal: "#16a34a",
    Elevated: "#ca8a04",
    "Stage 1": "#ea580c",
    "Stage 2": "#dc2626",
    "Hypertensive Crisis": "#7f1d1d",
  };

  // ----- form submission -----

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formMessage.textContent = "";
    formMessage.className = "message";

    const data = Object.fromEntries(new FormData(form));
    // Strip empty optionals so the server treats them as absent.
    for (const key of ["pulse", "measured_at", "note"]) {
      if (!data[key]) delete data[key];
    }

    try {
      const res = await fetch("/api/readings", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(data),
      });
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      formMessage.textContent = "Saved.";
      formMessage.className = "message success";
      form.reset();
      renderReadingCard(body);
      refreshAfterMutation();
    } catch (err) {
      formMessage.textContent = err.message;
      formMessage.className = "message error";
    }
  });

  function renderReadingCard(reading) {
    const cls = categoryClass(reading.category);
    latestReading.innerHTML = `
      <div class="reading-card">
        <div class="pair">${reading.systolic}/${reading.diastolic}</div>
        <span class="badge ${cls}">${escapeHtml(reading.category)}</span>
        <div class="meta">${readingMetaHtml(reading)}</div>
      </div>
    `;
  }

  function readingMetaHtml(reading) {
    const measured = new Date(reading.measured_at).toLocaleString();
    const pulse = reading.pulse != null ? `, pulse ${reading.pulse}` : "";
    const note = reading.note ? `<br /><em>${escapeHtml(reading.note)}</em>` : "";
    return `
      ${measured}${pulse}<br />
      MAP ${reading.map} mmHg · pulse pressure ${reading.pulse_pressure} mmHg
      ${note}
    `;
  }

  function categoryClass(category) {
    return category.toLowerCase().replace(/\s+/g, "-");
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  // ----- stats -----

  statsButton.addEventListener("click", async () => {
    statsOutput.innerHTML = "";
    try {
      const res = await fetch(`/api/stats?range=${encodeURIComponent(statsRange.value)}`);
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      renderStats(body);
    } catch (err) {
      statsOutput.innerHTML = `<p class="message error">${escapeHtml(err.message)}</p>`;
    }
  });

  function renderStats(s) {
    if (!s.count) {
      statsOutput.innerHTML = `<p class="message">No readings in this range yet.</p>`;
      return;
    }
    statsOutput.innerHTML = [
      stat("Readings", s.count),
      stat("Systolic avg", s.systolic.avg),
      stat("Systolic median", s.systolic.median),
      stat("Diastolic avg", s.diastolic.avg),
      stat("Diastolic median", s.diastolic.median),
      stat("Pulse avg", s.pulse.avg ?? "—"),
      stat("Pulse median", s.pulse.median ?? "—"),
      stat("MAP avg", s.map_avg),
      stat("Pulse pressure avg", s.pulse_pressure_avg),
    ].join("");
  }

  function stat(label, value) {
    return `
      <div class="stat">
        <div class="label">${escapeHtml(label)}</div>
        <div class="value">${escapeHtml(value)}</div>
      </div>
    `;
  }

  // ----- history (list + edit + delete) -----

  // Cache of readings currently shown so edit can prefill from memory.
  let historyCache = new Map();

  historyRange.addEventListener("change", () => {
    updateExportLink();
    loadHistory(historyRange.value);
  });

  async function loadHistory(range) {
    historyMessage.textContent = "";
    historyMessage.className = "message";
    try {
      const res = await fetch(`/api/readings?range=${encodeURIComponent(range)}`);
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      const items = body.items || [];
      historyCache = new Map(items.map((r) => [String(r.id), r]));
      renderHistory(items);
    } catch (err) {
      historyOutput.innerHTML = "";
      historyMessage.textContent = err.message;
      historyMessage.className = "message error";
    }
  }

  function renderHistory(items) {
    if (!items.length) {
      historyOutput.innerHTML = "";
      historyMessage.textContent = "No readings in this range yet.";
      return;
    }
    historyMessage.textContent = "";
    // Newest first in the list view.
    const ordered = items.slice().reverse();
    historyOutput.innerHTML = ordered.map(historyRowHtml).join("");
  }

  function historyRowHtml(reading) {
    const cls = categoryClass(reading.category);
    return `
      <div class="history-row" data-id="${reading.id}">
        <div class="history-row-main">
          <div class="pair">${reading.systolic}/${reading.diastolic}</div>
          <span class="badge ${cls}">${escapeHtml(reading.category)}</span>
          <div class="meta">${readingMetaHtml(reading)}</div>
        </div>
        <div class="row-actions">
          <button type="button" class="secondary" data-action="edit">Edit</button>
          <button type="button" class="danger" data-action="delete">Delete</button>
        </div>
      </div>
    `;
  }

  historyOutput.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const row = button.closest(".history-row");
    if (!row) return;
    const id = row.dataset.id;
    const action = button.dataset.action;

    if (action === "edit") {
      const reading = historyCache.get(id);
      if (reading) startEdit(row, reading);
    } else if (action === "delete") {
      deleteReading(id);
    } else if (action === "save") {
      saveEdit(row, id);
    } else if (action === "cancel") {
      const reading = historyCache.get(id);
      if (reading) row.outerHTML = historyRowHtml(reading);
    }
  });

  function startEdit(row, reading) {
    const measured = toDatetimeLocal(reading.measured_at);
    row.outerHTML = `
      <div class="history-row history-row-editing" data-id="${reading.id}">
        <form class="history-edit-form" data-id="${reading.id}">
          <div class="row">
            <label>
              Systolic
              <input type="number" name="systolic" min="50" max="250" required value="${reading.systolic}" />
            </label>
            <label>
              Diastolic
              <input type="number" name="diastolic" min="30" max="150" required value="${reading.diastolic}" />
            </label>
            <label>
              Pulse
              <input type="number" name="pulse" min="20" max="250" value="${reading.pulse ?? ""}" />
            </label>
            <label>
              Measured at
              <input type="datetime-local" name="measured_at" value="${measured}" />
            </label>
          </div>
          <label>
            Note
            <textarea name="note" rows="2">${escapeHtml(reading.note ?? "")}</textarea>
          </label>
          <p class="message edit-message"></p>
          <div class="row-actions">
            <button type="button" data-action="save">Save</button>
            <button type="button" class="secondary" data-action="cancel">Cancel</button>
          </div>
        </form>
      </div>
    `;
  }

  async function saveEdit(row, id) {
    const form = row.querySelector("form.history-edit-form");
    const message = row.querySelector(".edit-message");
    message.textContent = "";
    message.className = "message edit-message";

    const data = Object.fromEntries(new FormData(form));
    for (const key of ["pulse", "measured_at", "note"]) {
      if (!data[key]) delete data[key];
    }

    try {
      const res = await fetch(`/api/readings/${encodeURIComponent(id)}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(data),
      });
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      historyCache.set(String(body.id), body);
      const newRow = document.createElement("div");
      newRow.innerHTML = historyRowHtml(body).trim();
      row.replaceWith(newRow.firstChild);
      refreshAfterMutation();
    } catch (err) {
      message.textContent = err.message;
      message.className = "message edit-message error";
    }
  }

  async function deleteReading(id) {
    if (!confirm("Delete this reading? This cannot be undone.")) return;
    try {
      const res = await fetch(`/api/readings/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      historyCache.delete(String(id));
      loadHistory(historyRange.value);
      refreshAfterMutation();
    } catch (err) {
      historyMessage.textContent = err.message;
      historyMessage.className = "message error";
    }
  }

  function toDatetimeLocal(iso) {
    // <input type="datetime-local"> wants "YYYY-MM-DDTHH:MM" in local time.
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    return (
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
      `T${pad(d.getHours())}:${pad(d.getMinutes())}`
    );
  }

  function updateExportLink() {
    exportPdf.href = `/api/readings/export.pdf?range=${encodeURIComponent(historyRange.value)}`;
  }

  function refreshAfterMutation() {
    loadHistory(historyRange.value);
    loadChart(chartRange.value);
    loadTimesScatter(chartRange.value);
  }

  // ----- chart -----

  chartRange.addEventListener("change", () => {
    loadChart(chartRange.value);
    loadTimesScatter(chartRange.value);
  });

  async function loadChart(range) {
    chartMessage.textContent = "";
    chartMessage.className = "message";
    try {
      const res = await fetch(`/api/readings?range=${encodeURIComponent(range)}`);
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      const items = body.items || [];
      if (!items.length) {
        if (chart) {
          chart.destroy();
          chart = null;
        }
        chartMessage.textContent = "No readings in this range yet.";
        return;
      }
      renderChart(items);
    } catch (err) {
      chartMessage.textContent = err.message;
      chartMessage.className = "message error";
    }
  }

  function renderChart(items) {
    const labels = items.map((r) => r.measured_at);
    const data = {
      labels,
      datasets: [
        dataset("Systolic", items.map((r) => r.systolic), "#dc2626"),
        dataset("Diastolic", items.map((r) => r.diastolic), "#2563eb"),
        dataset(
          "Pulse",
          items.map((r) => r.pulse),
          "#16a34a",
          true
        ),
      ],
    };
    if (chart) chart.destroy();
    chart = new Chart(chartCanvas, {
      type: "line",
      data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            type: "time",
            time: { tooltipFormat: "PPpp" },
            ticks: { maxRotation: 0, autoSkip: true },
          },
          y: { beginAtZero: false },
        },
        plugins: {
          legend: { position: "bottom" },
        },
      },
    });
  }

  function dataset(label, values, color, spanGaps = false) {
    return {
      label,
      data: values,
      borderColor: color,
      backgroundColor: color,
      tension: 0.2,
      spanGaps,
    };
  }

  // ----- times scatter -----

  async function loadTimesScatter(range) {
    timesScatterMessage.textContent = "";
    timesScatterMessage.className = "message";
    try {
      const res = await fetch(`/api/readings?range=${encodeURIComponent(range)}`);
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      const items = body.items || [];
      if (!items.length) {
        if (timesScatter) {
          timesScatter.destroy();
          timesScatter = null;
        }
        timesScatterMessage.textContent = "No readings in this range yet.";
        return;
      }
      renderTimesScatter(items);
    } catch (err) {
      timesScatterMessage.textContent = err.message;
      timesScatterMessage.className = "message error";
    }
  }

  function jitterFromId(id) {
    return (((id * 9301 + 49297) % 233280) / 233280) - 0.5;
  }

  function pad2(n) {
    return n < 10 ? `0${n}` : `${n}`;
  }

  function renderTimesScatter(items) {
    const points = items.map((r) => {
      const d = new Date(r.measured_at);
      const x = d.getHours() + d.getMinutes() / 60 + d.getSeconds() / 3600;
      return {
        x,
        y: jitterFromId(r.id),
        category: r.category,
        measured_at: r.measured_at,
      };
    });
    const colorsArr = points.map((p) => CATEGORY_COLORS[p.category] || "#64748b");

    if (timesScatter) timesScatter.destroy();
    timesScatter = new Chart(timesScatterCanvas, {
      type: "scatter",
      data: {
        datasets: [
          {
            label: "Reading time",
            data: points,
            backgroundColor: colorsArr,
            borderColor: colorsArr,
            pointRadius: 5,
            pointHoverRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: "linear",
            min: 0,
            max: 24,
            ticks: {
              stepSize: 3,
              callback: (value) => `${pad2(value)}:00`,
            },
            title: { display: false },
          },
          y: {
            display: false,
            min: -1,
            max: 1,
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const p = ctx.raw;
                const d = new Date(p.measured_at);
                const hhmm = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
                return `${hhmm} — ${p.category}`;
              },
            },
          },
        },
      },
    });
  }

  // initial render
  updateExportLink();
  loadHistory(historyRange.value);
  loadChart(chartRange.value);
  loadTimesScatter(chartRange.value);
})();
