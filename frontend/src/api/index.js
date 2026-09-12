import { createHttpClient } from "./http-client.js";
import { createMockClient } from "./mock-client.js";
export function createClient(env = import.meta.env, options = {}) {
  const source = env.VITE_DATA_SOURCE || "mock";
  if (source === "mock") return createMockClient(options);
  if (source === "api")
    return createHttpClient(
      env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
      options.fetcher,
    );
  throw new Error("VITE_DATA_SOURCE должен быть mock или api");
}
export const api = createClient();
