import { useEffect, useState } from "react";

import { api } from "./api";
import type { Health } from "./types";

export function useHealth(): Health | null {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);
  return health;
}
