import "dotenv/config";
import express from "express";
import { setupApi } from "./api/index";
import { mastraConfig } from "./config/mastra.config";
import { getSecret } from "./config/secrets";

const app = express();

// Middleware
app.use(express.json());

// Setup API bridge environment keys for Mastra SDK resolver
const openaiKey = getSecret("OPENAI_API_KEY") || getSecret("MASTRA_OPENAI_API_KEY");
if (openaiKey) {
  process.env.OPENAI_API_KEY = openaiKey;
}
const anthropicKey = getSecret("ANTHROPIC_API_KEY") || getSecret("MASTRA_ANTHROPIC_API_KEY");
if (anthropicKey) {
  process.env.ANTHROPIC_API_KEY = anthropicKey;
}

// Setup Mastra API
setupApi(app);

// Start server
app.listen(mastraConfig.port, () => {
  console.log(`Mastra Service running on port ${mastraConfig.port}`);
  console.log(`Python Backend: ${mastraConfig.pythonBackendUrl}`);
});
