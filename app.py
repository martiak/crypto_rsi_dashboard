from flask import Flask, render_template_string
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
        print("🔄 Fetching new data from Binance...")
        cached_signals = analyze_rsi_trends()
        last_fetched_time = now
    else:
        print("✅ Using cached signals.")

    signals = cached_signals

    html_template = """
    <html>
    <head>
        <title>Crypto RSI Dashboard</title>
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 6px;
                text-align: center;
            }
            th {
                background-color: #f2f2f2;
                cursor: pointer;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            .sort-icon {
                font-size: 16px;
                margin-left: 6px;
                display: inline-block;
                min-width: 1em;
                color: #333;
                font-weight: bold;
            }
            .progress-bar-container {
                width: 100%;
                background-color: #e0e0e0;
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
        </style>
    </head>
    <body>
        <h2>📊 Crypto RSI Dashboard</h2>
        <table id="rsiTable">
            <thead>
                <tr>
                    {% for col in signals[0].keys() if col != "icon_url" %}
                        <th onclick="sortTable({{ loop.index0 }}, {{ 'true' if 'RSI' in col else 'false' }}, this)">
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
                                <img src="{{ signal.icon_url }}" alt="{{ signal.Coin }}" width="32" height="32" style="vertical-align: middle; margin-right: 8px;">
                                {{ signal.Coin }}
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

        <script>
        let currentSortColumn = null;
        let currentSortDir = "asc";

        function sortTable(n, isNumeric = false, headerEl = null) {
            const table = document.getElementById("rsiTable");
            if (!table) return;

            // Reset icons
            document.querySelectorAll("th .sort-icon").forEach(icon => icon.innerText = "");

            // Toggle sort direction
            if (currentSortColumn === n) {
                currentSortDir = currentSortDir === "asc" ? "desc" : "asc";
            } else {
                currentSortDir = "asc";
                currentSortColumn = n;
            }

            const icon = headerEl?.querySelector(".sort-icon");
            if (icon) icon.innerText = currentSortDir === "asc" ? "▲" : "▼";

            let rows = Array.from(table.rows).slice(1); // skip header
            rows.sort((a, b) => {
                const x = a.cells[n]?.innerText || "";
                const y = b.cells[n]?.innerText || "";

                if (isNumeric) {
                    const xVal = parseFloat(x) || 0; // Default to 0 if parsing fails
                    const yVal = parseFloat(y) || 0;
                    return currentSortDir === "asc" ? xVal - yVal : yVal - xVal;
                }

                const xVal = x.toLowerCase();
                const yVal = y.toLowerCase();
                if (xVal < yVal) return currentSortDir === "asc" ? -1 : 1;
                if (xVal > yVal) return currentSortDir === "asc" ? 1 : -1;
                return 0;
            });

            const tbody = table.querySelector("tbody");
            rows.forEach(row => tbody.appendChild(row));
        }
        </script>
    </body>
    </html>
    """

    return render_template_string(html_template, signals=signals)

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(debug=True)