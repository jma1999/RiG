import { useEffect, useRef } from "react"
import { IfcViewerAPI } from "web-ifc-viewer"

export default function IfcViewer() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<IfcViewerAPI | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    // init the viewer
    const viewer = new IfcViewerAPI({
      container: containerRef.current,
      backgroundColor: new (window as any).THREE.Color(0x0a0a0a),
    })
    viewerRef.current = viewer

    // point to the wasm you copied to /public/ifc
    viewer.IFC.setWasmPath("/ifc/")

    // optional: grid + axes
    viewer.axes.setAxes()
    viewer.grid.setGrid()

    // enable basic picking/highlight
    viewer.IFC.selector.prePickIfcItem = true

    return () => {
      // cleanup
      viewerRef.current?.dispose?.()
      viewerRef.current = null
    }
  }, [])

  return <div ref={containerRef} className="h-96 w-full rounded-xl border" />
}
