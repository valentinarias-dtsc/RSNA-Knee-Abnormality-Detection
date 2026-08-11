# 03 - Report label generation implementation

## Resumen técnico

Se implementó la etapa 03 como módulos Python y un entry point sin notebook. La versión activa es `report-label-policy-v1.0.0`. El flujo lee únicamente `StudyInstanceUID`, `Report` y los 12 targets oficiales de `train.csv`; no importa ni consulta DICOM o tablas de Series.

## Contexto

El componente materializa la supervisión textual identificada por las etapas de caracterización y revisión de estrategia. Su salida es un contrato para entrenamiento MRI posterior, no un modelo predictivo.

## Arquitectura

```text
train.csv
   → validación de input
   → normalización, secciones y grupo lingüístico
   → extracción target-específica
   → derived labels + confidence + evidence
   → evaluación contra gold (antes del override)
   → official override
   → artefactos + figuras + reportes
```

## Archivos creados o modificados

- `src/report_labels/__init__.py`: API pública del paquete.
- `src/report_labels/constants.py`: targets, dominios y política léxica multilingüe.
- `src/report_labels/text.py`: normalización, segmentación, contexto y grupos lingüísticos.
- `src/report_labels/extraction.py`: extracción y agregación de evidencia por target.
- `src/report_labels/evaluation.py`: métricas gold y error analysis.
- `src/report_labels/pipeline.py`: validaciones, override, persistencia y figuras.
- `src/report_labels/reporting.py`: generación de ambos Markdown desde resultados reales.
- `scripts/generate_report_labels.py`: entry point reproducible.
- `config/03_report_label_generation/policy_v1.json`: contrato y parámetros declarativos.
- `tests/test_report_labels.py`: tests unitarios e integración/schema.
- `.gitignore`: excepciones acotadas para versionar outputs de esta etapa.
- `README.md`: comando y contrato principal.

## Módulos e interfaces

`ReportLabelExtractor.extract(report)` devuelve un `ExtractionResult` por target sin consultar gold. `build_supervision(train)` expande Studies a formato largo. `evaluate_gold(frame)` calcula métricas sólo con derived pre-override. `validate_supervision(frame, train, expected_studies)` protege cardinalidad, dominios, provenance, missing y prioridad official. `run_pipeline(...)` orquesta la etapa completa.

## Orquestador / entry point

Desde la raíz:

```powershell
python scripts/generate_report_labels.py
```

Los paths pueden cambiarse mediante argumentos `--train`, `--artifact-dir`, `--figure-dir`, `--stage-report` y `--implementation-report`.

## Configuración

`policy_v1.json` declara versión, 12 targets, estados válidos, prioridad de fuentes, semántica de confidence, cardinalidades esperadas y prohibición de inputs MRI. Los léxicos ejecutables permanecen en Python para permitir tests y revisión de cambios.

## Tests

Los tests cubren afirmación ACL, negación, incertidumbre, ausencia de mención, determinismo, contexto no diagnóstico, schema 4.407 × 12, conservación de Studies, dominios, unresolved y gold override. Se usa `unittest`, por lo que no se agregó una dependencia de testing.

```powershell
python -m unittest discover -s tests -v
```

## Dependencias

Se reutilizan Python estándar, pandas, NumPy y Matplotlib ya presentes. Se eligió CSV largo en vez de Parquet para no incorporar `pyarrow` sólo por persistencia.

## Artefactos generados

- `artifacts/03_report_label_generation/supervision_long_v1.csv`: supervisión larga principal.
- `artifacts/03_report_label_generation/gold_metrics_v1.csv`: métricas pre-override por target.
- `artifacts/03_report_label_generation/error_analysis_v1.csv`: casos auditables gold.
- `artifacts/03_report_label_generation/language_summary_v1.csv`: cobertura lingüística.
- `artifacts/03_report_label_generation/run_metadata_v1.json`: schema, hashes, versión y conteos.

## Figuras generadas

- `figures/03_report_label_generation/status_coverage_by_target_v1.png`: estados por target; utilizada en el reporte de etapa.
- `figures/03_report_label_generation/gold_metrics_by_target_v1.png`: coverage y métricas gold; utilizada en el reporte de etapa.

## Reportes generados

- `reports/stages/03 - report label generation.md`: resultados, decisiones e interpretación.
- `reports/implementation/03 - report label generation implementation.md`: este documento técnico.

## Reproducibilidad

```powershell
python -m unittest discover -s tests -v
python scripts/generate_report_labels.py
```

Los labels, métricas, errores y figuras son deterministas para input y código fijos. `execution_timestamp_utc` del metadata cambia en cada ejecución y está documentado como campo operativo.

## Limitaciones técnicas

La segmentación y el alcance de negación son basados en reglas; no existe parser clínico. Los léxicos requieren mantenimiento explícito y los grupos lingüísticos no sustituyen language identification validado. CSV no conserva tipos nullable tan estrictamente como Parquet, por lo que el schema se valida al generar y se registra en metadata.

## Conexión con el siguiente componente

El pipeline MRI dispone de una fila por Study-target con `final_label`, `final_source`, `confidence` y missing explícito. Debe pivotar por `StudyInstanceUID`, construir máscaras de pérdida para unresolved y mantener mayor peso o tratamiento separado para `official`. El Report no forma parte del contrato de inferencia.
