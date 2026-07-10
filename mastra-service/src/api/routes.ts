import express from "express";
import { incidentResponseWorkflow } from "../workflows";

const router = express.Router();

// POST /mastra/workflows/incident-response
// Execute incident response workflow
router.post("/workflows/incident-response", async (req, res) => {
  try {
    const { incident_id, incident_type, alert_data, metrics, logs } = req.body;

    const context = {
      incident: {
        incident_id,
        incident_type,
        alert_data,
        metrics,
      }
    };
    // Execute the workflow via Mastra SDK
    const controller = new AbortController();
    const result = await incidentResponseWorkflow.execute({
      inputData: context,
      abortSignal: controller.signal,
      setState: async () => {},
      suspend: async () => {}
    });

    res.json({
      status: "success",
      workflow_id: incident_id,
      result: result
    });
  } catch (error) {
    res.status(500).json({
      status: "error",
      message: error instanceof Error ? error.message : "Workflow execution failed"
    });
  }
});

// GET /mastra/health
router.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    service: "mastra-workflow-service",
    timestamp: new Date().toISOString()
  });
});

export default router;
