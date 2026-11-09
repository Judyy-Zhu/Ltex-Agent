# Real square roots and polynomial reasoning: development topic U09

This environment uses native real arithmetic, squares, order, cart(R,R) and the nonnegative principal real square root. No geometry definitions are preloaded. Additional imports, user axioms, trust, abstract_prop and foundation releases are forbidden. Formal native-foundation auditing remains pending.

sqrt(x) requires the real-domain condition 0 <= x. Prove it before application. Native rules support sqrt(x)^2=x for nonnegative x and sqrt(x^2)=|x| for arbitrary real x. Proving sqrt(x)!=0 generally requires x>0; nonnegativity alone is insufficient.

The following standalone teaching examples are not answers to Euclid propositions:

```litex
thm training_root:
    ? forall x R:
        0 <= x
        =>:
            sqrt(x)^2 = x
    sqrt(x)^2 = x

thm training_square_zero:
    ? forall x R:
        x^2 = 0
        =>:
            x = 0
    x = 0
```

State polynomial factorizations, expansions and established equalities step by step for the verifier. Do not skip a complex derivation in one leap; inspect its first unsolved obligation. Existential witnesses still use witness exist ... st {...} from ..., with all witness properties proved.

check(incremental) sends a fragment to the persistent Session; do not resend accepted declarations. Assemble the complete .lit file from the journal and use check(final) in a fresh process. Any source edit requires another final check.
