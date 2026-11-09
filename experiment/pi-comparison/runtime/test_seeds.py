import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from prepare import prepare_job,write_json
from native_sessions import SessionLedger
from seed_support import seed_source,assemble_final
from tool_host import Host


class SeedControls(unittest.TestCase):
    def test_paired_interface_and_frozen_input_partition(self):
        with tempfile.TemporaryDirectory() as temporary:
            jobs=[]
            for language in ('lean','litex'):
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True);jobs.append(job)
                interface=json.loads((root/'input/seed-interface.json').read_text())
                self.assertEqual(job['foundation']['approved_seed_symbols'],[e['name'] for e in interface['exports']])
                self.assertEqual(len(interface['exports']),7)
                self.assertEqual(interface['proposition_proofs_provided'],[])
                self.assertEqual(interface['agent_tasks_completed_by_seed'],[])
                self.assertIn(Path(job['seed_path']).name,job['language_specific_input_files'])
            self.assertEqual(jobs[0]['shared_input_files'],jobs[1]['shared_input_files'])
            for name in jobs[0]['shared_input_files']:
                self.assertEqual((Path(temporary)/'lean/input'/name).read_bytes(),(Path(temporary)/'litex/input'/name).read_bytes())
            self.assertEqual(jobs[0]['foundation']['seed']['interface_sha256'],jobs[1]['foundation']['seed']['interface_sha256'])

    def test_universal_interface_properties_in_both_native_sessions(self):
        lean='''theorem seed_coordinates (x y : ℝ) : geo_x (geo_point x y) = x ∧ geo_y (geo_point x y) = y := by exact ⟨rfl,rfl⟩
theorem seed_reconstruct (p : GeoPoint) : geo_point (geo_x p) (geo_y p) = p := by rfl
theorem seed_vector (a b : GeoPoint) : geo_x (geo_vec a b) = geo_x b - geo_x a ∧ geo_y (geo_vec a b) = geo_y b - geo_y a := by exact ⟨rfl,rfl⟩
theorem seed_products (u v : GeoPoint) : geo_dot u v = geo_x u * geo_x v + geo_y u * geo_y v ∧ geo_det u v = geo_x u * geo_y v - geo_y u * geo_x v := by exact ⟨rfl,rfl⟩
'''
        litex='''thm seed_coordinates:
    ? forall x, y R:
        geo_x(geo_point(x,y)) = x
        geo_y(geo_point(x,y)) = y
    geo_x(geo_point(x,y)) = x
    geo_y(geo_point(x,y)) = y
thm seed_reconstruct:
    ? forall p GeoPoint:
        geo_point(geo_x(p),geo_y(p)) = p
    geo_point(geo_x(p),geo_y(p)) = p
thm seed_vector:
    ? forall a, b GeoPoint:
        geo_x(geo_vec(a,b)) = geo_x(b) - geo_x(a)
        geo_y(geo_vec(a,b)) = geo_y(b) - geo_y(a)
    geo_x(geo_vec(a,b)) = geo_x(b) - geo_x(a)
    geo_y(geo_vec(a,b)) = geo_y(b) - geo_y(a)
thm seed_products:
    ? forall u, v GeoPoint:
        geo_dot(u,v) = geo_x(u)*geo_x(v) + geo_y(u)*geo_y(v)
        geo_det(u,v) = geo_x(u)*geo_y(v) - geo_y(u)*geo_x(v)
    geo_dot(u,v) = geo_x(u)*geo_x(v) + geo_y(u)*geo_y(v)
    geo_det(u,v) = geo_x(u)*geo_y(v) - geo_y(u)*geo_x(v)
'''
        with tempfile.TemporaryDirectory() as temporary:
            for language,source in (('lean',lean),('litex',litex)):
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True)
                ledger=SessionLedger(root,job);path='properties.'+('lean' if language=='lean' else 'lit')
                (root/'work'/path).write_text(source)
                try:
                    result=ledger.check(path,source,time.monotonic()+90)
                    self.assertTrue(result['passed'],result)
                    self.assertEqual(result['starts'],1)
                finally:ledger.close()

    def test_known_values_orientation_and_restart_reload(self):
        sources={
            'lean':'example : geo_vec (geo_point 2 3) (geo_point 5 7) = geo_point 3 4 := by norm_num [geo_vec,geo_point,geo_x,geo_y]\nexample : geo_dot (geo_point 2 3) (geo_point 5 7) = 31 := by norm_num [geo_dot,geo_point,geo_x,geo_y]\nexample : geo_det (geo_point 2 3) (geo_point 5 7) = -1 := by norm_num [geo_det,geo_point,geo_x,geo_y]\n',
            'litex':'''have numA GeoPoint = (2,3)
have numB GeoPoint = (5,7)
numA(1) = 2
numA(2) = 3
numB(1) = 5
numB(2) = 7
geo_vec(numA,numB) = (numB(1)-numA(1),numB(2)-numA(2))
geo_vec(numA,numB)(1) = numB(1)-numA(1)
geo_vec(numA,numB)(2) = numB(2)-numA(2)
numB(1) - numA(1) = 3
numB(2) - numA(2) = 4
geo_vec(numA,numB)(1) = 3
geo_vec(numA,numB)(2) = 4
by thm tuple_equal_from_coordinates(geo_vec(numA,numB),(3,4))
geo_vec(numA,numB) = (3,4)
geo_dot(numA,numB) = 31
geo_det(numA,numB) = -1
'''}
        with tempfile.TemporaryDirectory() as temporary:
            for language,source in sources.items():
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True)
                ledger=SessionLedger(root,job);path='values.'+('lean' if language=='lean' else 'lit')
                (root/'work'/path).write_text(source)
                try:
                    first=ledger.check(path,source,time.monotonic()+90)
                    self.assertTrue(first['passed'],first)
                    ledger.close()
                    second=ledger.check(path,source,time.monotonic()+90)
                    self.assertTrue(second['passed'],second)
                    self.assertEqual(second['restarts'],1)
                    self.assertGreater(second['replayed_blocks'],0)
                finally:ledger.close()

    def test_seed_copy_tampering_blocks_even_before_kernel_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True)
                path=Path(job['seed_path']);path.write_bytes(path.read_bytes()+b'\n')
                ledger=SessionLedger(root,job)
                try:
                    with self.assertRaisesRegex(ValueError,'seed changed'):
                        ledger.check('unused','',time.monotonic()+10)
                    self.assertIsNone(ledger.native)
                finally:ledger.close()

    def test_final_seed_prefix_is_protected(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True)
                write_json(root/'state.json',{'deadline_monotonic':time.monotonic()+120,'checks':0,'last_final_receipt':None})
                host=Host(root);path='final.'+('lean' if language=='lean' else 'lit')
                source=assemble_final(job,'')
                try:
                    host.dispatch('write_source',{'path':path,'content':source})
                    passed=host.dispatch('check',{'path':path,'mode':'final'})
                    self.assertTrue(passed['passed'],passed)
                    if language=='lean':modified=source.replace('b.2 - a.2','a.2 - b.2')
                    else:modified=source.replace('b(2) - a(2)','a(2) - b(2)')
                    self.assertNotEqual(modified,source)
                    host.dispatch('write_source',{'path':path,'content':modified})
                    rejected=host.dispatch('check',{'path':path,'mode':'final'})
                    self.assertFalse(rejected['passed'])
                    self.assertIn('unchanged frozen seed',rejected['controller_error'])
                finally:host.close()

    def test_false_orientation_is_rejected_by_actual_compilers(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True)
                write_json(root/'state.json',{'deadline_monotonic':time.monotonic()+120,'checks':0,'last_final_receipt':None})
                host=Host(root);path='false.'+('lean' if language=='lean' else 'lit')
                body=('example : geo_det (geo_point 2 3) (geo_point 5 7) = 1 := by norm_num [geo_det,geo_point,geo_x,geo_y]\n'
                      if language=='lean' else 'geo_point(2,3) = (2,3)\ngeo_point(5,7) = (5,7)\ngeo_det((2,3),(5,7)) = -1\ngeo_det(geo_point(2,3),geo_point(5,7)) = 1\n')
                try:
                    host.dispatch('write_source',{'path':path,'content':assemble_final(job,body)})
                    rejected=host.dispatch('check',{'path':path,'mode':'final'})
                    self.assertFalse(rejected['passed'],rejected)
                    self.assertIsNone(rejected['controller_error'])
                    self.assertNotEqual(rejected['exit_code'],0)
                finally:host.close()


if __name__=='__main__':unittest.main()
