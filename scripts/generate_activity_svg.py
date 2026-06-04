#!/usr/bin/env python3
"""Generate an anonymized professional GitHub activity SVG for a profile README.

What it does:
- Reads aggregated GitHub contribution data from the GitHub GraphQL API.
- Generates assets/professional-activity.svg.
- Does NOT expose repository names, branch names, commit messages, issue titles,
  PR titles, or proprietary details.

Environment variables:
- GH_TOKEN: preferred token for reading private/organization contribution data.
- GITHUB_TOKEN: fallback token used by GitHub Actions.
- GITHUB_USER: GitHub username. Defaults to GITHUB_ACTOR, then carlosmartins19.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

OUTPUT_PATH = Path("assets/professional-activity.svg")
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def graphql_request(query: str, variables: dict) -> dict:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Missing GH_TOKEN or GITHUB_TOKEN")

    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {exc.code}: {body}") from exc

    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], indent=2))

    return data["data"]


def fetch_activity(login: str) -> dict:
    today = dt.date.today()
    start = today - dt.timedelta(days=365)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "login": login,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{today.isoformat()}T23:59:59Z",
    }

    data = graphql_request(query, variables)
    user = data.get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {login}")

    return user["contributionsCollection"]


def level_for_count(count: int, max_count: int) -> int:
    if count <= 0 or max_count <= 0:
        return 0

    ratio = count / max_count

    if ratio < 0.25:
        return 1
    if ratio < 0.50:
        return 2
    if ratio < 0.75:
        return 3

    return 4


def color_for_level(level: int) -> str:
    return ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"][level]


def metric_card(x: int, y: int, label: str, value: int) -> str:
    safe_label = html.escape(label)
    safe_value = html.escape(f"{value:,}")

    return f'''
    <g>
      <rect x="{x}" y="{y}" width="164" height="74" rx="12" fill="#ffffff" stroke="#d8dee4"/>
      <text x="{x + 18}" y="{y + 30}" font-size="13" fill="#57606a">{safe_label}</text>
      <text x="{x + 18}" y="{y + 58}" font-size="28" font-weight="700" fill="#24292f">{safe_value}</text>
    </g>'''


def build_svg(activity: dict, login: str) -> str:
    calendar = activity["contributionCalendar"]
    weeks = calendar["weeks"][-53:]

    counts = [
        day["contributionCount"]
        for week in weeks
        for day in week["contributionDays"]
    ]
    max_count = max(counts) if counts else 0

    svg_width = 860
    svg_height = 390

    card_y = 118
    card_height = 74
    card_bottom = card_y + card_height

    square = 11
    gap = 3

    heatmap_x = 32
    calendar_title_y = card_bottom + 32
    heatmap_y = calendar_title_y + 14

    heatmap_rows = 7
    heatmap_height = heatmap_rows * square + (heatmap_rows - 1) * gap

    footer_y = heatmap_y + heatmap_height + 28
    legend_square_y = footer_y - 9
    updated_at_y = footer_y + 17

    heatmap_parts: list[str] = []

    for week_index, week in enumerate(weeks):
        days = week["contributionDays"]

        for day_index, day in enumerate(days):
            count = int(day["contributionCount"])
            level = level_for_count(count, max_count)

            x = heatmap_x + week_index * (square + gap)
            y = heatmap_y + day_index * (square + gap)

            date_label = html.escape(day["date"])

            heatmap_parts.append(
                f'<rect x="{x}" y="{y}" width="{square}" height="{square}" rx="2" '
                f'fill="{color_for_level(level)}">'
                f'<title>{date_label}: {count} contributions</title>'
                f'</rect>'
            )

    total = int(calendar["totalContributions"])
    commits = int(activity["totalCommitContributions"])
    prs = int(activity["totalPullRequestContributions"])
    reviews = int(activity["totalPullRequestReviewContributions"])
    issues = int(activity["totalIssueContributions"])

    updated_at = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    safe_login = html.escape(login)

    return f'''<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Professional GitHub activity for {safe_login}</title>
  <desc id="desc">Aggregated GitHub contribution metrics for the last 12 months. Repository names and private details are not disclosed.</desc>

  <rect width="{svg_width}" height="{svg_height}" rx="18" fill="#f6f8fa"/>
  <rect x="1" y="1" width="{svg_width - 2}" height="{svg_height - 2}" rx="17" stroke="#d8dee4"/>

  <text x="32" y="44" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="22" font-weight="700" fill="#24292f">Professional GitHub Activity</text>
  <text x="32" y="70" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="13" fill="#57606a">Aggregated contribution data from the last 12 months</text>
  <text x="32" y="92" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="12" fill="#6e7781">Repository names, branches, commit messages and proprietary details are not disclosed.</text>

  <g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
    {metric_card(32, card_y, "Total contributions", total)}
    {metric_card(212, card_y, "Commits", commits)}
    {metric_card(392, card_y, "Pull requests", prs)}
    {metric_card(572, card_y, "Reviews", reviews)}
  </g>

  <g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
    <text x="32" y="{calendar_title_y}" font-size="13" font-weight="600" fill="#24292f">Contribution calendar</text>
    {''.join(heatmap_parts)}

    <text x="32" y="{footer_y}" font-size="12" fill="#6e7781">Issues: {issues:,}</text>

    <text x="640" y="{footer_y}" font-size="12" fill="#6e7781">Less</text>
    <rect x="674" y="{legend_square_y}" width="11" height="11" rx="2" fill="#ebedf0"/>
    <rect x="691" y="{legend_square_y}" width="11" height="11" rx="2" fill="#9be9a8"/>
    <rect x="708" y="{legend_square_y}" width="11" height="11" rx="2" fill="#40c463"/>
    <rect x="725" y="{legend_square_y}" width="11" height="11" rx="2" fill="#30a14e"/>
    <rect x="742" y="{legend_square_y}" width="11" height="11" rx="2" fill="#216e39"/>
    <text x="762" y="{footer_y}" font-size="12" fill="#6e7781">More</text>

    <text x="32" y="{updated_at_y}" font-size="11" fill="#8c959f">Last updated: {updated_at}</text>
  </g>
</svg>
'''


def fallback_svg(message: str) -> str:
    safe_message = html.escape(message[:160])

    return f'''<svg width="860" height="220" viewBox="0 0 860 220" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Professional GitHub activity</title>
  <desc id="desc">The activity chart will be generated by GitHub Actions.</desc>
  <rect width="860" height="220" rx="18" fill="#f6f8fa"/>
  <rect x="1" y="1" width="858" height="218" rx="17" stroke="#d8dee4"/>
  <text x="32" y="52" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="22" font-weight="700" fill="#24292f">Professional GitHub Activity</text>
  <text x="32" y="84" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="14" fill="#57606a">This chart is generated automatically from aggregated GitHub contribution data.</text>
  <text x="32" y="112" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="13" fill="#6e7781">Repository names, branches, commit messages and proprietary details are not disclosed.</text>
  <text x="32" y="154" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="12" fill="#8c959f">Status: {safe_message}</text>
</svg>
'''


def main() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    login = (
        os.environ.get("GITHUB_USER")
        or os.environ.get("GITHUB_ACTOR")
        or "carlosmartins19"
    )

    try:
        activity = fetch_activity(login)
        svg = build_svg(activity, login)
    except Exception as exc:
        print(f"Failed to generate activity chart: {exc}", file=sys.stderr)
        svg = fallback_svg(str(exc))

    OUTPUT_PATH.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
