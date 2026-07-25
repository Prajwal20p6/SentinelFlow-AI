import { getSecret } from "./secrets";

export const mastraConfig = {
  port: parseInt(getSecret("PORT", "3001"), 10),
  nodeEnv: getSecret("NODE_ENV", "development"),
  pythonBackendUrl: getSecret("PYTHON_BACKEND_URL", "http://localhost:8000"),
  pythonBackendApiKey: getSecret("PYTHON_BACKEND_API_KEY", ""),
  qdrantUrl: getSecret("QDRANT_URL", "http://localhost:6333"),
  mastraOpenaiApiKey: getSecret("MASTRA_OPENAI_API_KEY", ""),
  mastraAnthropicApiKey: getSecret("MASTRA_ANTHROPIC_API_KEY", ""),
  mastraGoogleApiKey: getSecret("MASTRA_GOOGLE_API_KEY", "")
};
