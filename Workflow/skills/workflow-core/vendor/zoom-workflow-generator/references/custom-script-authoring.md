# Custom Script authoring

This file owns selection, PlanIR shape, composition, Python authoring, and safety guidance for a
`custom_script` step. Read it only when the graph includes that step.

## When to use Custom Script

Use Custom Script when the workflow needs information that is not directly available but can be
reasonably and deterministically derived from declared system variables or upstream node outputs
through procedural computation, extraction, parsing, normalization, filtering, aggregation,
calculation, restructuring, or serialization. Prefer it when the accuracy of that derived value
materially affects later workflow behavior.

Do not use Custom Script to obtain external information, call connectors, make subjective or semantic
judgments, compensate for missing source data, or infer facts absent from declared inputs. When local
procedural computation cannot reliably produce the requested result, fall back to an AI Reasoning
node with the necessary declared inputs and capabilities.

Custom Script should usually not terminate a workflow. It computes data but does not deliver that
data to the user. Add an appropriate downstream node to render, send, write, or otherwise deliver the
result. If the derived data is accuracy-critical, gate downstream writes or deliveries on
`code_succeeded isTrue`.

## PlanIR shape

```json
{
  "id": "derive",
  "kind": "custom_script",
  "intent": "Derive an accurate normalized report from the available records.",
  "inputs": [
    {
      "name": "records",
      "source": "{{reason.records}}",
      "type": "array",
      "description": "Records available from the upstream step",
      "required": true
    }
  ],
  "outputs": [
    {
      "name": "report_json",
      "type": "string",
      "description": "Serialized structured report for downstream rendering",
      "required": true
    },
    {
      "name": "code_succeeded",
      "type": "boolean",
      "description": "Whether the accuracy-critical derivation completed successfully",
      "required": true
    },
    {
      "name": "error_message",
      "type": "string",
      "description": "Non-sensitive failure reason, empty on success",
      "required": true
    }
  ],
  "code": "<complete Python program>"
}
```

The compiler emits `zm.system.operators.code` with `node_type: "logic"`, derives the runtime input
maps and schemas, and persists `intent` as top-level `prompt`.

The compiler owns `input`, `requestJson`, `inputSchema`, `parameter`, and `outputSchema`. Author the
complete sandbox program in PlanIR `code`. Do not emit an object containing those fields,
and do not emit a business-body fragment that omits `run_node`.

## Reliability policy

Prefer robustness and a usable failure signal over performance, cleverness, or optimistic output.
Never fabricate a computed value merely to keep the node successful. When accurate derivation is
not possible, return conservative type-correct fallback values and identify the failure explicitly.
If robustness and immediate business-result correctness conflict, preserve process liveness and emit
`code_succeeded=false`; downstream logic must not mistake the fallback for an accurate result.

Treat every input as untrusted regardless of its declared schema:

- Check runtime types before using values. Accept only the shapes the computation understands.
- Handle missing, null, malformed, mixed-type, out-of-range, and unexpectedly large values.
- Prefer explicit runtime checks. If an assertion helps document an invariant, keep it inside the
  caught computation path and never use it as the sole runtime validation because assertions can be
  disabled.
- Bound loops, recursion, collection growth, parsing, and output size when input can control them.
- Catch conversion and computation errors locally. A bad record should be skipped or represented in
  the failure signal according to the workflow's requested behavior, not crash the program.
- Prefer simple deterministic algorithms and explicit intermediate values over compact or optimized
  code that is harder to validate.

## Fail-open output contract

The program must prevent uncaught exceptions from terminating the Code node. Every Custom Script
PlanIR step declares these required outputs in addition to its business outputs:

- `code_succeeded` — required `boolean`; true only when every accuracy-critical computation needed
  for the business outputs completed successfully.
- `error_message` — required `string`; empty on success, otherwise a concise, non-sensitive failure
  description suitable for downstream handling. Do not include input contents, secrets, stack traces,
  or filesystem details.

`run_node` must catch `Exception` around all parsing and business computation. On computation failure,
return the normal runtime envelope with `success: true`, `code_succeeded: false`, an `error_message`,
and type-correct fallback values for every declared business output. This keeps the node process
healthy while exposing that its derived data is unusable. Downstream steps must bind or condition on
`code_succeeded` whenever using the derived value could produce an inaccurate write or delivery.

The `__main__` launcher must also catch `Exception`, construct the same fail-open envelope, and print
valid JSON. Do not use `BaseException`; process termination signals are not recoverable business
errors.

## Runtime contract

The program runs in `zm.system.operators.code`. It must:

1. Define exactly `run_node(input_data, context)` — no `*args`, no extra parameters.
2. Normalize a non-dict `input_data` to `{}` before reading named inputs. Read inputs with
   `input_data.get("<name>")` or `input_data["<name>"]`; never call `input_data.values()`.
3. Return `{"success": true, "output": {...}}` on both computation-success and handled-failure
   paths. Output keys must match the PlanIR `outputs`, including the two reliability outputs above.
4. Include an `if __name__ == "__main__":` launcher that reads sibling `request.json` and prints
   `json.dumps(result, ensure_ascii=False)` to stdout.
5. Use exactly this filesystem access, once:

   `request_path = Path(__file__).with_name("request.json")`

   Then call `request_path.read_text(...)`. Do not call `open()`, import `os`, or touch another path.

Do not execute the program while authoring.

## PlanIR inputs and outputs

- Every key the code reads must exist as a PlanIR `inputs[].name` with a `source` binding.
- Do not invent inputs beyond those bindings.
- Every key placed in `output` must exist as a PlanIR `outputs[].name`.
- Allowed field types are `string`, `integer`, `number`, `boolean`, `object`, `array`, `null`, and
  `unknown`.
- When the next step is HTML, emit only plain text or serialized structured data that the template
  needs. Never emit HTML elements, tags, fragments, attributes, components, scripts, or styles.
  The HTML sandbox renders only the HTML node's `template` parameter; other bound inputs are escaped
  as data during rendering. HTML slots cannot bind objects, arrays, numbers, or booleans directly.

## Least-privilege libraries

Keep code local, deterministic, and minimal. Use only the built-in modules needed from this set:
`collections`, `datetime`, `decimal`, `functools`, `html`, `itertools`, `json`, `math`, `operator`,
`pathlib`, `re`, `statistics`, and `typing`.

Do not use dynamic imports, dynamic code execution, runtime reflection, or dunder attribute access.
Do not access the network, processes, environment, secrets, interactive input, or filesystem beyond
the single required sibling `request.json` read. Access only explicitly declared inputs by name and
avoid APIs that enumerate or mutate the input container.

## Downstream HTML boundary

- Output plain text as text, not markup.
- Output structured data as a JSON string using `json.dumps(..., ensure_ascii=False)`.
- Never build presentation HTML in Python. Layout, elements, styling, accessibility, and DOM
  construction belong exclusively to the downstream HTML node's template.
- A Code output that happens to contain `<tag>` text is data, not trusted markup; the HTML renderer
  escapes it instead of adding that element to the page.

## Comments and edits

- Comments are optional. If present they must be English only.
- When patching existing code, return the complete updated program, not a diff. Keep the `run_node`
  signature, launcher, reliability outputs, and still-active behavior. Re-author an unsafe legacy
  body instead of preserving it.

## Complete compilable example

PlanIR `inputs`: `report` (object). PlanIR business output: `report_json` (string), plus the required
`code_succeeded` and `error_message` reliability outputs.

```python
import json
from pathlib import Path


def failure_output(message):
    return {
        "success": True,
        "output": {
            "report_json": "{}",
            "code_succeeded": False,
            "error_message": message,
        },
    }


def run_node(input_data, context):
    try:
        if not isinstance(input_data, dict):
            return failure_output("Code input was not an object")
        report = input_data.get("report")
        if not isinstance(report, dict):
            return failure_output("Report input was not an object")
        serialized = json.dumps(report, ensure_ascii=False)
        report_json = (
            serialized.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        )
        return {
            "success": True,
            "output": {
                "report_json": report_json,
                "code_succeeded": True,
                "error_message": "",
            },
        }
    except Exception:
        return failure_output("Report transformation failed")


if __name__ == "__main__":
    try:
        request_path = Path(__file__).with_name("request.json")
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        result = run_node(payload.get("input_data", {}), payload.get("context", {}))
    except Exception:
        result = failure_output("Code request could not be processed")
    print(json.dumps(result, ensure_ascii=False))
```
