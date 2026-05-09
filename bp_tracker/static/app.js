(() => {
  const form = document.getElementById("reading-form");
  const formMessage = document.getElementById("form-message");
  const latestReading = document.getElementById("latest-reading");

  const statsButton = document.getElementById("stats-button");
  const statsRange = document.getElementById("stats-range");
  const statsOutput = document.getElementById("stats-output");

  const chartRange = document.getElementById("chart-range");
  const chartMessage = document.getElementById("chart-message");
  const chartCanvas = document.getElementById("bp-chart");

  let chart = null;

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
      // Refresh the chart so the new point shows up immediately.
      loadChart(chartRange.value);
    } catch (err) {
      formMessage.textContent = err.message;
      formMessage.className = "message error";
    }
  });

  function renderReadingCard(reading) {
    const cls = categoryClass(reading.category);
    const measured = new Date(reading.measured_at).toLocaleString();
    const pulse = reading.pulse != null ? `, pulse ${reading.pulse}` : "";
    latestReading.innerHTML = `
      <div class="reading-card">
        <div class="pair">${reading.systolic}/${reading.diastolic}</div>
        <span class="badge ${cls}">${escapeHtml(reading.category)}</span>
        <div class="meta">
          ${measured}${pulse}<br />
          MAP ${reading.map} mmHg · pulse pressure ${reading.pulse_pressure} mmHg
          ${reading.note ? `<br /><em>${escapeHtml(reading.note)}</em>` : ""}
        </div>
      </div>
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

  // ----- chart -----

  chartRange.addEventListener("change", () => loadChart(chartRange.value));

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

  // initial render
  loadChart(chartRange.value);
})();
