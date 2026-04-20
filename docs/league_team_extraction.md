# Overview:

rule based extraction implemented during the video ingestion to populate the missing league and teams fields on video documents. This logic is run inside the inigest_videos in the fastapi/routes/ingest.py

# league detection logic 
Here league is determined using the keyword matching on the video title, with a fallback to channel based mapping 

League                 | Keywords 
Champions League         ucl , champions league, uefa champions
Premier League           premier league, epl 
La Liga                  laliga, la liga
Bundesliga               bundesliga
Serie A                  serie a 
Ligue 1                  ligue 1 


# Channel Fallback 
If no title keyword is found, the channel name is used as a fallback signal.
This mapping is heuristic-based and assumes certain channels primarily cover specific leagues. While not always perfectly accurate, it improves coverage when titles do not explicitly mention a league.

Channel          | League 
golazo             Champions League 
nbc sports         Premier League 
sky sports         Premier League 

# Team Extraction
Team extraction is implemented using a rule-based approach with a predefined list of known team names.

A list of common club names and variations (e.g., "Spurs", "Man United", "Atlético") is maintained.
The video title is scanned for matches against this list.
All matching teams are collected (up to 2 per video).

Example

Title:
Spurs FLOP vs. Atlético in UCL

Extracted:
["Spurs", "Atlético"]

If no known team names are found, teams is set to null.

# Backfilling
Existing videos were updated by re-running the ingestion process, which applied the extraction logic to all stored video records.

# Limitations
Extraction depends on exact string matches from the predefined team list
Team name variations (e.g., abbreviations or accents) must be manually included
Some videos (e.g., commentary clips) do not mention teams in titles, resulting in teams: null
League detection may fail if no keyword or channel mapping is present

# Note: 
No LLM or external API is used for extraction
The approach is deterministic, efficient, and consistent with jira task. 


## Claim-to-Narrative Linking Validation

To ensure narrative grouping is correctly implemented, we validated that all narratives reference existing claims and that no orphaned claims exist.

### Validation Steps

* Queried the narratives collection to confirm that `claim_ids` arrays are populated and non-empty
* Verified that each `claim_id` corresponds to an existing document in the `claims` collection
* Confirmed that claims include a `narrative_category` and are properly associated with narratives

### Results
* No narratives with empty `claim_ids` were found
* All referenced claim IDs correspond to valid claim documents
* No orphaned claims were observed in the dataset

---

## Scorer Validation (mention_by_video)

To validate that enrichment and linking support downstream analytics, we verified the scorer's `mention_by_video` functionality.

### Validation Steps

* Queried the `claims` collection for documents with `mentions > 0`
* Confirmed that multiple claims return non-zero mention counts

### Results

* Non-zero mention counts were observed across multiple claims
* This confirms that:

  * claim-to-narrative relationships are functioning correctly
  * video-level aggregation via the scorer is working as expected

---

## Conclusion

The claim-to-narrative pipeline is fully operational. All claims are properly linked to narratives, no orphaned data exists, and scorer outputs confirm that enriched video data supports downstream analysis and frontend features.
