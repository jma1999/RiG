import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { API_BASE } from "@/lib/env";
import { 
  Building2, 
  Users, 
  DollarSign, 
  Wrench, 
  Calendar, 
  Network, 
  Activity,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Link as LinkIcon
} from "lucide-react";

export default function EnterpriseView() {
  const [domains, setDomains] = useState([]);
  const [selectedDomain, setSelectedDomain] = useState(null);
  const [domainData, setDomainData] = useState(null);
  const [crossDomainQuery, setCrossDomainQuery] = useState("");
  const [crossDomainResults, setCrossDomainResults] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDomains();
  }, []);

  useEffect(() => {
    if (selectedDomain) {
      loadDomainContract(selectedDomain);
    }
  }, [selectedDomain]);

  const loadDomains = async () => {
    try {
      const res = await fetch(`${API_BASE}/enterprise/domains`);
      if (res.ok) {
        const data = await res.json();
        setDomains(data.domains || []);
      }
    } catch (error) {
      console.error("Failed to load domains:", error);
    }
  };

  const loadDomainContract = async (domain) => {
    try {
      const res = await fetch(`${API_BASE}/enterprise/contracts/${domain}`);
      if (res.ok) {
        const data = await res.json();
        setDomainData(data);
      }
    } catch (error) {
      console.error("Failed to load domain contract:", error);
    }
  };

  const handleCrossDomainSearch = async () => {
    if (!crossDomainQuery.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/enterprise/cross-domain/equipment?entity_id=${encodeURIComponent(crossDomainQuery)}&domains=${domains.join(",")}`
      );
      if (res.ok) {
        const data = await res.json();
        setCrossDomainResults(data);
      }
    } catch (error) {
      console.error("Cross-domain search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const getDomainIcon = (domain) => {
    const icons = {
      controls: Activity,
      finance: DollarSign,
      hr: Users,
      workorders: Wrench,
      scheduling: Calendar,
      net: Network,
      space: Building2
    };
    return icons[domain] || Building2;
  };

  const getDomainColor = (domain) => {
    const colors = {
      controls: "bg-blue-600",
      finance: "bg-green-600",
      hr: "bg-purple-600",
      workorders: "bg-orange-600",
      scheduling: "bg-pink-600",
      net: "bg-cyan-600",
      space: "bg-gray-600"
    };
    return colors[domain] || "bg-gray-600";
  };

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">
            Enterprise Facilities Graph
          </h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            Cross-domain integration: Controls, HR, Finance, Assets, Scheduling, Network
          </p>
        </div>
        <Badge className="bg-purple-600 text-white">
          <LinkIcon className="h-3 w-3 mr-1" />
          Multi-Domain
        </Badge>
      </div>

      {/* Domain Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {domains.map((domain) => {
          const Icon = getDomainIcon(domain);
          const color = getDomainColor(domain);
          return (
            <Card
              key={domain}
              className={`palantir-card cursor-pointer transition-all ${
                selectedDomain === domain ? "ring-2 ring-[var(--palantir-text-accent)]" : ""
              }`}
              onClick={() => setSelectedDomain(domain)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`${color} p-2 rounded-lg`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--palantir-text-primary)] capitalize">
                        {domain}
                      </p>
                      <p className="text-xs text-[var(--palantir-text-muted)]">
                        {domain === "controls" && "BACnet, BMS"}
                        {domain === "finance" && "EBS/Kuali"}
                        {domain === "hr" && "Workday"}
                        {domain === "workorders" && "Maximo"}
                        {domain === "scheduling" && "Office365"}
                        {domain === "net" && "Network Topology"}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Cross-Domain Search */}
      <Card className="palantir-card-elevated">
        <CardHeader>
          <CardTitle>Cross-Domain Entity Search</CardTitle>
          <p className="text-sm text-[var(--palantir-text-muted)]">
            Find entities across multiple domains (e.g., "AHU-3" finds equipment, asset, responsible person)
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Enter entity ID or name (e.g., AHU-3, Conference_A, WD-EMP-12345)"
              value={crossDomainQuery}
              onChange={(e) => setCrossDomainQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleCrossDomainSearch()}
            />
            <Button
              onClick={handleCrossDomainSearch}
              disabled={loading || !crossDomainQuery.trim()}
              className="bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)]"
            >
              {loading ? "Searching..." : "Search"}
            </Button>
          </div>

          {crossDomainResults && (
            <div className="mt-4 space-y-2">
              <h3 className="font-semibold text-[var(--palantir-text-primary)]">
                Results for: {crossDomainResults.entity_id}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {crossDomainResults.domains_queried.map((domain) => (
                  <Badge key={domain} className={`${getDomainColor(domain)} text-white`}>
                    {domain}
                  </Badge>
                ))}
              </div>
              <pre className="bg-[var(--palantir-bg-secondary)] p-4 rounded-lg text-xs overflow-auto max-h-64">
                {JSON.stringify(crossDomainResults.results, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Selected Domain Contract Details */}
      {selectedDomain && domainData && (
        <Card className="palantir-card-elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 capitalize">
                  {getDomainIcon(selectedDomain) && (
                    <div className={`${getDomainColor(selectedDomain)} p-2 rounded-lg`}>
                      {React.createElement(getDomainIcon(selectedDomain), {
                        className: "h-5 w-5 text-white"
                      })}
                    </div>
                  )}
                  {selectedDomain} Domain Contract
                </CardTitle>
                <p className="text-sm text-[var(--palantir-text-muted)] mt-2">
                  Source: {domainData.source}
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-2">Scope</h3>
              <div className="bg-[var(--palantir-bg-secondary)] p-3 rounded-lg">
                <p className="text-sm">
                  <strong>Entities:</strong> {domainData.scope?.entities?.join(", ")}
                </p>
                <p className="text-sm mt-1">
                  <strong>Primary Keys:</strong> {domainData.scope?.primary_keys?.join(", ")}
                </p>
                <p className="text-sm mt-1">
                  <strong>IRI Policy:</strong> {domainData.scope?.iri_policy}
                </p>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-2">Freshness & Cadence</h3>
              <div className="bg-[var(--palantir-bg-secondary)] p-3 rounded-lg">
                <p className="text-sm">
                  <strong>Mode:</strong> {domainData.freshness?.mode}
                </p>
                {domainData.freshness?.push_latency && (
                  <p className="text-sm mt-1">
                    <strong>Push Latency:</strong> {domainData.freshness.push_latency}
                  </p>
                )}
                {domainData.freshness?.pull_latency && (
                  <p className="text-sm mt-1">
                    <strong>Pull Latency:</strong> {domainData.freshness.pull_latency}
                  </p>
                )}
                {domainData.freshness?.latency && (
                  <p className="text-sm mt-1">
                    <strong>Latency:</strong> {domainData.freshness.latency}
                  </p>
                )}
                <p className="text-sm mt-1">
                  <strong>Cadence:</strong> {domainData.freshness?.cadence}
                </p>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-2">SLAs</h3>
              <div className="bg-[var(--palantir-bg-secondary)] p-3 rounded-lg">
                <p className="text-sm">
                  <strong>Uptime:</strong> {domainData.slas?.uptime}
                </p>
                <p className="text-sm mt-1">
                  <strong>Fallback:</strong> {domainData.slas?.fallback}
                </p>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-2">Provenance & Security</h3>
              <div className="bg-[var(--palantir-bg-secondary)] p-3 rounded-lg">
                <p className="text-sm">
                  <strong>Writer:</strong> {domainData.provenance?.writer}
                </p>
                <p className="text-sm mt-1">
                  <strong>Security:</strong> {domainData.provenance?.security}
                </p>
                {domainData.provenance?.pii_fields && domainData.provenance.pii_fields.length > 0 && (
                  <p className="text-sm mt-1">
                    <strong>PII Fields:</strong> {domainData.provenance.pii_fields.join(", ")} (hashed/excluded)
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="palantir-card cursor-pointer hover:ring-2 hover:ring-[var(--palantir-text-accent)] transition-all">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-[var(--palantir-text-accent)]" />
              <div>
                <p className="font-semibold text-[var(--palantir-text-primary)]">FDD Faults</p>
                <p className="text-xs text-[var(--palantir-text-muted)]">
                  View open faults with root causes
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card cursor-pointer hover:ring-2 hover:ring-[var(--palantir-text-accent)] transition-all">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Users className="h-8 w-8 text-purple-600" />
              <div>
                <p className="font-semibold text-[var(--palantir-text-primary)]">Responsibility Chains</p>
                <p className="text-xs text-[var(--palantir-text-muted)]">
                  Who's responsible for what
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card cursor-pointer hover:ring-2 hover:ring-[var(--palantir-text-accent)] transition-all">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <DollarSign className="h-8 w-8 text-green-600" />
              <div>
                <p className="font-semibold text-[var(--palantir-text-primary)]">Billing & Finance</p>
                <p className="text-xs text-[var(--palantir-text-muted)]">
                  Meter billing and cost allocation
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

