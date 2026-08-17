"""Markdown reporting for the descriptive v3 corpus inspection."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .constants import POLICY_VERSION
from .inspection import InspectionParameters, OUTPUT_FILES


def _fmt(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(frame: pd.DataFrame, columns: list[str] | None = None, limit: int | None = None) -> str:
    display = frame.copy()
    if columns is not None:
        display = display[columns]
    if limit is not None:
        display = display.head(limit)
    if display.empty:
        return "_No se observaron filas para esta unidad._"
    header = "| " + " | ".join(display.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = ["| " + " | ".join(_fmt(value) for value in row) + " |" for row in display.itertuples(index=False, name=None)]
    return "\n".join([header, separator, *rows])


def _study_distribution_table(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "binary_resolved_targets", "positive_targets", "negative_targets", "uncertain_targets",
        "unknown_targets", "propositions", "unique_evidence_fragments",
    ]
    rows = []
    for column in columns:
        values = frame[column]
        rows.append({
            "measure": column,
            "mean": values.mean(),
            "std": values.std(ddof=1),
            "median": values.median(),
            "min": values.min(),
            "p05": values.quantile(0.05),
            "p25": values.quantile(0.25),
            "p75": values.quantile(0.75),
            "p95": values.quantile(0.95),
            "max": values.max(),
        })
    return pd.DataFrame(rows)


def write_inspection_report(
    path: Path,
    frames: dict[str, pd.DataFrame],
    diagnostics: dict[str, object],
    parameters: InspectionParameters,
    train_path: Path,
    supervision_path: Path,
    policy_config_path: Path,
    output_dir: Path,
) -> None:
    counts = frames["corpus_unit_counts"]
    global_counts = counts[
        counts["target"].eq("__all__")
        & counts["status"].eq("__all__")
        & ~counts["unit"].str.contains("per Report")
    ][["unit", "count", "denominator"]]
    clause_distribution = counts[counts["unit"].eq("clauses per Report")][[
        "count", "mean", "std", "median", "min", "max", "p05", "p25", "p75", "p95",
    ]]
    target_status = frames["target_status_summary"]
    language = frames["language_summary"]
    lengths = frames["text_length_summary"]
    detectors = frames["detector_summary"]
    detector_overall = detectors[detectors["target"].eq("__all__")][[
        "unit", "detector", "count", "unique_studies", "unique_study_target_pairs",
    ]].sort_values(["unit", "count"], ascending=[True, False])
    confidence_values = frames["confidence_summary"]
    confidence_values = confidence_values[confidence_values["dimension"].eq("confidence_value")][[
        "unit", "value", "count",
    ]]
    duplicate_summary = frames["duplicate_summary"]
    templates = frames["template_family_summary"]
    template_summary = templates.groupby("template_mode", as_index=False).agg(
        families=("template_family_sha256", "nunique"),
        duplicated_families=("is_duplicated_family", "sum"),
        reports_covered=("reports", "sum"),
        max_family_size=("reports", "max"),
        homogeneous_families=("homogeneous_across_each_target", "sum"),
        heterogeneous_families=("homogeneous_across_each_target", lambda values: int((~values).sum())),
    )
    duplicated_report_coverage = (
        templates.loc[templates["is_duplicated_family"]]
        .groupby("template_mode")["reports"]
        .sum()
    )
    template_summary["reports_in_duplicated_families"] = (
        template_summary["template_mode"].map(duplicated_report_coverage).fillna(0).astype(int)
    )
    view_overall = frames["view_kind_summary"]
    view_overall = view_overall[view_overall["record_type"].isin(["overall", "proposition_support_scope"])][[
        "record_type", "view_kind", "support_scope", "views", "mentions", "propositions", "selected_pair_participations",
    ]]
    collective = frames["collective_evidence_summary"]
    collective_overall = pd.DataFrame([{
        "mentions": collective["mentions"].sum() if not collective.empty else 0,
        "propositions": collective["propositions"].sum() if not collective.empty else 0,
        "selected_propositions": collective["selected_propositions"].sum() if not collective.empty else 0,
        "selected_study_target_pairs_participations": collective["selected_study_target_pairs"].sum() if not collective.empty else 0,
    }])
    conflicts = frames["conflict_cases"]
    conflict_summary = conflicts.groupby(["target", "winning_status", "language_group"], as_index=False).size().rename(columns={"size": "pairs"}) if not conflicts.empty else pd.DataFrame()
    uncertain_evidence = frames["evidence_inventory"]
    uncertain_evidence = uncertain_evidence[
        uncertain_evidence["is_winning_status"]
        & uncertain_evidence["proposition_status"].eq("uncertain")
    ]
    uncertain_target = uncertain_evidence.groupby("target", as_index=False).agg(
        evidence_instances=("evidence", "size"),
        unique_evidence_texts=("normalized_evidence", "nunique"),
    ) if not uncertain_evidence.empty else pd.DataFrame()
    unknown = frames["unknown_summary"]
    unknown_target = unknown.groupby("target", as_index=False).agg(
        pairs=("pairs", "sum"), unknown=("unknown", "sum"),
    )
    unknown_target["unknown_rate"] = unknown_target["unknown"] / unknown_target["pairs"]
    positive_cooccurrence = frames["target_cooccurrence"]
    positive_cooccurrence = positive_cooccurrence[
        positive_cooccurrence["matrix_type"].eq("positive_positive")
        & positive_cooccurrence["row_target"].ne(positive_cooccurrence["column_target"])
    ].sort_values("study_count", ascending=False).head(15)

    artifact_rows = [
        {"artifact": name, "path": str((output_dir / filename).as_posix()), "description": name.replace("_", " ")}
        for name, filename in OUTPUT_FILES.items()
    ]
    report = f"""# Report-label corpus inspection for NLP modeling evidence

## 1. Scope

Esta inspección caracteriza de forma descriptiva los `{diagnostics['studies']:,}` Reports y los `{diagnostics['study_target_pairs']:,}` pares Study × target procesados por `{POLICY_VERSION}`. Se reconstruyeron las unidades internas vigentes y se analizaron exclusivamente `status`, `derived_label`, evidence y provenance derivados del texto.

No se diseñó ningún modelo, no se compararon arquitecturas, no se seleccionaron pretrained models, no se definieron unidades de entrenamiento, teachers, thresholds ni subconjuntos de entrenamiento. No se modificaron policies ni labels. Los valores de `official_label` y `final_label` no se cargaron en la inspección analítica. Tampoco se utilizaron PixelData, DICOM/Series metadata, scanner ni anatomical plane.

## 2. Sources

- Dataset textual: `{train_path.as_posix()}`.
- Supervisión derivada v3: `{supervision_path.as_posix()}`.
- Configuración: `{policy_config_path.as_posix()}`.
- Código ejecutable: `src/report_labels/`, `src/report_labels/v3/` y `scripts/generate_report_labels.py`.
- Reportes revisados: stage 03 v3 y reporte de implementación v3.

Los hashes SHA-256 de inputs, fuentes revisadas y outputs se encuentran en `inspection_run_metadata.json`.

## 3. Reproducibility

Comando:

```powershell
python scripts/inspect_report_label_corpus.py
```

Parámetros semánticos: seed `{parameters.seed}`, máximo `{parameters.audit_sample_max_rows}` filas de auditoría, máximo `{parameters.similarity_max_pairs_per_stratum:,}` pares de similitud por target/status y top `{parameters.ngram_top_k}` n-grams. Los CSV son deterministas para inputs, código y parámetros fijos; el timestamp UTC se registra únicamente en metadata.

## 4. Units of analysis

- **Report:** texto completo asociado a un `StudyInstanceUID`.
- **Clause:** fragmento producido por `segment_report`; en v3 corresponde a un `TextView` strict.
- **TextView strict:** una cláusula con sección, flag diagnóstico y un `source_index`.
- **TextView linked:** combinación de dos cláusulas adyacentes permitida por encabezado corto o marcador explícito de continuación.
- **Mention:** resultado local de un detector antes de deduplicación.
- **Proposition:** combinación deduplicada por target, status, phenotype y evidence; puede contener varios detectors/views/rules.
- **Selected evidence:** Proposition persistida en `evidence_provenance`, incluida la Proposition conflictiva conservada por el reconciliador.
- **Study-target pair:** una fila derivada por Study y uno de los 12 targets.

Cada tabla explicita su denominador. Las participaciones de detectors/rules no son aditivas cuando una Proposition contiene más de una fuente.

## 5. Corpus size

{_table(global_counts)}

Distribución de cláusulas strict por Report:

{_table(clause_distribution)}

## 6. Target/status distribution

{_table(target_status, ['target', 'pairs', 'positive', 'negative', 'uncertain', 'unknown', 'binary_resolved', 'binary_resolved_rate', 'positive_over_binary_resolved', 'negative_over_binary_resolved'])}

Los porcentajes utilizan los `{diagnostics['studies']:,}` pares disponibles para cada target.

## 7. Language distribution

{_table(language, ['language_group', 'reports', 'study_target_pairs', 'positive', 'negative', 'uncertain', 'unknown', 'resolved_rate', 'strict_views', 'linked_views', 'mentions', 'propositions'])}

`language_group` y las hypotheses son heurísticas de routing. Las hypotheses no son exclusivas y sus conteos no deben sumarse como Reports independientes.

## 8. Text lengths

Token simple significa `normalize_text` seguido por la expresión Unicode `\\b\\w+\\b`; no se utilizó tokenizer de un modelo.

{_table(lengths, ['unit', 'measure', 'count', 'mean', 'std', 'median', 'min', 'p05', 'p25', 'p75', 'p95', 'p99', 'max'])}

## 9. Detector provenance

{_table(detector_overall, limit=20)}

Una Proposition puede estar soportada por más de un detector. `detector_combination_summary.csv` conserva las combinaciones y separa 1, 2 y 3+ detectors.

## 10. Confidence distribution

{_table(confidence_values, limit=30)}

La confidence es un ranking determinista de fuerza de evidencia definido por la policy; no es una probabilidad calibrada. `confidence_summary.csv` contiene además las distribuciones por target, status, detector, rule, phenotype, idioma, conflicto y modo colectivo/target-specific.

## 11. Phenotypes

{_table(frames['phenotype_summary'], ['phenotype', 'propositions', 'unique_studies', 'selected_pair_participations', 'selected_winning_pair_participations', 'targets', 'statuses'], limit=30)}

`target_phenotype_status.csv` expresa el porcentaje usando como denominador todas las Propositions del mismo target/status. La inspección no asigna un rol futuro a phenotype.

## 12. Rules

{_table(frames['rule_summary'], ['rule', 'mentions', 'propositions', 'unique_studies', 'selected_pair_participations', 'selected_winning_pair_participations', 'cumulative_selected_participation_share'], limit=30)}

La columna acumulada usa participaciones de reglas; un mismo par puede participar en más de una rule.

## 13. Duplicates and template families

{_table(duplicate_summary)}

La duplicate rate se define como `(instances - unique normalized texts) / instances`. Los grupos completos y sus IDs se encuentran en `duplicate_groups.csv`.

{_table(template_summary)}

Las familias exact y numeric-normalized usan la misma normalización vigente en `exact_template_consistency`. Se incluyen familias singleton y duplicadas, distinguidas por `is_duplicated_family`.

## 14. Lexical/textual diversity

{_table(frames['lexical_diversity_summary'], ['target', 'status', 'evidence_instances', 'unique_normalized_texts', 'duplicate_rate_excess', 'total_simple_tokens', 'unique_tokens', 'type_token_ratio', 'unigram_top_10_coverage', 'bigram_top_10_coverage'], limit=36)}

Type-token ratio depende de la longitud observada. `ngram_summary.csv` conserva unigramas/bigramas y `text_similarity_summary.csv` documenta exact match, normalized exact match y Jaccard sobre sets de tokens. Estas métricas describen similitud superficial, no similitud semántica.

## 15. Strict vs linked evidence

{_table(view_overall)}

`linked_view_dependency_cases.csv` contiene los pares con selected winning evidence que incluye linked views y distingue linked-only de soporte combinado.

## 16. Collective evidence

{_table(collective_overall)}

`collective_evidence_summary.csv` desagrega target, status, rule, language, phenotype y confidence sin decidir un uso posterior.

## 17. Conflicts

Se observaron `{len(conflicts):,}` pares con rationale conflictivo ({len(conflicts) / diagnostics['study_target_pairs']:.4%} de los pares).

{_table(conflict_summary, limit=30)}

`conflict_cases.csv` conserva winning/conflicting statuses y provenance completa; la inspección no los resuelve ni reinterpreta.

## 18. Uncertain cases

El artefacto v3 contiene `{diagnostics['status_counts']['uncertain']:,}` pares uncertain.

{_table(uncertain_target, limit=20)}

Los patrones se atribuyen únicamente a `UNCERTAINTY_TERMS` y `_V3_UNCERTAINTY` vigentes.

## 19. Unknown population

{_table(unknown_target, limit=20)}

Las tablas de unknown describen longitud, cláusulas, idioma, views y presencia de otros targets resueltos en el mismo Report. No se afirma que unknown carezca de hallazgos ni que sea irrelevante.

`clause_usage_summary.csv` separa cláusulas diagnósticas seleccionadas, cláusulas con mentions no seleccionadas y cláusulas sin mentions, sin convertirlas en labels.

## 20. Study-level structure and target co-occurrence

{_table(_study_distribution_table(frames['study_level_distribution']))}

Principales celdas off-diagonal de co-ocurrencia positive-positive, presentadas sólo como conteos:

{_table(positive_cooccurrence, ['row_target', 'column_target', 'study_count', 'denominator_studies'])}

`target_cooccurrence.csv` contiene matrices positive-positive, binary-resolved y shared normalized selected evidence. No se atribuye causalidad.

## 21. Effective example structure

{_table(frames['effective_example_structure'], ['target', 'status', 'raw_evidence_count', 'unique_normalized_evidence_count', 'unique_report_count', 'unique_exact_template_family_count', 'unique_numeric_normalized_template_family_count', 'detector_rule_combination_count', 'language_group_count'], limit=40)}

No se estima un effective sample size estadístico. Las columnas son conteos estructurales observables.

## 22. Audit sample

`audit_sample.csv` contiene `{len(frames['audit_sample']):,}` filas seleccionadas determinísticamente con seed `{parameters.seed}`. Las strata combinan target, status, detector, rule, phenotype, idioma, conflicto, soporte strict/linked y collective; unknown se muestrea por target/idioma. Los campos `judgment` y `review_note` están vacíos y no se realizó anotación clínica.

## 23. Limitations of this inspection

- Todas las unidades Mention/Proposition dependen de las reglas vigentes de v3.
- `language_group` y language hypotheses son heurísticas de routing.
- Las familias de templates se limitan a exact y numeric-normalized según el mecanismo existente.
- Exact match, n-grams y Jaccard describen forma textual y no equivalencia semántica.
- La classification de negation se reconstruye desde términos/spans persistidos y conserva una categoría residual cuando el marcador no puede reconstruirse.
- Las participaciones de detectors, rules y phenotypes se superponen.
- La inspección no evalúa corrección clínica ni utiliza official labels para comparar fuentes.

## 24. Artifact index

{_table(pd.DataFrame(artifact_rows))}
"""
    path.write_text(report, encoding="utf-8")
