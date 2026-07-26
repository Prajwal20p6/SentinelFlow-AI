import { describe, it } from "node:test";
import assert from "node:assert";
import { rcaAgent, threatIntelAgent, remediationAgent, prioritizationAgent } from "./index";

describe("Mastra Autonomous Agents Suite", () => {
  it("rcaAgent is initialized correctly", () => {
    assert.ok(rcaAgent, "rcaAgent should be defined");
    assert.strictEqual(rcaAgent.name, "RootCauseAnalysisAgent");
  });

  it("threatIntelAgent is initialized correctly", () => {
    assert.ok(threatIntelAgent, "threatIntelAgent should be defined");
    assert.strictEqual(threatIntelAgent.name, "ThreatIntelligenceAgent");
  });

  it("remediationAgent is initialized correctly", () => {
    assert.ok(remediationAgent, "remediationAgent should be defined");
    assert.strictEqual(remediationAgent.name, "RemediationAgent");
  });

  it("prioritizationAgent is initialized correctly", () => {
    assert.ok(prioritizationAgent, "prioritizationAgent should be defined");
    assert.strictEqual(prioritizationAgent.name, "IncidentPrioritizationAgent");
  });
});
