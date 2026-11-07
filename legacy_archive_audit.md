# Legacy Book.zip audit

Inspected on 2026-10-11 using Python `zipfile`, without extraction or mutation.

## Observed source inventory

Archive: `scripts/Euclid_Elements/Book.zip`.

- 308 archive entries, including directories and macOS metadata.
- Exactly 48 source files matching `Book/Prop[0-9][0-9].lit`, numbered 01 through 48.
- I.1: explicit `R²` equilateral apex construction and two squared-distance identities, using historical tuple indexing `a[1]`/`a[2]`.
- I.2: explicit endpoint construction using the square root of the input squared distance; its statement additionally requires `a != b`, unlike the unrestricted source construction problem. The coincident-point case must be included in redevelopment, rather than silently retaining this restriction.
- I.3–I.48: 46 source-numbered comments attached to a theorem with conclusion `a = a`; no formal expression of the respective source result.
- No additional non-metadata `.lit` files were found in the archive.
- The archive also supplies source prose, proof prose, diagrams, and historical working notes. Assess those against the authoritative PDF before reusing them.

## Representative source defect

Actual archived `Book/Prop47.lit` declaration:

```litex
thm proposition_47:
    ? forall a, b, c cart(R, R):
        a != b
        b != c
        =>:
            a = a
```

The surrounding comment names Pythagoras, but the theorem neither assumes a right triangle nor concludes the square/area equality. Redevelopment must express the genuine nondegenerate right-triangle statement and derive the equality of the squares on its sides. Exact Litex vocabulary remains dependent on the selected geometry foundation; no replacement declaration has been implemented or verified.

Classification: legacy/example defect and documentation drift, independent of parser compatibility or current verifier behavior. Repair category: Litex statement and proof authoring. This does not justify restoring old acceptance or adding trust to a migration reproduction.

Actual archived I.2 restriction and output:

```litex
? forall a, b, c cart(R, R):
    b != c
    a != b
    =>:
        exist l cart(R, R) st {(l[1] - a[1])^2 + (l[2] - a[2])^2 = (c[1] - b[1])^2 + (c[2] - b[2])^2}
```

The future source-faithful statement must also permit `a = b`. The archived coordinate witness `(a[1] + d, a[2])`, where `d` is the input segment length, does not mathematically need the extra inequality. Current syntax and the full-domain proof have not been tested. Classify this as a source-statement restriction to repair, not as a demonstrated kernel defect.

## Historical claims and verification limits

`Book/README.md` claims all 48 propositions were fully verified without trust. `Book/PROGRESS.md` lists only I.1 as done. `Book/TRANSLATION_LOG.md` reports five complete proofs, but the actual I.3–I.5 files in this archive have reflexive conclusions. Retain the documents as historical records; they are not a completion certificate.

The unchanged archived I.1/I.2 have now been run in intentionally isolated contexts with the current release. Both reject at parsing: ordinary coordinate calls replaced bracket indexing. I.1 reports this at line 15 and I.2 at line 16; the exact receipts and source hashes are in `experiment/commands.jsonl`, with raw results under `.draft/legacy/`. Classification: intended syntax change, earliest phase parsing. These rejections do not establish a mathematical proof defect or a kernel regression.

The redeveloped I.1/I.2 passed in the complete-library Session without trust. Their registered clean file gate is still pending; do not call the chapter complete from interactive results alone. No legacy binary gate or soundness comparison has been run. The 46 placeholders count as zero translated source propositions.

## Reproduction

From the golitex root, inspect the archive with Python `zipfile.ZipFile`. Select paths with `re.fullmatch(r'Book/Prop\d\d\.lit', name)` and examine each statement. All 46 files from 03 through 48 match `re.search(r'=>:\s*\n\s*a = a', source)`; only 01 and 02 do not. Do not treat this text check as proof verification.

Next: settle the geometry foundation, then compare I.1/I.2 source statements with their current-Litex counterparts in a persistent release Session. Preserve the original archive.
