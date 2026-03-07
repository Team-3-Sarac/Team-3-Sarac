import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="bg-black text-white min-h-screen">

      {/* HERO */}
      <section className="max-w-6xl mx-auto text-center py-28 px-6">

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-sm text-neutral-300 mb-6">
          <span className="w-2 h-2 bg-green-500 rounded-full"></span>
          Analyzing 1,200+ videos this week
        </div>

        <h1 className="text-5xl md:text-6xl font-bold leading-tight">
          YouTube intelligence
          <br />
          for soccer analytics
        </h1>

        <p className="text-neutral-400 mt-6 max-w-2xl mx-auto">
          AI-powered platform that analyzes YouTube content to deliver
          match summaries, sentiment insights, and trending topics
          across top European leagues.
        </p>

        <div className="flex justify-center gap-4 mt-8">
        <Link
          href="/dashboard"
          className="bg-white text-black px-6 py-3 rounded-md font-medium hover:bg-neutral-200 transition"
        >
          Go to Dashboard →
        </Link>

        <Link
          href="/trends"
          className="border border-neutral-700 px-6 py-3 rounded-md hover:bg-neutral-900 transition"
        >
          Learn more
        </Link>
        </div>

      </section>

      {/* STATS */}
      <section className="border-t border-neutral-800 border-b border-neutral-800">
        <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 text-center">

          <Stat number="1,200+" label="Videos analyzed weekly" />
          <Stat number="5" label="European leagues tracked" />
          <Stat number="34" label="Active trending topics" />
          <Stat number="92%" label="Sentiment accuracy" />

        </div>
      </section>


      {/* FEATURES */}
      <section className="max-w-6xl mx-auto py-28 px-6">

        <div className="text-center mb-16">
          <h2 className="text-3xl font-semibold">
            Everything you need to track the conversation
          </h2>

          <p className="text-neutral-400 mt-4">
            From real-time sentiment to AI-generated weekly digests,
            MatchIQ keeps you ahead of the narrative.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">

          <Feature
            title="Sentiment Analysis"
            desc="Track fan sentiment across YouTube comments and video content in real-time."
          />

          <Feature
            title="Trend Detection"
            desc="Discover emerging narratives before they go mainstream."
          />

          <Feature
            title="Channel Tracking"
            desc="Monitor top soccer YouTube channels automatically."
          />

          <Feature
            title="AI Summaries"
            desc="Get concise AI-generated digests of match coverage."
          />

          <Feature
            title="League Insights"
            desc="Compare engagement metrics across major leagues."
          />

          <Feature
            title="Multi-League Coverage"
            desc="Full coverage across the top 5 European leagues."
          />

        </div>
      </section>


      {/* LEAGUES */}
      <section className="text-center py-20 border-t border-neutral-800">

        <h2 className="text-3xl font-semibold">
          Covering the top 5 European leagues
        </h2>

        <p className="text-neutral-400 mt-4">
          Comprehensive YouTube content analysis across every major league.
        </p>

        <div className="flex justify-center gap-10 mt-10 text-neutral-300 text-lg">
          <span>Premier League</span>
          <span>La Liga</span>
          <span>Bundesliga</span>
          <span>Serie A</span>
          <span>Ligue 1</span>
        </div>

      </section>


      {/* CTA */}
      <section className="text-center py-28 border-t border-neutral-800">

        <h2 className="text-3xl font-semibold">
          Ready to explore the data?
        </h2>

        <p className="text-neutral-400 mt-4 max-w-xl mx-auto">
          Jump into the dashboard to see live sentiment trends,
          trending match content, and AI-generated intelligence.
        </p>

        <Link
          href="/dashboard"
          className="mt-8 inline-block bg-white text-black px-6 py-3 rounded-md font-medium hover:bg-neutral-200 transition"
        >
          Open Dashboard →
        </Link>

      </section>

    </div>
  );
}


function Stat({ number, label }: { number: string; label: string }) {
  return (
    <div className="py-10 border-neutral-800 border-r last:border-none">
      <div className="text-3xl font-bold">{number}</div>
      <div className="text-neutral-400 text-sm mt-2">{label}</div>
    </div>
  );
}

function Feature({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="border border-neutral-800 rounded-lg p-6 bg-neutral-950 hover:border-neutral-700 transition">
      <h3 className="font-semibold text-lg">{title}</h3>
      <p className="text-neutral-400 mt-2 text-sm">{desc}</p>
    </div>
  );
}