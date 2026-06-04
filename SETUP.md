# Setup - Professional GitHub Activity Chart

Copy these files into the root of your GitHub profile repository:

```txt
carlosmartins19/carlosmartins19
```

Files to add:

```txt
scripts/generate_activity_svg.py
.github/workflows/update-professional-activity.yml
assets/professional-activity.svg
```

Then replace the current `## 💼 Professional Activity` section in your `README.md` with the content from `README_SECTION.md`.

## Optional but recommended: add GH_TOKEN

The workflow can run with the default `GITHUB_TOKEN`, but that token may not see all private or organization-owned contribution data.

For better private/professional contribution coverage, create a repository secret:

```txt
Repository → Settings → Secrets and variables → Actions → New repository secret
```

Name:

```txt
GH_TOKEN
```

Value:

```txt
A GitHub Personal Access Token that can read your contribution data
```

Do not put the token in the README, workflow file, or source code.

## Run it

After committing the files:

```txt
Repository → Actions → Update professional activity chart → Run workflow
```

The workflow will generate `assets/professional-activity.svg` and commit the updated image automatically. It also runs every day at 07:17 UTC.

## Privacy

The generated SVG shows only aggregated numbers and a contribution heatmap. It does not expose repository names, branch names, commit messages, PR titles, issue titles, or proprietary details.
