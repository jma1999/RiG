import { useCallback, useEffect, useRef, useState } from "react"
import ForceGraph2D from "react-force-graph-2d"
import { API_BASE } from "@/lib/env"

interface GraphNode {
  id: string
  name: string
  type: string
  friendlyType?: string
  source?: string
  degree?: number
}

interface GraphLink {
  source: string
  target: string
  type: string
  friendlyType?: string
}

interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

interface GraphPanelProps {
  query?: string
  onNodeClick?: (node: GraphNode) => void
  className?: string
}

const FRIENDLY_TYPES: Record<string, string> = {
  IfcDistributionPort: "Distribution Port",
  IfcFlowTerminal: "Terminal",
  IfcFlowSegment: "Duct Segment",
  IfcFlowFitting: "Duct Fitting",
  IfcSpace: "Space",
  IfcBuildingStorey: "Building Level",
  IfcValve: "Valve",
  IfcFan: "Fan",
}

const FRIENDLY_RELATIONS: Record<string, string> = {
  CONNECTED_TO: "Connected To",
  FEEDS: "Feeds",
  CONTAINS: "Contains",
  ASSIGNED_TO_SYSTEM: "Assigned To System",
}

const friendlyType = (t?: string) => {
  if (!t) return t
  return FRIENDLY_TYPES[t] ?? t.replace(/([a-z0-9])([A-Z])/g, "$1 $2")
}

const friendlyRelation = (r: string) => FRIENDLY_RELATIONS[r] ?? r

export default function GraphPanel({ query, onNodeClick, className = "" }: GraphPanelProps) {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })

  const fetchGraphData = useCallback(async (searchQuery: string) => {
    if (!searchQuery?.trim()) {
      setGraphData({ nodes: [], links: [] })
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(searchQuery)}&k=20&hops=2`)
      const data = await res.json()
      
      if (!res.ok) throw new Error(data.error || "Search failed")

      const nodes: GraphNode[] = []
      const links: GraphLink[] = []
      const seen = new Set<string>()

      // Process subgraphs from search results
      data.subgraphs?.forEach((sg: any) => {
        sg.nodes?.forEach((n: any) => {
          if (seen.has(n.id)) return
          seen.add(n.id)
          nodes.push({
            id: n.id,
            name: n.name || "(unnamed)",
            type: n.type || "",
            friendlyType: friendlyType(n.type || ""),
            source: n.source || "",
          })
        })
        
        sg.edges?.forEach((e: any) => {
          links.push({
            source: e.src,
            target: e.dst,
            type: e.type,
            friendlyType: friendlyRelation(e.type),
          })
        })
      })

      // Calculate node degrees
      const degree: Record<string, number> = {}
      links.forEach((edge) => {
        if (edge.source) degree[edge.source] = (degree[edge.source] || 0) + 1
        if (edge.target) degree[edge.target] = (degree[edge.target] || 0) + 1
      })

      const enrichedNodes = nodes.map((n) => ({ ...n, degree: degree[n.id] || 0 }))

      setGraphData({ nodes: enrichedNodes, links })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph data")
      setGraphData({ nodes: [], links: [] })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (query) {
      fetchGraphData(query)
    }
  }, [query, fetchGraphData])

  // Resize observer
  useEffect(() => {
    const el = containerRef.current
    if (!el || typeof ResizeObserver === "undefined") return

    const updateSize = () => {
      setSize({ width: el.clientWidth, height: el.clientHeight })
    }
    updateSize()

    const observer = new ResizeObserver(() => updateSize())
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const drawNode = useCallback((node: any, ctx: CanvasRenderingContext2D, scale: number) => {
    const radius = 5 + Math.log((node.degree || 1) + 1) * 2
    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false)
    
    // Color by type
    ctx.fillStyle = node.type?.startsWith("IfcFlow")
      ? "#38bdf8"
      : node.type?.startsWith("IfcSpace")
      ? "#34d399"
      : "#e2e8f0"
    
    ctx.fill()
    ctx.font = `${Math.max(11 / scale, 8)}px Inter, system-ui`
    ctx.fillStyle = "#0f172a"
    const label = node.friendlyType || node.name?.slice(0, 36) || node.id
    ctx.fillText(label, node.x + radius + 4, node.y + 4)
  }, [])

  if (loading) {
    return (
      <div className={`h-96 rounded-xl border flex items-center justify-center ${className}`}>
        <div className="text-sm text-muted-foreground">Loading graph...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`h-96 rounded-xl border flex items-center justify-center ${className}`}>
        <div className="text-sm text-destructive">Error: {error}</div>
      </div>
    )
  }

  if (!graphData.nodes.length) {
    return (
      <div className={`h-96 rounded-xl border flex items-center justify-center ${className}`}>
        <div className="text-sm text-muted-foreground">
          {query ? "No results found" : "Enter a search query to see the graph"}
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} className={`h-96 rounded-xl border ${className}`}>
      {size.width > 0 && size.height > 0 && (
        <ForceGraph2D
          graphData={graphData}
          nodeId="id"
          nodeCanvasObject={drawNode}
          linkDirectionalArrowLength={4}
          linkColor={() => "#94a3b8"}
          onNodeClick={onNodeClick}
          width={size.width}
          height={size.height}
        />
      )}
    </div>
  )
}
