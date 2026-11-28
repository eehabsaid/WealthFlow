"use strict";

// ── Income Analytics — Chart.js charts (off / yoy / mom) ──

function _incomeChartBaseOpts(stacked, horizontal) {
  const ar = _incomeIsAr();
  const grid = { color: "rgb(30 58 110 / 45%)" };
  const tick = { color: "#7b93c9", font: { family: "Inter" } };
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? "y" : "x",
    plugins: {
      legend: {
        labels: { color: "#e8f0fe", usePointStyle: true, boxWidth: 8, font: { family: "Inter" } },
        rtl: ar,
      },
      tooltip: {
        rtl: ar,
        callbacks: {
          label: (c) => `${c.dataset.label}: ${_incomeFmt(c.parsed[horizontal ? "x" : "y"] ?? c.parsed)}`,
        },
      },
    },
    scales: {
      x: {
        stacked,
        grid,
        ticks: horizontal ? { ...tick, callback: (v) => _incomeFmt0(v) } : { ...tick },
        reverse: ar && !horizontal,
      },
      y: {
        stacked,
        grid,
        ticks: horizontal ? { ...tick } : { ...tick, callback: (v) => _incomeFmt0(v) },
        position: ar && !horizontal ? "right" : "left",
      },
    },
  };
}

function _incomeActiveSources(D) {
  const S = window._incomeState;
  return (D.sources || []).filter((s) => {
    if (!S.sources.includes(s.id)) return false;
    const g = (D.groups || []).find((x) => x.source === s.id);
    return !!g && (g.count_a > 0 || g.count_b > 0);
  });
}

function _incomeGroup(D, src) {
  return (D.groups || []).find((x) => x.source === src) || { amount_a: 0, amount_b: 0, count_a: 0, count_b: 0 };
}

function _incomeDrawCharts(D) {
  const c1 = document.getElementById("incomeC1");
  const c2 = document.getElementById("incomeC2");
  if (!c1 || !c2 || typeof Chart === "undefined") return;
  const S = window._incomeState;
  const active = _incomeActiveSources(D);
  const months = S.months.length ? S.months : Array.from({ length: 12 }, (_, i) => i + 1);
  const byMonth = (src, m) => {
    const recs = (D.records || []).filter((r) => r.period === "A" && r.source === src);
    return recs.filter((r) => parseInt(r.date.slice(5, 7), 10) === m).reduce((a, r) => a + r.amount, 0);
  };

  if (S.mode === "off") {
    window._incomeCharts.push(
      new Chart(c1, {
        type: "bar",
        data: {
          labels: months.map((m) => _incomeMonthName(m, "short")),
          datasets: active.map((s) => ({
            label: _incomeSourceLabel(s.id),
            data: months.map((m) => byMonth(s.id, m)),
            backgroundColor: s.color,
            borderRadius: 4,
            maxBarThickness: 38,
          })),
        },
        options: _incomeChartBaseOpts(true, false),
      })
    );
    const totals = active.map((s) => _incomeGroup(D, s.id).amount_a);
    const sumT = totals.reduce((a, b) => a + b, 0);
    window._incomeCharts.push(
      new Chart(c2, {
        type: "doughnut",
        data: {
          labels: active.map((s) => _incomeSourceLabel(s.id)),
          datasets: [
            {
              data: totals,
              backgroundColor: active.map((s) => s.color),
              borderColor: "#0d1530",
              borderWidth: 3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "68%",
          plugins: {
            legend: { position: "bottom", rtl: _incomeIsAr(), labels: { color: "#e8f0fe", usePointStyle: true, boxWidth: 8 } },
            tooltip: {
              callbacks: {
                label: (c) => `${c.label}: ${_incomeFmt(c.parsed)} (${sumT ? ((c.parsed / sumT) * 100).toFixed(1) : "0.0"}%)`,
              },
            },
          },
        },
      })
    );
    return;
  }

  const P = D.periods;
  const labA = _incomePeriodLabel(P[0]);
  const labB = _incomePeriodLabel(P[1]);

  if (S.mode === "yoy") {
    const line = (col, lab, period) => ({
      label: lab,
      data: months.map((m) => byMonthSrc(D, period, m)),
      borderColor: col,
      backgroundColor: col + "33",
      fill: true,
      tension: 0.35,
      pointRadius: 3,
    });
    window._incomeCharts.push(
      new Chart(c1, {
        type: "line",
        data: { labels: months.map((m) => _incomeMonthName(m, "short")), datasets: [line("#5aa2ff", labA, "A"), line("#ffb86b", labB, "B")] },
        options: _incomeChartBaseOpts(false, false),
      })
    );
  } else {
    window._incomeCharts.push(
      new Chart(c1, {
        type: "bar",
        data: {
          labels: active.map((s) => _incomeSourceLabel(s.id)),
          datasets: [
            { label: labA, data: active.map((s) => _incomeGroup(D, s.id).amount_a), backgroundColor: "#5aa2ff", borderRadius: 5, maxBarThickness: 40 },
            { label: labB, data: active.map((s) => _incomeGroup(D, s.id).amount_b), backgroundColor: "#ffb86b", borderRadius: 5, maxBarThickness: 40 },
          ],
        },
        options: _incomeChartBaseOpts(false, false),
      })
    );
  }

  if (S.mode === "yoy") {
    window._incomeCharts.push(
      new Chart(c2, {
        type: "bar",
        data: {
          labels: active.map((s) => _incomeSourceLabel(s.id)),
          datasets: [
            { label: labA, data: active.map((s) => _incomeGroup(D, s.id).amount_a), backgroundColor: "#5aa2ff", borderRadius: 4 },
            { label: labB, data: active.map((s) => _incomeGroup(D, s.id).amount_b), backgroundColor: "#ffb86b", borderRadius: 4 },
          ],
        },
        options: _incomeChartBaseOpts(false, true),
      })
    );
  } else {
    const d = active.map((s) => _incomeGroup(D, s.id).amount_b - _incomeGroup(D, s.id).amount_a);
    window._incomeCharts.push(
      new Chart(c2, {
        type: "bar",
        data: {
          labels: active.map((s) => _incomeSourceLabel(s.id)),
          datasets: [
            { label: t("income_change", "Change"), data: d, backgroundColor: d.map((v) => (v >= 0 ? "#00d68f" : "#ff4d6d")), borderRadius: 4 },
          ],
        },
        options: { ..._incomeChartBaseOpts(false, true), plugins: { ..._incomeChartBaseOpts(false, true).plugins, legend: { display: false } } },
      })
    );
  }
}

function byMonthSrc(D, period, m) {
  const recs = (D.records || []).filter((r) => r.period === period);
  return recs.filter((r) => parseInt(r.date.slice(5, 7), 10) === m).reduce((a, r) => a + r.amount, 0);
}
