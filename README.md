# Litex Stoicheia — Euclid's Elements

Existing results exported on 2026-11-07 from `../golitex/scripts/Euclid_Elements/`.
The original workspace is preserved. This export does not complete any book,
change a proof, or promote a checked draft into the canonical textbook.

## Start here

- [Canonical textbook](textbook/README.md): existing Book I and III chapters,
  supporting mathematical interfaces, and the original progress narrative.
  That narrative records 52 numbered canonical propositions; it is historical,
  not a fresh verification count.
- [Checked checkpoint index](results/index.json): 32 successful historical
  checkpoints with their actual `.lit` sources, configurations, receipts, and
  verifier JSON. The index includes source-hash comparisons where recorded.
- [Unfinished work](todo.md) and [translation records](translation_records/).
- [Latest retained progress journal](proof_journals/resume-2026-10-17.json).
- [Experiment report](experiment/report.md): historical measurements and
  observations; timestamps and stale process handles are preserved as evidence.

## Included results

| Area | Included historical checkpoints |
| --- | --- |
| Book I | I.35–I.40, the integrated area-stage prefix, I.42/I.44/I.46, I.43, and I.47 construction |
| Book II | II.1–II.13 canonical-prefix integration candidate |
| Book III | Audited integration candidate through III.26, III.28, and rectilinear clauses of III.31 |
| Book IV | Construction and incircle work, repaired IV.8–IV.10, IV.11–IV.12, and five-point-circle prerequisites |
| Book V | Equimultiple equivalence and ratio-order interfaces |
| Book VI | Independent checkpoints for VI.1–VI.7 |
| Region prerequisites | Polygon boundary, prescribed-area constructions, finite triangle decomposition, and dissection |

A checkpoint can include helpers and concrete consumers; its statement count
is not the number of completed source propositions. Partial source statements
and prerequisite results retain their original scope. No whole-book completion
is claimed.

## Verification and replay boundary

Files were copied with SHA-256 equality checks. The stored receipts record
successful historical runs on their recorded Litex binaries. No mathematical
verification was rerun during this export. Original receipt/configuration bytes
and historical absolute paths were preserved rather than rewriting evidence.

The canonical geometry module currently contains:

```toml
[export]
main = "../../../LitexGeo-AutoBuild/shenjiachen/新geo和geo_definitions/geo.lit"
```

That original dependency is absent at its referenced location. Some checkpoints
also refer to original workspace paths and unavailable pinned binaries. Restore
the correct dependency version and deliberately relocate configurations before
attempting a replay. Other available `geo.lit` variants are not silently
substituted; their hashes differ from later checkpoint dependencies.

Links in copied historical notes may still point to original `.draft/` paths.
Exported successful checkpoints are under `results/checkpoints/`; unexported
attempts and full journals remain in the original workspace. This directory
does not include failed scratch experiments, raw session logs, copied binaries,
build caches, or the old placeholder-only `Euclid_Elements_Book.lit` entrypoint.

See [export-manifest.json](export-manifest.json) for the exact file mapping,
byte sizes, hashes, and export scope.

# litex-Stoicheia
