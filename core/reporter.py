import os
import json
import time
from typing import Optional
from jinja2 import Template
from schema.execution_result import TestExecutionReport, StepStatus
from config.settings import settings


class Reporter:
    """
    Generates rich HTML reports and self-healing audit dashboards.
    """

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous Agentic Playwright Execution Report - {{ report.title }}</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-pass: #22c55e;
            --accent-fail: #ef4444;
            --accent-heal: #eab308;
            --accent-info: #3b82f6;
            --border-color: #334155;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }

        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
        }

        .badge {
            padding: 6px 16px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
        }

        .badge-PASSED { background-color: rgba(34, 197, 94, 0.2); color: var(--accent-pass); border: 1px solid var(--accent-pass); }
        .badge-FAILED { background-color: rgba(239, 68, 68, 0.2); color: var(--accent-fail); border: 1px solid var(--accent-fail); }
        .badge-HEALED { background-color: rgba(234, 179, 8, 0.2); color: var(--accent-heal); border: 1px solid var(--accent-heal); }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }

        .metric-card {
            background-color: var(--card-bg);
            padding: 16px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            text-align: center;
        }

        .metric-card .num {
            font-size: 28px;
            font-weight: 700;
            margin-top: 6px;
        }

        .metric-card.pass .num { color: var(--accent-pass); }
        .metric-card.fail .num { color: var(--accent-fail); }
        .metric-card.heal .num { color: var(--accent-heal); }

        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin: 32px 0 16px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background-color: var(--card-bg);
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }

        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
            font-size: 14px;
        }

        th {
            background-color: #090d16;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
        }

        tr:last-child td { border-bottom: none; }

        code {
            background-color: #090d16;
            padding: 3px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
            color: #60a5fa;
        }

        .heal-card {
            background-color: rgba(234, 179, 8, 0.05);
            border: 1px solid rgba(234, 179, 8, 0.3);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 16px;
        }

        .diff-box {
            display: flex;
            gap: 16px;
            margin-top: 12px;
        }

        .diff-col {
            flex: 1;
            background: #090d16;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }

        .diff-col .title {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 6px;
        }

        .screenshot-thumb {
            max-width: 200px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🤖 Autonomous Agentic Test Execution</h1>
                <p style="color: var(--text-muted); margin: 4px 0 0 0;">Target URL: <code>{{ report.target_url }}</code> | Duration: {{ report.duration_seconds }}s</p>
            </div>
            <span class="badge badge-{{ report.overall_status.value if report.overall_status.value is defined else report.overall_status }}">{{ report.overall_status.value if report.overall_status.value is defined else report.overall_status }}</span>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div style="color: var(--text-muted); font-size: 12px;">TOTAL STEPS</div>
                <div class="num">{{ report.total_steps }}</div>
            </div>
            <div class="metric-card pass">
                <div style="color: var(--text-muted); font-size: 12px;">PASSED</div>
                <div class="num">{{ report.passed_steps }}</div>
            </div>
            <div class="metric-card fail">
                <div style="color: var(--text-muted); font-size: 12px;">FAILED</div>
                <div class="num">{{ report.failed_steps }}</div>
            </div>
            <div class="metric-card heal">
                <div style="color: var(--text-muted); font-size: 12px;">HEALED</div>
                <div class="num">{{ report.healed_steps }}</div>
            </div>
        </div>

        {% if report.healing_audits %}
        <div class="section-title">🩺 Self-Healing Audit Log ({{ report.healing_audits|length }} Repaired)</div>
        {% for heal in report.healing_audits %}
        <div class="heal-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong>Step ID: {{ heal.step_id }} - {{ heal.strategy_used }}</strong>
                <span style="color: var(--accent-pass); font-size: 13px;">✓ Verified (Confidence: {{ (heal.confidence_score * 100)|round }}%)</span>
            </div>
            <p style="color: var(--accent-fail); font-size: 13px; margin: 8px 0;">Error: {{ heal.error_message }}</p>
            <div class="diff-box">
                <div class="diff-col">
                    <div class="title">❌ Original Failed Locator</div>
                    <code style="color: #f87171;">{{ heal.failed_locator }}</code>
                </div>
                <div class="diff-col">
                    <div class="title">✅ Healed Replacement Locator</div>
                    <code style="color: #4ade80;">{{ heal.healed_locator }}</code>
                </div>
            </div>
        </div>
        {% endfor %}
        {% endif %}

        <div class="section-title">📋 Execution Step Trace Graph</div>
        <table>
            <thead>
                <tr>
                    <th>Step</th>
                    <th>Intent</th>
                    <th>Description</th>
                    <th>Locator Used</th>
                    <th>Duration</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for step in report.step_results %}
                <tr>
                    <td><code>{{ step.step_id }}</code></td>
                    <td><span style="color: var(--text-muted);">{{ step.intent }}</span></td>
                    <td>{{ step.description }}</td>
                    <td><code>{{ step.used_locator or 'N/A' }}</code></td>
                    <td>{{ step.duration_ms }} ms</td>
                    <td><span class="badge badge-{{ step.status.value if step.status.value is defined else step.status }}">{{ step.status.value if step.status.value is defined else step.status }}</span></td>
                </tr>
                {% if step.error_message %}
                <tr>
                    <td colspan="6" style="background-color: rgba(239, 68, 68, 0.05); color: var(--accent-fail);">
                        <strong>Error:</strong> {{ step.error_message }}
                        {% if step.screenshot_path %}
                        <div style="margin-top: 8px;">
                            <img src="{{ step.screenshot_path }}" class="screenshot-thumb" alt="Screenshot" />
                        </div>
                        {% endif %}
                    </td>
                </tr>
                {% endif %}
                {% endfor %}
            </tbody>
        </table>

        {% if report.trace_path or report.video_path %}
        <div class="section-title">📦 Downloadable Artifacts</div>
        <div style="background-color: var(--card-bg); padding: 16px; border-radius: 10px; border: 1px solid var(--border-color);">
            {% if report.trace_path %}
            <p><strong>Playwright Trace:</strong> <code>{{ report.trace_path }}</code> (View with <code>npx playwright show-trace</code>)</p>
            {% endif %}
            {% if report.video_path %}
            <p><strong>Session Video:</strong> <code>{{ report.video_path }}</code></p>
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
    """

    @staticmethod
    def generate_html_report(report: TestExecutionReport, output_filename: str = "execution_report.html") -> str:
        """
        Renders and saves the HTML execution report.
        """
        template = Template(Reporter.HTML_TEMPLATE)
        rendered_html = template.render(report=report)

        report_path = settings.get_output_path("reports", output_filename)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        # Also write JSON summary report
        json_path = settings.get_output_path("reports", output_filename.replace(".html", ".json"))
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        return report_path
