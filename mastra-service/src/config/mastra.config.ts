export const mastraConfig = {
  port: process.env.PORT || 3001,
  nodeEnv: process.env.NODE_ENV || "development",
  pythonBackendUrl: process.env.PYTHON_BACKEND_URL || "http://localhost:8000",
  pythonBackendApiKey: process.env.PYTHON_BACKEND_API_KEY || "",
  qdrantUrl: process.env.QDRANT_URL || "http://localhost:6333",
  mastraOpenaiApiKey: process.env.MASTRA_OPENAI_API_KEY || "",
  mastraAnthropicApiKey: process.env.MASTRA_ANTHROPIC_API_KEY || "",
  mastraGoogleApiKey: process.env.MASTRA_GOOGLE_API_KEY || ""
};
