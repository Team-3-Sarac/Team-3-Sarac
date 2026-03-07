// dashboard - league overview, trends - content volume by league (bar graph)

import { LeagueStatus } from "./enums";

export interface LeagueOverview {
    code: string; // can be derived from league
    league: string;
    count: number; // derived from videos collection
    status: LeagueStatus; // derive from trending direction or video count
}

export interface LeagueVolume {
    league: string;
    count: number; // derived from videos
}