# Book I Proposition 1 acceptance checkpoint

Status: the registered first-three-proposition strict gate passed on 2026-10-11; the exact executable hash at launch of that gate was not captured. A changed post-run hash is disclosed in the experiment protocol, and epoch 2 is being replayed with pinned release bytes. This note does not certify the rest of Book I or Books II–VI.

## Before and current statement

The archived I.1 uses removed bracket indexing and states two squared-distance equalities. Its unchanged current-release run rejects at parsing (line 15). The new real-plane proof uses the existing strict equilateral relation, explicitly verifies a nonzero determinant, and checks the constructed vertex on both prescribed circles. The fences below are statement excerpts; the linked registered source contains the executed proof.

```litex
# thm proposition_1:
#     ? forall a, b cart(R, R):
#         a != b
#         =>:
#             exist c cart(R, R) st {(c[1] - a[1])^2 + (c[2] - a[2])^2 = (b[1] - a[1])^2 + (b[2] - a[2])^2, (c[1] - b[1])^2 + (c[2] - b[2])^2 = (b[1] - a[1])^2 + (b[2] - a[2])^2}

thm proposition_1:
    ? forall a, b cart(R, R):
        a != b
        =>:
            exist z cart(R, R) st {$geometry::main::is_equilateral(a, b, z)}
```

[Current registered proof](../../textbook/book01-constructions.lit). [Attempt journal](../../proof_journals/book01-full.jsonl).

## Evidence

- Clean command: `target/release/litex -lang en -strict -f scripts/Euclid_Elements/textbook/book01-constructions.lit`.
- Exit 0; Normal kind `run`, success true, session_error null; all eight target statements passed, including I.1, I.2 and I.3. Wall time: 458.1708 seconds.
- Target SHA256 before and after: `bfe2fdd189439032266c4c87e39a093815eed7f95bfdd0fad996e9b227bc93dd`. No trust or global axioms were added.
- Concrete use in the full-library Session: I.1 on a length-2 base produced a genuine triangle with both other squared side lengths 4.
- Executable negative probe: coincident vertices do not satisfy `geometry::main::is_equilateral`; the failure is soft and the Session continues.
- Separate I.2 consumer: a length-5 segment was copied from its own input start, the case excluded by the old extra inequality. A zero-length input is rejected at the theorem premise.

[Timed command records](../../experiment/commands.jsonl) contain exact paths and envelope summaries. Raw file receipt: `scripts/Euclid_Elements/.draft/experiment/book01-first-three-clean.json`. Raw Session use and negative receipts are in the task-owned `.draft/uses/`; durable journal records refer to them.

## Liveness and limits

The isolated deletion probe excludes the already-proven book theorem. Removing all three product-membership facts fails at the area-positivity chain. Matched scalar probes show that root membership can be omitted while product and quotient membership are retained, but that shorter full I.1 has not yet been accepted. The canonical file therefore retains the fully checked route. Circle membership lines remain as source-facing construction evidence even though the final existential only mentions equilateral triangles.

The foundation is the real-coordinate model and the existing analytic library, not a derivation solely from the five original Euclid postulates. I.1 verifies the actual two-circle intersection witness. I.2 and I.3 use explicit analytic constructions; they do not encode an operational collapsing-compass program or replay every original geometric step. Source ideas and these differences are recorded alongside the statements.
