"""English experiment metadata; the shared historical source catalog is unchanged."""
import json
import re

CJK=re.compile(r'[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f]')
SUBJECTS={1:'Foundations of plane geometry',2:'Geometric algebra',3:'Circles and tangents',
          4:'Inscribed and circumscribed figures',5:'Magnitudes and ratios',6:'Similarity and proportion',
          7:'Elementary number theory',8:'Continued proportions of numbers',9:'Number theory',
          10:'Incommensurable magnitudes',11:'Foundations of solid geometry',
          12:'Areas, volumes and exhaustion',13:'Regular solids'}
ACCEPTANCE=[
    'Submit a complete formalization of the source item with all required clause mappings and interface metadata.',
    'Saved files pass complete verification in a fresh process using the pinned verifier.',
    'No direct or transitive unproved dependencies beyond the approved foundation.',
    'A partial conclusion does not count as a complete task success.']
SUCCESS_POLICY={'criterion':'machine_verification','semantic_review_required':False,
                'semantic_annotations_affect_primary_score':False,
                'accuracy_definition':'machine-verified propositions divided by registered propositions'}
DEPENDENCY_POLICY=('Source order is navigation, not a claim that adjacent numbers are logical dependencies. '
                   'Do not assume missing predecessor results without proving them.')


def require_english(value,label='Agent-visible content'):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
    if CJK.search(text):raise ValueError(label+' contains CJK text; use English for experiment instructions, explanations and source comments')


def english_record(record):
    result={k:v for k,v in record.items() if not k.endswith('_zh')}
    title=f"Book {record['book_roman']}, {record['kind'].replace('_',' ')} {record['number']}"
    if record.get('preceding_proposition'):title+=f" (after proposition {record['preceding_proposition']})"
    if record['kind']=='definition':
        action=('Formalize the source concepts as checked definitions with explicit domains and representations. '
                'Prove only mathematical claims explicitly asserted by the source or required for well-definedness; '
                'do not add unrequested semantic-bridge theorems. ')
    elif record['kind'] in ('postulate','common_notion'):
        action=('Formalize this foundational source item accurately; state whether it is a property to prove in the selected model '
                'or an explicitly approved source postulate, and record the assumption boundary. ')
    else:
        action=('Formalize and prove the complete source item, preserving quantifiers, domains, nondegeneracy, '
                'all branches, conclusions and construction correctness. ')
    result.update(title=title,subject=SUBJECTS[record['book']],
                  instruction=action+'Use the original text located by source_span as the specification; a title or historical completion label is not a substitute.',
                  acceptance=list(ACCEPTANCE),
                  dependencies={**record['dependencies'],'policy':DEPENDENCY_POLICY})
    require_english(result,'Task record')
    return result
