"use client";

import { StudyWorkspace } from "@/components/study-workspace";
import { AuthGuard } from "@/components/auth-provider";

export default function Home() {
  return (
    <AuthGuard>
      <StudyWorkspace />
    </AuthGuard>
  );
}