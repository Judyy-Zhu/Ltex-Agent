"""Read-only observer tests; deliberately outside the sealed solver runtime."""
import json
from pathlib import Path
import tempfile
import unittest
from monitor import snapshot,render,live_usage


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


class MonitorControls(unittest.TestCase):
    def fixture(self,root,language):
        worker=root/'workers'/language
        write(worker/'plan.json',{'slots':[{},{}],'budget':{'max_task_rounds':5}})
        records={'done':{'status':'finished','published':True,'task_id':'DONE','attempt':'attempts/old',
                         'telemetry_complete':True,'usage':{'fields':{'token_total':{'known_subtotal':100,'missing_requests':0}}}},
                 'current':{'status':'active','task_id':language.upper()+'_CURRENT','attempt':'attempts/current'}}
        write(worker/'state.json',{'status':'running','records':records,'elapsed_execution_seconds':25})
        attempt=worker/'attempts/current'
        write(attempt/'manifest.json',{'status':'running','known_elapsed_seconds':10})
        write(attempt/'task-rounds.json',{'limit':5,'rounds':[{'kind':'candidate','status':'failed','passed':False}]})
        rows=[{'kind':'request','attempt':1},{'kind':'usage','attempt':1,'usage':{'prompt_tokens':10,'completion_tokens':2}},
              {'kind':'usage','attempt':1,'usage':{'prompt_tokens':10,'completion_tokens':2}},
              {'kind':'request','attempt':2}]
        (attempt/'provider.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n{"kind":"usage"')
        (attempt/'tools.jsonl').write_text(json.dumps({'tool':'check','seconds':.1,'error':False})+'\n')
        return attempt

    def test_language_isolation_and_token_aggregation_without_duplicate_usage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for language in ('lean','litex'):self.fixture(root,language)
            for language in ('lean','litex'):
                data=snapshot(root,language)
                self.assertEqual(data['language'],language)
                self.assertEqual(data['current']['task_id'],language.upper()+'_CURRENT')
                self.assertEqual(data['known_worker_tokens'],112)
                self.assertEqual(data['missing_worker_usage'],1)
                self.assertEqual(data['current']['usage']['requests'],2)
                self.assertEqual(data['current']['attempt_window_used'],1)
                self.assertEqual(data['finished_pass_rate'],1)

    def test_snapshot_does_not_write_files_and_sensitive_diagnostics_are_redacted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);attempt=self.fixture(root,'litex')
            write(attempt/'manifest.json',{'status':'waiting_network','last_transport_error':'fetch failed sk-test-secret'})
            write(attempt/'tool-results/failure.json',{'result':{'isError':True,'details':{'error':'Submission gate rejected sk-tool-secret'}}})
            (attempt/'tools.jsonl').write_text(json.dumps({'tool':'submit','seconds':.1,'error':True})+'\n')
            before={str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
            data=snapshot(root,'litex');text=render(data)
            after={str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            self.assertNotIn('sk-test-secret',text)
            self.assertNotIn('sk-tool-secret',text)
            self.assertIn('Submission gate rejected',text)
            self.assertIn('[REDACTED]',text)
            self.assertIn('waiting_network',text)

    def test_unavailable_state_is_not_reported_as_zero_finished(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.fixture(root,'lean')
            (root/'workers/lean/state.json').write_text('{"unfinished":')
            data=snapshot(root,'lean')
            self.assertFalse(data['state_available'])
            self.assertNotIn('finished',data)
            self.assertIn('not available',render(data))


if __name__=='__main__':unittest.main()
