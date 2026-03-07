// dashboard - trending match content

import { SentimentTone } from "./enums";

export interface MatchContent {
    league: string;
    sentiment: string; // not in schema yet
    sentiment_tone: SentimentTone; // not in schema yet
    title: string;
    channel_name: string;
    duration_seconds: number; // convert to "12:34" format
    view_count: number;
    like_count: number;
    comment_count: number;
    created_at: string; // derive "5h ago" from this
    youtube_video_id: string;
}