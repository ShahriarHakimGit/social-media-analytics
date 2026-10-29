const number = value => new Intl.NumberFormat().format(Number(value));
const money = value => new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(Number(value));

function cell(value) {
  const td = document.createElement('td');
  td.textContent = value;
  return td;
}

function populateTable(id, rows, columns) {
  const body = document.getElementById(id);
  body.replaceChildren();
  rows.forEach(row => {
    const tr = document.createElement('tr');
    columns.forEach(column => tr.append(cell(column(row))));
    body.append(tr);
  });
}

async function loadDashboard() {
  const message = document.getElementById('message');
  message.textContent = 'Refreshing analytics data…';
  try {
    const response = await fetch('/api/dashboard');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not read the database.');

    const summary = data.summary;
    document.getElementById('leads').textContent = number(summary.leads);
    document.getElementById('converted').textContent = number(summary.converted);
    document.getElementById('revenue').textContent = money(summary.revenue);
    document.getElementById('impressions').textContent = number(summary.impressions);
    document.getElementById('clicks').textContent = number(summary.clicks);
    document.getElementById('spend').textContent = money(summary.spend);

    const max = Math.max(...data.statuses.map(row => Number(row.count)), 1);
    const funnel = document.getElementById('funnel');
    funnel.replaceChildren();
    data.statuses.forEach(row => {
      const line = document.createElement('div');
      line.className = 'bar-line';
      line.innerHTML = `<span>${row.status}</span><div class="bar"><i style="width:${Number(row.count) / max * 100}%"></i></div><b>${row.count}</b>`;
      funnel.append(line);
    });

    populateTable('campaigns', data.campaigns, [
      row => row.campaign,
      row => number(row.impressions),
      row => number(row.clicks),
      row => money(row.spend),
    ]);
    populateTable('posts', data.posts, [
      row => row.post, row => row.platform, row => number(row.impressions),
      row => number(row.clicks), row => `${row.engagement}%`,
    ]);
    message.textContent = 'Data refreshed from MariaDB.';
  } catch (error) {
    message.textContent = `Could not load dashboard data: ${error.message}`;
  }
}

document.getElementById('refresh').addEventListener('click', loadDashboard);
loadDashboard();
