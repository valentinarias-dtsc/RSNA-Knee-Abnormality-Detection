# RSNA Knee Abnormality Detection

Pipeline reproducible para construir supervisión de 12 hallazgos de rodilla y preparar un modelo MRI que no dependa del reporte durante inferencia.

## Project Stages

| Stage | Status | Knowledge report | Implementation |
| --- | --- | --- | --- |
| 01 Dataset characterization | Completed | [Report](reports/stages/01_dataset_characterization.md) | [Implementation](reports/implementation/01_dataset_characterization_implementation.md) |
| 02 Supervision strategy review | Completed | [Report](reports/stages/02_supervision_strategy_review.md) | Documentation-only review |
| 03 Report label generation | Completed | [Report](reports/stages/03_report_label_generation.md) | [Implementation](reports/implementation/03_report_label_generation_implementation.md) |
| 04 MRI preprocessing and representation | Next | Not started | Not started |
| 05 Visual baseline | Future | Not started | Not started |

No se creó una etapa 00 formal: el contexto de la competencia se conserva como contexto global porque no había un cuerpo de findings persistidos que justificara un reporte analítico independiente.

## Naming Convention

Los componentes de etapa usan `<NN>_<english_snake_case>`. Los reportes de conocimiento viven en `reports/stages/`, los detalles técnicos en `reports/implementation/`, y cada etapa es dueña de sus outputs bajo `artifacts/<stage>/` y `figures/<stage>/`.

## Stage 03 Reproduction

Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -v
python scripts/generate_report_labels.py
```

El artefacto principal es `artifacts/03_report_label_generation/supervision_long_v1.csv`. Cada fila representa un par `StudyInstanceUID`-target y conserva estado, derived label/score, confidence, evidencia, official label, final label y provenance. `unknown` y `uncertain` permanecen missing salvo que exista un label official.

La implementación no usa DICOM, metadata de Series ni píxeles para derivar labels y no entrena modelos MRI.

## Repository Migration

La reorganización de etapas completadas, las rutas heredadas y las excepciones se documentan en [Repository Structure Migration](reports/repository_structure_migration.md).
