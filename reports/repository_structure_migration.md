# Repository Structure Migration

## Summary

Se reorganizaron las etapas completadas 01–03 bajo rutas canónicas, se separaron reportes de conocimiento e implementación, y se asignaron figuras y artefactos a su etapa propietaria. La migración preservó métricas, findings, metodología y outputs existentes; no ejecutó DICOM, generación de weak labels ni entrenamiento.

## Motivation

La estructura anterior mezclaba reportes en la raíz de `reports/`, figuras de etapa 01 en `reports/figures/` y nombres con espacios o separadores variables. Esto dificultaba identificar la historia del proyecto y podía hacer que los generadores recrearan rutas obsoletas.

## Naming Convention

Las etapas usan `<NN>_<english_snake_case>`. Los títulos y encabezados canónicos están en inglés, mientras el cuerpo histórico en español se conserva para evitar reescribir evidencia. Los reportes analíticos viven en `reports/stages/`; los reportes técnicos, en `reports/implementation/`.

## Stage Mapping

| Stage | Scope | Canonical report | Supporting outputs |
| --- | --- | --- | --- |
| 00 | Global competition context; no formal stage persisted | Not created | Historical prompts only |
| 01 | Dataset characterization | `reports/stages/01_dataset_characterization.md` | `figures/01_dataset_characterization/`, implementation report, script |
| 02 | Supervision strategy review | `reports/stages/02_supervision_strategy_review.md` | Third-party notebooks remain reference material |
| 03 | Report label generation | `reports/stages/03_report_label_generation.md` | `artifacts/03_report_label_generation/`, `figures/03_report_label_generation/`, implementation report |

## Files Moved or Renamed

| Old path | New path | Role |
| --- | --- | --- |
| `reports/dataset_initial_characterization.md` | `reports/stages/01_dataset_characterization.md` | Stage 01 knowledge report |
| `reports/kaggle_notebooks_supervision_strategy_review.md` | `reports/stages/02_supervision_strategy_review.md` | Stage 02 knowledge report |
| `reports/stages/03 - report label generation.md` | `reports/stages/03_report_label_generation.md` | Stage 03 knowledge report |
| `reports/implementation/03 - report label generation implementation.md` | `reports/implementation/03_report_label_generation_implementation.md` | Stage 03 implementation report |
| `reports/figures/anatomical_plane.png` | `figures/01_dataset_characterization/anatomical_plane.png` | Stage 01 figure |
| `reports/figures/positive_labels_per_study.png` | `figures/01_dataset_characterization/positive_labels_per_study.png` | Stage 01 figure |
| `reports/figures/report_length_chars.png` | `figures/01_dataset_characterization/report_length_chars.png` | Stage 01 figure |
| `reports/figures/series_per_study.png` | `figures/01_dataset_characterization/series_per_study.png` | Stage 01 figure |
| `reports/figures/slices_per_series.png` | `figures/01_dataset_characterization/slices_per_series.png` | Stage 01 figure |
| `reports/figures/target_prevalence.png` | `figures/01_dataset_characterization/target_prevalence.png` | Stage 01 figure |
| `reports/figures/train_missingness.png` | `figures/01_dataset_characterization/train_missingness.png` | Stage 01 figure |
| `prompts/01 - Inspección inicial y reporte descriptivo del dataset — RSNA Knee Abnormality Detection.md` | `prompts/01_dataset_characterization.md` | Historical stage prompt |
| `prompts/02 - revisión de notebooks Kaggle para validar la estrategia de supervisión.md` | `prompts/02_supervision_strategy_review.md` | Historical stage prompt |
| `prompts/03 - implementar desde cero la etapa reproducible de generación de labels desde Report.md` | `prompts/03_report_label_generation.md` | Historical stage prompt |
| `prompts/03.5 - reorganize completed project stages under the current repository structure and naming conventions.md` | `prompts/repository_structure_migration.md` | Historical maintenance prompt |

Se creó `reports/implementation/01_dataset_characterization_implementation.md` porque la etapa 01 sí tiene una implementación ejecutable sustancial. También se creó este informe como documento de mantenimiento a nivel repositorio, sin asignarle un número de etapa analítica.

## Legacy Paths Removed

Se retiraron los cuatro nombres de reportes heredados y el directorio `reports/figures/`. No quedaron copias paralelas de los reportes o imágenes migrados.

## References Updated

Se actualizaron README, enlaces entre reportes, rutas de imágenes, defaults CLI, plantillas generadoras, configuración y metadata de etapa. Los generadores de etapas 01 y 03 ahora escriben directamente en las rutas canónicas.

## Validation Performed

La validación incluye inventario de archivos, búsqueda de referencias heredadas fuera de este registro histórico, resolución de enlaces Markdown locales, compilación de Python, ayuda de los entry points, tests unitarios de report labels y revisión del diff Git. No se regeneraron outputs costosos.

## Remaining Exceptions

- Los cuerpos de los reportes históricos permanecen mayormente en español; sólo títulos y encabezados se normalizaron para preservar evidencia y evitar una reescritura editorial.
- Los prompts conservan internamente su redacción y encabezados originales porque son instrucciones históricas, no outputs oficiales de etapa.
- Los notebooks privados o de terceros no se renombraron ni se trataron como productos del proyecto.
- No se creó un reporte de etapa 00: no existía evidencia analítica persistida suficiente para justificarlo.

## Canonical Structure After Migration

```text
artifacts/
└── 03_report_label_generation/
figures/
├── 01_dataset_characterization/
└── 03_report_label_generation/
reports/
├── stages/
│   ├── 01_dataset_characterization.md
│   ├── 02_supervision_strategy_review.md
│   └── 03_report_label_generation.md
├── implementation/
│   ├── 01_dataset_characterization_implementation.md
│   └── 03_report_label_generation_implementation.md
└── repository_structure_migration.md
```
