# RSNA Knee Abnormality Detection

Pipeline reproducible para construir supervisión de 12 hallazgos de rodilla. La etapa
actual deriva weak labels exclusivamente desde `Report`, evalúa la extracción contra
los 58 Studies gold y aplica después la prioridad de labels oficiales.

## Etapa 03: labels desde Report

Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -v
python scripts/generate_report_labels.py
```

El artefacto principal queda en
`artifacts/03_report_label_generation/supervision_long_v1.csv`. Cada fila representa
un par `StudyInstanceUID`-target y conserva estado, derived label/score, confidence,
evidencia, official label, final label y provenance. `unknown` y `uncertain` permanecen
missing salvo que exista un label official.

La implementación no usa DICOM, metadata de Series ni píxeles y no entrena modelos MRI.
