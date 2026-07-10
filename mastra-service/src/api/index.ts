import express from "express";
import routes from "./routes";

export function setupApi(app: express.Application) {
  app.use("/mastra", routes);
}
