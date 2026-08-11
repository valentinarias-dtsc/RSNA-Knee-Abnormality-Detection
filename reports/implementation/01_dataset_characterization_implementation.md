# 01 Dataset Characterization — Implementation

## Technical Summary

La caracterización se implementa como un script Python reproducible que inspecciona las tablas del dataset, la jerarquía física Study/Series/Slice y una instancia DICOM determinista por Study. Produce un reporte Markdown y siete figuras sin cargar `PixelData` ni entrenar modelos.

## Stage Context

Esta implementación respalda `reports/stages/01_dataset_characterization.md`. Su propósito es establecer la estructura, granularidad, completitud y distribución descriptiva del dataset antes de decidir cómo construir supervisión.

## Architecture

```text
CSV tables + directory hierarchy + sampled DICOM headers
    → schema and relationship checks
    → descriptive statistics
    → Markdown tables and narrative
    → stage-owned figures
```

## Files Created or Modified

- `scripts/dataset_characterization.py`: análisis, validaciones, gráficos y generación del reporte.
- `reports/stages/01_dataset_characterization.md`: salida narrativa versionada.
- `figures/01_dataset_characterization/`: figuras versionadas de la etapa.

## Modules and Responsibilities

El script concentra lectura tabular, recorrido de archivos, muestreo determinista de headers DICOM, estadísticas descriptivas, validaciones de UIDs, renderizado de tablas Markdown y generación de gráficos. No existe un paquete reusable separado para esta etapa histórica.

## Entry Points

Desde la raíz del repositorio:

```powershell
python scripts/dataset_characterization.py
```

Los destinos se pueden sustituir con `--report` y `--figures-dir`; `--data-dir` cambia la fuente y `--max-dicom-studies` limita la inspección de Studies para una ejecución diagnóstica.

## Configuration

Los defaults canónicos son `data/`, `reports/stages/01_dataset_characterization.md` y `figures/01_dataset_characterization/`. No hay archivo de configuración independiente.

## Tests

No existe una suite unitaria específica para este script histórico. La validación de la migración comprueba sintaxis, ayuda CLI, existencia de outputs y resolución de enlaces, sin repetir la inspección DICOM costosa.

## Dependencies

Python, pandas, NumPy, Matplotlib y pydicom. El muestreo y la selección de instancias son deterministas.

## Generated Artifacts

La etapa no persiste tablas intermedias como artefactos canónicos; los resultados tabulares relevantes están incorporados en el reporte.

## Generated Figures

El directorio `figures/01_dataset_characterization/` contiene gráficos de prevalencia, labels positivos, composición Study/Series/Slice, plano anatómico, longitud de reportes y missingness.

## Reproduction

La ejecución completa puede recorrer un volumen grande de archivos. La migración no la repitió porque los resultados existentes se preservaron sin modificación semántica.

## Technical Limitations

La metadata DICOM proviene de una instancia determinista por Study y no representa todas las variaciones entre Series o Slices. El tamaño total es estimado y la detección de secciones de reportes es léxica.

## Interface With the Next Stage

La etapa establece que `StudyInstanceUID` es la unidad central, que `Report` sólo existe en train y que los targets oficiales están escasamente observados. Esos hallazgos alimentan `reports/stages/02_supervision_strategy_review.md`.
