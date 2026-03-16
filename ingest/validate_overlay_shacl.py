from pathlib import Path
from pyshacl import validate
from rdflib import Namespace, RDF

SH = Namespace("http://www.w3.org/ns/shacl#")

data_file = Path("data/processed/overlay/CASE_office_norm.ttl")
shapes_file = Path("data/shapes/CASE_office_normShapes.ttl")

conforms, results_graph, results_text = validate(
    data_graph=str(data_file),
    shacl_graph=str(shapes_file),
    data_graph_format="turtle",
    shacl_graph_format="turtle",
    inference="none",
    abort_on_first=False,
    allow_infos=True,
    allow_warnings=True,
    meta_shacl=False,
    advanced=True,
    js=False,
    debug=False,
)

print("\n" + "=" * 80)
print("SHACL VALIDATION RESULT")
print("=" * 80)
print("CONFORMS:", conforms)
print("=" * 80)

if conforms:
    print("Overlay graph passed SHACL validation.")
else:
    print("Overlay graph failed SHACL validation.\n")
    for result in results_graph.subjects(RDF.type, SH.ValidationResult):
        focus = results_graph.value(result, SH.focusNode)
        source_shape = results_graph.value(result, SH.sourceShape)
        path = results_graph.value(result, SH.resultPath)
        message = results_graph.value(result, SH.resultMessage)
        severity = results_graph.value(result, SH.resultSeverity)
        value = results_graph.value(result, SH.value)

        print("-" * 60)
        print("Focus Node   :", focus)
        print("Source Shape :", source_shape)
        print("Path         :", path)
        print("Value        :", value)
        print("Severity     :", severity)
        print("Message      :", message)

print("\nFull text report:\n")
print(results_text)

results_graph.serialize("data/processed/overlay/CASE_office_overlay_validation_report.ttl", format="turtle")
print("\nSaved TTL validation report to data/processed/overlay/CASE_office_overlay_validation_report.ttl")