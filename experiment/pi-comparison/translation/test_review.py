"""Offline checks of evidence binding and score separation, not semantic proofs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import review as r


def packet(proof=False,approved=False):
    return {'task_id':'TEST','language':'lean','formal_sha256':'formal-hash',
        'contract_sha256':'contract-hash','formal_source':'def p : Prop := True\n',
        'native_declarations':{'p':{'type':'Prop'}},
        'contract':{'status':'approved' if approved else 'draft_requires_interpretation_review',
            'source_claims':[{'id':'C1'}],'source_proof_steps':[{'id':'S1'}] if proof else [],
            'proof_route_required':proof}}


def assessed(p):
    result=r.template(p,'packet-hash')
    evidence=[{'declaration':'p','formal_excerpt':'def p : Prop := True'}]
    for item in result['claims']+list(result['dimensions'].values()):
        item.update(status='pass',reason='Fixture judgment only, not a semantic assertion.',evidence=copy.deepcopy(evidence))
    result['reviewer']={'kind':'human','identity':'test-reviewer','model':None}
    if p['contract']['proof_route_required']:
        result['proof_route'].update(status='faithful',reason='Fixture route judgment.',evidence=copy.deepcopy(evidence))
    return result


class ReviewTests(unittest.TestCase):
    def test_kernel_pass_does_not_imply_fidelity(self):
        p=packet(approved=True);p['kernel_status']='pass'
        result=r.evaluate(p,r.template(p,'packet-hash'),'packet-hash')
        self.assertEqual(result['translation_status'],'unreviewed')
        self.assertIsNone(result['verified_faithful_translation'])

    def test_draft_contract_never_produces_final_rate(self):
        p=packet();result=r.evaluate(p,assessed(p),'packet-hash')
        self.assertEqual(result['translation_status'],'provisional_pass')
        self.assertIsNone(result['verified_faithful_translation'])

    def test_approved_evidence_assessment_can_be_recorded(self):
        p=packet(approved=True)
        self.assertTrue(r.evaluate(p,assessed(p),'packet-hash')['verified_faithful_translation'])

    def test_stale_or_other_language_review_rejected(self):
        p=packet()
        for field in ('task_id','language','formal_sha256','contract_sha256','packet_sha256'):
            review=assessed(p);review[field]='wrong'
            with self.subTest(field=field),self.assertRaises(ValueError):r.evaluate(p,review,'packet-hash')

    def test_missing_source_step_rejected(self):
        p=packet(proof=True);review=assessed(p);review['claims'].pop()
        with self.assertRaisesRegex(ValueError,'Each original source'):r.evaluate(p,review,'packet-hash')

    def test_missing_or_invented_formal_evidence_rejected(self):
        p=packet()
        for evidence in ([],[{'formal_excerpt':'nonexistent theorem'}],[{'formal_excerpt':'def p','declaration':'nonexistent'}]):
            review=assessed(p);review['claims'][0]['evidence']=evidence
            with self.subTest(evidence=evidence),self.assertRaises(ValueError):r.evaluate(p,review,'packet-hash')

    def test_different_route_fails_strict_fidelity_even_when_goal_passes(self):
        p=packet(proof=True,approved=True);review=assessed(p)
        review['proof_route']['status']='alternative'
        result=r.evaluate(p,review,'packet-hash')
        self.assertEqual(result['assessed_fidelity'],'fail')
        self.assertFalse(result['verified_faithful_translation'])
        self.assertTrue(result['verified_meaning_preservation'])

    def test_model_refinement_requires_disclosure_and_justification(self):
        p=packet(proof=True,approved=True);review=assessed(p)
        review['proof_route']['status']='faithful_with_model_refinements'
        with self.assertRaisesRegex(ValueError,'additional model'):r.evaluate(p,review,'packet-hash')
        review['model_refinements']=[{'introduced_fact':'Circle intersection exists','justification':'Fixture only',
            'source_gap_or_model_change':'Source does not prove existence',
            'evidence':[{'formal_excerpt':'def p'}]}]
        self.assertTrue(r.evaluate(p,review,'packet-hash')['verified_faithful_translation'])
        review['proof_route']['status']='faithful'
        with self.assertRaisesRegex(ValueError,'Disclose'):r.evaluate(p,review,'packet-hash')

    def test_route_only_judgment_still_requires_identified_reviewer(self):
        p=packet(proof=True);review=r.template(p,'packet-hash')
        review['proof_route'].update(status='alternative',reason='Different route',evidence=[{'formal_excerpt':'def p'}])
        with self.assertRaisesRegex(ValueError,'identified'):r.evaluate(p,review,'packet-hash')

    def test_approved_contract_cannot_keep_unresolved_model_decision(self):
        path=r.HERE/'contracts/EUCLID.I.D001.json';contract=r.read(path)
        contract.update(status='approved',approval={'reviewer':'test','reason':'fixture'})
        with self.assertRaisesRegex(ValueError,'unresolved'):r.validate_contract(contract)

    def test_all_actual_source_contracts_bind_original_text(self):
        paths=list((r.HERE/'contracts').glob('*.json'))
        self.assertEqual(len(paths),11)
        for path in paths:
            with self.subTest(contract=path.name):r.validate_contract(r.read(path))

    def test_unknowns_are_not_fabricated_accuracy_or_machine_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=packet(approved=True)
            r.save(root/'a.packet.json',p);digest=r.sha(root/'a.packet.json')
            r.save(root/'a.review.json',r.template(p,digest))
            index={'policy':{},'registered_batch_slots':3,'slots_without_contract':[],
                'rows':[{'key':'1','task_id':'TEST','language':'lean','kernel_status':'pass',
                    'packet':'a.packet.json','packet_sha256':digest,'review':'a.review.json'},
                    {'key':'2','task_id':'FAIL','language':'lean','kernel_status':'fail'},
                    {'key':'3','task_id':'INTERRUPTED','language':'lean','kernel_status':'unknown'}]}
            r.save(root/'index.json',index);original=(root/'index.json').read_bytes()
            group=r.summarize(root)['groups']['lean']
            self.assertEqual((root/'index.json').read_bytes(),original)
            self.assertIsNone(group['verified_faithful_translation_rate'])
            self.assertEqual(group['kernel_passed'],1)
            self.assertEqual(group['unknown_translation_outcomes'],2)
            self.assertEqual(group['possible_rate_interval'],[0,2/3])
            (root/'a.packet.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'packet changed'):r.summarize(root)

    def test_actual_packet_generation_preserves_historical_artifacts(self):
        batch=r.BASE/'batches/local-compact10-01'
        watched=[batch/'state.json',batch/'plan.json']
        watched+=list(batch.glob('workers/*/attempts/*/submission.json'))
        before={str(p):r.sha(p) for p in watched}
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'reviews';index=r.make_packets(batch,output)
            self.assertEqual(len(index['rows']),20)
            self.assertEqual(sum('packet' in row for row in index['rows']),18)
            summary=r.summarize(output)
            self.assertEqual(summary['groups']['lean']['kernel_passed'],10)
            self.assertEqual(summary['groups']['litex']['kernel_passed'],8)
            self.assertTrue(all(g['verified_faithful_translation_rate'] is None for g in summary['groups'].values()))
        self.assertEqual({str(p):r.sha(p) for p in watched},before)


if __name__=='__main__':unittest.main()
