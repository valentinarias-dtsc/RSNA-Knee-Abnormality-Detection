# 03 Report Label Generation v3 — Implementation

## Technical summary

`report-label-policy-v3.0.0` coexiste con v2 y conserva sus artefactos. La política se selecciona desde el CLI; v3 agrega un intermediate representation tipado y un pipeline de comparación completo.

## Architecture

```text
Report
  → language hypotheses + strict/linked text views
  → exact v2 branch + controlled morphology + target detectors
  → Mention
  → deduplicated Proposition
  → target reconciliation
  → derived status/label + structured provenance
  → corpus-only audits and v2 comparison
  → final frozen-gold evaluation
  → official override and versioned artifacts
```

## Modules

- `v3/schema.py`: `TextView`, `Mention` y `Proposition`.
- `v3/text.py`: segmentación multivista y routing lingüístico no exclusivo.
- `v3/morphology.py`: reglas acotadas por idioma/target y exclusiones.
- `v3/extraction.py`: ensemble de evidence y detectores target-específicos.
- `v3/reconciliation.py`: deduplicación, precedencias y conflictos.
- `v3/evaluation.py`: provenance audit, detector summaries y template consistency.
- `v3/pipeline.py`: persistencia, comparación v2→v3, figuras y metadata.
- `v3/reporting.py`: reporte analítico y este reporte técnico.
- `config/03_report_label_generation/policy_v3.json`: contrato declarativo.

## Compatibility

V2 no fue modificada internamente. `python scripts/generate_report_labels.py --policy v2` reproduce la política congelada. El default del entry point es v3.

## Output schema additions

- `phenotypes`: phenotypes de las proposiciones seleccionadas.
- `detectors`: ramas que sostienen evidence.
- `evidence_provenance`: status, phenotype, evidence, detector, view, language, confidence, collective y rule.

## Validation order

1. Input y cardinalidad.
2. Extraction sin consultar gold.
3. Auditoría de 12 invariantes.
4. Consistencia de plantillas exactas y normalizadas respecto de números.
5. Comparación con v2.
6. Evaluación final en los 58 gold.
7. Override official y persistencia.

## Commands

```powershell
python -m unittest discover -s tests -v
python scripts/generate_report_labels.py --policy v3
python scripts/generate_report_labels.py --policy v2
```

## Generated artifacts

La supervisión principal es `supervision_long_v3.csv`. La comparación se materializa en `coverage_delta_v2_v3.csv`, `status_transitions_v2_v3.csv` y `newly_resolved_pairs_v2_v3.csv`. La trazabilidad se resume en `detector_summary_v3.csv` y la validación corpus-only en `template_consistency_v3.csv`, `consistency_audit_summary_v3.csv` y `consistency_audit_issues_v3.csv`.

Las figuras generadas son `status_coverage_by_target_v3.png`, `gold_metrics_by_target_v3.png` y `resolved_coverage_delta_v2_v3.png`.

## Dependency policy

No se agregaron dependencias. La implementación usa Python estándar, pandas, NumPy y Matplotlib ya fijados por el proyecto. No se usa un servicio externo, LLM, traducción web, DICOM ni metadata de imagen.

## Remaining limitations

La morfología es controlada y no equivale a lematización completa. El grafo se implementa como relaciones y proposiciones tipadas, no como dependency parser. La recuperación por similitud se limita en esta release a validación mediante plantillas exactas y numeric-normalized: no puede emitir labels.
