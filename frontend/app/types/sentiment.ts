// dashboard - sentiment trend graph
// need to add sentiment to db schema 

export interface Sentiment {
    day: string; // derived from created_at
    positive: number;
    negative: number;
}