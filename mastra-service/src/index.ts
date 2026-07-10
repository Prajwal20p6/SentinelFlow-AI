import express from "express";
import { setupApi } from "./api/index";
import { mastraConfig } from "./config/mastra.config";

const app = express();

// Middleware
app.use(express.json());

// Setup Mastra API
setupApi(app);

// Start server
app.listen(mastraConfig.port, () => {
  console.log(`Mastra Service running on port ${mastraConfig.port}`);
  console.log(`Python Backend: ${mastraConfig.pythonBackendUrl}`);
});
