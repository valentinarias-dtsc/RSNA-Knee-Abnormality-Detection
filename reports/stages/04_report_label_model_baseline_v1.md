# Stage 04 — Baseline NLP débilmente supervisada v1

## 1. Scope

Stage 04 implementa la tarea local `target + strict diagnostic clause -> {negative, positive, uncertain, no_evidence}` con un único encoder multilingual compartido por los 12 targets. El teacher es exclusivamente la supervisión textual derivada por `report-label-policy-v3.0.0`.

Esta release incluye construcción reproducible del dataset, exclusión de gold, alineación de surface text, negativos contrastivos conservadores, split agrupado, deduplicación train-only, entrenamiento/evaluación reusable, inferencia de todas las cláusulas strict y agregación Study-target. Todavía **no existe** un test independiente manualmente etiquetado sobre `teacher-unknown`.

El full training no se ejecutó en este entorno: el dispositivo disponible es CPU y el train deduplicado contiene 18.649 ejemplos. Sí se ejecutó un smoke test separado de 8 ejemplos train y 4 validation que validó carga por revisión, forward, backward, checkpoint save/load, inferencia y métricas de integración. Ese smoke no constituye resultados oficiales de Stage 04.

## 2. Upstream supervision

Las únicas fuentes semánticas son `data/train.csv`, `supervision_long_v3.csv`, `evidence_inventory.csv` y el código/config de Stage 03. Se excluyeron las 58 Studies con `final_source == official` usando sólo ese indicador; `official_label` y `final_label` no se cargan en ejemplos ni features.

De las 4.407 Studies fuente quedaron 4.349 elegibles. El filtro teacher exige evidence seleccionada y ganadora, status `positive|negative|uncertain`, `strict_only`, diagnostic, sin collective, sin conflict, y combinaciones formadas sólo por `v2_exact`, `v3_target` y `v3_morphology`.

## 3. Predictive task

La unidad es:

`canonical target description` + `raw strict diagnostic clause` -> local four-way status.

No se usa Report completo, linked view, Mention aislada ni supervisión oficial. `unknown` de v3 nunca se convierte en `no_evidence`.

## 4. Dataset construction

Después del filtrado, alineación exacta y consolidación de provenances ganadoras para la misma unidad local se obtuvieron 24.366 ejemplos teacher. Se generó un único target contrastivo para cada una de 22.508 cláusulas etiquetadas, para un total de 46.874 candidatos.

Cada `no_evidence` cumple: target distinto de todos los targets etiquetados en la cláusula, sin selected evidence, Mention ni Proposition para el candidato, y sin cue del target según lexicons y regex morfológicos v3. La selección es determinista y balanceada por target con seed `20260818`. No se usaron cláusulas sin detector ni Study-target `unknown`.

| local label | candidates |
|---|---:|
| negative | 9.890 |
| positive | 14.136 |
| uncertain | 340 |
| no_evidence | 22.508 |
| total | 46.874 |

## 5. Raw vs normalized text

El teacher mantiene `normalized_clause` para matching, hashes, dedup, families, collision y novelty. El Transformer recibe `raw_clause` con Unicode, diacríticos, capitalización y puntuación; sólo se colapsa whitespace.

La alineación exige `normalize(raw_clause) == normalized_clause`. Se registraron 435 filas de auditoría: 316 cláusulas afectadas por rewrites estructurales conocidos de v3, 114 references a cláusulas no alineadas, 4 casos no diagnostic y 1 mismatch de selected evidence. Ninguno se incorporó silenciosamente mediante fuzzy matching.

## 6. Dataset cardinalities

| stage | examples |
|---|---:|
| trusted aligned teacher | 24.366 |
| contrastive `no_evidence` | 22.508 |
| all candidates | 46.874 |
| train source before dedup | 29.869 |
| train after collisions and dedup | 18.649 |
| validation | 8.509 |
| TEST-ALL | 8.496 |

No hubo collision key `(target, normalized_clause)` con más de un label en train en esta corrida; el artifact se persiste aun vacío.

## 7. Duplicates

El split ocurre antes de dedup. Sólo train se colapsa por `(target, label, normalized_clause)`, conservando representante determinístico, `duplicate_count`, `unique_study_count` y hash/lista de Studies fuente. Se removieron 11.220 repeticiones (37,56% del train source) y quedaron 18.649 filas.

Validation y test conservan todas las instancias para `ALL`. `TEST-UNIQUE` retiene una instancia por `(target, label, normalized_clause)` y `TEST-NOVEL` compara contra todas las keys `(target, normalized_clause)` del train source previo a dedup.

## 8. Split strategy

Los grupos indivisibles usan la familia de Report numeric-normalized de Stage 03; los singletons reciben un ID por Study. El greedy determinista distribuye primero las familias duplicadas por cantidad de Studies y familias, aplica mejora local determinista, y luego aproxima idioma y `target x label` con ratios 70/15/15.

| split | Studies | groups | duplicate Studies | duplicate families | examples |
|---|---:|---:|---:|---:|---:|
| train | 3.082 | 2.974 | 145 | 37 | 29.869 |
| validation | 633 | 614 | 27 | 8 | 8.509 |
| test | 634 | 614 | 28 | 8 | 8.496 |

La proporción observada de Studies es 70,87% / 14,56% / 14,58%.

## 9. Leakage audit

Todas las auditorías pasaron: Study disjointness, duplicate-family disjointness, unicidad del manifest, reconciliación candidate-manifest, splits no vacíos, reproducción con mismo seed y presencia en cada split para 46 strata target-label con soporte en al menos tres grupos.

Manifest SHA-256: `44642fe2c451e09d64d5f134dde4e14e4848454bde3aa8f758fe9c11e21e19b0`.

## 10. Model

Baseline configurada: `FacebookAI/xlm-roberta-base`, revisión `e73636d4f797dec63c3081bb6ed5c7b0bb3f2089`, mediante `AutoTokenizer` y `AutoModelForSequenceClassification`. El smoke confirmó que esa revisión se resuelve y carga.

## 11. Input representation

Se usa pair encoding, dejando los special tokens al tokenizer:

1. `text_a`: canonical target description;
2. `text_b`: raw diagnostic clause.

Detector, rule, language, phenotype, confidence y v3 status no entran al modelo.

## 12. Tokenization/preprocessing

`max_length=128`, truncation y padding dinámico por batch. No hay stemming, lemmatization, accent stripping, punctuation removal, translation ni tokenización manual. La distribución real de truncation se calculará durante el full run con el tokenizer fijado; no se reporta un número antes de medirlo.

## 13. Training configuration

AdamW, learning rate `2e-5`, weight decay `0.01`, warmup `0.10`, hasta 5 epochs, batch 16/32, gradient clipping `1.0`, cross entropy y patience 2. El sampler pondera `target x label` por `1/sqrt(frequency)` con relative cap 10. Mixed precision sólo se habilita si CUDA está disponible.

Python 3.10.11; torch 2.8.0; transformers 4.55.2; scikit-learn 1.7.2. El smoke usó CPU, sin CUDA/GPU, y resolvió el commit configurado.

## 14. Validation trajectory

Pendiente del full run. No se creó `training_history.csv`, curvas ni best checkpoint oficial. El smoke tardó 20,33 segundos en su único epoch diminuto y no se usa para model selection.

## 15. TEST-ALL weak-label agreement

Pendiente del full run. TEST-ALL contiene 8.496 ejemplos. No se reportan accuracy/F1 antes de ejecutar entrenamiento e inferencia reales.

## 16. TEST-UNIQUE

Pendiente del full run. El slice contiene 5.865 ejemplos antes de predicción.

## 17. TEST-NOVEL

Pendiente del full run. El slice contiene 4.866 ejemplos cuya key exacta `(target, normalized_clause)` no aparece en el train source previo a dedup. Esto mide lexical-novel weak-label agreement, no semantic gold generalization.

## 18. Language slices

El manifest intenta preservar los diez `language_group` descriptivos de v3. Las métricas y supports por idioma se producirán en `metrics_by_language.csv` durante el full run.

## 19. Teacher-source / phenotype slices

Detector combinations y phenotype se preservan sólo como metadata. Sus métricas se producirán en `metrics_by_detector.csv` y `metrics_by_phenotype.csv`; no son features.

## 20. Study-level weak-label agreement

El código infiere todas las strict diagnostic clauses de validation/test para los 12 targets y agrega con `positive > uncertain > negative > no_evidence`; sólo `no_evidence` produce `unknown` cuando no hay otra evidence local. La comparación se hace exclusivamente contra v3 DERIVED status. Resultados pendientes del full run.

## 21. Error analysis

Pendiente de predicciones oficiales. El análisis implementado conserva raw clause, target, teacher provenance, predicted status, logits y softmax scores. Los futuros casos se describirán como disagreement contra el teacher; los softmax scores no se interpretarán como probabilidades calibradas.

## 22. Reproducibility

Config SHA-256: `69bc88008fb57997525cd4789385d09a142a4e6f0f6e184218a62ebe8f0f8d7e`. Los hashes de inputs y outputs están en `run_metadata.json`.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/train_report_label_model.py --config config/04_report_label_model/baseline_xlmr_v1.json --prepare-only
python scripts/train_report_label_model.py --config config/04_report_label_model/baseline_xlmr_v1.json --smoke-test
python scripts/train_report_label_model.py --config config/04_report_label_model/baseline_xlmr_v1.json
```

El último comando construye, entrena, selecciona sólo con validation, evalúa, infiere todas las strict clauses, agrega por Study y genera reportes tabulares/figuras. Requiere tiempo de cómputo adecuado; se recomienda CUDA para esta baseline.

## 23. Limitations

- Training y test labels provienen de la misma teacher family.
- TEST-NOVEL sólo excluye exact normalized target-clause overlap; no garantiza semantic novelty.
- Weak-label agreement no estima clinical accuracy.
- No existe aún evaluación manual sobre v3 unknown.
- No se realizó calibration ni threshold optimization.
- Linked views y collective evidence no se entrenaron.
- No se compararon encoders biomedical multilingual.
- No se realizó hyperparameter search.
- Los 58 official-label Studies no se utilizaron.
- El full training no se ejecutó en este entorno CPU; no hay métricas oficiales Stage 04 en esta entrega local.

## 24. Artifact index

| artifact | purpose |
|---|---|
| `candidate_examples.csv` | dataset candidato con surface text y provenance |
| `alignment_failures.csv` | exclusiones de alineación auditables |
| `no_evidence_generation_summary.csv` | guards y selección contrastiva |
| `excluded_official_studies.json` | manifest de aislamiento gold sin valores de label |
| `label_collision_cases.csv` | collisions train (vacío en esta corrida) |
| `split_assignments.csv` | asignación Study/family |
| `split_summary.csv` | cardinalidades por split y target-label |
| `split_leakage_audit.csv/json` | invariantes y reproducción |
| `train_examples_dedup.csv` | train final deduplicado |
| `validation_examples.csv` | weak-label validation ALL |
| `test_examples.csv` | weak-label test ALL con novelty flags |
| `dedup_summary.csv` | impacto de collision filtering/dedup |
| `test_slice_summary.csv` | supports ALL/UNIQUE/NOVEL |
| `run_metadata.json` | hashes, environment, counts y status |
| `dataset_size_before_after_dedup.png` | figura de cardinalidad |

Los artifacts de training, métricas, predicciones, agregación y curvas definidos por la pipeline se crean sólo al completar el full run. El checkpoint y el directorio smoke permanecen ignorados por Git.

