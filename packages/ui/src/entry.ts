import * as components from "./components";

const w = window as unknown as { SecAI?: Record<string, unknown> };
w.SecAI = Object.assign(w.SecAI ?? {}, components);
