"use client";

import { createContext, useContext } from "react";
import type { Incident } from "@/lib/api";

type IncidentContextValue = {
  selectedId: string | null;
  incident: Incident | null;
};

export const IncidentContext = createContext<IncidentContextValue>({
  selectedId: null,
  incident: null,
});

export function useIncidentContext() {
  return useContext(IncidentContext);
}

export function IncidentProvider({
  selectedId,
  incident,
  children,
}: {
  selectedId: string | null;
  incident: Incident | null;
  children: React.ReactNode;
}) {
  return (
    <IncidentContext.Provider value={{ selectedId, incident }}>{children}</IncidentContext.Provider>
  );
}
