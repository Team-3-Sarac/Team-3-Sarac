// trends - narrative trends line graph, trending topics table

import { TrendDirection } from "./enums";

export interface Narrative {
    narrative_label: string;
    mention_count: number;
    change_pct: number; // derive from mention_count
    trending_direction: TrendDirection;
    league: string[]; // update schema to hold more than 1 string (array instead of string)
    hot: boolean; // derive from mention_count
}

export interface NarrativeTrend {
    week: string; // derived from created_at
    Transfers: number; // category field not in schema yet
    Injuries: number;
    Tactics: number;
    Controversy: number;
}