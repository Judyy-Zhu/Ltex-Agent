"""Controller-owned declaration metadata. No solver API or guessed proof meaning."""
import json

MARKER='EUCLID_NATIVE_INDEX_V1:'


def lean_query(axioms=True):
    inspection=('let axioms ← Lean.collectAxioms name' if axioms else 'let axioms : Array Lean.Name := #[]')
    return '''run_cmd do
  let env ← Lean.getEnv
  for (name, info) in env.constants.toList do
    if (env.getModuleIdxFor? name).isNone && !name.isInternal then
      '''+inspection+'''
      let value := Lean.Json.mkObj [("name", Lean.toJson name.toString), ("type", Lean.toJson (toString info.type)), ("axioms", Lean.toJson (axioms.map (·.toString)))]
      Lean.logInfo m!"'''+MARKER+'''{value.compress}"
'''


def lean_metadata(response):
    values={}
    for message in response.get('messages',[]):
        data=message.get('data','')
        if message.get('severity')=='info' and data.startswith(MARKER):
            value=json.loads(data[len(MARKER):]);values[value['name']]=value
    return values


def litex_metadata(final_native,prefix_blocks,all_blocks):
    from submission_gate import litex_declarations
    results=final_native.get('statement_results',[])
    if len(results)!=all_blocks:
        raise ValueError('Native Litex statement count does not match the complete saved module')
    selected=results[prefix_blocks:]
    names=litex_declarations({'statement_results':selected})
    return {name:{'name':name,'native_statement':next(
        r['statement'] for r in selected if name in litex_declarations({'statement_results':[r]}))}
        for name in sorted(names)}
