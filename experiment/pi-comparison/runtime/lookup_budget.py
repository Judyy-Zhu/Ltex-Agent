"""Charge a generation once if it ignores the required candidate phase."""
import json


def recover_violations(root,rounds):
    path=root/'lookup-budget.json'
    if not path.exists():return
    data=json.loads(path.read_text())
    charged={r.get('api_attempt_id') for r in rounds.read()['rounds'] if r.get('kind')=='generation'}
    for event in data.get('violations',[]):
        identifier='lookup-limit:'+event['id']
        if identifier in charged:continue
        if rounds.summary()['remaining']==0:return
        number=rounds.begin(kind='generation',api_attempt_id=identifier)
        rounds.finish(number,False,'Generation ignored the required candidate phase after its information-query allowance')
        charged.add(identifier)
