db.createCollection("match_events", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "match_events",
      required: ["_id"],
      properties: {
        "_id": { bsonType: "objectId" },
        "video_id": { bsonType: "objectId" },
        "event_type": { bsonType: "string" },
        "team": { bsonType: "string" },
        "player": { bsonType: "string" },
        "match_minute": { bsonType: "int" },
        "description": { bsonType: "string" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("transcript_chunks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "transcript_chunks",
      required: ["_id"],
      properties: {
        "_id": { bsonType: "objectId" },
        "video_id": { bsonType: "objectId" },
        "chunk_index": { bsonType: "int" },
        "text": { bsonType: "string" },
        "start_time_seconds": { bsonType: "int" },
        "end_time_seconds": { bsonType: "int" },
        "embedding_id": { bsonType: "string" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("comments", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "comments",
      required: ["_id"],
      properties: {
        "_id": { bsonType: "objectId" },
        "video_id": { bsonType: "objectId" },
        "youtube_comment_id": { bsonType: "string" },
        "comment_text": { bsonType: "string" },
        "like_count": { bsonType: "int" },
        "embedding_id": { bsonType: "string" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("claims", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "claims",
      required: ["_id"],
      properties: {
        "_id": { bsonType: "objectId" },
        "video_id": { bsonType: "objectId" },
        "chunk_id": { bsonType: "objectId" },
        "claim_text": { bsonType: "string" },
        "embedding_id": { bsonType: "string" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("trends", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "trends",
      required: ["_id"],
      properties: {
        "_id": { bsonType: "objectId" },
        "narrative_id": { bsonType: "objectId" },
        "league": { bsonType: "string" },
        "time_window": { bsonType: "string" },
        "mention_count": { bsonType: "int" },
        "trending_direction": { bsonType: "string" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("narratives", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "narratives",
      required: ["_id"],
      properties: {
        "_id": { bsonType: "objectId" },
        "narrative_label": { bsonType: "string" },
        "league": { bsonType: "string" },
        "description": { bsonType: "string" },
        "claim_ids": { bsonType: "array", items: { bsonType: "objectId" } },
        "embedding_id": { bsonType: "string" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("videos", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "videos",
      required: ["_id"],
      properties: {
        "_id": { bsonType: "objectId" },
        "youtube_video_id": { bsonType: "string" },
        "title": { bsonType: "string" },
        "channel_id": { bsonType: "string" },
        "channel_name": { bsonType: "string" },
        "publish_date": { bsonType: "date" },
        "league": { bsonType: "string" },
        "teams": { bsonType: "array", items: { bsonType: "string" } },
        "view_count": { bsonType: "int" },
        "like_count": { bsonType: "int" },
        "comment_count": { bsonType: "int" },
        "duration_seconds": { bsonType: "int" },
        "summary": { bsonType: "string" },
        "thumbnail_url": { bsonType: "string" },
        "created_at": { bsonType: "date" },
        "updated_at": { bsonType: "date" },
      },
    },
  },
});