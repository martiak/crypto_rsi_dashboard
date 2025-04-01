from flask import Flask, render_template_string, request
from rsi_monitor import analyze_rsi_trends
import time

app = Flask(__name__)

# --- Simple cache for signals ---
cached_signals = []
last_fetched_time = 0
CACHE_TTL = 300  # 5 minutes

@app.route("/")
def home():
    global cached_signals, last_fetched_time
    now = time.time()

    if now - last_fetched_time > CACHE_TTL or not cached_signals:
        print("🔄 Fetching new data...")
        cached_signals = analyze_rsi_trends()
        last_fetched_time = now
    else:
        print("✅ Using cached signals.")

    signals = cached_signals

    # Bootstrap Dark Mode HTML Template with Modal
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crypto RSI Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-dark-5@1.1.3/dist/css/bootstrap-dark.min.css" rel="stylesheet">
        <style>
            .progress-bar-container {
                width: 100%;
                background-color: #444;
                border-radius: 5px;
                overflow: hidden;
                margin-bottom: 5px;
            }
            .progress-bar {
                height: 20px;
                text-align: center;
                line-height: 20px;
                color: white;
                border-radius: 5px;
            }
            .rsi-value {
                text-align: center;
                font-size: 12px;
                margin-top: -5px;
            }
            th {
                cursor: pointer;
            }
            .sort-icon {
                font-size: 12px;
                margin-left: 5px;
            }
            .progress-bar-container {
                background-color: #353535;
            }
        </style>
        <script src="https://s3.tradingview.com/tv.js"></script>
    </head>
    <body class="bg-dark text-light">
        <div class="container mt-5">
            <h1 class="text-center mb-4">📊 Crypto Dashboard</h1>
            <table class="table table-striped table-bordered table-dark" id="rsiTable">
                <thead class="table-dark">
                    <tr>
                        {% for col in signals[0].keys() if col != "icon_url" %}
                            <th onclick="sortTable({{ loop.index0 }}, {{ 'true' if 'RSI' in col or 'Price' in col else 'false' }}, this)">
                                {{ col }} <span class="sort-icon"></span>
                            </th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for signal in signals %}
                    <tr>
                        {% for col, value in signal.items() if col != "icon_url" %}
                            {% if col == "Coin" %}
                                <td>
                                    <a href="#" onclick="openChart('{{ signal.Coin }}')" style="text-decoration: none; color: #5FD0F3;">
                                        <img src="{{ signal.icon_url }}" alt="{{ signal.Coin }}" width="32" height="32" style="vertical-align: middle; margin-right: 8px;">
                                        {{ signal.Coin }}
                                    </a>
                                </td>
                            {% elif "RSI" in col %}
                                {% set rsi = value %}
                                {% set rsi_color = (
                                    'darkblue' if rsi == 50 else
                                    '#5FD0F3' if 40 <= rsi <= 60 else
                                    '#b9edd1' if 30 < rsi < 40 else
                                    '#F7CC53' if 60 < rsi <= 70 else
                                    'red' if 70 < rsi <= 80 else
                                    '#B20000' if rsi > 80 else
                                    '#51D28C' if 25 < rsi <= 35 else
                                    '#389362' if rsi <= 25 else
                                    '#4291AA'
                                ) %}
                                <td>
                                    <div class="progress-bar-container">
                                        <div class="progress-bar" style="width: {{ rsi }}%; background-color: {{ rsi_color }};"></div>
                                    </div>
                                    <div class="rsi-value">{{ rsi }}</div>
                                </td>
                            {% else %}
                                <td>{{ value }}</td>
                            {% endif %}
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Bootstrap Modal -->
        <div class="modal fade" id="chartModal" tabindex="-1" aria-labelledby="chartModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl" style="max-width: 90%; height: 90%;">
                <div class="modal-content bg-dark text-light" style="height: 100%;">
                    <div class="modal-header">
                        <h5 class="modal-title" id="chartModalLabel">TradingView Chart</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" style="height: calc(100% - 56px);">
                        <div id="tradingview_chart" style="width: 100%; height: 100%;"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function sortTable(columnIndex, isNumeric, headerElement) {
                const table = document.getElementById("rsiTable");
                const rows = Array.from(table.rows).slice(1);
                const isAscending = headerElement.classList.contains("asc");

                rows.sort((rowA, rowB) => {
                    const cellA = rowA.cells[columnIndex].innerText.trim();
                    const cellB = rowB.cells[columnIndex].innerText.trim();

                    if (isNumeric) {
                        return isAscending
                            ? parseFloat(cellA) - parseFloat(cellB)
                            : parseFloat(cellB) - parseFloat(cellA);
                    } else {
                        return isAscending
                            ? cellA.localeCompare(cellB)
                            : cellB.localeCompare(cellA);
                    }
                });

                rows.forEach(row => table.tBodies[0].appendChild(row));
                document.querySelectorAll("th").forEach(th => th.classList.remove("asc", "desc"));
                headerElement.classList.toggle("asc", !isAscending);
                headerElement.classList.toggle("desc", isAscending);
            }

            function openChart(coin) {
                const modal = new bootstrap.Modal(document.getElementById('chartModal'));
                modal.show();

                new TradingView.widget({
                    "container_id": "tradingview_chart",
                    "symbol": coin + "USDT",
                    "width": "100%",
                    "height": "100%",
                    "interval": "1H",
                    "timezone": "Etc/UTC",
                    "theme": "dark",
                    "style": "1",
                    "locale": "en",
                    "toolbar_bg": "#f1f3f6",
                    "enable_publishing": false,
                    "hide_top_toolbar": false,
                    "hide_legend": false,
                    "save_image": false,
                    "hide_side_toolbar": false,
                    "hide_volume": true,
                    "studies": ["STD;Divergence%1Indicator","STD;Supertrend"]
                });
            }
        </script>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return render_template_string(html_template, signals=signals)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Use the PORT environment variable
    print(f"Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port)  # Bind to 0.0.0.0 to make it externally accessible