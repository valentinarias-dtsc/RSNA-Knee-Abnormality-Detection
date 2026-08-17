Trabajá sobre el repositorio actual del proyecto `RSNA-Knee-Abnormality-Detection`.

## Objetivo

Realizar una inspección fáctica y reproducible de los datos y artefactos existentes relacionados con `03_report_label_generation`, especialmente la policy/report-label implementation vigente v3, para producir evidencia descriptiva que posteriormente pueda ser utilizada por el equipo para tomar decisiones sobre un posible modelo NLP supervisado.

IMPORTANTE:

- NO diseñes el modelo.
- NO recomiendes arquitecturas.
- NO elijas pretrained models.
- NO propongas estrategias de fine-tuning.
- NO decidas cuál debería ser la unidad de entrenamiento.
- NO determines qué reglas deberían formar parte de un futuro teacher.
- NO concluyas que una alternativa es mejor que otra.
- NO realices inferencias sobre qué estrategia de modelado "conviene".
- NO modifiques las policies de report-label generation actuales.
- NO cambies los labels existentes.
- NO utilices los 58 labels oficiales para ajustar reglas, seleccionar subconjuntos de ejemplos o diseñar decisiones.
- NO uses PixelData, DICOM metadata, Series metadata, scanner ni anatomical plane para generar o reinterpretar labels.

Tu tarea es exclusivamente:

1. inspeccionar;
2. medir;
3. documentar;
4. generar artefactos reproducibles;
5. dejar evidencia utilizable para decisiones posteriores.

Toda interpretación debe mantenerse estrictamente descriptiva.

---

# 1. Antes de implementar

Inspeccioná primero el estado real del repositorio.

Revisá, como mínimo:

- `src/report_labels/`
- `src/report_labels/v3/`
- `config/03_report_label_generation/`
- `reports/stages/03_report_label_generation_v3.md`
- reportes de implementación relacionados con stage 03, si existen;
- `tests/test_report_labels_v3.py`;
- artefactos existentes de report labels;
- scripts/entrypoints actuales usados para stage 03;
- estructura actual de `data/`, `artifacts/`, `reports/`, `figures/`, `scripts/` u otros directorios equivalentes.

No asumas nombres de archivos si pueden ser descubiertos en el repositorio.

Reutilizá convenciones, helpers, paths y estructura existentes siempre que sea razonable.

Si necesitás crear nuevos directorios, hacelo siguiendo la organización vigente del proyecto.

---

# 2. Reproducibilidad

Implementá las inspecciones mediante uno o más scripts reproducibles.

Preferentemente:

- código bajo un directorio consistente con los scripts existentes;
- outputs tabulares persistidos como CSV;
- metadata de ejecución en JSON;
- reporte final en Markdown;
- figuras sólo cuando aporten información descriptiva difícil de leer en tablas.

El script debe poder ejecutarse nuevamente sobre los mismos inputs para reconstruir los mismos artefactos semánticos.

Registrá como mínimo:

- timestamp de ejecución;
- paths de inputs;
- hashes SHA-256 de inputs relevantes;
- versión/policy de report labels utilizada;
- número de Studies;
- número de Study-target pairs;
- parámetros explícitos usados por la inspección;
- paths y SHA-256 de outputs generados;
- schema de los artefactos principales.

No sobrescribas silenciosamente artefactos de otras versiones.

---

# 3. Población bajo estudio

La inspección debe caracterizar por separado, cuando corresponda:

1. Reportes completos.
2. Study × target pairs.
3. `TextView` strict.
4. `TextView` linked.
5. mentions.
6. propositions.
7. evidence seleccionada finalmente.
8. status final derivado:
   - positive
   - negative
   - uncertain
   - unknown
9. phenotypes.
10. detectors.
11. rules.
12. idiomas/language hypotheses o `language_group`.
13. familias de templates o duplicados, si pueden reconstruirse consistentemente.

No mezcles estas unidades en una misma métrica sin explicitar el denominador.

---

# 4. Inspecciones requeridas

## A. Tamaño real del corpus candidato

Cuantificá:

- número de Reports;
- número total de cláusulas generadas por la segmentación vigente;
- cláusulas por Report:
  - mean
  - std
  - median
  - min
  - max
  - percentiles 5, 25, 75, 95;
- número de `strict TextView`;
- número de `linked TextView`;
- número de mentions;
- número de propositions;
- número de evidences finalmente seleccionadas;
- número de Study × target pairs:
  - positive;
  - negative;
  - uncertain;
  - unknown;
  - binary resolved.

Cuando sea posible, mostrar estos conteos también por target.

---

## B. Longitud textual

Para:

- Report completo;
- strict clause/view;
- linked view;
- evidence seleccionada;

calcular al menos:

### caracteres
- mean
- std
- median
- min
- max
- p05
- p25
- p75
- p95
- p99

### palabras/tokens simples
Usar una tokenización descriptiva simple y documentada, sin depender aún de ningún tokenizer de un modelo específico.

Calcular las mismas estadísticas.

No recomiendes un `max_length`; sólo reportá la distribución.

---

## C. Distribución por target y status

Crear una tabla target × status con:

- count;
- porcentaje sobre los 4,407 pares de ese target;
- positive;
- negative;
- uncertain;
- unknown;
- binary resolved rate.

Incluir además:

- ratio positive / binary-resolved;
- ratio negative / binary-resolved.

No interpretar imbalance como un problema ni recomendar correcciones.

---

## D. Distribución por idioma

Por `language_group` y, cuando esté disponible, por hypotheses de idioma:

- número de Reports;
- número de Study-target pairs;
- positive;
- negative;
- uncertain;
- unknown;
- resolved rate;
- número de strict views;
- número de linked views;
- número de mentions;
- número de propositions.

Luego generar:

- idioma × target × status;
- idioma × target × resolved rate.

No concluir si un idioma está "bien" o "mal" cubierto. Sólo describir diferencias.

---

## E. Teacher-source / detector provenance

Caracterizar las fuentes actuales de supervisión.

Por detector:

- `v2_exact`
- `v2_collective`
- `v3_morphology`
- `v3_target`
- cualquier otro detector realmente existente

medir:

- mentions;
- propositions;
- Study-target pairs finales en cuya selected provenance participa;
- target;
- status;
- phenotype;
- language;
- rule.

Importante:

Una Proposition puede estar soportada por más de un detector.

No sumar participaciones de detectors como si fueran ejemplos independientes.

Crear además una tabla que indique cuántas propositions tienen:

- 1 detector;
- 2 detectors;
- 3+ detectors;

y cuáles son las combinaciones más frecuentes.

---

## F. Confianza actual

Describir la distribución de `confidence` actual por:

- target;
- status;
- detector;
- rule;
- phenotype;
- language.

Reportar los valores únicos de confidence observados y sus frecuencias.

Separar:

- casos sin conflicto;
- casos con conflicto, si puede reconstruirse desde rationale/provenance;
- collective;
- target-specific.

No interpretar confidence como probabilidad.

Recordar explícitamente en el reporte que la policy la define como ranking determinista de fuerza de evidencia, no como probabilidad calibrada.

---

## G. Phenotypes

Inventariar todos los phenotypes observados.

Para cada phenotype:

- count de propositions;
- count de Study-target pairs finales donde participa;
- targets;
- status;
- detectors;
- languages;
- rules.

Crear target × phenotype × status.

Incluir porcentaje de cada phenotype dentro de cada target/status cuando el denominador sea claro.

No decidir si phenotype debería formar parte de un futuro output del modelo.

---

## H. Rules

Inventariar todas las reglas realmente utilizadas en los artefactos v3.

Por `rule`:

- detector;
- target;
- language;
- phenotype;
- status;
- number of mentions;
- number of propositions;
- number of Studies;
- number of Study-target pairs finales donde participa.

También mostrar:

- las reglas con mayor número de ejemplos;
- distribución acumulada de ejemplos por regla.

Objetivo descriptivo:
permitir observar si grandes cantidades de ejemplos derivan de pocas reglas.

No etiquetar esto como bueno/malo.

---

## I. Duplicados exactos

Analizar duplicación en al menos:

1. Reports completos normalizados.
2. strict views normalizadas.
3. linked views normalizadas.
4. evidence normalizada.

Para cada nivel:

- total instances;
- unique texts;
- duplicated instances;
- duplicate rate;
- número de grupos duplicados;
- tamaño medio/mediano/máximo de grupo;
- distribución de tamaños de grupos.

Generar un artefacto con los grupos más grandes, preservando IDs necesarios para auditoría.

No interpretar los duplicados como leakage todavía; sólo documentarlos.

---

## J. Familias de templates

Reutilizar, si existe, la lógica actual de `exact_template_consistency` o mecanismos equivalentes de stage 03.

Caracterizar por separado:

- exact templates;
- numeric-normalized templates;
- cualquier otra categoría ya implementada.

Medir:

- número de familias;
- número de Reports cubiertos;
- tamaño de cada familia;
- distribución de tamaños;
- target/status asociados;
- idiomas;
- cantidad de familias completamente homogéneas en status;
- cantidad de familias con heterogeneidad, si existe.

No desarrollar nuevos algoritmos complejos de clustering semántico para esta tarea.

Esta inspección debe ser reproducible y basada preferentemente en las definiciones que ya existen en el repositorio.

---

## K. Diversidad léxica superficial

Sin usar embeddings ni modelos externos, calcular estadísticas descriptivas por target/status para las evidences o cláusulas positivas/negativas:

- número de textos únicos;
- número de tokens únicos;
- type-token ratio, aclarando su dependencia de longitud;
- cantidad de unigramas frecuentes;
- cantidad de bigramas frecuentes;
- porcentaje cubierto por los N unigramas/bigramas más frecuentes, usando varios N descriptivos (por ejemplo 10, 25, 50, 100 cuando haya suficientes).

Generar tablas con los n-grams más frecuentes por target/status.

NO usar estas métricas para afirmar que existe mayor o menor "complejidad semántica".

Sólo describir concentración o diversidad lexical observable.

---

## L. Similitud textual basada en templates / texto, no embeddings

Sin elegir aún ningún pretrained model, medir de forma simple y reproducible cuánto se parecen los ejemplos etiquetados entre sí usando métodos puramente textuales, por ejemplo:

- exact match;
- normalized exact match;
- Jaccard sobre tokens;
- TF-IDF cosine similarity, si se considera útil como análisis descriptivo.

Si se usa TF-IDF:

- documentar vectorizer y parámetros;
- no tratarlo como modelo candidato;
- utilizarlo exclusivamente para describir redundancia/similitud superficial.

No realizar clustering interpretativo salvo que sea estrictamente necesario para resumir la distribución.

---

## M. Evidencia positiva y negativa por target

Para cada target:

- número de evidences positivas;
- negativas;
- uncertain;
- evidence texts únicos;
- proportion duplicated;
- detector source;
- phenotype;
- rule;
- language.

Crear ejemplos auditables, pero limitar la cantidad en el reporte principal.

Guardar un CSV separado con los registros completos necesarios para inspección manual.

---

## N. Conflictos

Identificar todos los Study-target pairs cuya resolución v3 conserve una conflicting proposition o rationale equivalente.

Medir:

- count total;
- porcentaje;
- target;
- winning status;
- conflicting status;
- detectors involucrados;
- phenotypes;
- rules;
- languages;
- confidence final.

Guardar provenance completa en un artefacto auditable.

No resolver ni reinterpretar estos casos.

---

## O. Collective evidence

Caracterizar por separado las propositions colectivas.

Medir:

- count;
- targets;
- positive/negative/uncertain;
- rule;
- language;
- phenotype;
- confidence;
- cuántas terminan seleccionadas como evidencia final.

No decidir si deben formar parte de un futuro training set.

---

## P. Strict vs linked views

Caracterizar cuánto aporta cada tipo de view.

Para cada `view_kind`:

- cantidad de views;
- cantidad de mentions;
- cantidad de propositions;
- targets;
- status;
- detectors;
- rules;
- phenotypes.

Además:

- propositions sostenidas sólo por strict;
- sólo por linked;
- por ambas;
- Study-target pairs cuya selected evidence depende de linked views.

Guardar ejemplos de estos grupos en un artefacto separado.

No concluir si linked debería mantenerse o eliminarse.

---

## Q. Contexto requerido alrededor de evidence

A partir de provenance/source indices, cuando sea reconstruible:

medir cuántos resultados finales provienen de:

- una sola cláusula;
- linked view de dos cláusulas;
- evidencia colectiva;
- otras estructuras existentes.

Para cada grupo mostrar:

- target;
- status;
- detector;
- phenotype;
- rule.

No determinar aún cuál debería ser el tamaño de contexto de un futuro modelo.

---

## R. Negación

Inventariar ejemplos/resoluciones donde la polaridad dependa de negación.

Cuando sea posible reconstruirlo objetivamente desde el código/provenance:

- target;
- language;
- status;
- detector;
- rule;
- tipo de negación:
  - preposed;
  - postposed;
  - explicit normality;
  - otro tipo ya implementado.

Contabilizar ejemplos.

No desarrollar una nueva clasificación lingüística si no está soportada por la implementación.

---

## S. Uncertainty

Caracterizar los  casos `uncertain`:

- count;
- target;
- language;
- detector;
- rule;
- phenotype;
- evidence text;
- patrones de uncertainty detectados, únicamente cuando puedan atribuirse directamente a las reglas existentes.

Medir textos únicos y duplicación.

No decidir si `uncertain` debería ser clase, excluirse o binarizarse.

---

## T. Unknown

Caracterizar `unknown` únicamente desde variables observables.

Para cada target/language:

- count;
- rate.

No afirmar que un `unknown` no contiene hallazgos clínicos.

No etiquetar `unknown` como irrelevant.

Si analizás cláusulas de Reports asociados a unknown, hacerlo únicamente para describir:

- número de cláusulas;
- longitud;
- idioma;
- presencia de otros targets resueltos en el mismo Report;
- estructura del reporte.

NO reinterpretar manual o automáticamente los unknown para crear nuevos labels.

---

## U. Posibles `irrelevant` observables sin asumir label semántico

No generes una clase `irrelevant`.

En su lugar, podés caracterizar descriptivamente:

- cláusulas diagnósticas no utilizadas como selected evidence para un target;
- cláusulas que contienen evidencia para otro target;
- cláusulas sin menciones de ningún detector.

Reportar sólo conteos y relaciones.

No convertirlas en training labels.

---

## V. Distribución de evidencia por Study

Medir:

- número de targets resolved por Study;
- positive targets por Study;
- negative targets por Study;
- uncertain por Study;
- unknown por Study;
- número de propositions por Study;
- número de evidence fragments únicos por Study.

Mostrar distribución y percentiles.

---

## W. Co-ocurrencia de targets

Generar matrices descriptivas de co-ocurrencia Study-level para:

- positive-positive;
- binary-resolved;
- shared evidence text, si existe.

No interpretar correlaciones como causalidad ni recomendar modelos multi-label.

---

## X. Independencia efectiva de ejemplos

Sin emitir una conclusión, generar métricas que permitan evaluar posteriormente cuán independientes son los ejemplos:

por target/status:

- raw evidence count;
- unique normalized evidence count;
- unique Report count;
- unique exact-template family count;
- unique numeric-normalized-template family count;
- detector-rule combinations;
- language groups.

Crear una tabla denominada, por ejemplo:

`effective_example_structure.csv`

No inventar un "effective sample size" estadístico salvo que exista una definición explícita y defendible ya acordada.

---

# 5. Auditoría manual asistida

No realizar anotación clínica nueva.

Sí preparar artefactos que faciliten una auditoría posterior humana.

Generar muestras deterministas y estratificadas de registros, por ejemplo:

- target;
- status;
- detector;
- rule;
- phenotype;
- language;
- conflict/no-conflict;
- strict/linked;
- collective/target-specific.

Usar una seed fija.

Persistir los sample IDs y la seed.

No escribir juicios como `correct`, `incorrect`, `likely correct`, etc.

La finalidad es únicamente preparar muestras inspeccionables.

---

# 6. Tests y validaciones del script

Agregar tests razonables para el nuevo código.

Como mínimo verificar:

- determinismo de outputs semánticos;
- cardinalidades;
- ausencia de pérdida de StudyInstanceUID;
- denominadores correctos;
- joins one-to-one o many-to-one según corresponda;
- status válidos;
- targets válidos;
- que las métricas de conteo reconcilien con los artefactos v3 existentes;
- que los ejemplos/sample outputs puedan rastrearse hasta el artefacto fuente.

No modificar tests existentes salvo que sea estrictamente necesario para compatibilidad, y en ese caso documentarlo.

---

# 7. Artefactos esperados

Adaptá nombres y paths a las convenciones reales del repositorio.

Como mínimo quiero artefactos equivalentes a:

- `corpus_unit_counts.csv`
- `text_length_summary.csv`
- `target_status_summary.csv`
- `language_target_status_summary.csv`
- `detector_summary.csv`
- `detector_combination_summary.csv`
- `confidence_summary.csv`
- `phenotype_summary.csv`
- `rule_summary.csv`
- `duplicate_summary.csv`
- `duplicate_groups.csv`
- `template_family_summary.csv`
- `lexical_diversity_summary.csv`
- `ngram_summary.csv`
- `evidence_inventory.csv`
- `conflict_cases.csv`
- `collective_evidence_summary.csv`
- `view_kind_summary.csv`
- `linked_view_dependency_cases.csv`
- `uncertain_summary.csv`
- `unknown_summary.csv`
- `study_level_distribution.csv`
- `target_cooccurrence.csv`
- `effective_example_structure.csv`
- `audit_sample.csv`
- `inspection_run_metadata.json`

No es obligatorio usar exactamente estos nombres si la estructura existente del proyecto indica otros mejores.

Evitar archivos redundantes.

---

# 8. Reporte final

Generar un reporte Markdown versionado y ubicado de manera consistente con los reportes existentes.

Título sugerido:

`Report-label corpus inspection for NLP modeling evidence`

El reporte debe ser AUTOCONTENIDO desde el punto de vista descriptivo.

Debe incluir:

## 1. Scope
Qué se inspeccionó y qué explícitamente NO se hizo.

## 2. Sources
Código, configs, datasets y artefactos usados.

## 3. Reproducibility
Script/entrypoint, hashes, metadata, policy version.

## 4. Units of analysis
Definición exacta de Report, clause, TextView, Mention, Proposition, evidence y Study-target pair según la implementación vigente.

## 5. Corpus size
Conteos principales.

## 6. Target/status distribution

## 7. Language distribution

## 8. Text lengths

## 9. Detector provenance

## 10. Confidence distribution

## 11. Phenotypes

## 12. Rules

## 13. Duplicates and template families

## 14. Lexical/textual diversity

## 15. Strict vs linked evidence

## 16. Collective evidence

## 17. Conflicts

## 18. Uncertain cases

## 19. Unknown population
Únicamente descripción observable.

## 20. Study-level structure and target co-occurrence

## 21. Effective example structure
Mostrar las métricas de redundancia/diversidad necesarias para posteriores decisiones.

## 22. Audit sample
Explicar cómo fue generado y dónde se encuentra.

## 23. Limitations of this inspection
Sólo limitaciones metodológicas de las mediciones:
- dependencia de las reglas actuales;
- language_group heurístico;
- templates definidos por los mecanismos usados;
- lexical similarity no equivale a semantic similarity;
- etc.

## 24. Artifact index
Lista de outputs con path y descripción.

---

# 9. Estilo del reporte

El tono debe ser:

- profesional;
- técnico;
- descriptivo;
- verificable;
- neutral.

Evitar frases como:

- "por lo tanto deberíamos...";
- "esto demuestra que conviene...";
- "el mejor modelo sería...";
- "hay suficientes datos";
- "no hay suficientes datos";
- "este target es fácil/difícil";
- "la clase está demasiado desbalanceada";
- "deberíamos excluir...";
- "esto justifica...".

En su lugar usar formulaciones puramente descriptivas, por ejemplo:

- "`MCL` contiene N ejemplos positivos derivados, de los cuales X% pertenecen a Y familias de templates."
- "El 80% de las evidences de este grupo está cubierto por N textos normalizados únicos."
- "Las linked views participan en N propositions y son la única view asociada a N Study-target pairs seleccionados."
- "La distribución observada es..."
- "La métrica no permite determinar..."

---

# 10. No utilizar conocimiento externo

Para esta tarea no es necesario hacer web research ni consultar papers/model cards.

No investigar BioBERT, ClinicalBERT, PubMedBERT, XLM-R ni otros modelos.

La tarea termina en la caracterización del corpus y de la supervisión disponible.

---

# 11. Relación con gold

Los 58 Studies con official labels pueden aparecer únicamente en:

- controles de cardinalidad existentes;
- reproducción de los artefactos actuales;
- documentación de la estructura del dataset.

No usar sus valores para:

- evaluar qué detector es mejor;
- seleccionar reglas;
- estimar qué ejemplos son fiables;
- seleccionar training examples;
- ajustar thresholds;
- comparar posibles teachers.

Este reporte debe ser utilizable ANTES de tomar esas decisiones.

Si algún artefacto actual mezcla `official_label`, `derived_label` y `final_label`, para estas inspecciones de teacher/corpus usar primordialmente los resultados derivados de reportes (`status`, `derived_label`, provenance), no el override oficial.

---

# 12. Entregable de implementación

Al terminar:

1. mostrar los archivos creados/modificados;
2. indicar el comando exacto para reproducir la inspección;
3. ejecutar los tests relevantes;
4. ejecutar el pipeline de inspección;
5. verificar que los artefactos esperados existan;
6. verificar que las cardinalidades principales reconcilien con v3;
7. resumir únicamente:
   - qué se inspeccionó;
   - qué artefactos se generaron;
   - si las validaciones pasaron.

NO agregues una sección de recomendaciones de modelado.

NO cierres con conclusiones sobre qué modelo debería entrenarse.