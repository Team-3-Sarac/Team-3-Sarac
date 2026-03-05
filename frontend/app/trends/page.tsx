"use client";
import Card from "../components/card";
import CardHeader from "../components/cardHeader";
import LegendDot from "../components/legendDot";
import BarChartMock from "../components/barChartMock";
import LineChartMock from "../components/lineChartMock";
import TopicRow from "../components/topicRow";



import { Flame, TrendingUp, TrendingDown } from "lucide-react";

export default function TrendsPage() {
  return (
    <div className="min-h-screen w-full bg-black text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Trend Detection</h1>
          <p className="mt-2 text-sm text-neutral-400">
            Discover trending topics and narratives across European soccer leagues
          </p>
        </div>

        {/* Top charts */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Content Volume by League"
              subtitle="Videos analyzed per league this month"
            />
            <div className="p-5">
              <BarChartMock />
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Narrative Trends"
              subtitle="Topic frequency over the past 6 weeks"
            />
            <div className="p-5">
              <LineChartMock />
              <div className="mt-4 flex flex-wrap gap-4 text-xs text-neutral-400">
                <LegendDot color="bg-emerald-400" label="Transfers" />
                <LegendDot color="bg-red-400" label="Injuries" />
                <LegendDot color="bg-sky-400" label="Tactics" />
                <LegendDot color="bg-amber-400" label="Controversy" />
              </div>
            </div>
          </Card>
        </div>

        {/* Table */}
        <div className="mt-6">
          <Card>
            <CardHeader
              title="Trending Topics"
              subtitle="Most discussed narratives across YouTube soccer content"
            />

            <div className="overflow-hidden">
              {/* table header */}
              <div className="grid grid-cols-12 gap-4 border-b border-neutral-800 px-5 py-3 text-xs uppercase tracking-wide text-neutral-500">
                <div className="col-span-6">Topic</div>
                <div className="col-span-2 text-right">Mentions</div>
                <div className="col-span-2 text-right">Change</div>
                <div className="col-span-2 text-right">Leagues</div>
              </div>

              <div className="divide-y divide-neutral-800">
                <TopicRow
                  hot
                  topic="Transfer Window Speculation"
                  mentions="342"
                  change="+28%"
                  changeDir="up"
                  leagues={["Premier …", "La Liga"]}
                />
                <TopicRow
                  hot
                  topic="VAR Controversy"
                  mentions="287"
                  change="+45%"
                  changeDir="up"
                  leagues={["Serie A", "Premier …"]}
                />
                <TopicRow
                  topic="Title Race Analysis"
                  mentions="256"
                  change="+12%"
                  changeDir="up"
                  leagues={["Premier …", "La Liga", "+1"]}
                />
                <TopicRow
                  topic="Player Injury Updates"
                  mentions="198"
                  change="-8%"
                  changeDir="down"
                  leagues={["Bundesliga", "Ligue 1"]}
                />
                <TopicRow
                  topic="Managerial Changes"
                  mentions="176"
                  change="0%"
                  changeDir="flat"
                  leagues={["Serie A"]}
                />
                <TopicRow
                  hot
                  topic="Youth Academy Breakouts"
                  mentions="134"
                  change="+32%"
                  changeDir="up"
                  leagues={["La Liga", "Bundesliga"]}
                />
                <TopicRow
                  hot
                  topic="Champions League Predictions"
                  mentions="298"
                  change="+18%"
                  changeDir="up"
                  leagues={["Premier …", "La Liga", "+2"]}
                />
                <TopicRow
                  topic="Tactical Evolution"
                  mentions="112"
                  change="-3%"
                  changeDir="down"
                  leagues={["Premier …"]}
                />
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}