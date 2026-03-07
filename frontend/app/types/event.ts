// dashboard - key events

import { EventType } from "./enums";

export interface MatchEvent {
    event_type: EventType;
    description: string;
    created_at: string; // will calculate time from this
}