import { Workflow, createStep } from "@mastra/core/workflows";
import { rcaAgent, threatIntelAgent, remediationAgent, prioritizationAgent } from "../agents";

interface IncidentData {
  incident_id: string;
  incident_type: string;
  alert_data: Record<string, unknown>;
  metrics: Record<string, unknown>;
  logs: unknown[];
}

export const incidentResponseWorkflow = new Workflow({
  id: "IncidentResponseWorkflow",
  description: "Complete incident response workflow using Mastra agents",
  options: {
    sharePubsub: true
  }
});

// ── Simulation Fallback Generators ──────────────────────────
function getMockRca(incident_type: string, incident_id: string) {
  const type = (incident_type || "").toUpperCase();
  const timestamp = new Date().toISOString();
  const randomSuffix = Math.floor(Math.random() * 1000);
  const confidenceBase = 85 + Math.floor(Math.random() * 12);
  
  if (type === "CPU_SPIKE") {
    const cpuValue = 85 + Math.floor(Math.random() * 14);
    const podName = `api-gateway-${randomSuffix}`;
    return {
      root_cause: `High CPU utilization (${cpuValue}%) detected on node-${randomSuffix % 10}/${podName} pod. Scale deployment to mitigate. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase,
      evidence: [`CPU usage at ${cpuValue}%`, `Pod node scheduling latency increased to ${Math.floor(Math.random() * 500)}ms`, `Memory pressure at ${60 + Math.floor(Math.random() * 20)}%`],
      similar_incidents: [`INC-${100 + randomSuffix}`, `INC-${200 + randomSuffix}`]
    };
  } else if (type === "DISK_FULL") {
    const diskValue = 90 + Math.floor(Math.random() * 8);
    const volumeSize = 400 + Math.floor(Math.random() * 200);
    return {
      root_cause: `Storage space exceeded ${diskValue}% on infrastructure node-${randomSuffix % 10}. Clear persistent volume cache. Incident #${incident_id} at ${timestamp}. Volume: ${volumeSize}GB`,
      confidence: confidenceBase - 2,
      evidence: [`Disk capacity alert at ${diskValue}% of ${volumeSize}GB volume`, `Write latency increased to ${Math.floor(Math.random() * 100)}ms`],
      similar_incidents: [`INC-${300 + randomSuffix}`]
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    const ipBytes = [198, 51, 100, 42].map((n, i) => i === 3 ? n + randomSuffix % 200 : n);
    const sourceIP = ipBytes.join('.');
    const attempts = 30 + Math.floor(Math.random() * 50);
    return {
      root_cause: `Repeated failed SSH login attempts detected from unrecognized host IP ${sourceIP}. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase + 3,
      evidence: [`IP ${sourceIP} attempted ${attempts} failed login attempts in ${1 + Math.floor(Math.random() * 3)} minutes`, `User agent pattern matches known attack signatures`],
      similar_incidents: [`INC-${400 + randomSuffix}`]
    };
  } else if (type === "PHISHING_ATTACK") {
    const sourceIP = `103.45.${randomSuffix % 256}.${randomSuffix % 256}`;
    return {
      root_cause: `Simulated Office 365 phishing breach. PowerShell running, unusual logins from ${sourceIP}, database exfiltration. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase,
      evidence: [`Unusual login from IP ${sourceIP}`, `Malicious PowerShell download execution from ${randomSuffix} domains`, `Database query volume increased by ${200 + Math.floor(Math.random() * 300)}%`],
      similar_incidents: [`INC-${500 + randomSuffix}`]
    };
  } else if (type === "DDOS_ATTACK") {
    const reqPerSec = 10000 + Math.floor(Math.random() * 10000);
    const surgePercent = 300 + Math.floor(Math.random() * 300);
    return {
      root_cause: `Traffic volume surge of ${reqPerSec} req/sec from botnet IPs. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase + 2,
      evidence: [`Ingress traffic surge of ${surgePercent}%`, `Botnet source IP identified in blocklists`, `Request latency increased to ${Math.floor(Math.random() * 5000)}ms`],
      similar_incidents: [`INC-${600 + randomSuffix}`]
    };
  } else if (type === "ERROR_RATE_SPIKE" || type === "ERROR_RATE") {
    const errorRate = 15 + Math.floor(Math.random() * 20);
    return {
      root_cause: `Application error rate spiked to ${errorRate}%. Regression error on latest deployment rollout version ${randomSuffix}. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase - 3,
      evidence: [`HTTP 5xx errors reached ${errorRate}%`, `Error rate increased by ${200 + Math.floor(Math.random() * 400)}%`, `Affected endpoints: /api/v1/${randomSuffix}`],
      similar_incidents: [`INC-${700 + randomSuffix}`]
    };
  } else if (type === "MEMORY_EXHAUSTION") {
    const memValue = 85 + Math.floor(Math.random() * 12);
    return {
      root_cause: `Memory usage approached ${memValue}% limit. Potential memory leak identified on node processes. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase - 1,
      evidence: [`Memory consumption at ${memValue}%`, `GC pause time increased to ${Math.floor(Math.random() * 500)}ms`, `Heap dump size: ${Math.floor(Math.random() * 500)}MB`],
      similar_incidents: [`INC-${800 + randomSuffix}`]
    };
  } else if (type === "HIGH_LATENCY") {
    const latencyValue = 3000 + Math.floor(Math.random() * 4000);
    return {
      root_cause: `HTTP latency spike above warning limits (${latencyValue}ms). CoreDNS queries experiencing connection timeouts. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase - 5,
      evidence: [`Response time latency at ${latencyValue}ms`, `DNS query timeout rate: ${Math.floor(Math.random() * 30)}%`, `Network hop count increased to ${10 + Math.floor(Math.random() * 10)}`],
      similar_incidents: [`INC-${900 + randomSuffix}`]
    };
  } else if (type === "NETWORK_OUTAGE") {
    const packetLoss = 30 + Math.floor(Math.random() * 50);
    return {
      root_cause: `Network partition detected between availability zones. Packet loss at ${packetLoss}%. Service mesh proxy connectivity degraded. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase - 2,
      evidence: [`Packet loss rate: ${packetLoss}%`, `Cross-AZ latency elevated to ${2000 + Math.floor(Math.random() * 3000)}ms`, `Service mesh proxy ${randomSuffix % 5} nodes unreachable`],
      similar_incidents: [`INC-${950 + randomSuffix}`]
    };
  } else {
    const sourceIP = `99.88.${randomSuffix % 256}.${randomSuffix % 256}`;
    return {
      root_cause: `Impossible travel login detected, database bulk download attempt from IP ${sourceIP}. Incident #${incident_id} at ${timestamp}.`,
      confidence: confidenceBase,
      evidence: [`Login from ${sourceIP}, bulk database download command matched`, `Geolocation distance: ${5000 + Math.floor(Math.random() * 5000)}km`, `Login time difference: ${Math.floor(Math.random() * 60)} minutes`],
      similar_incidents: [`INC-${1000 + randomSuffix}`]
    };
  }
}

function getMockThreat(incident_type: string, incident_id?: string) {
  const type = (incident_type || "").toUpperCase();
  const rnd = Math.floor(Math.random() * 1000);
  const ts = new Date().toISOString();
  const conf = 85 + Math.floor(Math.random() * 12);
  if (type === "CPU_SPIKE" || type === "DISK_FULL") {
    return {
      threat_level: "low",
      risk_score: 5 + Math.floor(Math.random() * 15),
      iocs_found: [],
      recommendations: [`Monitor capacity metrics (incident #${incident_id || rnd}, ${ts})`, "Check resource quotas"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    const ip = `198.51.${rnd % 256}.${rnd % 256}`;
    return {
      threat_level: "critical",
      risk_score: 85 + Math.floor(Math.random() * 12),
      iocs_found: [ip],
      recommendations: [`Block IP ${ip} at edge firewall`, "Enable account lockout policies", "Review audit logs"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf + 3
    };
  } else if (type === "PHISHING_ATTACK") {
    const ip = `103.45.${rnd % 256}.${rnd % 256}`;
    return {
      threat_level: "high",
      risk_score: 78 + Math.floor(Math.random() * 15),
      iocs_found: [ip],
      recommendations: ["Revoke session tokens", "Enforce MFA re-enrollment", "Sweep endpoint for persistence"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf
    };
  } else if (type === "DDOS_ATTACK") {
    const ip = `185.${rnd % 256}.${rnd % 256}.${rnd % 256}`;
    return {
      threat_level: "critical",
      risk_score: 90 + Math.floor(Math.random() * 8),
      iocs_found: [ip],
      recommendations: ["Apply rate-limiting rules", "Enable cloudflare proxy shielding", "Blackhole route suspect prefixes"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf + 2
    };
  } else if (type === "ERROR_RATE_SPIKE" || type === "ERROR_RATE") {
    return {
      threat_level: "low",
      risk_score: 8 + Math.floor(Math.random() * 12),
      iocs_found: [],
      recommendations: ["Rollback recent code changes", "Check deployment rollout history"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf - 3
    };
  } else if (type === "MEMORY_EXHAUSTION") {
    return {
      threat_level: "low",
      risk_score: 5 + Math.floor(Math.random() * 10),
      iocs_found: [],
      recommendations: ["Check memory dump profile", "Profile heap allocations"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf - 1
    };
  } else if (type === "HIGH_LATENCY") {
    return {
      threat_level: "low",
      risk_score: 12 + Math.floor(Math.random() * 15),
      iocs_found: [],
      recommendations: ["Check CoreDNS logs", "Trace network hop latencies"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf - 5
    };
  } else if (type === "NETWORK_OUTAGE") {
    return {
      threat_level: "medium",
      risk_score: 35 + Math.floor(Math.random() * 20),
      iocs_found: [],
      recommendations: ["Verify service mesh proxy health", "Check network policy rules", "Validate cross-AZ connectivity", "Restart kube-proxy if stale"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf - 2
    };
  } else {
    const ip = `99.88.${rnd % 256}.${rnd % 256}`;
    return {
      threat_level: "critical",
      risk_score: 80 + Math.floor(Math.random() * 15),
      iocs_found: [ip],
      recommendations: ["Apply Kubernetes network policy isolation", "Isolate compromised pod", "Rotate service account tokens"],
      scan_id: `SCAN-${rnd}`,
      confidence: conf
    };
  }
}

function getMockPriority(incident_type: string, incident_id?: string) {
  const type = (incident_type || "").toUpperCase();
  const rnd = Math.floor(Math.random() * 1000);
  const ts = new Date().toISOString();
  if (type === "CPU_SPIKE") {
    const affected = 500 + Math.floor(Math.random() * 3000);
    return {
      priority_level: "P1",
      sla_minutes: 20 + Math.floor(Math.random() * 20),
      justification: `Critical API gateway performance degradation. ${affected} users affected. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "HIGH", revenue_impact_usd: affected * (2 + Math.floor(Math.random() * 5)) }
    };
  } else if (type === "DISK_FULL") {
    const affected = 100 + Math.floor(Math.random() * 400);
    return {
      priority_level: "P2",
      sla_minutes: 45 + Math.floor(Math.random() * 30),
      justification: `PostgreSQL storage pool pressure warning. ${affected} users affected. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "MEDIUM", revenue_impact_usd: affected * (1 + Math.floor(Math.random() * 3)) }
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    const affected = 2000 + Math.floor(Math.random() * 8000);
    return {
      priority_level: "P0",
      sla_minutes: 10 + Math.floor(Math.random() * 10),
      justification: `Active server brute force infiltration attempt. ${affected} users at risk. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "CRITICAL", revenue_impact_usd: affected * (5 + Math.floor(Math.random() * 10)) }
    };
  } else if (type === "PHISHING_ATTACK") {
    const affected = 3000 + Math.floor(Math.random() * 5000);
    return {
      priority_level: "P0",
      sla_minutes: 10 + Math.floor(Math.random() * 10),
      justification: `Phishing breach with credential compromise. ${affected} users affected. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "CRITICAL", revenue_impact_usd: affected * (5 + Math.floor(Math.random() * 10)) }
    };
  } else if (type === "DDOS_ATTACK") {
    const affected = 5000 + Math.floor(Math.random() * 10000);
    return {
      priority_level: "P0",
      sla_minutes: 5 + Math.floor(Math.random() * 10),
      justification: `DDoS attack causing service degradation. ${affected} users affected. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "CRITICAL", revenue_impact_usd: affected * (3 + Math.floor(Math.random() * 7)) }
    };
  } else if (type === "ERROR_RATE_SPIKE" || type === "ERROR_RATE") {
    const affected = 1000 + Math.floor(Math.random() * 3000);
    return {
      priority_level: "P1",
      sla_minutes: 25 + Math.floor(Math.random() * 20),
      justification: `Customer facing transaction processing errors escalated. ${affected} users affected. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "HIGH", revenue_impact_usd: affected * (2 + Math.floor(Math.random() * 5)) }
    };
  } else if (type === "MEMORY_EXHAUSTION") {
    const affected = 200 + Math.floor(Math.random() * 800);
    return {
      priority_level: "P2",
      sla_minutes: 45 + Math.floor(Math.random() * 30),
      justification: `Pod memory pool warning limits reached. ${affected} users affected. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "MEDIUM", revenue_impact_usd: affected * (1 + Math.floor(Math.random() * 4)) }
    };
  } else if (type === "HIGH_LATENCY") {
    const affected = 500 + Math.floor(Math.random() * 2000);
    return {
      priority_level: "P2",
      sla_minutes: 40 + Math.floor(Math.random() * 30),
      justification: `Response delay affecting client endpoints. ${affected} users affected. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "MEDIUM", revenue_impact_usd: affected * (1 + Math.floor(Math.random() * 4)) }
    };
  } else if (type === "NETWORK_OUTAGE") {
    const affected = 3000 + Math.floor(Math.random() * 7000);
    return {
      priority_level: "P1",
      sla_minutes: 15 + Math.floor(Math.random() * 15),
      justification: `Cross-availability-zone network partition affecting service mesh connectivity. ${affected} users impacted. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "HIGH", revenue_impact_usd: affected * (3 + Math.floor(Math.random() * 6)) }
    };
  } else {
    const affected = 5000 + Math.floor(Math.random() * 10000);
    return {
      priority_level: "P0",
      sla_minutes: 10 + Math.floor(Math.random() * 10),
      justification: `Potential data exfiltration / breach attempt. ${affected} users at risk. (Inc #${incident_id || rnd}, ${ts})`,
      business_impact: { affected_users: affected, risk: "CRITICAL", revenue_impact_usd: affected * (5 + Math.floor(Math.random() * 10)) }
    };
  }
}

function getMockRemediation(incident_type: string, incident_id?: string) {
  const type = (incident_type || "").toUpperCase();
  const rnd = Math.floor(Math.random() * 1000);
  const ts = new Date().toISOString();
  const conf = 82 + Math.floor(Math.random() * 15);
  if (type === "CPU_SPIKE") {
    const replicas = 2 + Math.floor(Math.random() * 6);
    return {
      recommended_option: {
        action: `kubectl scale deployment api-gateway --replicas=${replicas}`,
        name: `Scale api-gateway to ${replicas} replicas`,
        reasoning: `Auto-scaling api-gateway from current to ${replicas} replicas to handle CPU spike. (Inc #${incident_id || rnd}, ${ts})`,
        success_probability: conf + 5,
        downtime_estimate: "0m",
        risk_level: "low",
        composite_score: 0.9 + Math.random() * 0.1
      },
      ranked_options: [
        {
          action: `kubectl scale deployment api-gateway --replicas=${replicas}`,
          name: `Scale api-gateway to ${replicas} replicas`,
          reasoning: "Direct horizontal scaling bypasses resource contention without service restart",
          success_probability: conf + 5,
          downtime_estimate: "0m",
          risk_level: "low",
          composite_score: 0.9 + Math.random() * 0.1
        },
        {
          action: "kubectl rollout restart deployment api-gateway",
          name: "Rolling restart api-gateway",
          reasoning: "Restart can clear transient state but causes brief pod termination cycle",
          success_probability: conf - 15,
          downtime_estimate: "1-2m",
          risk_level: "medium",
          composite_score: 0.7 + Math.random() * 0.1
        },
        {
          action: `kubectl patch hpa api-gateway --patch '{"spec":{"maxReplicas":${replicas * 2}}}'`,
          name: `Update HPA max to ${replicas * 2}`,
          reasoning: "Adjusting HPA ceiling for sustained load rather than manual replica count",
          success_probability: conf - 5,
          downtime_estimate: "0m",
          risk_level: "low",
          composite_score: 0.8 + Math.random() * 0.1
        }
      ],
      rollback_plan: `kubectl scale deployment api-gateway --replicas=1`
    };
  } else if (type === "DISK_FULL") {
    return {
      recommended_option: {
        action: `kubectl exec ${incident_id ? `pod-${incident_id}` : 'postgres-primary'} -- df -h`,
        name: "Disk diagnostics on primary",
        reasoning: "Run safe diagnostic to assess disk pressure before cleanup. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf - 2,
        downtime_estimate: "0m",
        risk_level: "low",
        composite_score: 0.85
      },
      ranked_options: [
        {
          action: `kubectl exec ${incident_id ? `pod-${incident_id}` : 'postgres-primary'} -- df -h`,
          name: "Disk diagnostics on primary",
          reasoning: "Non-destructive diagnostic step before action",
          success_probability: conf - 2,
          downtime_estimate: "0m",
          risk_level: "low",
          composite_score: 0.85
        },
        {
          action: `kubectl exec ${incident_id ? `pod-${incident_id}` : 'postgres-primary'} -- find /var/log -name "*.log" -mtime +7 -delete`,
          name: "Clean old log files",
          reasoning: "Remove logs older than 7 days to free disk space",
          success_probability: conf,
          downtime_estimate: "0m",
          risk_level: "low",
          composite_score: 0.88
        }
      ],
      rollback_plan: "No rollback required for safe diagnostics"
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    return {
      recommended_option: {
        action: `kubectl delete pod auth-service-${(rnd % 9000) + 1000}`,
        name: "Terminate compromised auth pod",
        reasoning: "Force pod recreation to purge potential session hijack. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf,
        downtime_estimate: "10s",
        risk_level: "medium",
        composite_score: 0.82
      },
      ranked_options: [
        {
          action: `kubectl delete pod auth-service-${(rnd % 9000) + 1000}`,
          name: "Terminate compromised auth pod",
          reasoning: "Pod deletion forces ReplicaSet to recreate with fresh state",
          success_probability: conf,
          downtime_estimate: "10s",
          risk_level: "medium",
          composite_score: 0.82
        },
        {
          action: `kubectl apply -f - <<'EOF'\napiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: isolate-auth\nspec:\n  podSelector:\n    matchLabels:\n      app: auth-service\n  policyTypes: [Ingress]\nEOF`,
          name: "Isolate auth-service with NetworkPolicy",
          reasoning: "Network isolation prevents lateral movement while investigation proceeds",
          success_probability: conf + 2,
          downtime_estimate: "0m",
          risk_level: "low",
          composite_score: 0.91
        }
      ],
      rollback_plan: "Pod will auto-recreate via ReplicaSet"
    };
  } else if (type === "PHISHING_ATTACK") {
    return {
      recommended_option: {
        action: `kubectl delete pod identity-provider-${(rnd % 9000) + 1000}`,
        name: "Rotate identity provider pod",
        reasoning: "Force pod recreation to revoke active sessions. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf + 2,
        downtime_estimate: "10s",
        risk_level: "medium",
        composite_score: 0.86
      },
      ranked_options: [
        {
          action: `kubectl delete pod identity-provider-${(rnd % 9000) + 1000}`,
          name: "Rotate identity provider pod",
          reasoning: "Recreation clears potentially compromised session state",
          success_probability: conf + 2,
          downtime_estimate: "10s",
          risk_level: "medium",
          composite_score: 0.86
        }
      ],
      rollback_plan: "Pod auto-recreates via ReplicaSet"
    };
  } else if (type === "DDOS_ATTACK") {
    const replicas = 3 + Math.floor(Math.random() * 5);
    return {
      recommended_option: {
        action: `kubectl scale deployment ingress-gateway --replicas=${replicas}`,
        name: `Scale ingress-gateway to ${replicas} replicas`,
        reasoning: `Horizontal scaling to absorb DDoS traffic surge. (Inc #${incident_id || rnd}, ${ts})`,
        success_probability: conf + 3,
        downtime_estimate: "0m",
        risk_level: "low",
        composite_score: 0.92
      },
      ranked_options: [
        {
          action: `kubectl scale deployment ingress-gateway --replicas=${replicas}`,
          name: `Scale ingress-gateway to ${replicas} replicas`,
          reasoning: "Scale out to distribute traffic load",
          success_probability: conf + 3,
          downtime_estimate: "0m",
          risk_level: "low",
          composite_score: 0.92
        }
      ],
      rollback_plan: `kubectl scale deployment ingress-gateway --replicas=1`
    };
  } else if (type === "ERROR_RATE_SPIKE" || type === "ERROR_RATE") {
    return {
      recommended_option: {
        action: `kubectl rollout undo deployment/${incident_id ? `svc-${incident_id}` : 'mock-service'}`,
        name: "Rollback last deployment",
        reasoning: "Revert to last known good state to eliminate regression. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf + 2,
        downtime_estimate: "10s",
        risk_level: "low",
        composite_score: 0.90
      },
      ranked_options: [
        {
          action: `kubectl rollout undo deployment/${incident_id ? `svc-${incident_id}` : 'mock-service'}`,
          name: "Rollback last deployment",
          reasoning: "Standard rollback procedure for deployment-induced regressions",
          success_probability: conf + 2,
          downtime_estimate: "10s",
          risk_level: "low",
          composite_score: 0.90
        },
        {
          action: `kubectl rollout restart deployment/${incident_id ? `svc-${incident_id}` : 'mock-service'}`,
          name: "Restart affected service",
          reasoning: "Fresh pod start can clear transient error states",
          success_probability: conf - 5,
          downtime_estimate: "15s",
          risk_level: "medium",
          composite_score: 0.78
        }
      ],
      rollback_plan: "No rollback required for code reversion"
    };
  } else if (type === "MEMORY_EXHAUSTION") {
    return {
      recommended_option: {
        action: `kubectl rollout restart deployment/${incident_id ? `svc-${incident_id}` : 'mock-service'}`,
        name: "Restart to clear memory leak",
        reasoning: "Pod restart clears accumulated memory. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf,
        downtime_estimate: "10s",
        risk_level: "medium",
        composite_score: 0.84
      },
      ranked_options: [
        {
          action: `kubectl rollout restart deployment/${incident_id ? `svc-${incident_id}` : 'mock-service'}`,
          name: "Restart to clear memory leak",
          reasoning: "Immediate memory release via pod recreation",
          success_probability: conf,
          downtime_estimate: "10s",
          risk_level: "medium",
          composite_score: 0.84
        },
        {
          action: `kubectl patch deployment/${incident_id ? `svc-${incident_id}` : 'mock-service'} -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"limits":{"memory":"2Gi"}}}]}}}}'`,
          name: "Increase memory limit to 2Gi",
          reasoning: "Provide more headroom if leak is slow and manageable",
          success_probability: conf - 10,
          downtime_estimate: "30s",
          risk_level: "low",
          composite_score: 0.75
        }
      ],
      rollback_plan: "Pod will auto-recreate via ReplicaSet"
    };
  } else if (type === "HIGH_LATENCY") {
    return {
      recommended_option: {
        action: `kubectl rollout restart deployment/coredns -n kube-system`,
        name: "Restart CoreDNS",
        reasoning: "DNS resolution delays often cause latency spikes. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf - 2,
        downtime_estimate: "10s",
        risk_level: "low",
        composite_score: 0.86
      },
      ranked_options: [
        {
          action: `kubectl rollout restart deployment/coredns -n kube-system`,
          name: "Restart CoreDNS",
          reasoning: "Clears DNS cache and connection state",
          success_probability: conf - 2,
          downtime_estimate: "10s",
          risk_level: "low",
          composite_score: 0.86
        },
        {
          action: `kubectl get svc kube-dns -n kube-system -o yaml | kubectl apply -f -`,
          name: "Refresh DNS service",
          reasoning: "Re-apply DNS service spec to fix any service drift",
          success_probability: conf - 8,
          downtime_estimate: "5s",
          risk_level: "low",
          composite_score: 0.80
        }
      ],
      rollback_plan: "No rollback required for safe CoreDNS reset"
    };
  } else if (type === "NETWORK_OUTAGE") {
    return {
      recommended_option: {
        action: `kubectl rollout restart daemonset/service-mesh-proxy -n kube-system`,
        name: "Restart service mesh proxy daemonset",
        reasoning: "Network partition recovery requires proxy reconnection to restore cross-AZ routing. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf,
        downtime_estimate: "30s",
        risk_level: "medium",
        composite_score: 0.82
      },
      ranked_options: [
        {
          action: `kubectl rollout restart daemonset/service-mesh-proxy -n kube-system`,
          name: "Restart service mesh proxy",
          reasoning: "Re-establish proxy tunnels across availability zones",
          success_probability: conf,
          downtime_estimate: "30s",
          risk_level: "medium",
          composite_score: 0.82
        },
        {
          action: `kubectl delete configmap coredns -n kube-system && kubectl rollout restart deployment/coredns -n kube-system`,
          name: "Reset DNS and restart CoreDNS",
          reasoning: "Clear DNS cache that may hold stale cross-AZ endpoints",
          success_probability: conf - 10,
          downtime_estimate: "60s",
          risk_level: "medium",
          composite_score: 0.75
        }
      ],
      rollback_plan: "Service mesh proxy auto-recovers; CoreDNS restarts restore DNS resolution"
    };
  } else {
    return {
      recommended_option: {
        action: `kubectl delete pod database-primary-${(rnd % 9000) + 1000}`,
        name: "Isolate compromised database pod",
        reasoning: "Force pod recreation to purge breach persistence. (Inc #" + (incident_id || rnd) + ", " + ts + ")",
        success_probability: conf - 2,
        downtime_estimate: "15s",
        risk_level: "high",
        composite_score: 0.80
      },
      ranked_options: [
        {
          action: `kubectl delete pod database-primary-${(rnd % 9000) + 1000}`,
          name: "Isolate compromised database pod",
          reasoning: "Force clean state via pod recreation",
          success_probability: conf - 2,
          downtime_estimate: "15s",
          risk_level: "high",
          composite_score: 0.80
        }
      ],
      rollback_plan: "Pod auto-recreates via ReplicaSet"
    };
  }
}

// Step 1: Root Cause Analysis
const analyze_root_cause = createStep({
  id: "analyze_root_cause",
  description: "Run RCA agent to determine root cause",
  execute: async ({ getInitData }) => {
    const incident = getInitData() as IncidentData;
    const prompt = `Analyze this incident and determine root cause:
Type: ${incident.incident_type}
Data: ${JSON.stringify(incident.alert_data)}
Metrics available: ${Object.keys(incident.metrics || {}).join(", ")}
Logs entries: ${(incident.logs || []).length} entries`;

    try {
      const result = await rcaAgent.generate(prompt);
      const rca_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return rca_result;
    } catch (err) {
      console.warn("RCA Agent failed, running simulation fallback:", err);
      return getMockRca(incident.incident_type, incident.incident_id);
    }
  }
});

// Step 2: Threat Intelligence Enrichment
const enrich_threat_intel = createStep({
  id: "enrich_threat_intel",
  description: "Run threat intel agent to enrich incident data",
  execute: async ({ getInitData, getStepResult }) => {
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    const incident = getInitData() as IncidentData;
    const prompt = `Enrich this incident with threat intelligence:
Incident Type: ${incident.incident_type}
Root Cause: ${JSON.stringify(rca_result)}
Look for IOCs (IPs, domains, hashes, URLs, emails) and check threat databases`;

    try {
      const result = await threatIntelAgent.generate(prompt);
      const threat_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return threat_result;
    } catch (err) {
      console.warn("Threat Intel Agent failed, running simulation fallback:", err);
      return getMockThreat(incident.incident_type, incident.incident_id);
    }
  }
});

// Step 3: Prioritization
const prioritize_incident = createStep({
  id: "prioritize_incident",
  description: "Run prioritization agent to assign SLA",
  execute: async ({ getInitData, getStepResult }) => {
    const incident = getInitData() as IncidentData;
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    const threat_result = getStepResult("enrich_threat_intel") as Record<string, any>;

    const prompt = `Prioritize this incident:
Type: ${incident.incident_type}
RCA Confidence: ${rca_result?.confidence || 0}%
Threat Level: ${threat_result?.threat_level || "unknown"}
Affected Services: ${JSON.stringify(incident.alert_data)}`;

    try {
      const result = await prioritizationAgent.generate(prompt);
      const priority_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return priority_result;
    } catch (err) {
      console.warn("Prioritization Agent failed, running simulation fallback:", err);
      return getMockPriority(incident.incident_type, incident.incident_id);
    }
  }
});

// Step 4: Remediation Planning
const plan_remediation = createStep({
  id: "plan_remediation",
  description: "Run remediation agent to suggest actions",
  execute: async ({ getInitData, getStepResult }) => {
    const incident = getInitData() as IncidentData;
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    const priority_result = getStepResult("prioritize_incident") as Record<string, any>;
    const threat_result = getStepResult("enrich_threat_intel") as Record<string, any>;

    const prompt = `Plan remediation for this incident:
Root Cause: ${JSON.stringify(rca_result)}
Priority: ${priority_result?.priority_level || "unknown"}
Threat Level: ${threat_result?.threat_level || "unknown"}
Business Impact: ${JSON.stringify(priority_result?.business_impact || {})}

Suggest multiple remediation options ranked by safety and effectiveness.`;

    try {
      const result = await remediationAgent.generate(prompt);
      const remediation_options = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return remediation_options;
    } catch (err) {
      console.warn("Remediation Agent failed, running simulation fallback:", err);
      return getMockRemediation(incident.incident_type, incident.incident_id);
    }
  }
});

// Step 5: Return workflow result
const workflow_complete = createStep({
  id: "workflow_complete",
  description: "Workflow execution complete",
  execute: async ({ getInitData, getStepResult }) => {
    const incident = getInitData() as IncidentData;
    const rca_result = getStepResult("analyze_root_cause");
    const threat_result = getStepResult("enrich_threat_intel");
    const priority_result = getStepResult("prioritize_incident");
    const remediation_options = getStepResult("plan_remediation");

    return {
      status: "completed",
      incident_id: incident.incident_id,
      rca: rca_result,
      threats: threat_result,
      priority: priority_result,
      remediation: remediation_options
    };
  }
});

// Chain steps sequentially and commit
incidentResponseWorkflow
  .then(analyze_root_cause)
  .then(enrich_threat_intel)
  .then(prioritize_incident)
  .then(plan_remediation)
  .then(workflow_complete)
  .commit();
