import type { Metadata } from "next";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpsRoom.ai — Incident War Room",
  description: "Real-time multi-agent incident response",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit" agent="opsroom">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
