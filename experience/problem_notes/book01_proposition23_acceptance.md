# Book I.23 angle copy: Session checkpoint

Given a nonzero target ray AB and a genuine source angle DCE, form source arm coordinates u,v and target arm w. Let k=|u|²>0, n=u·v and z=det(u,v). The copied second arm is ((n w₁-z w₂)/k, (n w₂+z w₁)/k), added to A. Its determinant with w is z|w|²/k, nonzero; its squared norm is |v|²|w|²/k and its dot with w is n|w|²/k. These independently established laws imply angle congruence with its sign condition retained.

The complete source theorem passed Session 55623 on attempt 3; exact source and earlier failures are in `translation_records/book01-proposition23.json` and `proof_journals/book01-full.jsonl`. A translated orthogonal-angle use passed, while a zero target base rejected at the exact distinctness premise. This is Session evidence, not a whole-file or book gate. Euclid's alternate original route uses I.22 and I.8; that route is documented but not separately checked here. Canonical promotion remains pending while I.22 gate 34818 freezes the inputs.

Ordinary failures were repaired in the same Session. First repair: explicit nonzero quotient contradiction. Second repair: separate denominator positivity and its actual squared-distance expression. Neither repair changes the theorem's domain, adds a geometric premise, or adds trust.
