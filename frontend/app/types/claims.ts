// trends - claims

import { ClaimSentiment } from "./enums";

export interface Claim {
    claim_text: string;
    confidence: number; // not in schema yet
    sentiment: ClaimSentiment; // not in schema yet
    mentions: number; // derived
    leagues: string[];
}