import IfcViewer from "@/components/IfcViewer"
import GraphPanel from "@/components/GraphPanel"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export default function App() {
  return (
    <div className="min-h-dvh bg-background text-foreground p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <Tabs defaultValue="chat">
          <TabsList className="grid grid-cols-3 w-full">
            <TabsTrigger value="chat">Chat</TabsTrigger>
            <TabsTrigger value="graph">Graph</TabsTrigger>
            <TabsTrigger value="cmms">CMMS</TabsTrigger>
          </TabsList>

          <TabsContent value="chat">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  IFC Viewer <Badge>alpha</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <IfcViewer />
                <div className="flex gap-2">
                  <Input placeholder="Ask about this model…" className="flex-1" />
                  <Button>Send</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="graph">
            <Card>
              <CardHeader><CardTitle>Neo4j Relationships (demo)</CardTitle></CardHeader>
              <CardContent><GraphPanel /></CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="cmms">
            <Card>
              <CardContent className="h-96 flex items-center justify-center">
                CMMS Panel
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
