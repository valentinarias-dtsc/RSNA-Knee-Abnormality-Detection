Trabajá sobre el estado ACTUAL del repositorio:

`valentinarias-dtsc/RSNA-Knee-Abnormality-Detection`

Objetivo general:
implementar una primera baseline reproducible de clasificación NLP débilmente supervisada como un NUEVO STAGE 04, utilizando como teacher la supervisión textual derivada por `report-label-policy-v3.0.0`.

La implementación debe respetar el estilo y la arquitectura de ingeniería que ya utiliza el repositorio:

- lógica reusable y testeable dentro de `src/`;
- scripts bajo `scripts/` como entrypoints/orquestadores finos;
- configuración declarativa versionada bajo `config/`;
- artefactos reproducibles bajo `artifacts/`;
- figuras bajo `figures/`;
- reportes analíticos bajo `reports/stages/`;
- reportes técnicos bajo `reports/implementation/`;
- tests bajo `tests/`;
- no implementar lógica sustantiva en notebooks;
- no crear un script monolítico de entrenamiento.

Antes de modificar código, inspeccioná el estado actual del repositorio y reutilizá las convenciones, helpers, schemas, segmentación, provenance y artefactos existentes cuando corresponda.

No asumas que este prompt conoce cada nombre de archivo actualizado: verificá los paths reales antes de implementar.

---

# 1. Alcance exacto de Stage 04 v0

Este stage implementa una baseline de:

    (target, strict diagnostic clause) -> local status

utilizando un único encoder Transformer multilingual compartido por los 12 targets.

El output local debe tener cuatro estados conceptuales:

- `positive`
- `negative`
- `uncertain`
- `no_evidence`

IMPORTANTE:

`no_evidence` NO es equivalente a `unknown` de report-label v3.

Nunca convertir automáticamente:

    Study-target status == unknown

en:

    clause-target == no_evidence

Los `unknown` de v3 pueden contener hallazgos que las reglas simplemente no reconocieron.

La construcción de un test set manual con casos no etiquetados/resueltos por las reglas QUEDA FUERA DE ESTE STAGE.

No crear ese gold test.
No pseudo-anotarlo.
No inferir ground truth para unknown.
No utilizar el modelo para convertir unknown en nuevos training labels.

Ese componente será incorporado en una actualización posterior.

---

# 2. Qué debe responder esta primera baseline

Stage 04 debe permitir medir reproduciblemente:

1. si un Transformer multilingual puede aprender la función local producida por el teacher;
2. cuánto agreement obtiene sobre weak labels held-out;
3. cuánto agreement obtiene sobre formulaciones textuales que no aparecieron literalmente en training;
4. cómo varía el resultado por target, status e idioma;
5. cómo se comporta una primera agregación clause -> Study-target;
6. cuánto efecto puede atribuirse a duplicación/memorización versus generalización textual.

NO debe afirmar todavía:

- clinical accuracy;
- que el modelo supera a las reglas;
- que generaliza correctamente sobre teacher-unknown;
- que constituye el modelo final de la competición;
- que las probabilidades de softmax están calibradas;
- que weak-label test performance equivale a gold performance.

Usar explícitamente términos como:

- weak-label agreement;
- teacher-held-out evaluation;
- lexical-novel test slice;

cuando corresponda.

---

# 3. Upstream sources

Stage 04 debe consumir exclusivamente información textual y derivados de Stage 03.

Inspeccionar y reutilizar según corresponda:

- `data/train.csv`
- `artifacts/03_report_label_generation/supervision_long_v3.csv`
- `artifacts/03_report_label_generation/corpus_inspection_v3/`
- `config/03_report_label_generation/policy_v3.json`
- `src/report_labels/`
- `src/report_labels/v3/`
- `reports/stages/03_report_label_generation_v3.md`
- `reports/stages/03_report_label_corpus_inspection_v3.md`
- `reports/implementation/03_report_label_generation_v3_implementation.md`
- tests existentes.

Inspeccionar los schemas reales de:

- evidence inventory;
- detector summaries;
- duplicate groups;
- template families;
- context structure;
- clause usage;
- effective example structure;

antes de decidir qué artefacto reutilizar directamente y qué debe reconstruirse.

No duplicar innecesariamente lógica que ya existe en `src/report_labels`.

---

# 4. Prohibición de gold leakage

Los 58 Studies con official labels NO pueden utilizarse para:

- training;
- validation;
- model selection;
- threshold tuning;
- sampling;
- teacher filtering;
- rule selection;
- hyperparameter selection;
- early stopping.

Para este Stage 04 v0 tampoco hacer evaluación final contra esos 58 gold, porque el nuevo modelo es local clause-level y el benchmark independiente teacher-unknown todavía no existe.

No cargar `official_label` o `final_label` dentro del dataset de training.

Usar exclusivamente:

- Report;
- status derivado;
- evidence/provenance;
- información textual;
- metadata descriptiva permitida.

---

# 5. Unidad de entrenamiento

La unidad principal debe ser:

    target + strict diagnostic clause

NO:

    full Report -> 12 labels

NO:

    full Report + target -> label

NO:

    linked view como baseline principal

NO:

    Mention aislada sin contexto

La baseline v0 debe usar exclusivamente `strict diagnostic clauses`.

Razón metodológica documentada en Stage 03:

- 79,781 strict TextViews;
- sólo 2,578 linked TextViews;
- 41,175 propositions strict-only;
- sólo 636 linked-only;
- selected evidence tiene mediana cercana a 8 simple tokens y p95 cercano a 24.

Linked views deben conservarse como una futura ablation, pero no mezclarse con v0.

---

# 6. Preservar surface text para el Transformer

Las reglas v3 utilizan normalización textual agresiva apropiada para matching:

- Unicode normalization;
- lowercasing;
- eliminación de diacríticos;
- etc.

NO utilizar esa representación normalizada como input principal del Transformer si puede preservarse el surface text original.

El modelo debe recibir:

- Unicode original;
- diacríticos;
- capitalización original;
- puntuación original;

con preprocessing mínimo.

La normalización v3 sí debe conservarse para:

- matching teacher;
- hashes;
- deduplicación;
- template comparison;
- leakage checks;
- lookup/alignment.

Implementar, si todavía no existe, un mecanismo robusto para obtener `raw_clause` preservando exactamente las fronteras semánticas de la segmentación strict vigente.

Requisito importante:

para cada strict clause utilizada por Stage 04 debe poder verificarse que:

    normalize(raw_clause)

produce la misma representación normalizada esperada por la segmentación vigente.

Si hay casos que no pueden alinearse de forma inequívoca:

- no hacer matching fuzzy silencioso;
- registrarlos;
- producir un artifact de alignment failures;
- excluirlos de training hasta que sean auditables.

No modificar el comportamiento de report-label v3.

---

# 7. Teacher de alta confianza para v0

Construir labels `positive`, `negative` y `uncertain` únicamente desde selected WINNING evidence que cumpla:

- strict-only;
- diagnostic;
- no conflict;
- non-collective;
- final selected proposition con status:
  - positive;
  - negative;
  - uncertain;
- detectors restringidos a combinaciones formadas por:
  - `v2_exact`
  - `v3_target`
  - `v3_morphology`

Excluir para baseline v0 cualquier proposition donde participe:

- `v2_collective`

Excluir:

- retained conflicting propositions;
- Study-target conflicts;
- linked-only evidence;
- unresolved/unknown;
- official overrides.

No usar `confidence` como probabilidad.

Conservarla únicamente como metadata/provenance.

---

# 8. Provenance del training dataset

Cada training candidate debe conservar como mínimo:

- `StudyInstanceUID`
- `source_index` / clause index
- `raw_clause`
- `normalized_clause`
- normalized clause hash
- target
- canonical target description
- local label
- original v3 status
- phenotype
- detector combination
- rules
- language_group
- view_kind
- collective flag
- conflict flag
- teacher confidence
- evidence provenance
- report normalized hash
- duplicate/template family identifiers cuando existan
- teacher source type.

No usar:

- detector;
- rule;
- phenotype;
- confidence;
- language_group

como FEATURES del Transformer.

Son exclusivamente metadata para:

- filtering;
- splitting;
- sampling;
- auditing;
- evaluation slices.

---

# 9. Construcción conservadora de `no_evidence`

Este punto debe implementarse explícitamente.

NO tomar los Study-target `unknown` como `no_evidence`.

Para baseline v0, generar `no_evidence` únicamente mediante contrastive target sampling sobre cláusulas que ya contienen una selected winning evidence confiable PARA OTRO TARGET.

Ejemplo:

    clause:
    "Moderate joint effusion."

    Effusion -> positive

puede ser candidata para:

    ACL -> no_evidence

sólo si ACL pasa todos los guards definidos abajo.

Para un target candidato T:

1. T no puede tener selected evidence en esa clause.
2. T no puede tener ningún Mention v3 en esa strict clause.
3. T no puede tener ninguna Proposition v3 en esa strict clause.
4. La cláusula no debe contener una señal anatómica/lexical explícita de T según los patrones target-specific vigentes que pueda indicar que el teacher simplemente falló.
5. No debe utilizarse la condición Study-target `unknown` como evidencia de irrelevancia.
6. El target debe ser diferente de todos los targets etiquetados por la cláusula.

Reutilizar patrones v3 existentes para este guard cuando sea posible en vez de inventar una segunda ontology.

Por defecto generar:

    1 no_evidence target por labeled clause

cuando exista al menos un candidato seguro.

La selección debe ser:

- determinista con seed;
- aproximadamente distribuida entre los 12 targets;
- reproducible.

Registrar:

- `no_evidence_source = contrastive_other_target`
- target del que proviene la evidence real;
- lista de targets ya etiquetados en la cláusula;
- razón/guards que permitieron seleccionar el target contrastivo.

NO utilizar todavía las ~47k clauses sin detector mention para crear `no_evidence`.
Esas clauses pueden contener evidence no detectada y forman parte del problema que se estudiará más adelante.

---

# 10. Target descriptions

Implementar una mapping declarativa versionada para los 12 targets.

Usar como baseline una descripción natural corta en inglés, no únicamente el código de target.

Por ejemplo:

- ACL:
  `anterior cruciate ligament abnormality`
- MCL:
  `medial collateral ligament abnormality`
- Medial Meniscus:
  `medial meniscus abnormality`
- Lateral Meniscus:
  `lateral meniscus abnormality`
- Medial OA:
  `medial tibiofemoral osteoarthritis or cartilage abnormality`
- Lateral OA:
  `lateral tibiofemoral osteoarthritis or cartilage abnormality`
- PF OA:
  `patellofemoral osteoarthritis or cartilage abnormality`
- Effusion:
  `knee joint effusion`
- Synovitis:
  `knee synovitis`
- Baker's:
  `Baker cyst`
- Contusion:
  `bone contusion`
- Fracture:
  `fracture`

Guardar esta mapping en config.

No insertar la explicación target dentro de las clauses.
Usarla como el primer elemento del sentence pair.

---

# 11. Input del Transformer

Usar pair encoding:

    text_a = canonical target description
    text_b = raw diagnostic clause

Conceptualmente:

    [target description] [SEP] [raw clause]

Dejar que el tokenizer específico del pretrained model implemente sus special tokens.

No construir special tokens manualmente.

No agregar al input:

- detector;
- rule;
- language;
- phenotype;
- confidence;
- v3 status.

---

# 12. Baseline encoder

La baseline primaria de Stage 04 v0 debe ser:

    FacebookAI/xlm-roberta-base

o el identificador oficial vigente equivalente verificado en el model registry.

Implementar usando abstractions de Hugging Face:

- `AutoTokenizer`
- `AutoModelForSequenceClassification`

La arquitectura del código debe permitir cambiar posteriormente `model_name_or_path` desde config sin modificar la pipeline.

No implementar todavía KBioXLM ni mDeBERTa como runs obligatorios.

Sí dejar la arquitectura suficientemente genérica para que futuros configs puedan utilizar:

- XLM-R alternatives;
- biomedical multilingual encoders;
- otros AutoModel-compatible encoders.

XLM-R-base es la única baseline requerida para esta release.

---

# 13. Dependencias

El `requirements.txt` actual no contiene stack de deep learning.

Agregar sólo dependencias mínimas necesarias, con versiones EXACTAMENTE PINNED y compatibles con el Python real del proyecto.

Como mínimo se espera evaluar la necesidad de:

- `torch`
- `transformers`
- `scikit-learn`

Evitar agregar `datasets`, `accelerate`, Lightning u otros frameworks si no son necesarios.

Preferencia para v0:

- PyTorch Dataset/DataLoader;
- Hugging Face tokenizer/model;
- training loop reusable y explícito;
- scikit-learn para métricas.

Documentar:

- Python version;
- torch version;
- transformers version;
- sklearn version;
- CUDA version si existe;
- device utilizado.

No asumir GPU.
El pipeline debe funcionar en CPU, aunque sea más lento.

Si CUDA está disponible:
- permitir mixed precision configurable;
- registrar hardware.

---

# 14. Longitud/tokenización

Baseline:

    max_length = 128

Usar:

- truncation;
- dynamic padding por batch;
- attention mask estándar.

No hacer:

- stemming;
- lemmatization;
- manual accent stripping;
- punctuation removal;
- translation;
- stopword removal;
- manual tokenization;
- manual medical vocabulary replacement.

Preprocessing textual permitido para model input:

- normalización mínima de whitespace que no altere semántica.

El tokenizer pretrained debe recibir el surface text.

---

# 15. Split train / validation / test

Éste es un requisito CRÍTICO.

NUNCA hacer random split a nivel clause.

La unidad primaria de split debe ser:

    StudyInstanceUID

Todas las clauses de un mismo Study deben permanecer dentro del mismo split.

Además, todos los Reports pertenecientes a la misma exact duplicate/template family deben permanecer dentro del MISMO split.

Usar la lógica de exact/numeric-normalized families existente en Stage 03 cuando corresponda.

El corpus inspection encontró 53 duplicate Report families / 201 Reports dentro de familias duplicadas, por lo cual deben agruparse explícitamente.

Construir un `split_group_id`:

- duplicate Report family ID cuando un Report pertenece a una familia duplicada;
- Study-specific singleton group cuando no.

Los grupos son indivisibles.

---

# 16. Proporciones del split

Usar por defecto:

- 70% train
- 15% validation
- 15% internal test

Seed base sugerida:

    20260818

Guardar en config.

La asignación debe ser determinista.

Intentar conservar aproximadamente en cada split:

- language distribution;
- target/status distribution;

sin romper jamás los group constraints.

No depender de una simple `train_test_split` sobre clauses.

Implementar, si es necesario, un grouped deterministic stratification/greedy assignment reusable.

Documentar exactamente el algoritmo utilizado.

Generar `split_assignments.csv`:

- StudyInstanceUID
- split_group_id
- template family
- language_group
- split.

---

# 17. Invariantes obligatorios del split

Crear auditorías que fallen si:

1. un Study aparece en más de un split;
2. una duplicate Report family aparece en más de un split;
3. un example row aparece en más de un split por Study;
4. el split no es reproducible con la misma seed/config;
5. una partición queda inesperadamente vacía para un target/status con soporte suficiente para distribuirse;
6. existen discrepancias entre split manifest y training/evaluation datasets.

Persistir un `split_leakage_audit.csv/json`.

El pipeline debe lanzar excepción ante violations graves.

---

# 18. Deduplicación de clauses

El corpus inspection mostró una duplicación muy elevada de selected evidence:

    38,706 instances
    13,324 unique normalized texts
    ~65.6% duplicate excess

y ciertos negativos presentan redundancia extrema.

Por lo tanto:

NO entrenar dando peso lineal a cada repetición textual.

Procedimiento recomendado:

1. construir el dataset candidato completo;
2. hacer el split por Study/group PRIMERO;
3. luego, exclusivamente dentro de TRAIN:
   deduplicar por:

       (target, label, normalized_clause)

4. seleccionar un representante determinístico;
5. conservar:
   - duplicate_count
   - unique_study_count
   - list/hash of source studies cuando sea razonable.

Validation y test NO deben deduplicarse para la evaluación `ALL`.

Crear además slices unique/novel según se define más abajo.

---

# 19. Label collisions durante deduplicación

Antes de colapsar textos, verificar si:

    (target, normalized_clause)

aparece con MÁS DE UN label entre training candidates.

No elegir uno silenciosamente.

Generar:

    label_collision_cases.csv

con provenance completa.

Para v0:

- excluir de training las keys collisionadas;
- reportar cuántas fueron excluidas;
- conservarlas para futura auditoría.

---

# 20. TEST-ALL, TEST-UNIQUE y TEST-NOVEL

No usar una única evaluación.

Definir:

### TEST-ALL

Todos los examples del internal weak-label test con su distribución observada.

### TEST-UNIQUE

Una instancia determinística por:

    (target, label, normalized_clause)

dentro de test.

Sirve para evitar que frases repetidas dominen la métrica.

### TEST-NOVEL

Subconjunto de TEST-ALL donde:

    (target, normalized_clause)

NO apareció en NINGÚN training source example antes de deduplicación.

IMPORTANTE:
la comparación de novelty debe hacerse contra el TRAIN SOURCE SET previo a dedupe, no sólo contra las filas finales retenidas.

Persistir para cada test row:

- `seen_in_train`
- `novel_exact_target_clause`
- duplicate counts.

TEST-NOVEL es la evaluación interna principal de lexical generalization.

No llamarla semantic gold generalization.

---

# 21. Training sampling

Después de deduplicar train, aplicar sampling que evite que grandes strata dominen completamente.

Usar como baseline un WeightedRandomSampler o mecanismo equivalente con peso dependiente de:

    target × label

Recomendación:

    weight proportional to 1 / sqrt(stratum_frequency)

con un cap configurable para que strata extremadamente pequeños no sean oversampled de forma absurda.

Por ejemplo:

    max relative sampling weight = 10

Mantener esto en config.

NO utilizar focal loss en v0.

Loss:

    standard cross entropy

Registrar distribución:

- raw train;
- deduplicated train;
- effective sampled batches/epoch.

---

# 22. Training configuration baseline

Configurable, pero usar inicialmente valores equivalentes a:

- model: `FacebookAI/xlm-roberta-base`
- max_length: 128
- optimizer: AdamW
- learning_rate: 2e-5
- weight_decay: 0.01
- warmup_ratio: 0.10
- max_epochs: 5
- train_batch_size: 16
- eval_batch_size: 32
- gradient_clip_norm: 1.0
- seed: 20260818
- early_stopping_patience: 2

Adaptar batch size sólo si el hardware real lo exige y documentar el cambio.

No hacer una búsqueda extensa de hyperparameters en esta release.

Ésta es una baseline, no una tuning campaign.

---

# 23. Model selection

Seleccionar best checkpoint únicamente mediante VALIDATION weak labels.

Métrica primaria recomendada:

    mean per-target macro-F1

Procedimiento:

1. calcular macro-F1 dentro de cada target sobre labels con soporte;
2. promediar entre targets;
3. usar ese valor para early stopping / best checkpoint.

Además calcular:

- global macro-F1;
- weighted F1;
- accuracy;
- per-label precision/recall/F1.

No utilizar test para model selection.

---

# 24. Label mapping

Definir un mapping numérico explícito en config y en el model config.

El valor numérico no debe implicar precedencia.

Por ejemplo:

    negative
    positive
    uncertain
    no_evidence

con IDs explícitos.

Configurar:

- `id2label`
- `label2id`

en el Hugging Face model.

---

# 25. Checkpoint

Guardar el best checkpoint reproduciblemente.

Debe contener como mínimo:

- model weights;
- HF config;
- tokenizer files;
- label mapping;
- target description mapping;
- training config;
- model source/revision;
- upstream Stage 03 policy version;
- checkpoint metadata.

Usar `save_pretrained()` / `from_pretrained()` compatible format.

Registrar el concepto de CHECKPOINT en el implementation report:

checkpoint = estado persistido del modelo/tokenizer/config necesario para reconstruir inferencia sin reentrenar.

---

# 26. No versionar pesos grandes en Git por defecto

Los model checkpoints pueden ser muy grandes.

Actualizar `.gitignore` de forma explícita para Stage 04:

- permitir versionar lightweight CSV/JSON artifacts de Stage 04;
- permitir reportes y configs;
- ignorar checkpoint/model binaries y caches.

No commitear por defecto:

- `.safetensors`
- `pytorch_model.bin`
- optimizer states;
- Hugging Face caches;
- downloaded pretrained model cache.

Guardar paths/hashes/manifests de esos archivos localmente.

No romper las excepciones ya existentes para Stage 03.

---

# 27. Reproducibilidad del pretrained model

Registrar:

- model identifier;
- tokenizer identifier;
- resolved revision/commit hash del model registry si está disponible;
- transformers version.

Si es posible, después de resolver el checkpoint inicial, fijar una revision reproducible en config en lugar de depender indefinidamente de `main`.

No modificar modelos remotos.

---

# 28. Module layout sugerido

Crear un paquete reusable equivalente a:

    src/report_label_model/

con separación razonable de responsabilidades.

Por ejemplo:

- `constants.py`
- `schema.py`
- `dataset.py`
- `splitting.py`
- `tokenization.py`
- `modeling.py`
- `training.py`
- `evaluation.py`
- `aggregation.py`
- `reporting.py`
- `pipeline.py`

No es obligatorio usar exactamente esos archivos si una estructura menor resulta más clara.

Pero NO poner dataset construction, split, training y reporting dentro del script CLI.

---

# 29. Script de orquestación

Crear algo equivalente a:

    scripts/train_report_label_model.py

El script debe ser fino:

- parse args;
- resolver ROOT;
- cargar config;
- llamar al pipeline reusable;
- imprimir outputs.

Seguir el estilo de:

- `scripts/generate_report_labels.py`
- `scripts/inspect_report_label_corpus.py`

No contener cientos de líneas de lógica de negocio.

---

# 30. Configuración Stage 04

Crear directorio versionado:

    config/04_report_label_model/

y un config baseline equivalente a:

    baseline_xlmr_v1.json

El config debe incluir explícitamente:

- stage/version;
- upstream policy version;
- model name/revision;
- 12 target descriptions;
- four-class label mapping;
- teacher inclusion/exclusion rules;
- no_evidence sampling policy;
- split ratios;
- seed;
- dedup key;
- max_length;
- sampling policy;
- optimizer;
- learning rate;
- batch sizes;
- epochs;
- early stopping;
- primary metric;
- output paths/version.

Evitar constantes ocultas en código cuando son decisiones de experimento.

---

# 31. Internal inference dataset

Además del teacher-held-out local test, Stage 04 debe poder correr el modelo sobre TODAS las strict diagnostic clauses de validation/test Studies.

Para cada:

    Study
    target
    strict diagnostic clause

producir:

- predicted label;
- logits;
- softmax scores;
- raw clause;
- target;
- clause index;
- language;
- model version.

No interpretar softmax como probabilidad calibrada.

Usar el término `score` o `softmax_score`.

---

# 32. Primera agregación Study-target

Implementar un agregador separado y determinista para diagnóstico end-to-end.

Para cada Study-target:

1. ignorar clauses predichas `no_evidence`;
2. si existe al menos un `positive`:
   Study-target -> positive
3. de lo contrario, si existe `uncertain`:
   -> uncertain
4. de lo contrario, si existe `negative`:
   -> negative
5. de lo contrario:
   -> unknown

Es decir:

    positive > uncertain > negative > no_evidence

No usar thresholds complejos todavía.
No entrenar el agregador.
No mezclarlo dentro del Transformer.

Mantenerlo como módulo independiente.

---

# 33. Evaluación Study-level de v0

Comparar esa agregación únicamente contra:

    v3 DERIVED status

de los Studies pertenecientes a validation/test.

NO contra official/final labels.

Llamar a esta evaluación:

    Study-level weak-label agreement

y no:

    clinical accuracy

Reportar:

- agreement;
- coverage;
- confusion matrix;
- per-target agreement;
- transitions:
  teacher status -> model-aggregated status.

Esto permite comprobar el pipeline end-to-end sin consumir gold.

---

# 34. Métricas locales obligatorias

Para validation y test:

### Overall

- accuracy
- macro-F1
- weighted-F1

### Por label

- precision
- recall
- F1
- support

### Por target

- macro-F1
- per-label precision/recall/F1
- support

### Por language_group

- same key metrics
- support

### Teacher source slices

Cuando corresponda:

- `v2_exact`
- `v3_target`
- `v3_morphology`
- combinations.

### Phenotype slices

Phenotype sólo como evaluation metadata.

### Test slices

Separar:

- TEST-ALL
- TEST-UNIQUE
- TEST-NOVEL

No ocultar strata con support bajo.
Sí reportar support junto a métricas.

---

# 35. Confusion matrices

Generar confusion matrices:

- validation overall;
- TEST-ALL;
- TEST-NOVEL;

con labels en orden explícito.

Guardar datos tabulares además de imágenes.

---

# 36. Training curves

Persistir por epoch:

- train loss;
- validation loss;
- validation primary metric;
- global macro-F1;
- learning rate;
- epoch duration si es útil;
- best checkpoint flag.

Generar figuras simples coherentes con Stage 03.

No depender sólo de stdout/logs.

---

# 37. Artifacts Stage 04

Crear un directorio versionado equivalente a:

    artifacts/04_report_label_model/baseline_xlmr_v1/

Como mínimo generar artefactos equivalentes a:

### Dataset construction

- `candidate_examples.csv`
- `alignment_failures.csv`
- `no_evidence_generation_summary.csv`
- `label_collision_cases.csv`

### Splits

- `split_assignments.csv`
- `split_summary.csv`
- `split_leakage_audit.csv`

### Training data

- `train_examples_dedup.csv`
- `validation_examples.csv`
- `test_examples.csv`
- `dedup_summary.csv`

### Training

- `training_history.csv`
- `checkpoint_manifest.json`

### Evaluation

- `metrics_overall.csv`
- `metrics_by_target.csv`
- `metrics_by_label.csv`
- `metrics_by_language.csv`
- `metrics_by_detector.csv`
- `metrics_by_phenotype.csv`
- `test_slice_summary.csv`
- `confusion_matrix_test_all.csv`
- `confusion_matrix_test_novel.csv`

### Predictions

- `predictions_local_test.csv`
- `predictions_study_test.csv`

### Study aggregation

- `study_level_weak_agreement.csv`
- `study_status_transitions.csv`

### Reproducibility

- `run_metadata.json`

Adaptar nombres sólo si las convenciones reales del repo justifican algo mejor.

No generar artifacts redundantes.

---

# 38. Metadata

`run_metadata.json` debe registrar al menos:

- timestamp UTC;
- git commit SHA;
- git dirty flag si es posible;
- Stage 04 version;
- Stage 03 upstream policy/version;
- config SHA-256;
- train.csv SHA-256;
- supervision v3 SHA-256;
- corpus-inspection inputs relevantes + hashes;
- split manifest SHA-256;
- seed;
- model identifier;
- model revision;
- tokenizer;
- package versions;
- Python version;
- device;
- CUDA/GPU metadata si aplica;
- number of raw candidate examples;
- number after filters;
- number after train dedup;
- counts by split;
- counts by target/status;
- checkpoint path/hash;
- all generated output paths/hashes.

Los semantic outputs deben ser deterministas para:

    same inputs + same config + same software/model revision + same seed

hasta donde lo permita PyTorch.

Activar deterministic settings razonables y documentar cualquier operación no determinista inevitable.

---

# 39. Figures

Crear bajo algo equivalente a:

    figures/04_report_label_model/baseline_xlmr_v1/

Como mínimo:

- training / validation loss;
- validation primary metric by epoch;
- TEST-ALL confusion matrix;
- TEST-NOVEL confusion matrix;
- per-target macro-F1 TEST-ALL vs TEST-NOVEL;
- dataset size before/after dedup si aporta información.

Mantener estilo sobrio y consistente con reports previos.

---

# 40. Stage report

Crear:

    reports/stages/04_report_label_model_baseline_v1.md

o nombre equivalente consistente con el repo.

Debe ser un reporte analítico reproducible y autocontenido.

Estructura sugerida:

## 1. Scope

Qué hace Stage 04 y qué queda fuera.

Explicar explícitamente que todavía NO existe el independent manually labeled teacher-unknown test set.

## 2. Upstream supervision

Descripción de report-label v3 y filtros aplicados.

## 3. Predictive task

`target + strict diagnostic clause -> 4-way status`.

## 4. Dataset construction

Teacher filters y `no_evidence`.

## 5. Raw vs normalized text

Por qué el teacher usa normalized text y el model surface text.

## 6. Dataset cardinalities

Antes/después de:
- filters
- splitting
- dedup.

## 7. Duplicates

Impacto estructural observado y procedimiento usado.

## 8. Split strategy

Study-disjoint + duplicate-report-family grouping.

## 9. Leakage audit

Resultados explícitos.

## 10. Model

XLM-R-base.

## 11. Input representation

Target description + raw clause.

## 12. Tokenization/preprocessing

Max length y distribución de truncation real.

Reportar cuántos examples fueron truncados.

## 13. Training configuration

Todos los hyperparameters.

## 14. Validation trajectory

Training curves / best epoch.

## 15. TEST-ALL weak-label agreement

Métricas globales y por target.

## 16. TEST-UNIQUE

Métricas.

## 17. TEST-NOVEL

Métricas y support.

## 18. Language slices

Resultados por idioma.

## 19. Teacher-source / phenotype slices

Descriptivo.

## 20. Study-level weak-label agreement

Agregación y resultados.

## 21. Error analysis

No hacer reinterpretación clínica libre.

Mostrar:
- false agreements/disagreements against teacher;
- representative clauses;
- target;
- teacher provenance;
- predicted status;
- scores.

Hablar de disagreement, no de model error clínico, salvo que exista gold.

## 22. Reproducibility

Comandos, hashes y environment.

## 23. Limitations

Debe incluir explícitamente:

- training y test labels provienen del mismo teacher family;
- TEST-NOVEL sólo excluye exact normalized target-clause overlap y no garantiza semantic novelty;
- weak-label agreement no estima clinical accuracy;
- no existe aún evaluation sobre v3 unknown con manual ground truth;
- no se ha hecho calibration;
- no se han probado linked views;
- no se ha probado collective evidence;
- no se han comparado encoders biomedical multilingual todavía;
- no se ha realizado hyperparameter search;
- 58 official labels no fueron utilizados.

## 24. Artifact index

Paths y descripciones.

NO incluir recomendaciones grandilocuentes.
NO declarar que XLM-R es el mejor modelo.

---

# 41. Implementation report

Crear:

    reports/implementation/04_report_label_model_baseline_v1_implementation.md

Mantener estilo similar a:

`03_report_label_generation_v3_implementation.md`

Incluir:

- Technical summary
- Architecture
- Modules
- Dataset build flow
- Split implementation
- Dedup implementation
- Model/input implementation
- Training loop
- Checkpoint format
- Evaluation implementation
- Study aggregation
- Commands
- Generated artifacts
- Dependency changes
- Reproducibility
- Known limitations
- Deferred work.

Incluir diagrama textual equivalente a:

    Report
      -> strict diagnostic clauses
      -> teacher-aligned local examples
      -> contrastive no_evidence
      -> grouped Study split
      -> train-only dedup
      -> target-conditioned tokenizer
      -> XLM-R-base
      -> local four-way predictions
      -> weak-label evaluation
      -> deterministic Study aggregation

---

# 42. Tests

Agregar tests nuevos sin romper los existentes.

Como mínimo testear:

## Dataset

- strict-only selection;
- diagnostic-only;
- exclusion of linked;
- exclusion of collective;
- exclusion of conflicts;
- exclusion of official labels;
- valid statuses;
- raw/normalized alignment.

## `no_evidence`

- never derived from Study-target unknown;
- source clause has trusted evidence for another target;
- candidate target has no Mention;
- candidate target has no Proposition;
- candidate target fails if explicit lexical/anatomical cue exists;
- deterministic generation with seed.

## Split

- Study disjointness;
- duplicate Report family disjointness;
- deterministic split;
- target/status distributions reconcile;
- no row disappears unexpectedly.

## Dedup

- unique `(target,label,normalized_clause)` in train;
- duplicate counts correct;
- deterministic representative;
- label collisions surfaced and excluded.

## TEST-NOVEL

Assert that every row satisfies:

    (target, normalized_clause)
    not in train_source_keys

## Model input

- correct sentence-pair construction;
- label mapping;
- max length config;
- no teacher metadata inserted into input.

No unit test should require downloading XLM-R from the network.

Use mocks/stubs/tiny local objects where needed.

## Aggregation

Test precedence:

    positive > uncertain > negative > no_evidence

and:

    all no_evidence -> unknown

## Metrics

Test metric calculations with known toy examples.

## Metadata

Hash/reproducibility sanity checks.

Finalmente ejecutar:

    python -m unittest discover -s tests -v

y verificar que los Stage 03 tests sigan pasando.

---

# 43. Smoke test y full run

Implementar un CLI mode para smoke testing sobre una pequeña subset SIN alterar el split oficial.

Por ejemplo:

    --smoke-test

Debe validar:

- dataset build;
- tokenizer/model load;
- forward pass;
- backward pass;
- checkpoint save/load;
- inference;
- metrics.

El smoke mode NO debe producir las métricas oficiales del Stage 04.

Después ejecutar el full pipeline si el ambiente tiene:

- acceso al pretrained checkpoint;
- dependencias instaladas;
- recursos suficientes.

Si el entorno bloquea model download o training:

- NO inventar resultados;
- completar código/tests/dataset/split artifacts que sí puedan ejecutarse;
- dejar documentado exactamente qué comando falta ejecutar;
- indicar la causa concreta.

---

# 44. CLI esperado

Diseñar un entrypoint aproximadamente así:

    python scripts/train_report_label_model.py \
        --config config/04_report_label_model/baseline_xlmr_v1.json

y opcionalmente:

    python scripts/train_report_label_model.py \
        --config ... \
        --smoke-test

No requerir edición manual de código para cambiar paths/model/config.

---

# 45. Commands in reporting

Documentar comandos exactos para:

1. instalar dependencies;
2. ejecutar tests;
3. construir dataset/splits;
4. entrenar;
5. evaluar;
6. reproducir Stage 04 completo;
7. cargar best checkpoint para inference.

Si todo ocurre en una sola pipeline, explicar qué subetapas ejecuta.

---

# 46. Git / artifact policy

Inspeccionar `.gitignore` actual.

Actualizarlo de forma estrecha y segura:

- no romper Stage 03;
- permitir lightweight Stage 04 artifacts necesarios;
- ignorar pesos/caches;
- evitar una regla global demasiado amplia.

No agregar downloaded model cache al repositorio.

---

# 47. No hacer todavía

No implementar en esta release:

- manual test set de v3 unknown;
- pseudo-labeling;
- self-training;
- active learning;
- calibration;
- threshold optimization;
- hard-negative mining complejo;
- linked views training;
- collective evidence training;
- learned Study aggregator;
- multi-task
