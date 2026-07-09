'use strict';

function _drawBarChart(canvasId, labels, datasets) {
    setTimeout(() => {
        const ctx = document.getElementById(canvasId);
        if (!ctx || !window.Chart) return;
        if (ctx._chart) ctx._chart.destroy();
        ctx._chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: datasets.map(ds => ({
                    label: ds.label,
                    data: ds.data,
                    backgroundColor: ds.color + 'cc',
                    borderColor: ds.color,
                    borderRadius: 4,
                    borderWidth: 1,
                })),
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
                scales: {
                    x: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                    y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                },
            },
        });
    }, 50);
}

function _drawPieChart(canvasId, labels, data) {
    setTimeout(() => {
        const ctx = document.getElementById(canvasId);
        if (!ctx || !window.Chart) return;
        if (ctx._chart) ctx._chart.destroy();
        const colors = ['#1a6ef5','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899'];
        ctx._chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data, backgroundColor: colors.slice(0, data.length), borderWidth: 0 }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 12, padding: 12 } } },
            },
        });
    }, 50);
}

// ── Shared helpers ─────────────────────────────────────────────