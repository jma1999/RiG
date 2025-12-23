import React, { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
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
      controls: "bg-[var(--palantir-info)]/20 text-[var(--palantir-info)] border border-[var(--palantir-info)]/30",
      finance: "bg-[var(--palantir-success)]/20 text-[var(--palantir-success)] border border-[var(--palantir-success)]/30",
      hr: "bg-[var(--palantir-info)]/20 text-[var(--palantir-info)] border border-[var(--palantir-info)]/30",
      workorders: "bg-[var(--palantir-warning)]/20 text-[var(--palantir-warning)] border border-[var(--palantir-warning)]/30",
      scheduling: "bg-[var(--palantir-info)]/20 text-[var(--palantir-info)] border border-[var(--palantir-info)]/30",
      net: "bg-[var(--palantir-info)]/20 text-[var(--palantir-info)] border border-[var(--palantir-info)]/30",
      space: "bg-[var(--palantir-text-muted)]/20 text-[var(--palantir-text-secondary)] border border-[var(--palantir-border-primary)]"
    };
    return colors[domain] || "bg-[var(--palantir-text-muted)]/20 text-[var(--palantir-text-secondary)] border border-[var(--palantir-border-primary)]";
  };

  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-6 overflow-y-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-3">
            <Network className="text-nexus-accent" />
            ENTERPRISE INTEGRATIONS
          </h2>
          <p className="text-sm text-slate-400 mt-1 font-mono">
             HOLISTIC IWMS: MAXIMO • KUALI • WORKDAY • OFFICE365 • CALENDLY
          </p>
        </div>
        <Badge className="bg-nexus-accent/20 text-nexus-accent border border-nexus-accent/30">
          <LinkIcon className="h-3 w-3 mr-1" />
          Multi-Domain
        </Badge>
      </div>

      {/* Domain Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {[
          { id: 'workorders', name: 'Maximo', icon: Wrench, desc: 'Asset Management & Work Orders', color: 'bg-nexus-warning/20 text-nexus-warning border-nexus-warning/30' },
          { id: 'finance', name: 'Kuali', icon: DollarSign, desc: 'Financial Management & Billing', color: 'bg-nexus-success/20 text-nexus-success border-nexus-success/30' },
          { id: 'hr', name: 'Workday', icon: Users, desc: 'HR & Organizational Structure', color: 'bg-nexus-accent/20 text-nexus-accent border-nexus-accent/30' },
          { id: 'scheduling', name: 'Office365', icon: Calendar, desc: 'Calendar & Scheduling', color: 'bg-nexus-accent/20 text-nexus-accent border-nexus-accent/30' },
          { id: 'scheduling', name: 'Calendly', icon: Calendar, desc: 'Meeting Scheduling', color: 'bg-nexus-info/20 text-nexus-info border-nexus-info/30' },
          { id: 'controls', name: 'BACnet/BMS', icon: Activity, desc: 'Building Controls', color: 'bg-nexus-accent/20 text-nexus-accent border-nexus-accent/30' }
        ].map((integration) => {
          const Icon = integration.icon;
          return (
            <div
              key={integration.id + integration.name}
              className={`bg-nexus-900/50 border ${integration.color} rounded-xl p-4 cursor-pointer transition-all hover:bg-nexus-900 hover:scale-105`}
              onClick={() => setSelectedDomain(integration.id)}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`${integration.color} p-2 rounded-lg`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-white">
                    {integration.name}
                  </p>
                  <p className="text-xs text-slate-400">
                    {integration.desc}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Domain Details */}
      {selectedDomain && domainData && (
        <div className="bg-nexus-900/50 border border-nexus-700 rounded-xl p-6 mb-6">
          <h3 className="text-lg font-bold text-white mb-4 capitalize">{selectedDomain} Contract</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-400">Scope:</span>
              <span className="text-white ml-2">{domainData.scope || 'N/A'}</span>
            </div>
            <div>
              <span className="text-slate-400">Freshness:</span>
              <span className="text-white ml-2">{domainData.freshness || 'N/A'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Legacy domain cards for backward compatibility */}
      {domains.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {domains.map((domain) => {
            const Icon = getDomainIcon(domain);
            const color = getDomainColor(domain);
            return (
              <div
                key={domain}
                className={`bg-nexus-900/50 border ${color} rounded-xl p-4 cursor-pointer transition-all ${
                  selectedDomain === domain ? "ring-2 ring-nexus-accent" : ""
                }`}
                onClick={() => setSelectedDomain(domain)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`${color} p-2 rounded-lg`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-semibold text-white capitalize">
                        {domain}
                      </p>
                      <p className="text-xs text-slate-400">
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
              </div>
            );
          })}
        </div>
      )}

      {/* Cross-Domain Search */}
      <div className="bg-nexus-900/50 border border-nexus-700 rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-2">Cross-Domain Entity Search</h3>
        <p className="text-sm text-slate-400 mb-4">
          Find entities across multiple domains (e.g., "AHU-3" finds equipment, asset, responsible person)
        </p>
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter entity ID or name (e.g., AHU-3, Conference_A, WD-EMP-12345)"
              value={crossDomainQuery}
              onChange={(e) => setCrossDomainQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleCrossDomainSearch()}
              className="flex-1 bg-nexus-800 text-white placeholder:text-slate-500 border border-nexus-700 rounded-lg px-4 py-2 focus:outline-none focus:border-nexus-accent"
            />
            <button
              onClick={handleCrossDomainSearch}
              disabled={loading || !crossDomainQuery.trim()}
              className="bg-nexus-accent text-nexus-900 px-4 py-2 rounded-lg font-medium hover:bg-nexus-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>

          {crossDomainResults && (
            <div className="mt-4 space-y-2">
              <h3 className="font-semibold text-white">
                Results for: {crossDomainResults.entity_id}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {crossDomainResults.domains_queried?.map((domain) => (
                  <span key={domain} className={`${getDomainColor(domain)} px-3 py-1 rounded text-xs font-medium`}>
                    {domain}
                  </span>
                ))}
              </div>
              <pre className="bg-nexus-900 p-4 rounded-lg text-xs overflow-auto max-h-64 text-slate-300 border border-nexus-700">
                {JSON.stringify(crossDomainResults.results, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Selected Domain Contract Details */}
      {selectedDomain && domainData && (
        <div className="bg-nexus-900/50 border border-nexus-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2 capitalize">
                {getDomainIcon(selectedDomain) && (
                  <div className={`${getDomainColor(selectedDomain)} p-2 rounded-lg`}>
                    {React.createElement(getDomainIcon(selectedDomain), {
                      className: "h-5 w-5"
                    })}
                  </div>
                )}
                {selectedDomain} Domain Contract
              </h3>
              <p className="text-sm text-slate-400 mt-2">
                Source: {domainData.source}
              </p>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-white mb-2">Scope</h3>
              <div className="bg-nexus-900 p-3 rounded-lg border border-nexus-700">
                <p className="text-sm text-slate-300">
                  <strong className="text-white">Entities:</strong> {domainData.scope?.entities?.join(", ") || 'N/A'}
                </p>
                <p className="text-sm mt-1 text-slate-300">
                  <strong className="text-white">Primary Keys:</strong> {domainData.scope?.primary_keys?.join(", ") || 'N/A'}
                </p>
                <p className="text-sm mt-1 text-slate-300">
                  <strong className="text-white">IRI Policy:</strong> {domainData.scope?.iri_policy || 'N/A'}
                </p>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-white mb-2">Freshness & Cadence</h3>
              <div className="bg-nexus-900 p-3 rounded-lg border border-nexus-700">
                <p className="text-sm text-slate-300">
                  <strong className="text-white">Mode:</strong> {domainData.freshness?.mode || 'N/A'}
                </p>
                {domainData.freshness?.push_latency && (
                  <p className="text-sm mt-1 text-slate-300">
                    <strong className="text-white">Push Latency:</strong> {domainData.freshness.push_latency}
                  </p>
                )}
                {domainData.freshness?.pull_latency && (
                  <p className="text-sm mt-1 text-slate-300">
                    <strong className="text-white">Pull Latency:</strong> {domainData.freshness.pull_latency}
                  </p>
                )}
                {domainData.freshness?.latency && (
                  <p className="text-sm mt-1 text-slate-300">
                    <strong className="text-white">Latency:</strong> {domainData.freshness.latency}
                  </p>
                )}
                <p className="text-sm mt-1 text-slate-300">
                  <strong className="text-white">Cadence:</strong> {domainData.freshness?.cadence || 'N/A'}
                </p>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-white mb-2">SLAs</h3>
              <div className="bg-nexus-900 p-3 rounded-lg border border-nexus-700">
                <p className="text-sm text-slate-300">
                  <strong className="text-white">Uptime:</strong> {domainData.slas?.uptime || 'N/A'}
                </p>
                <p className="text-sm mt-1 text-slate-300">
                  <strong className="text-white">Fallback:</strong> {domainData.slas?.fallback || 'N/A'}
                </p>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-white mb-2">Provenance & Security</h3>
              <div className="bg-nexus-900 p-3 rounded-lg border border-nexus-700">
                <p className="text-sm text-slate-300">
                  <strong className="text-white">Writer:</strong> {domainData.provenance?.writer || 'N/A'}
                </p>
                <p className="text-sm mt-1 text-slate-300">
                  <strong className="text-white">Security:</strong> {domainData.provenance?.security || 'N/A'}
                </p>
                {domainData.provenance?.pii_fields && domainData.provenance.pii_fields.length > 0 && (
                  <p className="text-sm mt-1 text-slate-300">
                    <strong className="text-white">PII Fields:</strong> {domainData.provenance.pii_fields.join(", ")} (hashed/excluded)
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        <div className="bg-nexus-900/50 border border-nexus-700 rounded-xl p-4 cursor-pointer hover:ring-2 hover:ring-nexus-accent transition-all">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-8 w-8 text-nexus-accent" />
            <div>
              <p className="font-semibold text-white">FDD Faults</p>
              <p className="text-xs text-slate-400">
                View open faults with root causes
              </p>
            </div>
          </div>
        </div>

        <div className="bg-nexus-900/50 border border-nexus-700 rounded-xl p-4 cursor-pointer hover:ring-2 hover:ring-nexus-accent transition-all">
          <div className="flex items-center gap-3">
            <Users className="h-8 w-8 text-nexus-accent" />
            <div>
              <p className="font-semibold text-white">Responsibility Chains</p>
              <p className="text-xs text-slate-400">
                Who's responsible for what
              </p>
            </div>
          </div>
        </div>

        <div className="bg-nexus-900/50 border border-nexus-700 rounded-xl p-4 cursor-pointer hover:ring-2 hover:ring-nexus-accent transition-all">
          <div className="flex items-center gap-3">
            <DollarSign className="h-8 w-8 text-nexus-success" />
            <div>
              <p className="font-semibold text-white">Billing & Finance</p>
              <p className="text-xs text-slate-400">
                Meter billing and cost allocation
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

