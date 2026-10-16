# Global Major Industrial Accident Report

A Streamlit dashboard (Thai UI) that tracks major industrial accidents around the world. It shows statistics, a world map and event cards, and can search the web for new incidents using Gemini with Google Search.

## Features

- **Update latest data**: searches the web (Gemini + Google Search) for accidents in the last N days (1 to 60), skips events already stored, checks each reference link, and adds the new ones to `data/accidents.json`.
- **Link checker**: re-checks every reference link. Dead links are replaced with a new working link when one can be found, otherwise reported.
- **Month filter**: select a month or "ทั้งหมด" (all). The KPI cards, map and event cards follow this selection.
- **KPI cards**: number of events, fatalities and injuries for the selected period.
- **World map**: one dot per event, colored by severity (red = fatalities, orange = injuries only, blue = no casualties). Hover for location, date and impact.
- **Monthly summary**: table and bar chart of events, fatalities and injuries for each month of the selected year.
- **Event cards**: 6 per page, with description, impact and a link to the source.
- **AI summary**: generates a written summary of the selected period with Gemini.
- Dates are shown in the Thai Buddhist calendar (year + 543).

## Project structure

```
app.py                         Whole app (UI, data update, GitHub saving)
data/accidents.json            Event data
logo.png                       Logo shown in the header and as page icon
requirements.txt               Python dependencies
.streamlit/config.toml         Streamlit theme/config
.streamlit/secrets.toml.example  Template for secrets
```

Each record in `data/accidents.json` has: `id`, `date`, `location`, `lat`, `lng`, `event`, `fatalities`, `injuries`, `reference`.

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit it
streamlit run app.py
```

## Configuration

Set these in `.streamlit/secrets.toml` (local) or in App settings > Secrets (Streamlit Cloud). They can also be environment variables. Never commit `secrets.toml`.

| Key | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | For update, link fix and AI summary | Gemini API key |
| `GEMINI_MODEL` | No | Force one model. Default: tries several Gemini flash models |
| `GITHUB_TOKEN` | For persistent updates | Token with Contents: read and write on the repo |
| `GITHUB_REPO` | For persistent updates | `owner/repo` |
| `GITHUB_BRANCH` | No | Defaults to `main` |
| `UPDATE_PASSWORD` | No | If set, the update buttons only work after entering it |

## How data updates are saved

- **With `GITHUB_TOKEN` and `GITHUB_REPO` set**: GitHub is the source of truth. The app reads the current file from GitHub, merges new records, and commits `data/accidents.json` back. Streamlit Cloud then redeploys with the new data.
- **Without them**: the file is written locally only. On Streamlit Cloud those changes are lost when the app restarts, and the app shows a warning.

## Deploy

Deploy the repo on Streamlit Cloud with `app.py` as the main file and add the secrets above.

## Notes

- The data is collected by an AI search, so entries and fatality/injury numbers should be verified against the linked source before being relied on.
- Data is cached for 5 minutes and cleared after each update.
