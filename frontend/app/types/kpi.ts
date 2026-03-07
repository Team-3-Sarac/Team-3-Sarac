// dashboard - kpi row

import { TrendDirection } from "./enums";

export interface KpiItem {
    value: string;
    sub: string;
    trend: TrendDirection;
}

export interface KpiResponse {
    videos_analyzed: KpiItem;
    trending_topics: KpiItem;
    avg_sentiment: KpiItem;
    channels_tracked: KpiItem;
}