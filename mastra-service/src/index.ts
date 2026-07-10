import "dotenv/config";
import express from "express";
import { setupApi } from "./api/index";
import { mastraConfig } from "./config/mastra.config";

const app = express();

// Middleware
app.use(express.json());

// Setup API bridge environment keys for Mastra SDK resolver
if (!process.env.OPENAI_API_KEY && process.env.MASTRA_OPENAI_API_KEY) {
  process.env.OPENAI_API_KEY = process.env.MASTRA_OPENAI_API_KEY;
}
if (!process.env.ANTHROPIC_API_KEY && process.env.MASTRA_ANTHROPIC_API_KEY) {
  process.env.ANTHROPIC_API_KEY = process.env.MASTRA_ANTHROPIC_API_KEY;
}

// Setup Mastra API
setupApi(app);

// Start server
app.listen(mastraConfig.port, () => {
  console.log(`Mastra Service running on port ${mastraConfig.port}`);
  console.log(`Python Backend: ${mastraConfig.pythonBackendUrl}`);
});
