# Creator Risk Feature Documentation

## Overview

The Creator Risk feature analyzes video content for potentially harmful material and provides risk assessments at both the video and channel levels. This helps users identify content creators whose videos may contain risky or harmful content.

## Risk Categories

The system analyzes content for the following risk categories:

1. **Self-Harm References** - Content referencing self-harm, suicide, or self-destructive behavior
2. **Violence or Threats** - Threats of violence, physical harm, or violent content
3. **Illegal Activities** - Promotion or discussion of illegal activities
4. **Misinformation** - False or misleading information, especially harmful advice
5. **Hate Speech** - Hate speech, discrimination, or prejudiced content
6. **Harassment** - Harassment, bullying, or targeted abuse
7. **Toxicity** - General toxicity, harmful language, or negative behavior

## Risk Scoring

### Score Calculation

- **Overall Risk Score**: 0-100 float, aggregated from all risk categories
- **Risk Level**: Categorical label based on score:
  - **Low** (0-25): Minimal risk indicators
  - **Medium** (26-50): Some risk indicators present
  - **High** (51-75): Significant risk indicators
  - **Critical** (76-100): Severe risk indicators

### Aggregation

- **Video Level**: Each video is analyzed individually using LLM analysis of transcripts
- **Channel Level**: Average of all video risk scores for that channel

## Architecture

```
fastapi/
├── pipeline/
│   └── creator_risk.py          # Risk analysis pipeline
├── routes/
│   └── database/
│       ├── schema.py            # Pydantic models with risk fields
│       └── ingest.py            # Risk API endpoints
└── data/
    └── seed_creator_risk_mock.py # Mock data seeder

frontend/
├── api/
│   └── backend.ts               # Risk API client functions
└── app/
    ├── components/
    │   ├── channelRow.tsx       # Risk column display
    │   └── riskModal.tsx        # Risk detail modal
    └── channels/
        └── page.tsx             # Channels page with risk integration
```

## Backend Pipeline

### Running the Risk Analysis Pipeline

```bash
cd fastapi
python pipeline/creator_risk.py
```

The pipeline:
1. Fetches videos without risk analysis
2. Retrieves transcripts for each video
3. Analyzes transcripts using GPT-4.1-mini
4. Updates video documents with risk scores
5. Aggregates scores to channel level

### Rate Limiting

The pipeline implements the same rate-limiting patterns as the sentiment analysis:
- Global traffic light system for 429 errors
- Semaphore limiting 10 concurrent analyses
- Exponential backoff with jitter

## API Endpoints

### Get Channels with Risk Filter

```
GET /ingest/channels/risk?risk_level=high&min_risk_score=50&max_risk_score=100&limit=50
```

Parameters:
- `risk_level` (optional): Filter by risk level (low, medium, high, critical)
- `min_risk_score` (optional): Minimum risk score
- `max_risk_score` (optional): Maximum risk score
- `limit` (optional): Maximum results (default: 100)

### Get Channel Risk Details

```
GET /ingest/channels/{channel_id}/risk
```

Response:
```json
{
  "channel_id": "UC1234567890",
  "channel_name": "Example Channel",
  "video_count": 50,
  "videos_with_risk": 45,
  "avg_risk_score": 62.5,
  "risk_level": "high",
  "risk_breakdown": {
    "self_harm": 0.15,
    "violence": 0.45,
    "illegal_activities": 0.2,
    "misinformation": 0.65,
    "hate_speech": 0.1,
    "harassment": 0.3,
    "toxicity": 0.5
  },
  "high_risk_videos": [
    {
      "video_id": "abc123",
      "title": "Video Title",
      "risk_score": 85.2,
      "risk_level": "critical"
    }
  ]
}
```

### Get Videos with Risk Filter

```
GET /ingest/videos/risk?channel_id=UC1234567890&min_risk_score=50&limit=50
```

## Frontend Components

### Channel Row

The channel row component displays:
- Risk score (0-100)
- Risk level badge (color-coded)
- Click handler to open risk detail modal

### Risk Modal

The modal displays:
- Overall risk score and level
- Video analysis statistics
- Risk category breakdown (progress bars)
- List of high-risk videos
- Informational note about scoring

## Database Schema

### Videos Collection

```javascript
{
  _id: ObjectId,
  youtube_video_id: String,
  // ... other fields
  risk_score: Number,        // 0-100
  risk_level: String,        // "low" | "medium" | "high" | "critical"
  risk_breakdown: Object,    // { self_harm: 0.5, violence: 0.3, ... }
  updated_at: Date
}
```

### Channels Collection

```javascript
{
  _id: ObjectId,
  channel_id: String,
  // ... other fields
  risk_score: Number,        // 0-100 (aggregated)
  risk_level: String,        // "low" | "medium" | "high" | "critical"
  risk_breakdown: Object,    // { self_harm: 0.5, violence: 0.3, ... }
  updated_at: Date
}
```

## Mock Data Seeding

For testing or demonstration purposes, seed mock risk data:

```bash
cd fastapi
python data/seed_creator_risk_mock.py
```

This populates:
- Random risk scores based on channel type profiles
- Realistic risk breakdowns for each category
- Aggregated channel-level risk data

## Usage Example

### 1. Run the Risk Pipeline

```bash
python pipeline/creator_risk.py
```

### 2. View Risk Data in UI

Navigate to the Channels page (`/channels`) to see:
- Risk scores for each channel
- Color-coded risk badges
- Click any risk badge to view detailed breakdown

### 3. Filter by Risk Level

Use the API endpoints to filter channels/videos by risk:

```typescript
import { getChannelsWithRisk } from './api/backend';

// Get high-risk channels
const highRiskChannels = await getChannelsWithRisk({
  risk_level: 'high',
  limit: 50
});

// Get channels with risk score above 70
const veryHighRisk = await getChannelsWithRisk({
  min_risk_score: 70
});
```

## Performance Considerations

- **Batch Processing**: Videos are processed in batches with controlled concurrency
- **Caching**: Risk scores are cached in the database; only new videos are analyzed
- **Incremental Updates**: Pipeline only processes videos without risk data
- **Token Efficiency**: Transcripts are truncated to 15,000 characters max

## Future Enhancements

Potential improvements:
- [ ] Historical risk tracking over time
- [ ] Risk trend alerts (when channel risk increases significantly)
- [ ] Comment analysis in addition to transcripts
- [ ] Video thumbnail/image analysis
- [ ] User-configurable risk thresholds
- [ ] Export risk reports
- [ ] Risk comparison between channels

## Troubleshooting

### Pipeline Not Processing Videos

1. Check that transcripts exist in the database
2. Verify OpenAI API key is set
3. Check rate limit status in console output

### Risk Scores Not Appearing in UI

1. Run the mock data seeder for testing
2. Check API endpoints are returning data
3. Verify database has risk fields populated

### High Token Usage

To reduce token usage:
- Lower the transcript character limit (currently 15,000)
- Reduce concurrency (currently 10)
- Process videos in smaller batches
