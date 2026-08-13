"""Markdown reports generated from stage artifacts and in-memory results."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from .constants import POLICY_CONFIG_NAME, POLICY_VERSION, TARGETS


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


def write_stage_report(
    path: Path,
    train: pd.DataFrame,
    supervision: pd.DataFrame,
    metrics: pd.DataFrame,
    errors: pd.DataFrame,
    languages: pd.DataFrame,
    audit_summary: pd.DataFrame,
    audit_issues: pd.DataFrame,
    artifacts: dict[str, Path],
    figures: dict[str, Path],
) -> None:
    status_counts = supervision["status"].value_counts()
    final_counts = supervision["final_source"].value_counts()
    resolved_studies = supervision.groupby("StudyInstanceUID")["final_label"].apply(lambda values: values.notna().all()).sum()
    coverage = metrics[["target", "gold_positives", "gold_negatives", "coverage", "precision", "recall", "f1", "fp", "fn", "unknown", "uncertain"]]
    errors_by_type = errors["error_type"].value_counts().rename_axis("error_type").reset_index(name="cases")
    lang_display = languages[["language_group", "studies", "gold_studies", "resolved_rate"]]
    all_resolved_rate = supervision["derived_label"].notna().mean()

    text = f"""# 03 Report Label Generation

## 1. Executive Summary

Esta etapa implementa una política textual interpretable para transformar los {len(train):,} reportes de `train.csv` en estados auditables para los 12 targets. La política `{POLICY_VERSION}` reconoce evidencia target-específica, negación, normalidad, incertidumbre y menciones colectivas seguras en varios grupos lingüísticos. La ausencia de mención se conserva como `unknown`.

Antes de cualquier override, la extracción se evaluó contra los 58 Studies con labels oficiales completos. La cobertura binaria observada sobre ese conjunto es target-dependiente; las métricas de abajo describen sólo 58 casos y no constituyen evidencia concluyente de generalización. Para la supervisión final se aplicó la prioridad `official > report_derived`, preservando en columnas separadas los valores derived, official y final.

La etapa produce un contrato reusable para el futuro pipeline MRI, pero no procesa DICOM ni píxeles y no entrena ningún modelo visual.

## 2. Previous Stage Connection

La caracterización inicial estableció una fila por `StudyInstanceUID`, 4.407 reportes, 12 targets y sólo 58 filas completamente anotadas. La revisión posterior de notebooks públicos confirmó el flujo `Report → supervisión de entrenamiento → modelo MRI sin Report en inferencia`. Esos dos resultados motivan esta etapa 03 y fijan dos decisiones: el texto sólo construye supervisión y los labels oficiales tienen prioridad únicamente después de evaluar el extractor.

## 3. Objective and Questions

El objetivo fue construir supervisión reproducible desde `Report` sin usar MRI ni metadata de adquisición. Las preguntas operativas fueron: qué evidencia textual permite resolver cada target; cómo distinguir afirmación, negación, incertidumbre y silencio; qué cobertura ofrece una política multilingüe conservadora; cómo se comporta frente al gold set; y qué provenance necesita el siguiente componente.

## 4. Data and Inputs

- Fuente: `data/train.csv`.
- Unidad: `StudyInstanceUID`; {len(train):,} IDs únicos y ningún duplicado.
- Texto: {train['Report'].notna().sum():,} Reports no missing.
- Targets: {len(TARGETS)} columnas binarias parcialmente observadas.
- Gold: {train[list(TARGETS)].notna().all(axis=1).sum():,} Studies con los 12 labels completos.
- Variables excluidas: DICOM, PixelData, tablas de Series, scanner y plano anatómico.

## 5. Problem Formulation

Para cada par Study-target se guarda `status ∈ {{positive, negative, uncertain, unknown}}`. `derived_label` sólo vale 1 o 0 para estados positive/negative; uncertain y unknown permanecen missing. `derived_score` ordena evidencia explícita pero no es una probabilidad calibrada. `confidence` está en `[0,1]` y representa fuerza determinista de evidencia. `official_label` conserva el gold cuando existe. `final_label` usa official y, en su ausencia, un derived binario; `final_source` explicita `official`, `report_derived` o `unresolved`.

## 6. Relevant Text Exploration

La medición por script y marcadores léxicos muestra heterogeneidad sustancial; los grupos son auxiliares reproducibles y no diagnósticos perfectos de idioma.

{_table(lang_display)}

Esta distribución descartó una solución English-only. La tasa `resolved_rate` se calcula sobre los 12 targets por Study y muestra dónde el léxico conservador deja mayor proporción sin resolver.

## 7. Methodology

1. Normalización Unicode determinista: case folding, remoción de diacríticos, guiones y espacios homogéneos, preservando escrituras griega y cirílica.
2. Segmentación en cláusulas y contexto de secciones. Se unen continuaciones con igual indentación que empiezan en minúscula después de coma o de una línea extensa sin puntuación; una línea en blanco impide la unión. Indicaciones, antecedentes y técnica se excluyen de las afirmaciones diagnósticas.
3. Matching target-específico mediante anatomía y vocabulario patológico separado para ligamentos, meniscos y compartimentos OA. Dentro de una cláusula, cada hallazgo se asocia con la anatomía compatible más próxima para evitar contaminación entre targets; los hallazgos directos usan términos propios.
4. Negación, normalidad e incertidumbre se resuelven dentro de la cláusula local.
5. Las menciones colectivas explícitas se expanden sólo cuando la semántica lo permite: una normalidad grupal se propaga con menor confidence; un positivo ambiguo de cruzados o colaterales no se asigna a un miembro particular.
6. Agregación conservadora: positivo explícito, negativo explícito, uncertain o unknown. Los conflictos conservan positivo con menor confidence y evidencia completa.
7. Persistencia evidence-first: se guardan primero las cláusulas que determinan el estado y, si existe conflicto real entre cláusulas distintas, al menos una evidencia discordante visible.
8. Auditoría exhaustiva por fila: schema, provenance, correspondencia entre evidence y cláusula diagnóstica, visibilidad de la evidencia decisiva, rationale y confidence.
9. Evaluación derived vs official antes del override y construcción final con prioridad official y provenance.

## 8. Decisions

- El silencio no es evidencia negativa: queda `unknown`.
- La incertidumbre explícita no se binariza.
- No se usan excepciones por Study ni reglas ajustadas a observaciones puntuales del gold set.
- La confidence es ordinal y determinista, no calibrada; la evidencia colectiva recibe menor valor que una mención target-específica.
- Se usa CSV largo porque es interoperable con las dependencias existentes y no exige un motor Parquet adicional.
- No se infiere Synovitis desde Effusion ni Contusion desde edema inespecífico: esas proxies aumentarían cobertura a costa de cambiar la semántica del target.

La revisión de menor a mayor cobertura lingüística incorporó flexiones y expresiones observadas en el corpus para griego, turco, búlgaro/cirílico, sudeslavo, neerlandés, alemán, español, francés e inglés. La revisión equivalente por target priorizó Synovitis, Contusion y Fracture, luego OA, Baker y finalmente ligamentos, meniscos y Effusion. Los primeros tres conservan baja cobertura porque se evitó reemplazar mención explícita con proxies como derrame, edema medular o normalidad ósea global.

El análisis también rechazó resoluciones previas espurias: la normalidad del menisco dentro de un compartimento no niega OA, y una rotura meniscal próxima al MCL no demuestra lesión del ligamento. Por eso una mejora léxica puede aumentar positivos explícitos mientras una corrección de alcance devuelve otros pares a `unknown`.

## 9. Findings and Results

La política resolvió {supervision['derived_label'].notna().sum():,} de {len(supervision):,} pares Study-target ({all_resolved_rate:.1%}). Estados completos: positive={status_counts.get('positive', 0):,}, negative={status_counts.get('negative', 0):,}, uncertain={status_counts.get('uncertain', 0):,}, unknown={status_counts.get('unknown', 0):,}.

### Observed Evaluation on the Gold Set

{_table(coverage)}

![Estados de extracción](../../figures/03_report_label_generation/{figures['status'].name})

La figura muestra que coverage y unresolved dependen fuertemente del target; los hallazgos que suelen declararse directamente tienen un patrón distinto de los que requieren anatomía más patología.

![Métricas en gold](../../figures/03_report_label_generation/{figures['metrics'].name})

La segunda figura separa cobertura de precision/recall/F1. Estas últimas se calculan únicamente entre casos binariamente resueltos; por eso no deben leerse sin la barra de coverage.

## 10. Interpretation

Lo observado establece que una política léxica conservadora puede producir una fracción relevante de labels auditables sin convertir silencios en negativos. No establece que los scores sean probabilidades ni que pequeñas diferencias entre targets se generalicen. El tamaño N=58 amplifica la variabilidad y algunos gold labels pueden codificar una semántica más amplia o distinta de la frase explícita del reporte.

## 11. Error Analysis

El artefacto de error analysis incluye FP, FN, unknown y uncertain con Report y evidencia. Resumen:

{_table(errors_by_type)}

Los patrones esperables son vocabulario no cubierto, alcance imperfecto de negación, frases con varias estructuras, incertidumbre, variación lingüística y discrepancia report/gold. Una discordancia no se atribuye automáticamente al extractor: reporte y gold pueden representar criterios clínicos o ventanas de información diferentes.

### Consistency Audit

La auditoría evaluó las {len(supervision):,} filas y cada elemento de `evidence` persistido. Los issues remanentes se guardan de forma separada; total observado: {len(audit_issues):,}.

{_table(audit_summary)}

## 12. Final Supervision Output

El artefacto final contiene {len(supervision):,} filas largas ({len(train):,} Studies × {len(TARGETS)} targets). Provenance final: official={final_counts.get('official', 0):,}, report_derived={final_counts.get('report_derived', 0):,}, unresolved={final_counts.get('unresolved', 0):,}. Hay {resolved_studies:,} Studies con los 12 `final_label` resueltos. Los {58 * 12:,} pares gold se preservan como official aun cuando la extracción textual discrepe.

## 13. Artifacts and Figures

- `artifacts/03_report_label_generation/{artifacts['supervision'].name}`: artefacto principal largo; contiene derived, score, confidence, status, evidencia, official, final y provenance.
- `artifacts/03_report_label_generation/{artifacts['metrics'].name}`: métricas por target calculadas antes del override.
- `artifacts/03_report_label_generation/{artifacts['errors'].name}`: auditoría de FP, FN, unknown y uncertain sobre los 58 gold Studies.
- `artifacts/03_report_label_generation/{artifacts['languages'].name}`: resumen de grupos lingüísticos y estados.
- `artifacts/03_report_label_generation/{artifacts['coverage'].name}`: grilla completa idioma-target, ordenada de menor a mayor cobertura.
- `artifacts/03_report_label_generation/{artifacts['audit_summary'].name}`: conteos de diez invariantes evaluadas sobre todo el artefacto.
- `artifacts/03_report_label_generation/{artifacts['audit_issues'].name}`: detalle Study-target de cualquier inconsistencia remanente.
- `artifacts/03_report_label_generation/{artifacts['metadata'].name}`: versión de política, input/hash, schema, conteos, hashes y definición de confidence.
- `figures/03_report_label_generation/{figures['status'].name}`: composición de estados por target; se interpreta junto con coverage.
- `figures/03_report_label_generation/{figures['metrics'].name}`: coverage y métricas gold por target; N=58 limita las conclusiones.
- `reports/stages/{path.name}`: este registro de conocimiento y decisiones.
- `reports/implementation/03_report_label_generation_implementation.md`: arquitectura, archivos, tests y comandos.

## 14. Limitations

- El gold set tiene 58 Studies y puede no representar todos los idiomas, centros o estilos.
- Los grupos lingüísticos son heurísticos; texto mixto o transliterado puede clasificarse de forma imperfecta.
- Los léxicos no agotan sinonimia, flexión ni errores tipográficos.
- El alcance de negación por cláusula puede fallar en oraciones con varias afirmaciones.
- Unknown y uncertain reducen la cobertura utilizable; esto es una decisión conservadora.
- Algunos targets, en especial Synovitis, pueden no mencionarse aunque estén presentes en MRI.
- Confidence ordena fuerza de evidencia; no está calibrada contra frecuencia clínica.
- Report y gold pueden no codificar exactamente la misma definición o granularidad.

## 15. Conclusions

Queda establecida una segunda política versionada, modular y auditable para `Report → supervisión`. Derived y official se mantienen separados, la evaluación precede al override y los estados no resueltos permanecen missing. Los resultados cuantifican cobertura y errores sin presentar el gold set pequeño como validación definitiva.

## 16. Propuesta conceptual para una eventual v3 — no implementada

Si se busca ampliar cobertura sin diluir precisión, la alternativa prudente no es sumar un segundo generador que vote labels completos, sino combinar evidencia a nivel de mención. Una v3 podría ejecutar en paralelo: reglas comunes de alta precisión; léxicos y patrones morfosintácticos por idioma; y patrones target-específicos para patologías cuya terminología no es intercambiable. Un reconciliador conservaría provenance por span, aplicaría prioridad `target-specific > collective > generic` y sólo emitiría un label cuando alguna rama aporte una mención explícita. El desacuerdo quedaría `uncertain` o requeriría revisión; ninguna rama podría convertir no mención en negativo. Esta arquitectura debería evaluarse contra un gold multilingüe mayor antes de reemplazar v2.

## 17. Next Stage Connection

El siguiente componente puede consumir `final_label`, `final_source`, `confidence` y máscaras de missing por Study-target. La transición prevista es `report-derived + gold supervision → MRI preprocessing/representation → first visual baseline`. Esa etapa deberá usar exclusivamente información visual disponible en inferencia y queda fuera del alcance actual.
"""
    path.write_text(text, encoding="utf-8")


def write_implementation_report(path: Path, artifacts: dict[str, Path], figures: dict[str, Path]) -> None:
    text = f"""# 03 Report Label Generation — Implementation

## Technical Summary

Se implementó la etapa 03 como módulos Python y un entry point sin notebook. La versión activa es `{POLICY_VERSION}`. El flujo lee únicamente `StudyInstanceUID`, `Report` y los 12 targets oficiales de `train.csv`; no importa ni consulta DICOM o tablas de Series.

## Stage Context

El componente materializa la supervisión textual identificada por las etapas de caracterización y revisión de estrategia. Su salida es un contrato para entrenamiento MRI posterior, no un modelo predictivo.

## Architecture

```text
train.csv
   → validación de input
   → normalización, secciones y grupo lingüístico
   → extracción target-específica
   → derived labels + confidence + evidence
   → evaluación contra gold (antes del override)
   → official override
   → artefactos + figuras + reportes
```

## Files Created or Modified

- `src/report_labels/__init__.py`: API pública del paquete.
- `src/report_labels/constants.py`: targets, dominios y política léxica multilingüe.
- `src/report_labels/text.py`: normalización, segmentación, contexto y grupos lingüísticos.
- `src/report_labels/extraction.py`: extracción y agregación de evidencia por target.
- `src/report_labels/evaluation.py`: métricas gold y error analysis.
- `src/report_labels/pipeline.py`: validaciones, override, persistencia y figuras.
- `src/report_labels/reporting.py`: generación de ambos Markdown desde resultados reales.
- `scripts/generate_report_labels.py`: entry point reproducible.
- `config/03_report_label_generation/{POLICY_CONFIG_NAME}`: contrato y parámetros declarativos de la versión activa.
- `tests/test_report_labels.py`: tests unitarios e integración/schema.
- `.gitignore`: excepciones acotadas para versionar outputs de esta etapa.
- `README.md`: comando y contrato principal.

## Modules and Responsibilities

`ReportLabelExtractor.extract(report)` devuelve un `ExtractionResult` por target sin consultar gold. `build_supervision(train)` expande Studies a formato largo. `evaluate_gold(frame)` calcula métricas sólo con derived pre-override. `validate_supervision(frame, train, expected_studies)` protege cardinalidad, dominios, provenance, missing y prioridad official. `run_pipeline(...)` orquesta la etapa completa.

## Entry Points

Desde la raíz:

```powershell
python scripts/generate_report_labels.py
```

Los paths pueden cambiarse mediante argumentos `--train`, `--artifact-dir`, `--figure-dir`, `--stage-report` y `--implementation-report`.

## Configuration

`{POLICY_CONFIG_NAME}` declara versión, 12 targets, estados válidos, prioridad de fuentes, semántica de confidence, política de menciones colectivas, cardinalidades esperadas y prohibición de inputs MRI. Los léxicos ejecutables permanecen en Python para permitir tests y revisión de cambios.

## Tests

Los tests cubren afirmación ACL, negación, incertidumbre, ausencia de mención, determinismo, contexto no diagnóstico, plurales multilingües, menciones colectivas seguras y ambiguas, line wrapping, el Study auditado, schema 4.407 × 12, conservación de Studies, dominios, unresolved y gold override. Se usa `unittest`, por lo que no se agregó una dependencia de testing.

```powershell
python -m unittest discover -s tests -v
```

## Dependencies

Se reutilizan Python estándar, pandas, NumPy y Matplotlib ya presentes. Se eligió CSV largo en vez de Parquet para no incorporar `pyarrow` sólo por persistencia.

## Generated Artifacts

- `artifacts/03_report_label_generation/{artifacts['supervision'].name}`: supervisión larga principal.
- `artifacts/03_report_label_generation/{artifacts['metrics'].name}`: métricas pre-override por target.
- `artifacts/03_report_label_generation/{artifacts['errors'].name}`: casos auditables gold.
- `artifacts/03_report_label_generation/{artifacts['languages'].name}`: cobertura lingüística.
- `artifacts/03_report_label_generation/{artifacts['coverage'].name}`: cobertura y estados para cada combinación idioma-target.
- `artifacts/03_report_label_generation/{artifacts['audit_summary'].name}`: auditoría agregada de consistencia.
- `artifacts/03_report_label_generation/{artifacts['audit_issues'].name}`: inconsistencias detalladas, vacío cuando se cumplen todas las invariantes.
- `artifacts/03_report_label_generation/{artifacts['metadata'].name}`: schema, hashes, versión y conteos.

## Generated Figures

- `figures/03_report_label_generation/{figures['status'].name}`: estados por target; utilizada en el reporte de etapa.
- `figures/03_report_label_generation/{figures['metrics'].name}`: coverage y métricas gold; utilizada en el reporte de etapa.

## Generated Reports

- `reports/stages/03_report_label_generation.md`: resultados, decisiones e interpretación.
- `reports/implementation/{path.name}`: este documento técnico.

## Reproduction

```powershell
python -m unittest discover -s tests -v
python scripts/generate_report_labels.py
```

Los labels, métricas, errores y figuras son deterministas para input y código fijos. `execution_timestamp_utc` del metadata cambia en cada ejecución y está documentado como campo operativo.

## Technical Limitations

La segmentación y el alcance de negación son basados en reglas; no existe parser clínico. Los léxicos requieren mantenimiento explícito y los grupos lingüísticos no sustituyen language identification validado. CSV no conserva tipos nullable tan estrictamente como Parquet, por lo que el schema se valida al generar y se registra en metadata.

## Interface With the Next Stage

El pipeline MRI dispone de una fila por Study-target con `final_label`, `final_source`, `confidence` y missing explícito. Debe pivotar por `StudyInstanceUID`, construir máscaras de pérdida para unresolved y mantener mayor peso o tratamiento separado para `official`. El Report no forma parte del contrato de inferencia.
"""
    path.write_text(text, encoding="utf-8")
