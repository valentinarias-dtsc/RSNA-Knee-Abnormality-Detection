# Revisión de notebooks Kaggle: estrategia de supervisión

## Conclusión

**Sí, con salvedades importantes.**

Los notebooks respaldan explícitamente el flujo central: usar `Report` para producir targets —labels derivados, weak labels o soft labels— en los estudios sin las 12 anotaciones, combinar esos targets con los 58 estudios completamente etiquetados y entrenar modelos que predicen los 12 hallazgos a partir del MRI.

La principal salvedad es que los datos Study/Series no se utilizan, en general, para **derivar labels**: aparecen como inputs visuales, metadata auxiliar o incluso como una rama predictiva independiente. Además, algunos notebooks son de inferencia y consumen checkpoints ya entrenados, por lo que documentan la estrategia de supervisión pero no ejecutan íntegramente su construcción.

## Evidencia por notebook

**`0-899-let-me-cook.ipynb`**

- Uso del `Report`: ejecuta un extractor sobre todos los reportes; puede sustituir sus resultados por una tabla de labels previamente extraídos mediante otro lector.
- Origen de los labels usados para entrenamiento: los 58 estudios con las 12 anotaciones completas tienen prioridad y mayor peso; los restantes reciben los 12 targets derivados del reporte.
- Tratamiento de targets missing/no observados: una fila sólo se considera explícitamente etiquetada si tiene completos los 12 targets; en caso contrario utiliza el vector derivado. Las menciones ausentes reciben baja confianza y menor peso.
- Inputs esperados en inferencia: MRI DICOM y metadata de Series/Study; no utiliza `Report`.
- Evaluación respecto de la hipótesis: `explícita`.

**`rsna-knee-baseline-v1.ipynb`**

- Uso del `Report`: declara que `train.csv` contiene `Report` y `test.csv` no; emplea un extractor multilingüe o una tabla de labels leídos previamente.
- Origen de los labels usados para entrenamiento: targets derivados para el corpus amplio y anotaciones explícitas, con mayor peso, para los 58 estudios completos.
- Tratamiento de targets missing/no observados: los estudios sin las 12 anotaciones completas reciben targets derivados; la confianza del extractor actúa por target como peso de supervisión.
- Inputs esperados en inferencia: exclusivamente datos MRI y metadata necesaria para interpretar las series.
- Evaluación respecto de la hipótesis: `explícita`.

**`rsna-knee-dinov2-at-meniscus-resolution.ipynb`**

- Uso del `Report`: afirma que los labels de los 4.349 estudios no anotados deben derivarse del reporte; acepta soft labels extraídos previamente o ejecuta un extractor inline.
- Origen de los labels usados para entrenamiento: matriz de soft labels para los 4.407 estudios, sobrescrita con los labels oficiales en los 58 estudios completos.
- Tratamiento de targets missing/no observados: los targets explícitos ausentes se reemplazan por labels derivados; en el fallback por reglas, la falta de una extracción se completa con cero. Los 58 estudios explícitos reciben mayor peso.
- Inputs esperados en inferencia: imágenes MRI, manifiesto de series y metadata disponible en ambos splits; el código indica expresamente que las features no leen reportes.
- Evaluación respecto de la hipótesis: `explícita`.

**`rsna-knee-enhanced-ensemble.ipynb`**

- Uso del `Report`: no lo procesa porque es un notebook de inferencia; declara que los reportes deben supervisar el entrenamiento y no estar disponibles en test.
- Origen de los labels usados para entrenamiento: upstream, incorporados en los checkpoints adjuntos; el notebook señala que esos checkpoints dependen de supervisión derivada de reportes.
- Tratamiento de targets missing/no observados: no construye el training set ni resuelve targets missing; sólo constata la existencia de 58 estudios completamente anotados.
- Inputs esperados en inferencia: `test.csv`, `test_series.csv`, DICOM y checkpoints; no requiere texto.
- Evaluación respecto de la hipótesis: `explícita`.

**`rsna-knee-read-the-report-then-the-knee.ipynb`**

- Uso del `Report`: establece literalmente el procedimiento “leer los reportes como targets, entrenar un modelo puramente visual y descartar el texto”; implementa extracción graduada y distintas fuentes de labels derivados.
- Origen de los labels usados para entrenamiento: reportes procesados por extractores o consenso de varios lectores; los 58 labels oficiales sobrescriben los derivados y reciben mayor peso.
- Tratamiento de targets missing/no observados: los estudios sin labels explícitos reciben weak/soft labels. La ruta base reduce el peso de hallazgos no mencionados; otras ramas exigen disponibilidad de múltiples fuentes derivadas antes de formar el consenso.
- Inputs esperados en inferencia: MRI y, en algunas ramas, metadata DICOM/Series; `Report` no es requerido.
- Evaluación respecto de la hipótesis: `explícita`.

## Síntesis transversal

El flujo predominante es:

`Report → extracción/estimación de los 12 labels → combinación con los 58 labels explícitos → entrenamiento del modelo MRI → predicción de los 12 targets`

La metadata Study/Series aparece principalmente después de la construcción de los labels, como input del modelo o de ramas predictivas. No hay evidencia transversal suficiente para describirla como una fuente general de derivación de labels. El `Report` se mantiene como supervisión de entrenamiento y no como input necesario durante inferencia.

## Implicación para el proyecto

**Continuar con una etapa específica de extracción/estimación de labels desde los reportes antes de desarrollar el baseline visual.**
