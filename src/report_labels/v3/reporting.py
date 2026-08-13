"""Generated analytical and implementation reports for policy v3."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .constants import POLICY_CONFIG_NAME, POLICY_VERSION


def _fmt(value: object) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    shown = frame[columns] if columns else frame
    headers = [str(column) for column in shown.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in shown.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_fmt(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def write_v3_stage_report(
    path: Path,
    train: pd.DataFrame,
    supervision: pd.DataFrame,
    metrics: pd.DataFrame,
    errors: pd.DataFrame,
    languages: pd.DataFrame,
    coverage_delta: pd.DataFrame,
    transitions: pd.DataFrame,
    detectors: pd.DataFrame,
    templates: pd.DataFrame,
    audit_summary: pd.DataFrame,
    artifacts: dict[str, Path],
    figures: dict[str, Path],
) -> None:
    status = supervision["status"].value_counts()
    binary = int(supervision["derived_label"].notna().sum())
    target_delta = coverage_delta[coverage_delta["scope"].eq("target")][
        ["target", "pairs", "resolved_rate_v2", "resolved_rate_v3", "delta"]
    ].sort_values("delta", ascending=False)
    language_delta = coverage_delta[coverage_delta["scope"].eq("language_group")][
        ["language_group", "pairs", "resolved_rate_v2", "resolved_rate_v3", "delta"]
    ].sort_values("resolved_rate_v3")
    v2_unknown_resolved = int(transitions[
        transitions["status_v2"].eq("unknown") & transitions["status_v3"].isin(["positive", "negative"])
    ]["pairs"].sum())
    v2_resolved_unknown = int(transitions[
        transitions["status_v2"].isin(["positive", "negative"]) & transitions["status_v3"].eq("unknown")
    ]["pairs"].sum())
    changed_binary = int(transitions[
        transitions["status_v2"].isin(["positive", "negative"])
        & transitions["status_v3"].isin(["positive", "negative"])
        & transitions["status_v2"].ne(transitions["status_v3"])
    ]["pairs"].sum())
    detector_display = detectors.groupby("detector", as_index=False)["propositions"].sum().sort_values("propositions", ascending=False)
    phenotype_display = detectors.groupby("phenotype", as_index=False)["propositions"].sum().sort_values("propositions", ascending=False).head(15)
    gold_display = metrics[["target", "gold_positives", "coverage", "precision", "recall", "f1", "fp", "fn", "unknown", "uncertain"]]
    error_display = errors["error_type"].value_counts().rename_axis("error_type").reset_index(name="cases")
    template_studies = int(templates["studies"].sum())
    template_groups = len(templates)

    text = f"""# 03 Report Label Generation — Policy v3

## 1. Resumen ejecutivo

La política `{POLICY_VERSION}` implementa una arquitectura de ensemble a nivel de evidencia para los {len(train):,} `Report`. V3 no vota labels completos: combina menciones exactas, morfología controlada por idioma, relaciones anatómicas target-específicas y estructura del reporte en proposiciones clínicas auditables. La ausencia de una proposición aceptable continúa siendo `unknown`; no se infieren negativos a partir del silencio.

V3 resolvió binariamente {binary:,} de {len(supervision):,} pares ({binary / len(supervision):.1%}). Estados: positive={status.get('positive', 0):,}, negative={status.get('negative', 0):,}, uncertain={status.get('uncertain', 0):,}, unknown={status.get('unknown', 0):,}. Respecto de v2, {v2_unknown_resolved:,} pares pasaron de `unknown` a un estado binario, {v2_resolved_unknown:,} hicieron la transición inversa y {changed_binary:,} cambiaron entre positive y negative.

Los 58 estudios oficiales se utilizaron sólo después de congelar la extracción y completar las validaciones corpus-only. Las métricas gold son un sentinel final pequeño, no un conjunto de desarrollo ni una base para ajustar términos o umbrales.

## 2. Qué cambia respecto de v2

| Dimensión | v2 | v3 |
| --- | --- | --- |
| Unidad de combinación | menciones dentro de cláusulas | proposiciones con phenotype y provenance |
| Segmentación | una vista de cláusulas | vistas estrictas y vínculos estructurales de alta confianza |
| Variación lingüística | términos enumerados | exactos más familias morfológicas acotadas |
| Asociación | proximidad local fija | relación target–finding con competencia anatómica |
| OA | términos y anatomía en ventana | scope compartimental target-específico |
| Idioma | grupo descriptivo | hipótesis de routing no exclusivas |
| Persistencia | evidence y rationale | evidence, phenotype, detector, view, rule y confidence |
| No mención | unknown | unknown, sin cambios |

## 3. Metodología

1. Normalización determinista preservando el texto fuente mediante evidence textual.
2. Segmentación multivista: cláusulas estrictas y vistas vinculadas sólo ante encabezados o continuaciones explícitas; no se unen cláusulas adyacentes arbitrarias.
3. Rama exacta v2 conservada como detector común de alta precisión.
4. Morfología controlada sobre formas observadas en el corpus. Cada regla está limitada por target, idioma y exclusiones.
5. Detectores target-específicos para ligamentos, meniscos y OA. La asociación compite con anatomías vecinas y evita asignar una patología al target sólo por coexistir en la oración.
6. Detectores directos estrictos para Effusion, Synovitis, Baker's, Contusion y Fracture.
7. Deduplicación en objetos `Proposition`; la provenance conserva detectores, vistas, reglas, idiomas y phenotype.
8. Reconciliación conservadora positive → uncertain → negative únicamente cuando existe evidencia. Los conflictos reducen confidence y se hacen visibles.
9. Validación corpus-only y comparación con v2.
10. Evaluación final contra los 58 gold, antes del override oficial.

## 4. Coverage por target

{_table(target_delta)}

![Delta de cobertura v3 vs v2](../../figures/03_report_label_generation/{figures['delta'].name})

La columna `delta` está expresada como proporción; la figura la presenta en puntos porcentuales. Una ganancia no se interpreta automáticamente como mejora de precisión: debe leerse junto con las transiciones, provenance y evaluación final.

## 5. Idiomas

{_table(language_delta)}

La implementación prioriza los grupos menos cubiertos mediante reglas morfológicas específicas, pero conserva rutas comunes para términos importados. El grupo de idioma sigue siendo heurístico y no constituye un diagnóstico lingüístico.

## 6. Contribución de detectores y phenotypes

{_table(detector_display)}

Los conteos representan participación en proposiciones persistidas y pueden superponerse cuando la rama exacta y una regla v3 sostienen la misma evidencia.

{_table(phenotype_display)}

Separar phenotype de label conserva diferencias como tear, sprain, degeneration, fracture o chondral abnormality. V3 mantiene inicialmente la política binaria previa; no usa 58 casos para redefinir la ontología de competición.

## 7. Salvaguardas semánticas

- Contusion exige contusión/bone bruise explícito. Edema óseo o medular aislado no alcanza.
- Synovitis exige inflamación, engrosamiento, hipertrofia o proliferación sinovial explícita. Plica, quiste, tenosinovitis y condromatosis no se convierten en Synovitis.
- Baker's requiere Baker/cyst o una variante anatómica inequívoca. Una masa poplítea indeterminada permanece sin resolver.
- La presencia espacial de MCL junto a una rotura meniscal no demuestra lesión ligamentaria.
- Los colectivos positivos sólo se expanden cuando el conjunto de targets es inequívoco.
- `uncertain` no se binariza y `unknown` no contiene evidence ni provenance.

## 8. Validación corpus-only

Se evaluaron {template_groups:,} grupos de plantillas exactas o normalizadas respecto de valores numéricos, que reúnen {template_studies:,} asignaciones estudio–familia. Targets inconsistentes dentro de una familia: {int(templates['inconsistent_targets'].sum()):,}.

La auditoría exhaustiva validó las {len(supervision):,} filas, todos los elementos de evidence y todos los objetos de provenance:

{_table(audit_summary)}

No se usaron los labels oficiales para descubrir vocabulario, escoger reglas, establecer confidence ni resolver errores de esta fase.

## 9. Resultados sobre el sentinel gold

{_table(gold_display)}

![Métricas gold v3](../../figures/03_report_label_generation/{figures['metrics'].name})

Estas métricas tienen N=58 por target. Precision, recall y F1 se calculan sólo sobre pares binariamente resueltos y deben interpretarse junto con coverage. No se aplicaron correcciones posteriores basadas en estos resultados.

## 10. Error analysis

{_table(error_display)}

El artefacto de errores conserva el `Report`, evidence, rationale y provenance resumida. Una discordancia no demuestra por sí sola un error del extractor: report y gold pueden utilizar distinta granularidad clínica.

## 11. Output final

![Estados v3 por target](../../figures/03_report_label_generation/{figures['status'].name})

El output mantiene una fila por `StudyInstanceUID`–target. `official_label`, `derived_label` y `final_label` permanecen separados; el override se aplica sólo al final con prioridad `official > report_derived > unresolved`.

Artefactos principales:

- `{artifacts['supervision'].name}`: supervisión larga con provenance estructurada.
- `{artifacts['coverage_delta'].name}`: delta v2→v3 por target, idioma e idioma–target.
- `{artifacts['transitions'].name}`: matriz de transiciones de estados.
- `{artifacts['newly_resolved'].name}`: los pares v2-unknown recuperados por v3, con evidence y provenance completas.
- `{artifacts['detectors'].name}`: contribución por detector, phenotype, target e idioma.
- `{artifacts['templates'].name}`: consistencia de plantillas exactas.
- `{artifacts['audit_summary'].name}` y `{artifacts['audit_issues'].name}`: auditoría exhaustiva.
- `{artifacts['metadata'].name}`: hashes, schema, garantías y reproducibilidad.

## 12. Limitaciones

- La arquitectura sigue siendo rule-based; no existe un parser clínico completo.
- Las familias morfológicas están acotadas al corpus actual y no prueban generalización fuera de él.
- Las vistas vinculadas son deliberadamente conservadoras y pueden omitir relaciones válidas.
- La confidence es ordinal, no calibrada.
- El gold permanente es demasiado pequeño para definir con seguridad la semántica de phenotypes leves o degenerativos.
- Coverage no equivale a exactitud; los nuevos pares deben auditarse mediante provenance.

## 13. Conclusión

V3 transforma el extractor de coincidencias locales en un sistema de proposiciones clínicas auditables sin abandonar la interpretabilidad ni la política de no mención. La separación entre extracción, phenotype, reconciliación y mapeo binario permite aumentar coverage de manera localizada, medir exactamente qué detector produjo cada cambio y conservar v2 como baseline reproducible.
"""
    path.write_text(text, encoding="utf-8")


def write_v3_implementation_report(path: Path, artifacts: dict[str, Path], figures: dict[str, Path]) -> None:
    text = f"""# 03 Report Label Generation v3 — Implementation

## Technical summary

`{POLICY_VERSION}` coexiste con v2 y conserva sus artefactos. La política se selecciona desde el CLI; v3 agrega un intermediate representation tipado y un pipeline de comparación completo.

## Architecture

```text
Report
  → language hypotheses + strict/linked text views
  → exact v2 branch + controlled morphology + target detectors
  → Mention
  → deduplicated Proposition
  → target reconciliation
  → derived status/label + structured provenance
  → corpus-only audits and v2 comparison
  → final frozen-gold evaluation
  → official override and versioned artifacts
```

## Modules

- `v3/schema.py`: `TextView`, `Mention` y `Proposition`.
- `v3/text.py`: segmentación multivista y routing lingüístico no exclusivo.
- `v3/morphology.py`: reglas acotadas por idioma/target y exclusiones.
- `v3/extraction.py`: ensemble de evidence y detectores target-específicos.
- `v3/reconciliation.py`: deduplicación, precedencias y conflictos.
- `v3/evaluation.py`: provenance audit, detector summaries y template consistency.
- `v3/pipeline.py`: persistencia, comparación v2→v3, figuras y metadata.
- `v3/reporting.py`: reporte analítico y este reporte técnico.
- `config/03_report_label_generation/{POLICY_CONFIG_NAME}`: contrato declarativo.

## Compatibility

V2 no fue modificada internamente. `python scripts/generate_report_labels.py --policy v2` reproduce la política congelada. El default del entry point es v3.

## Output schema additions

- `phenotypes`: phenotypes de las proposiciones seleccionadas.
- `detectors`: ramas que sostienen evidence.
- `evidence_provenance`: status, phenotype, evidence, detector, view, language, confidence, collective y rule.

## Validation order

1. Input y cardinalidad.
2. Extraction sin consultar gold.
3. Auditoría de 12 invariantes.
4. Consistencia de plantillas exactas y normalizadas respecto de números.
5. Comparación con v2.
6. Evaluación final en los 58 gold.
7. Override official y persistencia.

## Commands

```powershell
python -m unittest discover -s tests -v
python scripts/generate_report_labels.py --policy v3
python scripts/generate_report_labels.py --policy v2
```

## Generated artifacts

La supervisión principal es `{artifacts['supervision'].name}`. La comparación se materializa en `{artifacts['coverage_delta'].name}`, `{artifacts['transitions'].name}` y `{artifacts['newly_resolved'].name}`. La trazabilidad se resume en `{artifacts['detectors'].name}` y la validación corpus-only en `{artifacts['templates'].name}`, `{artifacts['audit_summary'].name}` y `{artifacts['audit_issues'].name}`.

Las figuras generadas son `{figures['status'].name}`, `{figures['metrics'].name}` y `{figures['delta'].name}`.

## Dependency policy

No se agregaron dependencias. La implementación usa Python estándar, pandas, NumPy y Matplotlib ya fijados por el proyecto. No se usa un servicio externo, LLM, traducción web, DICOM ni metadata de imagen.

## Remaining limitations

La morfología es controlada y no equivale a lematización completa. El grafo se implementa como relaciones y proposiciones tipadas, no como dependency parser. La recuperación por similitud se limita en esta release a validación mediante plantillas exactas y numeric-normalized: no puede emitir labels.
"""
    path.write_text(text, encoding="utf-8")
