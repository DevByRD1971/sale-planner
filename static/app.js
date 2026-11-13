(function () {
  var data = JSON.parse(document.getElementById('data').textContent);
  var names = data.scenarios;
  var rows = data.table;

  var colours = {
    Conservative: '#7b9cc4',
    Realistic: '#2f6db3',
    Optimistic: '#2a9d8f'
  };
  var dashes = { Conservative: [6, 4], Realistic: [], Optimistic: [2, 3] };

  var hints = {
    price: 'Estimated price if you sold on 30 June of each year.',
    cgt: 'Capital gains tax (including Medicare levy) if you sold on 30 June of each year.',
    net: 'Profit after selling costs and capital gains tax, if sold on 30 June of each year.'
  };

  var metric = 'price';
  var chart = null;

  function money(v) {
    var n = Math.round(v);
    var s = Math.abs(n).toLocaleString('en-AU');
    return (n < 0 ? '-$' : '$') + s;
  }

  function renderTable() {
    var body = document.querySelector('#yearTable tbody');
    var html = '';
    rows.forEach(function (r) {
      html += '<tr><td>' + r.year + '</td>';
      names.forEach(function (n) {
        html += '<td class="num">' + money(r[n][metric]) + '</td>';
      });
      html += '</tr>';
    });
    body.innerHTML = html;
  }

  function renderChart() {
    var ctx = document.getElementById('chart');
    var sets = names.map(function (n) {
      return {
        label: n,
        data: rows.map(function (r) { return Math.round(r[n][metric]); }),
        borderColor: colours[n],
        backgroundColor: colours[n],
        borderDash: dashes[n],
        borderWidth: 2.5,
        pointRadius: rows.length > 12 ? 0 : 3,
        pointHoverRadius: 5,
        tension: 0.25
      };
    });
    if (chart) {
      chart.data.datasets = sets;
      chart.update();
      return;
    }
    chart = new Chart(ctx, {
      type: 'line',
      data: { labels: rows.map(function (r) { return r.year; }), datasets: sets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
          tooltip: {
            callbacks: {
              label: function (c) { return c.dataset.label + ': ' + money(c.parsed.y); }
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            grid: { color: '#e3ecf6' },
            ticks: { callback: function (v) { return money(v); } }
          }
        }
      }
    });
  }

  function setMetric(m) {
    metric = m;
    document.querySelectorAll('.tab').forEach(function (t) {
      t.classList.toggle('on', t.dataset.metric === m);
    });
    document.getElementById('metricHint').textContent = hints[m];
    renderTable();
    renderChart();
  }

  document.querySelectorAll('.tab').forEach(function (t) {
    t.addEventListener('click', function () { setMetric(t.dataset.metric); });
  });
  setMetric('price');
})();
