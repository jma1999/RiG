import ForceGraph2D from "react-force-graph-2d"

const nodes = [
  { id: "Building" }, { id: "Storey" }, { id: "Space" }, { id: "Wall" }, { id: "Door" }
]
const links = [
  { source: "Building", target: "Storey" },
  { source: "Storey", target: "Space" },
  { source: "Space", target: "Wall" },
  { source: "Wall", target: "Door" },
]

export default function GraphPanel() {
  return (
    <div className="h-96 rounded-xl border">
      <ForceGraph2D
        graphData={{ nodes, links }}
        nodeAutoColorBy="id"
        nodeLabel="id"
      />
    </div>
  )
}
