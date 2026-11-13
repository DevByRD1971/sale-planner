(function () {
  var d = JSON.parse(document.getElementById('rdata').textContent);
  var colours = ['#7b9cc4', '#2f6db3', '#2a9d8f', '#5fb3b3', '#9db8d9', '#a8cfc9', '#c4d3e6'];

  function money(v) {
    var n = Math.round(v);
    return (n < 0 ? '-$' : '$') + Math.abs(n).toLocaleString('en-AU');
  }

  var sets = [{
    label: 'Rent income',
    data: [Math.round(d.gross), 0],
    backgroundColor: '#1d4f85',
    borderWidth: 0
  }];
  d.groups.forEach(function (g, i) {
    sets.push({
      label: g[0],
      data: [0, Math.round(g[1])],
      backgroundColor: colours[i % colours.length],
      borderWidth: 0
    });
  });

  new Chart(document.getElementById('rentChart'), {
    type: 'bar',
    data: { labels: ['Rent income', 'Costs'], datasets: sets },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            usePointStyle: true, boxWidth: 8,
            filter: function (item, data) {
              var ds = data.datasets[item.datasetIndex];
              return ds.data.some(function (v) { return v > 0; });
            }
          }
        },
        tooltip: {
          filter: function (c) { return c.parsed.x > 0; },
          callbacks: { label: function (c) { return c.dataset.label + ': ' + money(c.parsed.x); } }
        }
      },
      scales: {
        x: { stacked: true, grid: { color: '#e3ecf6' }, ticks: { callback: function (v) { return money(v); } } },
        y: { stacked: true, grid: { display: false } }
      }
    }
  });
})();
