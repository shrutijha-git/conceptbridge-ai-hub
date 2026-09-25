import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";

import { AuthProvider } from "../components/auth-provider";

export const metadata: Metadata = {
  title: "ConceptBridge — your learning workspace",
  description:
    "Understand a concept, practise it, and keep your learning context together.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}