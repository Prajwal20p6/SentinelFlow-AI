import { Agent } from "@mastra/core/agent";
import type { Tool } from "@mastra/core/tools";

const getThreatIntelTools = (): Tool[] => [
  {
    id: "enrich_ioc",
    description: "Enrich indicator of compromise (IP, domain, hash) with threat intelligence",
    inputSchema: {
      type: "object",
      properties: {
        ioc_type: { type: "string", enum: ["ip", "domain", "hash", "url", "email"] },
        ioc_value: { type: "string" }
      },
      required: ["ioc_type", "ioc_value"]
    },
    execute: async ({ ioc_type, ioc_value }) => {
      // Call Python backend which integrates with threat intel APIs
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/threat-intelligence/enrich`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ ioc_type, ioc_value })
        }
      );
      return response.json();
    }
  },
  {
    id: "check_breach_databases",
    description: "Check if IOCs appear in known breach databases",
    inputSchema: {
      type: "object",
      properties: {
        ioc_value: { type: "string" }
      },
      required: ["ioc_value"]
    },
    execute: async ({ ioc_value }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/threat-intelligence/breaches?ioc=${ioc_value}`,
        {
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`
          }
        }
      );
      return response.json();
    }
  }
];

export const threatIntelAgent = new Agent({
  name: "ThreatIntelligenceAgent",
  instructions: `You are a cybersecurity threat intelligence specialist.
Your job is to enrich incident data with threat intelligence from multiple sources.
Use the provided tools to check indicators of compromise against threat databases.
Provide threat assessment with risk scores and recommended actions.
Format your response as JSON with fields: threat_level (low|medium|high|critical), risk_score (0-100), iocs_found (array), recommendations (array)`,
  model: "openai/gpt-4o",
  tools: getThreatIntelTools()
});
