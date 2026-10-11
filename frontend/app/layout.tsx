import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "ForgeJudge",
  description: "A cloud-native coding platform and judge engine.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <Link className="wordmark" href="/problems">FORGEJUDGE</Link>
          <nav className="main-nav" aria-label="Main navigation">
            <Link href="/problems">Problems</Link>
            <Link href="/submissions">Submissions</Link>
          </nav>
          <div className="phase-label">JUDGE / 01</div>
        </header>
        {children}
      </body>
    </html>
  );
}