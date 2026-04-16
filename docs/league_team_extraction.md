# League & Team Extraction Logic

## Overview
Rule based extraction implemented during video ingestion to populate `league` and `teams` fields on video documents. Runs inside `ingest_videos` in `fastapi/routes/ingest.py`.

## League Detection
Uses keyword matching against the video title, with a channel-name fallback.

### Title Keywords
| League | Keywords |
|---|---|
| Champions League | `ucl`, `champions league`, `uefa champions` |
| Premier League | `premier league`, `epl` |
| La Liga | `laliga`, `la liga` |
| Bundesliga | `bundesliga` |
| Serie A | `serie a` |
| Ligue 1 | `ligue 1` |

### Channel Fallback
If no title keyword matches, the channel name is checked:
| Channel | League |
|---|---|
| golazo | Champions League |
| nbc sports | Premier League |
| sky sports | Premier League |

## Team Extraction
Two strategies are attempted in order:

**Strategy 1 — vs-pattern (preferred)**
Regex looks for `Team A vs/v Team B` in the title and extracts both sides.

**Strategy 2 — Known teams whitelist (fallback)**
Scans the title for any known team name from a hardcoded list covering Premier League, La Liga, Bundesliga, Serie A, Ligue 1, and UCL clubs.

If neither strategy finds anything, `teams` is set to `null`.

## Limitations
- vs-pattern can be too greedy on titles like `"Spurs FLOP vs. Atlético in UCL"`
- Known teams list must be manually maintained as new clubs appear
- ~55% of videos currently have `league: null` due to titles not containing league keywords
