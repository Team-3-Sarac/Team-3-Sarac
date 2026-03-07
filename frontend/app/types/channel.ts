// channels - channel overview table, kpi row

import { TrendDirection } from "./enums";

export interface Channel {
    channel_id: string;
    channel_initials: string; // derived from channel_name
    channel_name: string;
    handle: string; // not in schema yet
    sub_count: string; // not in schema yet
    league: string;
    video_count: number; // derived from videos
    sentiment_pct: number; // not in schema yet
    sentiment_dir: TrendDirection; // derived from sentiment_pct
    latest_title: string; // derived from videos collection
    latest_views: string; // derived from videos collection
}