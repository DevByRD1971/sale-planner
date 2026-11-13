(function () {
  var d = JSON.parse(document.getElementById('sdata').textContent);
  var names = ['Conservative', 'Realistic', 'Optimistic'];
  var colours = ['#7b9cc4', '#2f6db3', '#2a9d8f'];
  var dashes = [[6, 4], [], [2, 3]];

  function money(v) {
    var n = Math.round(v);
    return (n < 0 ? '-$' : '$') + Math.abs(n).toLocaleString('en-AU');
  }

  var labels = d.rows.map(function (r) { return 'Age ' + r.age; });
  var sets = d.highlight.map(function (rate, i) {
    return {
      label: names[i] + ' (' + rate + '%)',
      data: d.rows.map(function (r) { return Math.round(r.balances[String(rate)]); }),
      borderColor: colours[i],
      backgroundColor: colours[i],
      borderDash: dashes[i],
      borderWidth: 2.5,
      pointRadius: d.rows.length > 14 ? 0 : 3,
      pointHoverRadius: 5,
      tension: 0.25
    };
  });

  new Chart(document.getElementById('superChart'), {
    type: 'line',
    data: { labels: labels, datasets: sets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
        tooltip: { callbacks: { label: function (c) { return c.dataset.label + ': ' + money(c.parsed.y); } } }
      },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: '#e3ecf6' }, ticks: { callback: function (v) { return money(v); } } }
      }
    }
  });
})();
