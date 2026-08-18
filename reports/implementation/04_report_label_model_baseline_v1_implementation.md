# Stage 04 report-label model baseline v1 — Implementation report

## Technical summary

La implementación agrega un paquete reusable `src/report_label_model/`, un entrypoint fino, config versionada, tests y artifacts reproducibles. No modifica el comportamiento de report-label v3. La unidad del encoder es siempre `(target description, raw strict diagnostic clause)`.

El estado entregado incluye preparación completa y smoke exitoso. El full training quedó diferido porque el host no tiene CUDA; no se fabricaron outputs de performance.

## Architecture

```text
Report
  -> strict diagnostic clauses
  -> exact raw/normalized alignment
  -> teacher-aligned local examples
  -> contrastive no_evidence
  -> grouped Study/template-family split
  -> train-only collision audit and dedup
  -> target-conditioned tokenizer
  -> XLM-R-base four-way classifier
  -> teacher-held-out / lexical-novel weak-label evaluation
  -> all-strict-clause inference
  -> deterministic Study aggregation
```

## Modules

- `constants.py`: version, labels, detectors y split identifiers.
- `dataset.py`: surface alignment, gold exclusion, teacher filters, no-evidence guards, collisions, dedup y novelty.
- `splitting.py`: family map assignment, deterministic greedy stratification, duplicate-family local improvement y leakage audits.
- `modeling.py`: sentence-pair Dataset/collator, AutoModel loading, checkpoint support e inference.
- `training.py`: seeding, WeightedRandomSampler, AdamW loop, scheduler, validation-only model selection y early stopping.
- `evaluation.py`: accuracy/F1, per-label/target/language/source/phenotype tables y confusion matrices.
- `aggregation.py`: precedence local-to-Study y weak-label comparison.
- `metadata.py`: SHA-256, git/environment/package capture y checkpoint manifests.
- `reporting.py`: curvas, confusion matrices, target comparison y dedup figure.
- `pipeline.py`: orquestación de prepare, smoke y full run.

## Dataset build flow

`data/train.csv` se lee sólo con `StudyInstanceUID,Report`. `supervision_long_v3.csv` se lee una vez con `StudyInstanceUID,final_source` para construir el exclusion manifest, y en evaluación Study-level sólo con `StudyInstanceUID,target,status`. Nunca se cargan `official_label` o `final_label` en el dataset.

El inventario de evidence se filtra por selected winning status, strict-only, target-specific, noncollective, conflict-free y detector subset permitido. Provenances múltiples de una misma unidad local se consolidan determinísticamente, uniendo detectors/rules/phenotypes y reteniendo confidence sólo como metadata ordinal.

La alineación reconstruye los fragmentos surface con los boundaries vigentes y exige igualdad exacta al normalizar. Los dos rewrites estructurales existentes en v3 se usan únicamente para recuperar posición y evitar cascadas; esas cláusulas siguen fallando la igualdad y se excluyen.

## `no_evidence` implementation

Se agrupa por Study y source clause con evidence trusted. Para cada target candidato se consultan selected targets, todas las v3 Mentions/Propositions y los lexicons/regex vigentes (`ANATOMY_TERMS`, `DIRECT_TERMS`, `DIRECT_RULES`, `STRUCTURAL_ANATOMY_ROOTS`, `OA_ANATOMY_PATTERNS`). Un greedy estable por hash/seed elige entre los targets con menor uso acumulado. No existe input de Study-target unknown en esta función.

## Split implementation

La family numeric-normalized reproduce `NUMBER_PATTERN` y hashing de la inspección v3; subsume exact duplicates. Las familias duplicadas se asignan primero contra objetivos de cantidad de Studies y familias, con mejora local determinista. Los singletons restantes minimizan desviación normalizada de Study count, language y target-label.

El manifest se calcula dos veces y se compara byte-semánticamente en memoria. Los checks graves lanzan excepción. Resultado: 3.082/633/634 Studies y 37/8/8 duplicate families en train/validation/test.

## Dedup implementation

El split precede siempre a dedup. En train se detectan collisions por `(target, normalized_clause)`; toda key multietiqueta se persiste y excluye. Luego se selecciona el representante lexicográficamente estable por `(StudyInstanceUID, source_index, example_id)` dentro de `(target,label,normalized_clause)`. Validation/test no se deduplican para ALL.

TEST-NOVEL consulta las keys del train source previo a collision filtering/dedup. TEST-UNIQUE se materializa lógicamente de forma determinista durante evaluación.

## Model and input implementation

`PairDataset` llama al tokenizer con dos argumentos textuales; no construye special tokens. `PairCollator` aplica padding dinámico. `AutoModelForSequenceClassification` recibe `label2id/id2label` explícitos. `model_name_or_path`, tokenizer y revision son configurables.

La revisión baseline es `e73636d4f797dec63c3081bb6ed5c7b0bb3f2089`. `local_files_only` existe como opción de runtime y se activa sólo en smoke después de descargar el snapshot; no está fijado en el config oficial.

## Training loop

El loop PyTorch explícito usa AdamW, linear warmup, cross entropy, clip norm y mixed precision sólo en CUDA. `WeightedRandomSampler` usa `1/sqrt(target-label frequency)`, cap relativo 10 y exactamente `len(train_dedup)` muestras por epoch. La distribución efectiva se registra por epoch.

Cada epoch calcula validation loss y mean per-target macro-F1. Sólo una mejora de esa métrica guarda checkpoint; patience se aplica sin consultar test. Las opciones deterministas de PyTorch se habilitan con `warn_only=True` para reportar operaciones que no puedan garantizarse.

## Checkpoint format

El best checkpoint usa `save_pretrained(..., safe_serialization=True)` y `tokenizer.save_pretrained()`. Incluye HF config/weights/tokenizer, `stage04_config.json` y `checkpoint_metadata.json`. El manifest registra paths, sizes y hashes. Checkpoint significa el estado persistido necesario para reconstruir inferencia sin reentrenar.

Los binarios, optimizer state, smoke y caches se ignoran estrechamente en `.gitignore`; CSV/JSON ligeros, configs, figuras y reportes quedan permitidos.

## Evaluation implementation

`evaluation.py` genera overall accuracy/macro-F1/weighted-F1; precision/recall/F1/support por label; métricas por target, language, detector combination y phenotype; y confusion matrices con label order explícito. Model selection sólo consume validation.

La inferencia interna cruza cada strict diagnostic clause alineada de validation/test con los 12 target descriptions. Persiste logits y `softmax_score_*`, nunca calibrated probability. Las métricas test se separan en TEST-ALL, TEST-UNIQUE y TEST-NOVEL.

## Study aggregation

`aggregation.py` ignora `no_evidence` y aplica `positive > uncertain > negative`; si todas las clauses son `no_evidence` o no hay strict diagnostic clause, devuelve `unknown`. El agregado se une únicamente con `status` DERIVED v3 y produce agreement, coverage y transitions.

## Commands

```powershell
# 1. Dependencies
python -m pip install -r requirements.txt

# 2. All tests
python -m unittest discover -s tests -v

# 3. Dataset, splits, audits and dedup only
python scripts/train_report_label_model.py --config config/04_report_label_model/baseline_xlmr_v1.json --prepare-only

# 4. Tiny integration smoke (never official metrics)
python scripts/train_report_label_model.py --config config/04_report_label_model/baseline_xlmr_v1.json --smoke-test

# 5/6. Train, select, evaluate, infer and aggregate end-to-end
python scripts/train_report_label_model.py --config config/04_report_label_model/baseline_xlmr_v1.json
```

Checkpoint inference after a completed full run:

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

checkpoint = "artifacts/04_report_label_model/baseline_xlmr_v1/checkpoint"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSequenceClassification.from_pretrained(checkpoint)
batch = tokenizer(
    "anterior cruciate ligament abnormality",
    "The ACL is intact.",
    truncation=True,
    max_length=128,
    return_tensors="pt",
)
logits = model(**batch).logits
```

## Generated artifacts

La preparación generó candidate/alignment/no-evidence tables; gold exclusion manifest; split assignments/summary/audits; train dedup, validation y test; dedup/test-slice summaries; metadata; y figura de cardinalidad. `run_metadata.json` contiene hashes de todos los inputs y outputs presentes.

El full runner está implementado para producir history, sampled distribution, checkpoint manifest, métricas, confusion matrices, local/all-clause predictions, Study predictions/agreement/transitions y figuras. Esos archivos no existen todavía porque no se completó un full training real.

## Dependency changes

Se agregaron sólo `torch==2.8.0`, `transformers==4.55.2` y `scikit-learn==1.7.2`. No se agregaron datasets, accelerate, Lightning ni frameworks equivalentes. El entorno verificado usa Python 3.10.11 y CPU.

## Reproducibility

- Seed: `20260818`.
- Config SHA-256: `69bc88008fb57997525cd4789385d09a142a4e6f0f6e184218a62ebe8f0f8d7e`.
- Split manifest SHA-256: `44642fe2c451e09d64d5f134dde4e14e4848454bde3aa8f758fe9c11e21e19b0`.
- Model revision: `e73636d4f797dec63c3081bb6ed5c7b0bb3f2089`.
- Tests: 77 passed en la suite completa final.
- Smoke: forward/backward/save-load/inference/metrics passed en CPU; 20,33 s para el epoch diminuto.

## Known limitations

El teacher y weak-label test pertenecen a la misma rule family. Novelty es exacta, no semántica. No existe gold local para unknown, calibration, linked/collective training, learned aggregator, encoder comparison ni tuning campaign. El full CPU run no se inició por costo de cómputo; la pipeline y el checkpoint smoke sí fueron ejercitados.

## Deferred work

- full baseline training en hardware adecuado;
- independent manually labeled teacher-unknown test set;
- calibration y threshold studies;
- linked/collective ablations;
- biomedical multilingual encoders;
- learned Study aggregation, pseudo-labeling, self-training y active learning.
