Base for twin data:      https://example.com/ifc/
Custom namespace (ex):   https://example.com/rig#
Prefix: ex:

ex:Equip_FlowTerminal_1      → equipment for that IFC element
ex:Point_SAT_FlowTerminal_1  → supply air temperature point
ex:Series_SAT_FlowTerminal_1 → logical handle for the time series

ex:Equip_FlowTerminal_1
  a 223:Equipment
  a brick:Air_Terminal
  (aligned to IFC)
  related IFC element: inst:IfcFlowTerminal_123456

ex:Point_SAT_FlowTerminal_1
  a 223:SensorPoint
  a brick:Supply_Air_Temperature_Sensor
  a brick:Sensor
  a sosa:Sensor
  qudt:unit          unit:DegreeCelsius
  brick:isPointOf    ex:Equip_FlowTerminal_1

ex:Series_SAT_FlowTerminal_1
  a ex:TimeSeries
  ex:forPoint         ex:Point_SAT_FlowTerminal_1
  ex:storageBackend   "timescale"            (for example)
  ex:timescaleTable   "point_timeseries"
  ex:timescaleKey     "SAT_FlowTerminal_1"

ex:Equip_FlowTerminal_1
  ex:physicalRealization   inst:IfcFlowTerminal_123456

ex:physicalRealization

Equipment → IFC element → geometry / placement / storey
