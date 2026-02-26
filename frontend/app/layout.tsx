import type { Metadata } from "next";
import "@/styles/globals.css";
import "@/styles/layout.css";
import "@/styles/components.css";
import "@/styles/home.css";
import "@/styles/dashboard.css";
import "@/styles/channels.css";
import "@/styles/trends.css";
import Header from "../components/Header";
import Sidebar from "../components/Sidebar";

export const metadata: Metadata = {
  title: "Soccer Intelligence",
  description: "Soccer analytics and fan sentiment dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Header />
        <Sidebar />

        <div className="layout-body">
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}