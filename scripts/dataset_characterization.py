#!/usr/bin/env python
"""Caracterización descriptiva y reproducible del dataset RSNA Knee.

El script no modifica los datos fuente. Recorre exhaustivamente la estructura
de archivos y las tablas CSV. Para DICOM lee, sin PixelData, una instancia
determinista por Study; de este modo cubre todos los estudios sin convertir una
revisión inicial en una lectura redundante de cada slice.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pydicom


TARGETS = [
    "ACL",
    "MCL",
    "Medial Meniscus",
    "Lateral Meniscus",
    "Medial OA",
    "Lateral OA",
    "PF OA",
    "Effusion",
    "Synovitis",
    "Baker's",
    "Contusion",
    "Fracture",
]

DICOM_TAGS = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "SOPInstanceUID",
    "InstanceNumber",
    "Manufacturer",
    "ManufacturerModelName",
    "MagneticFieldStrength",
    "InstitutionName",
    "StationName",
    "ProtocolName",
    "SeriesDescription",
    "SequenceName",
    "ScanningSequence",
    "SequenceVariant",
    "Rows",
    "Columns",
    "PixelSpacing",
    "SliceThickness",
    "SpacingBetweenSlices",
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "Laterality",
    "ImageLaterality",
    "BodyPartExamined",
]

IDENTIFIER_TAGS = {
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "SOPInstanceUID",
}


def esc(value: Any) -> str:
    """Escapa texto para una celda Markdown."""
    if value is None:
        return "—"
    text = str(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|")
    return text if text else "—"


def fmt_int(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def fmt_num(value: Any, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: Any, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{float(value):.{digits}f}%".replace(".", ",")


def human_bytes(n_bytes: int) -> str:
    value = float(n_bytes)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TiB"


def stats(values: Iterable[float]) -> dict[str, float]:
    s = pd.Series(list(values), dtype="float64").dropna()
    if s.empty:
        return {}
    q = s.quantile([0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    return {
        "N": int(s.size),
        "Media": float(s.mean()),
        "Varianza": float(s.var(ddof=0)),
        "SD": float(s.std(ddof=0)),
        "P25": float(q.loc[0.25]),
        "Mediana": float(q.loc[0.5]),
        "P75": float(q.loc[0.75]),
        "P90": float(q.loc[0.9]),
        "P95": float(q.loc[0.95]),
        "P99": float(q.loc[0.99]),
        "Mín": float(s.min()),
        "Máx": float(s.max()),
    }


def markdown_table(headers: list[str], rows: list[list[Any]], align_right: set[int] | None = None) -> str:
    align_right = align_right or set()
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---:" if i in align_right else "---" for i in range(len(headers))) + " |")
    out.extend("| " + " | ".join(esc(v) for v in row) + " |" for row in rows)
    return "\n".join(out)


def normalized_dicom_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)) or value.__class__.__name__ == "MultiValue":
        return "\\".join(str(v) for v in value)
    text = str(value).strip()
    return text or None


def scan_partition(base: Path, partition: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    ext_counts: Counter[str] = Counter()
    file_count = 0
    study_count = 0
    series_count = 0
    unexpected: list[str] = []

    study_entries = sorted((e for e in os.scandir(base) if e.is_dir(follow_symlinks=False)), key=lambda e: e.name)
    for study_index, study_entry in enumerate(study_entries, start=1):
        study_count += 1
        series_entries = sorted(
            (e for e in os.scandir(study_entry.path) if e.is_dir(follow_symlinks=False)), key=lambda e: e.name
        )
        for entry in os.scandir(study_entry.path):
            if not entry.is_dir(follow_symlinks=False):
                unexpected.append(str(Path(entry.path).relative_to(base.parent)))
        for series_entry in series_entries:
            series_count += 1
            n_files = 0
            n_dicom = 0
            example_dicom: str | None = None
            for file_entry in os.scandir(series_entry.path):
                if not file_entry.is_file(follow_symlinks=False):
                    unexpected.append(str(Path(file_entry.path).relative_to(base.parent)))
                    continue
                suffix = Path(file_entry.name).suffix.lower() or "[sin extensión]"
                ext_counts[suffix] += 1
                file_count += 1
                n_files += 1
                if suffix == ".dcm":
                    n_dicom += 1
                    if example_dicom is None or file_entry.name < Path(example_dicom).name:
                        example_dicom = file_entry.path
            records.append(
                {
                    "partition": partition,
                    "path_study_uid": study_entry.name,
                    "path_series_uid": series_entry.name,
                    "n_files": n_files,
                    "n_slices": n_dicom,
                    "example_dicom": example_dicom,
                }
            )
        if study_index % 500 == 0:
            print(f"[{partition}] estructura: {study_index:,}/{len(study_entries):,} estudios", flush=True)

    return records, {
        "partition": partition,
        "studies": study_count,
        "series": series_count,
        "files": file_count,
        "extensions": ext_counts,
        "unexpected": unexpected,
        "directories": 1 + study_count + series_count,
    }


def read_dicom_headers(series_df: pd.DataFrame, max_studies: int) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    selected_indices: list[int] = []
    for partition, group in series_df.groupby("partition", sort=True):
        # Una serie determinista (la primera ordenada) por cada Study.
        indices = group.groupby("path_study_uid", sort=True).head(1).index.to_list()
        if max_studies > 0 and len(indices) > max_studies:
            positions = np.linspace(0, len(indices) - 1, max_studies, dtype=int)
            indices = [indices[p] for p in positions]
        selected_indices.extend(indices)

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    total = len(selected_indices)
    for position, idx in enumerate(selected_indices, start=1):
        source = series_df.loc[idx]
        path = source["example_dicom"]
        base = {
            "partition": source["partition"],
            "path_study_uid": source["path_study_uid"],
            "path_series_uid": source["path_series_uid"],
            "path_sop_uid": Path(path).stem if path else None,
            "path": path,
        }
        if not path:
            errors.append({"path": str(Path(source["partition"]) / source["path_study_uid"] / source["path_series_uid"]), "error": "Serie sin DICOM"})
            continue
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True, force=False)
            row = dict(base)
            for tag in DICOM_TAGS:
                row[tag] = normalized_dicom_value(getattr(ds, tag, None))
            rows.append(row)
        except Exception as exc:  # la revisión no debe abortar por un header ilegible
            errors.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
        if position % 1000 == 0 or position == total:
            print(f"DICOM headers: {position:,}/{total:,}", flush=True)
    return pd.DataFrame(rows), errors


def column_level(column: str) -> str:
    if column == "StudyInstanceUID":
        return "Study"
    if column == "SeriesInstanceUID":
        return "Series"
    if column == "Report":
        return "Report"
    if column in TARGETS:
        return "Target / Label"
    if column in {"Fluid_Sensitive", "Fat_Suppression", "Anatomical_Plane"}:
        return "Metadata técnica"
    return "No determinado"


def column_interpretation(file_name: str, column: str) -> str:
    if column == "StudyInstanceUID":
        return "Identificador DICOM global del MRI Study / Exam."
    if column == "SeriesInstanceUID":
        return "Identificador DICOM global de la Series dentro de un Study."
    if column == "Report":
        return "Texto del reporte radiológico asociado al Study."
    if column == "Fluid_Sensitive":
        return "Indicador binario provisto para caracterizar si la serie es sensible a fluido."
    if column == "Fat_Suppression":
        return "Indicador binario provisto para caracterizar supresión de grasa."
    if column == "Anatomical_Plane":
        return "Plano anatómico categórico provisto para la serie."
    if column in TARGETS:
        if file_name == "sample_submission.csv":
            return "Columna de predicción del template de submission; 0,5 es un valor placeholder."
        return f"Label binario observado denominado «{column}» cuando no es missing."
    return "No determinado a partir de los datos inspeccionados."


def example_values(series: pd.Series, column: str) -> str:
    values = series.dropna()
    if values.empty:
        return "—"
    if column == "Report":
        lengths = values.astype(str).str.len().head(3).tolist()
        return "longitudes (chars): " + ", ".join(map(str, lengths))
    examples = values.astype(str).drop_duplicates().head(3).tolist()
    return "; ".join(examples)


def save_hist(values: pd.Series, path: Path, title: str, xlabel: str, discrete: bool = False, clip_p99: bool = False) -> None:
    clean = pd.Series(values, dtype="float64").dropna()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    plotted = clean
    suffix = ""
    if clip_p99 and not clean.empty:
        limit = clean.quantile(0.99)
        plotted = clean[clean <= limit]
        suffix = f" (visualización hasta P99={limit:g})"
    if discrete and clean.nunique() <= 40:
        counts = plotted.value_counts().sort_index()
        ax.bar(counts.index.astype(str), counts.values, color="#33658A")
    else:
        bins = min(50, max(10, int(math.sqrt(max(len(plotted), 1)))))
        ax.hist(plotted, bins=bins, color="#33658A", edgecolor="white")
    ax.set_title(title + suffix)
    ax.set_xlabel(xlabel, loc="center")
    ax.set_ylabel("Frecuencia", loc="center")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_bar(series: pd.Series, path: Path, title: str, xlabel: str, ylabel: str, horizontal: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    if horizontal:
        ax.barh(series.index.astype(str), series.values, color="#33658A")
        ax.set_xlabel(ylabel, loc="center")
        ax.set_ylabel(xlabel, loc="center")
        ax.invert_yaxis()
    else:
        ax.bar(series.index.astype(str), series.values, color="#33658A")
        ax.set_xlabel(xlabel, loc="center")
        ax.set_ylabel(ylabel, loc="center")
        ax.tick_params(axis="x", rotation=45)
    ax.set_title(title)
    ax.grid(axis="y" if not horizontal else "x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--data-dir", type=Path, default=repo_root / "data")
    parser.add_argument("--report", type=Path, default=repo_root / "reports" / "dataset_initial_characterization.md")
    parser.add_argument("--figures-dir", type=Path, default=repo_root / "reports" / "figures")
    parser.add_argument(
        "--max-dicom-studies",
        type=int,
        default=0,
        help="Máximo de Studies DICOM por partición (0 = todos); siempre se lee una instancia por Study.",
    )
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    report_path = args.report.resolve()
    figures_dir = args.figures_dir.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_paths = sorted(data_dir.glob("*.csv"))
    tables = {p.name: pd.read_csv(p) for p in csv_paths}
    required = {"train.csv", "test.csv", "train_series.csv", "test_series.csv", "sample_submission.csv"}
    missing_required = required - tables.keys()
    if missing_required:
        raise FileNotFoundError(f"Faltan tablas esperadas después del descubrimiento: {sorted(missing_required)}")

    all_records: list[dict[str, Any]] = []
    scan_summaries: dict[str, dict[str, Any]] = {}
    for partition in ("train", "test"):
        records, summary = scan_partition(data_dir / f"{partition}_series", partition)
        all_records.extend(records)
        scan_summaries[partition] = summary
    physical_series = pd.DataFrame(all_records)

    # Incluye las tablas raíz en las métricas físicas globales.
    root_files = [p for p in data_dir.iterdir() if p.is_file()]
    root_bytes = sum(p.stat().st_size for p in root_files)
    root_empty = sum(p.stat().st_size == 0 for p in root_files)
    ext_counts = Counter(p.suffix.lower() or "[sin extensión]" for p in root_files)
    for summary in scan_summaries.values():
        ext_counts.update(summary["extensions"])
    total_files = len(root_files) + sum(v["files"] for v in scan_summaries.values())
    total_dirs = 1 + sum(v["directories"] for v in scan_summaries.values())

    # El stat de cientos de miles de archivos es costoso en este volumen. Se
    # estima el tamaño DICOM con hasta 1.000 archivos por partición, elegidos de
    # forma determinista y equiespaciada entre Series; los CSV sí se miden todos.
    estimated_dicom_bytes = 0.0
    size_sample_sizes: list[int] = []
    for partition, group in physical_series.groupby("partition", sort=True):
        candidates = group.loc[group["example_dicom"].notna(), "example_dicom"].tolist()
        if len(candidates) > 1000:
            positions = np.linspace(0, len(candidates) - 1, 1000, dtype=int)
            candidates = [candidates[p] for p in positions]
        sizes = []
        for path in candidates:
            try:
                sizes.append(Path(path).stat().st_size)
            except OSError:
                continue
        size_sample_sizes.extend(sizes)
        partition_slices = int(group["n_slices"].sum())
        estimated_dicom_bytes += (float(np.mean(sizes)) * partition_slices) if sizes else 0.0
    total_bytes = int(root_bytes + estimated_dicom_bytes)
    empty_files_inspected = root_empty + sum(size == 0 for size in size_sample_sizes)

    dicom, dicom_errors = read_dicom_headers(physical_series, args.max_dicom_studies)
    dicom_sample_scope = "todos los Studies físicos" if args.max_dicom_studies == 0 else f"hasta {args.max_dicom_studies:,} Studies por partición"

    train = tables["train.csv"]
    test = tables["test.csv"]
    train_series = tables["train_series.csv"]
    test_series = tables["test_series.csv"]
    submission = tables["sample_submission.csv"]
    test_uid_set = set(test["StudyInstanceUID"].astype(str))
    submission_uid_set = set(submission["StudyInstanceUID"].astype(str))
    submission_matches_test = (
        test_uid_set == submission_uid_set
        and submission["StudyInstanceUID"].is_unique
        and len(submission) == len(test)
    )

    # Métricas exhaustivas derivadas de tablas y estructura de archivos.
    series_per_study = physical_series.groupby(["partition", "path_study_uid"]).size().rename("n_series")
    slices_per_series = physical_series.set_index(["partition", "path_series_uid"])["n_slices"]
    slices_per_study = physical_series.groupby(["partition", "path_study_uid"])["n_slices"].sum()

    report_chars = train["Report"].astype("string").str.len()
    report_words = train["Report"].astype("string").map(lambda x: len(re.findall(r"\b\w+\b", x, flags=re.UNICODE)) if pd.notna(x) else np.nan)
    section_patterns = {
        "Findings / equivalentes": r"\b(?:findings|hallazgos|bevindingen|resultados)\b",
        "Impression / equivalentes": r"\b(?:impression|impresi[oó]n|impressie)\b",
        "Conclusion / equivalentes": r"\b(?:conclusion|conclusi[oó]n|conclusie)\b",
    }
    section_presence = {
        name: train["Report"].astype("string").str.contains(pattern, case=False, regex=True, na=False).mean() * 100
        for name, pattern in section_patterns.items()
    }

    target_valid_rows = train[TARGETS].notna().any(axis=1)
    target_complete_rows = train[TARGETS].notna().all(axis=1)
    n_positive = train.loc[target_valid_rows, TARGETS].sum(axis=1, min_count=1)

    # PatientID se observa mediante una instancia por Study; la cobertura se explicita.
    patient_series = dicom.dropna(subset=["PatientID"]).copy() if not dicom.empty else pd.DataFrame()
    study_patient_sets: dict[str, set[str]] = defaultdict(set)
    if not patient_series.empty:
        for row in patient_series.itertuples(index=False):
            study_patient_sets[str(row.path_study_uid)].add(str(row.PatientID))
    study_to_patient = {study: next(iter(ids)) for study, ids in study_patient_sets.items() if len(ids) == 1}
    contradictory_patient_studies = {study: ids for study, ids in study_patient_sets.items() if len(ids) > 1}
    studies_per_patient = pd.Series(Counter(study_to_patient.values()), dtype="int64")

    # Figuras.
    save_hist(series_per_study, figures_dir / "series_per_study.png", "Series por Study", "Número de Series", discrete=True)
    save_hist(slices_per_series, figures_dir / "slices_per_series.png", "Slices DICOM por Series", "Número de slices", discrete=True, clip_p99=True)
    prevalence = train[TARGETS].mean(skipna=True).mul(100).sort_values(ascending=True)
    save_bar(prevalence, figures_dir / "target_prevalence.png", "Prevalencia de targets en observaciones válidas", "Target", "Prevalencia (%)", horizontal=True)
    save_hist(n_positive, figures_dir / "positive_labels_per_study.png", "Labels positivos por Study con targets", "Número de labels positivos", discrete=True)
    save_hist(report_chars, figures_dir / "report_length_chars.png", "Longitud de reportes radiológicos", "Caracteres", clip_p99=True)
    plane_counts = pd.concat([train_series["Anatomical_Plane"], test_series["Anatomical_Plane"]]).value_counts()
    save_bar(plane_counts, figures_dir / "anatomical_plane.png", "Series por plano anatómico", "Plano", "Series")
    missing_key = train[["StudyInstanceUID", "Report", *TARGETS]].isna().mean().mul(100).sort_values(ascending=False)
    save_bar(missing_key, figures_dir / "train_missingness.png", "Missingness de variables principales (train.csv)", "Variable", "Missing (%)", horizontal=True)

    # Diccionario de datos.
    dictionary_rows: list[list[Any]] = []
    for file_name, df in tables.items():
        for column in df.columns:
            missing_pct = df[column].isna().mean() * 100
            dictionary_rows.append(
                [
                    column,
                    file_name,
                    str(df[column].dtype),
                    column_level(column),
                    fmt_int(df[column].nunique(dropna=True)),
                    fmt_pct(missing_pct),
                    example_values(df[column], column),
                    column_interpretation(file_name, column),
                ]
            )

    # Identificadores tabulares.
    id_rows: list[list[Any]] = []
    for file_name, df in tables.items():
        for column, level in (("StudyInstanceUID", "Study"), ("SeriesInstanceUID", "Series")):
            if column in df:
                id_rows.append(
                    [
                        file_name,
                        column,
                        level,
                        fmt_int(df[column].nunique(dropna=True)),
                        "Sí" if df[column].is_unique else "No",
                        fmt_int(df[column].duplicated(keep=False).sum()),
                    ]
                )

    # Targets.
    target_rows: list[list[Any]] = []
    for target in TARGETS:
        valid = train[target].dropna()
        positives = int((valid == 1).sum())
        negatives = int((valid == 0).sum())
        target_rows.append(
            [target, fmt_int(valid.size), positives, negatives, fmt_num(valid.sum(), 0), fmt_pct(valid.mean() * 100)]
        )

    # Estadísticas consolidadas.
    consolidated: list[tuple[str, dict[str, float]]] = [
        ("Series por Study", stats(series_per_study)),
        ("Slices por Series", stats(slices_per_series)),
        ("Report length (chars)", stats(report_chars)),
        ("Report length (words)", stats(report_words)),
    ]
    if not studies_per_patient.empty:
        consolidated.append(("Studies por PatientID observado", stats(studies_per_patient)))
    stat_headers = ["Métrica", "N", "Media", "Varianza", "SD", "P25", "Mediana", "P75", "P90", "P95", "P99", "Mín", "Máx"]
    stat_rows = []
    for label, values in consolidated:
        stat_rows.append([label, fmt_int(values.get("N")), *[fmt_num(values.get(k)) for k in stat_headers[2:]]])

    # Resumen de metadata DICOM.
    dicom_tag_rows: list[list[Any]] = []
    for tag in DICOM_TAGS:
        values = dicom[tag].dropna() if tag in dicom else pd.Series(dtype="object")
        top = "—"
        if tag not in IDENTIFIER_TAGS and not values.empty:
            top = "; ".join(f"{esc(k)} ({fmt_int(v)})" for k, v in values.value_counts().head(5).items())
        elif tag in IDENTIFIER_TAGS and not values.empty:
            top = "Valores identificadores omitidos; se informa cardinalidad."
        dicom_tag_rows.append(
            [tag, fmt_int(values.size), fmt_pct(values.size / max(len(dicom), 1) * 100), fmt_int(values.nunique()), top]
        )

    # Consistencias de UID en la muestra DICOM.
    def mismatch_count(left: str, right: str) -> int:
        if dicom.empty:
            return 0
        comparable = dicom[[left, right]].dropna()
        return int((comparable[left].astype(str) != comparable[right].astype(str)).sum())

    study_uid_mismatch = mismatch_count("path_study_uid", "StudyInstanceUID")
    series_uid_mismatch = mismatch_count("path_series_uid", "SeriesInstanceUID")
    sop_uid_mismatch = mismatch_count("path_sop_uid", "SOPInstanceUID")

    # Metadata geométrica descriptiva.
    dimension_counts = (
        dicom.dropna(subset=["Rows", "Columns"]).assign(dimension=lambda x: x["Rows"].astype(str) + " × " + x["Columns"].astype(str))["dimension"].value_counts().head(15)
        if not dicom.empty
        else pd.Series(dtype="int64")
    )
    laterality = pd.Series(dtype="object")
    if not dicom.empty:
        laterality = dicom["ImageLaterality"].fillna(dicom["Laterality"]).fillna("Ausente").value_counts()

    # Relaciones y completitud por partición.
    completeness_rows: list[list[Any]] = []
    for partition, study_table, series_table in (
        ("train", train, train_series),
        ("test", test, test_series),
    ):
        studies = set(study_table["StudyInstanceUID"].astype(str))
        series_studies = set(series_table["StudyInstanceUID"].astype(str))
        folder_studies = set(physical_series.loc[physical_series["partition"] == partition, "path_study_uid"].astype(str))
        report_studies = set(train.loc[train["Report"].notna(), "StudyInstanceUID"].astype(str)) if partition == "train" else set()
        target_studies = set(train.loc[target_valid_rows, "StudyInstanceUID"].astype(str)) if partition == "train" else set()
        patient_studies = set(study_to_patient) & studies
        completeness_rows.append(
            [
                partition,
                fmt_int(len(studies)),
                fmt_pct(len(studies & series_studies) / max(len(studies), 1) * 100),
                fmt_pct(len(studies & folder_studies) / max(len(studies), 1) * 100),
                fmt_pct(len(studies & report_studies) / max(len(studies), 1) * 100) if partition == "train" else "No disponible",
                fmt_pct(len(studies & target_studies) / max(len(studies), 1) * 100) if partition == "train" else "No disponible",
                fmt_pct(len(patient_studies) / max(len(studies), 1) * 100),
                fmt_int(len(studies & series_studies & folder_studies)),
            ]
        )

    # Duplicados de tablas y relaciones.
    duplicate_rows = []
    for file_name, df in tables.items():
        duplicate_rows.append([file_name, fmt_int(len(df)), fmt_int(df.duplicated().sum())])
    series_relation_inconsistencies = {}
    for partition, df in (("train", train_series), ("test", test_series)):
        counts = df.groupby("SeriesInstanceUID")["StudyInstanceUID"].nunique()
        series_relation_inconsistencies[partition] = int((counts > 1).sum())

    # Comparación train/test.
    comparison_rows: list[list[Any]] = []
    for metric, train_value, test_value in (
        ("Studies (tabla principal)", train["StudyInstanceUID"].nunique(), test["StudyInstanceUID"].nunique()),
        ("Series (tabla de series)", train_series["SeriesInstanceUID"].nunique(), test_series["SeriesInstanceUID"].nunique()),
        ("Series físicas", int((physical_series["partition"] == "train").sum()), int((physical_series["partition"] == "test").sum())),
        ("Slices DICOM", int(physical_series.loc[physical_series["partition"] == "train", "n_slices"].sum()), int(physical_series.loc[physical_series["partition"] == "test", "n_slices"].sum())),
        ("Media series / Study", series_per_study.loc["train"].mean(), series_per_study.loc["test"].mean()),
        ("Media slices / Series", slices_per_series.loc["train"].mean(), slices_per_series.loc["test"].mean()),
        ("Mediana slices / Series", slices_per_series.loc["train"].median(), slices_per_series.loc["test"].median()),
    ):
        comparison_rows.append([metric, fmt_num(train_value), fmt_num(test_value)])

    plane_data = pd.concat(
        [
            train_series.assign(partition="train")[["partition", "Anatomical_Plane"]],
            test_series.assign(partition="test")[["partition", "Anatomical_Plane"]],
        ],
        ignore_index=True,
    )
    plane_comparison = pd.crosstab(plane_data["Anatomical_Plane"], plane_data["partition"])

    dicom_comparison_rows: list[list[Any]] = []
    if not dicom.empty:
        dicom_comparison = dicom.copy()
        dicom_comparison["Rows × Columns"] = np.where(
            dicom_comparison["Rows"].notna() & dicom_comparison["Columns"].notna(),
            dicom_comparison["Rows"].astype(str) + " × " + dicom_comparison["Columns"].astype(str),
            None,
        )
        for partition in ("train", "test"):
            partition_dicom = dicom_comparison[dicom_comparison["partition"] == partition]
            for tag in ("Manufacturer", "MagneticFieldStrength", "Rows × Columns"):
                values = partition_dicom[tag].dropna()
                for value, count in values.value_counts().head(10).items():
                    dicom_comparison_rows.append(
                        [partition, tag, value, fmt_int(count), fmt_pct(count / max(len(values), 1) * 100)]
                    )

    # Texto del reporte.
    train_studies = train["StudyInstanceUID"].nunique()
    test_studies = test["StudyInstanceUID"].nunique()
    all_studies = set(train["StudyInstanceUID"].astype(str)) | set(test["StudyInstanceUID"].astype(str))
    all_series_uids = set(train_series["SeriesInstanceUID"].astype(str)) | set(test_series["SeriesInstanceUID"].astype(str))
    total_slices = int(physical_series["n_slices"].sum())
    patient_count = len(set(study_to_patient.values())) if study_to_patient else None
    report_count = int(train["Report"].notna().sum())
    execution_time = datetime.now().astimezone().isoformat(timespec="seconds")

    lines: list[str] = []
    add = lines.append
    add("# RSNA Knee Abnormality Detection")
    add("## Caracterización inicial del dataset")
    add("")
    add(f"**Fecha de ejecución:** {execution_time}.  ")
    add(f"**Directorio inspeccionado:** `{data_dir.relative_to(repo_root) if data_dir.is_relative_to(repo_root) else data_dir}`.  ")
    add("**Convención estadística:** todas las varianzas y desviaciones estándar usan la convención poblacional (`ddof=0`).")
    add("")
    add("### 1. Resumen ejecutivo descriptivo")
    add("")
    add(
        f"El dataset local contiene {fmt_int(train_studies)} Studies en train y {fmt_int(test_studies)} en test. "
        f"Las imágenes están organizadas como Study → Series → Slice/DICOM Instance. Se identificaron "
        f"{fmt_int(len(all_series_uids))} Series tabulares y {fmt_int(total_slices)} archivos DICOM físicos. "
        f"`train.csv` aporta un reporte por Study; los 12 targets aparecen únicamente para "
        f"{fmt_int(target_valid_rows.sum())} de {fmt_int(len(train))} Studies de train."
    )
    add("")
    add(
        "La unidad clínica central y de unión es `StudyInstanceUID`. La unidad física mínima es el archivo DICOM "
        "(Slice/Instance), mientras que el template `sample_submission.csv` solicita una fila de predicciones por Study. "
        "Por ello, unidad de almacenamiento, unidad de label y unidad aparente de predicción no son equivalentes."
    )
    add("")
    add("#### Dimensiones generales")
    add("")
    dimensions_rows = [
        ["Patients (PatientID observado en DICOM)", fmt_int(patient_count)],
        ["Studies", fmt_int(len(all_studies))],
        ["Series (tabla)", fmt_int(len(all_series_uids))],
        ["Series (directorios físicos)", fmt_int(len(physical_series))],
        ["Slices / DICOM Instances", fmt_int(total_slices)],
        ["Radiology reports", fmt_int(report_count)],
        ["Targets", fmt_int(len(TARGETS))],
        ["Studies con algún target observado", fmt_int(target_valid_rows.sum())],
        ["Archivos totales en data/", fmt_int(total_files)],
        ["Directorios relevantes (incluye data/)", fmt_int(total_dirs)],
        ["Tamaño físico estimado", human_bytes(total_bytes)],
    ]
    add(markdown_table(["Entidad", "Cantidad"], dimensions_rows, {1}))
    add("")
    add("#### Estadísticas principales")
    add("")
    add(markdown_table(stat_headers, stat_rows, set(range(1, len(stat_headers)))))
    add("")
    add("### 2. Estructura de archivos")
    add("")
    add("```text")
    add("data/")
    add("├── train.csv                         # una fila por Study; Report y targets parcialmente observados")
    add("├── train_series.csv                  # una fila por Series")
    add("├── test.csv                          # una fila por Study")
    add("├── test_series.csv                   # una fila por Series")
    add("├── sample_submission.csv             # una fila de predicciones por Study de test")
    add("├── train_series/")
    add("│   └── <StudyInstanceUID>/<SeriesInstanceUID>/<SOPInstanceUID>.dcm")
    add("└── test_series/")
    add("    └── <StudyInstanceUID>/<SeriesInstanceUID>/<SOPInstanceUID>.dcm")
    add("```")
    add("")
    add(markdown_table(["Extensión", "Archivos"], [[k, fmt_int(v)] for k, v in sorted(ext_counts.items())], {1}))
    add("")
    add(f"El recorrido físico fue exhaustivo para nombres y conteos: {fmt_int(total_files)} archivos y {fmt_int(total_dirs)} directorios. El tamaño estimado es {human_bytes(total_bytes)}; se calculó con el tamaño exacto de los {fmt_int(len(root_files))} archivos raíz y una muestra determinista estratificada de {fmt_int(len(size_sample_sizes))} DICOM ({fmt_int(empty_files_inspected)} vacíos dentro de lo inspeccionado).")
    add("")
    add("### 3. Dimensiones generales")
    add("")
    ratio_rows = [
        ["Studies / PatientID observado", fmt_num(len(study_to_patient) / patient_count if patient_count else np.nan)],
        ["Series / Study", fmt_num(len(physical_series) / len(all_studies))],
        ["Slices / Series", fmt_num(total_slices / len(physical_series))],
        ["Slices / Study", fmt_num(total_slices / len(all_studies))],
    ]
    add(markdown_table(["Ratio", "Valor"], ratio_rows, {1}))
    add("")
    add("La cantidad de Patients se basa en `PatientID` leído en una instancia por cada Study; no existe Patient ID en los CSV. La cobertura se detalla más adelante.")
    add("")
    add("### 4. Diccionario de variables")
    add("")
    add(markdown_table(["Variable", "Archivo", "Tipo", "Nivel aparente", "Valores únicos", "Missing %", "Ejemplos no nulos", "Interpretación descriptiva"], dictionary_rows, {4, 5}))
    add("")
    add("### 5. Identificadores y jerarquía")
    add("")
    add(markdown_table(["Archivo", "Variable real", "Nivel", "Cardinalidad", "Único en tabla", "Filas en grupos duplicados"], id_rows, {3, 5}))
    add("")
    add("La jerarquía empírica observada es:")
    add("")
    add("```text")
    add("PatientID (sólo metadata DICOM)")
    add("└── StudyInstanceUID")
    add("    ├── Report (train.csv)")
    add("    ├── 12 targets parcialmente observados (train.csv)")
    add("    └── SeriesInstanceUID (tablas y directorios)")
    add("        └── SOPInstanceUID.dcm / Slice (archivos y metadata)")
    add("```")
    add("")
    add(f"Series IDs asociados a más de un Study en las tablas: train={fmt_int(series_relation_inconsistencies['train'])}, test={fmt_int(series_relation_inconsistencies['test'])}. ")
    add(f"En headers DICOM leídos: discrepancias path/header de Study UID={fmt_int(study_uid_mismatch)}, Series UID={fmt_int(series_uid_mismatch)} y filename/SOP UID={fmt_int(sop_uid_mismatch)}.")
    add("")
    if not studies_per_patient.empty:
        multi_patient_pct = (studies_per_patient > 1).mean() * 100
        add(f"Se observaron {fmt_int(patient_count)} PatientID únicos para {fmt_int(len(study_to_patient))} Studies con header legible; {fmt_pct(multi_patient_pct)} de los Patients tienen más de un Study. La relación observada es uno-a-uno, por lo que `PatientID` podría funcionar como pseudónimo específico del examen y no permite demostrar longitudinalidad real. Al leerse una sola Series por Study, esta pasada tampoco puede detectar contradicciones de PatientID entre Series del mismo Study.")
    else:
        add("No pudo reconstruirse el nivel Patient a partir de la metadata DICOM leída.")
    add("")
    add("### 6. Unidad de análisis y unidad de predicción")
    add("")
    add("- **Unidad física de almacenamiento:** un archivo `.dcm` por Slice / DICOM Instance.")
    add("- **Granularidad de `*_series.csv`:** una fila por Series.")
    add("- **Granularidad de `train.csv` y `test.csv`:** una fila por Study.")
    add("- **Unidad de reporte y label:** Study; el reporte y los targets comparten fila con `StudyInstanceUID`.")
    add("- **Unidad aparente de predicción:** Study; `sample_submission.csv` contiene una fila por `StudyInstanceUID` de test y una columna por target.")
    add("")
    add("El Study funciona como unidad principal de análisis porque enlaza tablas, Series, DICOM, Report y, cuando están disponibles, targets. Patient sólo se recupera desde headers DICOM; Series y Slice son niveles subordinados de adquisición.")
    add("")
    add("### 7. Targets y prevalencias")
    add("")
    add(f"Los 12 targets tienen dtype inferido `float64` por la presencia de missing, pero sus {fmt_int(target_valid_rows.sum())} valores observados son binarios (0/1). Hay {fmt_int(target_complete_rows.sum())} filas con los 12 targets completos y {fmt_int((target_valid_rows & ~target_complete_rows).sum())} con observación parcial.")
    add("")
    add(markdown_table(["Target", "N válido", "Positivos", "Negativos", "Sumatoria", "Prevalencia"], target_rows, {1, 2, 3, 4, 5}))
    add("")
    positive_stats = stats(n_positive)
    add("Para `n_positive_labels`, calculado sólo en Studies con al menos un target observado: " + ", ".join(f"{k}={fmt_num(v)}" for k, v in positive_stats.items()) + ".")
    add("")
    positive_distribution = n_positive.value_counts().sort_index()
    add(markdown_table(["Labels positivos por Study", "Studies"], [[fmt_num(k, 0), fmt_int(v)] for k, v in positive_distribution.items()], {0, 1}))
    add("")
    add("![Prevalencia de targets](figures/target_prevalence.png)")
    add("")
    add("![Labels positivos por Study](figures/positive_labels_per_study.png)")
    add("")
    add("### 8. Composición Study → Series")
    add("")
    add("La distribución se calculó exhaustivamente sobre directorios físicos. Frecuencias:")
    add("")
    series_frequency = series_per_study.value_counts().sort_index()
    add(markdown_table(["Series por Study", "Studies"], [[fmt_int(k), fmt_int(v)] for k, v in series_frequency.items()], {0, 1}))
    add("")
    low_series = series_per_study[series_per_study == series_per_study.min()]
    high_threshold = series_per_study.quantile(0.99)
    high_series = series_per_study[series_per_study >= high_threshold]
    add(f"El mínimo observado fue {fmt_int(series_per_study.min())} Series ({fmt_int(len(low_series))} Studies) y el máximo {fmt_int(series_per_study.max())}. El umbral P99 es {fmt_num(high_threshold)}; {fmt_int(len(high_series))} Studies se ubican en o por encima de él. Son observaciones descriptivas, no una clasificación automática de outliers.")
    add("")
    add("![Series por Study](figures/series_per_study.png)")
    add("")
    add("Las categorías tabulares de adquisición son:")
    add("")
    series_categories = []
    for col in ["Anatomical_Plane", "Fluid_Sensitive", "Fat_Suppression"]:
        for val, count in pd.concat([train_series[col], test_series[col]]).value_counts(dropna=False).items():
            series_categories.append([col, val, fmt_int(count), fmt_pct(count / (len(train_series) + len(test_series)) * 100)])
    add(markdown_table(["Variable", "Categoría", "Series", "%"], series_categories, {2, 3}))
    add("")
    add("![Plano anatómico](figures/anatomical_plane.png)")
    add("")
    add("### 9. Composición Series → Slice")
    add("")
    slices_frequency = slices_per_series.value_counts().sort_index()
    # Una tabla completa sigue siendo manejable; limita a 60 filas si aparecieran demasiadas cardinalidades.
    display_slices_frequency = slices_frequency if len(slices_frequency) <= 60 else pd.concat([slices_frequency.head(30), slices_frequency.tail(30)])
    add(markdown_table(["Slices por Series", "Series"], [[fmt_int(k), fmt_int(v)] for k, v in display_slices_frequency.items()], {0, 1}))
    add("")
    slice_p01 = slices_per_series.quantile(0.01)
    slice_p99 = slices_per_series.quantile(0.99)
    add(f"Se observaron {fmt_int((slices_per_series <= slice_p01).sum())} Series con conteo menor o igual a P1 ({fmt_num(slice_p01)}) y {fmt_int((slices_per_series >= slice_p99).sum())} con conteo mayor o igual a P99 ({fmt_num(slice_p99)}). La cantidad por sí sola no permite concluir que una Series esté incompleta.")
    add("")
    add("![Slices por Series](figures/slices_per_series.png)")
    add("")
    add("### 10. Reportes radiológicos")
    add("")
    add(f"`train.csv` contiene {fmt_int(report_count)} reportes no missing asociados por fila a Study, {fmt_int(train['Report'].nunique())} textos únicos y {fmt_int(train['Report'].duplicated(keep=False).sum())} filas pertenecientes a grupos de textos exactamente duplicados.")
    add("")
    section_rows = [[name, fmt_pct(value)] for name, value in section_presence.items()]
    add(markdown_table(["Sección textual detectada", "% de reportes"], section_rows, {1}))
    add("")
    add("La detección usa expresiones regulares simples y equivalentes frecuentes en inglés, español y neerlandés. No se estimaron longitudes de sección porque la estructura y el idioma son heterogéneos y una segmentación básica no resultó suficientemente robusta para presentarla como medición.")
    add("")
    add("![Longitud de reportes](figures/report_length_chars.png)")
    add("")
    add("### 11. Metadata DICOM")
    add("")
    add(f"Se intentó leer una instancia determinista por Study sobre {dicom_sample_scope}, con `pydicom.dcmread(..., stop_before_pixels=True)`: {fmt_int(len(dicom) + len(dicom_errors))} inspeccionadas, {fmt_int(len(dicom))} correctamente leídas y {fmt_int(len(dicom_errors))} con problemas. Esta pasada cubre todos los Studies, pero sólo una Series y un Slice por Study.")
    add("")
    add(markdown_table(["Tag", "No nulos", "Disponibilidad", "Cardinalidad", "Valores frecuentes (hasta 5)"], dicom_tag_rows, {1, 2, 3}))
    add("")
    if not dimension_counts.empty:
        add("Combinaciones de dimensiones más frecuentes en las instancias inspeccionadas:")
        add("")
        add(markdown_table(["Rows × Columns", "Instancias"], [[k, fmt_int(v)] for k, v in dimension_counts.items()], {1}))
        add("")
    if not laterality.empty:
        add("Laterality combinada (`ImageLaterality` con fallback a `Laterality`):")
        add("")
        add(markdown_table(["Valor", "Instancias"], [[k, fmt_int(v)] for k, v in laterality.items()], {1}))
        add("")
    add("La disponibilidad se refiere a los headers inspeccionados. Para valores que pueden variar por slice (por ejemplo, posición o `InstanceNumber`), no representa una enumeración exhaustiva de todas las instancias.")
    add("")
    add("### 12. Missingness y completitud")
    add("")
    add(markdown_table(["Partición", "Studies", "Con fila en series CSV", "Con directorio físico", "Con Report", "Con targets", "Con PatientID observado", "Presentes en tabla + series CSV + físico"], completeness_rows, set(range(1, 8))))
    add("")
    add("El missingness más marcado en las variables principales corresponde a los targets de `train.csv`; los IDs, Report y campos de las tablas de Series no presentan missing. Los porcentajes DICOM por tag figuran en la sección anterior.")
    add("")
    add("![Missingness de train](figures/train_missingness.png)")
    add("")
    add("### 13. Duplicados e integridad básica")
    add("")
    add(markdown_table(["Tabla", "Filas", "Filas exactamente duplicadas (adicionales)"], duplicate_rows, {1, 2}))
    add("")
    add(f"- Archivos vacíos en la muestra de tamaño ({fmt_int(len(size_sample_sizes))} DICOM más archivos raíz): {fmt_int(empty_files_inspected)}.")
    add(f"- Series físicas sin DICOM: {fmt_int((physical_series['n_slices'] == 0).sum())}.")
    add(f"- Headers DICOM inspeccionados con error: {fmt_int(len(dicom_errors))}.")
    add(f"- Discrepancias Study UID path/header: {fmt_int(study_uid_mismatch)}.")
    add(f"- Discrepancias Series UID path/header: {fmt_int(series_uid_mismatch)}.")
    add(f"- Discrepancias SOP UID filename/header: {fmt_int(sop_uid_mismatch)}.")
    add(f"- SOPInstanceUID duplicados entre headers inspeccionados: {fmt_int(dicom['SOPInstanceUID'].dropna().duplicated().sum() if not dicom.empty else 0)}.")
    add(f"- Paths duplicados entre headers inspeccionados: {fmt_int(dicom['path'].dropna().duplicated().sum() if not dicom.empty else 0)}.")
    add(f"- Paths inesperados fuera del patrón Study/Series/Slice: {fmt_int(sum(len(v['unexpected']) for v in scan_summaries.values()))}.")
    if dicom_errors:
        add("")
        add("Ejemplos de problemas de lectura DICOM (hasta 10):")
        add("")
        add(markdown_table(["Path", "Error"], [[e["path"], e["error"]] for e in dicom_errors[:10]]))
    add("")
    add("Los conteos de duplicados no implican por sí solos que las observaciones sean erróneas; identifican repeticiones que pueden revisarse posteriormente.")
    add("")
    add("### 14. Comparación descriptiva train/test")
    add("")
    add(markdown_table(["Métrica", "Train", "Test"], comparison_rows, {1, 2}))
    add("")
    if not plane_comparison.empty:
        plane_rows = [[idx, fmt_int(row.get("train", 0)), fmt_int(row.get("test", 0))] for idx, row in plane_comparison.iterrows()]
        add(markdown_table(["Anatomical_Plane", "Train", "Test"], plane_rows, {1, 2}))
        add("")
    if dicom_comparison_rows:
        add("Frecuencias DICOM observables en la instancia inspeccionada por Study (hasta 10 categorías por variable y partición):")
        add("")
        add(markdown_table(["Partición", "Variable", "Valor", "Studies inspeccionados", "% no missing de la variable"], dicom_comparison_rows, {3, 4}))
        add("")
    add("Las diferencias anteriores son exclusivamente descriptivas. Test no contiene labels ni reportes, por lo que no se calculan prevalencias ni longitudes de texto para esa partición.")
    add("")
    add("### 15. Observaciones adicionales")
    add("")
    add(f"- `sample_submission.csv` {'contiene exactamente una fila por cada Study ID de test' if submission_matches_test else 'no coincide exactamente con los Study IDs únicos de test'} y 12 columnas con valores placeholder de 0,5.")
    add("- `Fluid_Sensitive`, `Fat_Suppression` y `Anatomical_Plane` caracterizan Series en tablas separadas de los headers DICOM.")
    add("- Los reportes muestran heterogeneidad de idioma y formato; aquí sólo se midieron presencia, duplicación y longitud, sin interpretación clínica.")
    add("- Los targets faltantes no se trataron como negativos; toda prevalencia usa únicamente observaciones válidas.")
    add("")
    add("### 16. Limitaciones de esta caracterización")
    add("")
    add("- La metadata DICOM se extrajo de una instancia determinista por Study, sin PixelData. Los conteos físicos de Series y slices sí son exhaustivos.")
    add(f"- El tamaño total es una estimación basada en {fmt_int(len(size_sample_sizes))} DICOM estratificados por partición; no se ejecutó `stat` sobre cada archivo por su costo observado.")
    add("- PatientID no existe en tablas y se reconstruye desde esa inspección de headers; sus métricas deben leerse con esa procedencia.")
    add("- No se realizó validación clínica ni evaluación semántica de reportes o targets.")
    add("- La detección de secciones textuales es léxica y multilingüe básica, no un pipeline NLP.")
    add("- No se calculó el número de `SeriesDescription` distintas por Study: la extracción de headers usa una sola Series por Study; `ProtocolName` resultó ausente en todos los headers inspeccionados.")
    add("- No se cargaron píxeles ni se verificó la calidad visual de las imágenes.")
    add("")
    add("### 17. Glosario")
    add("")
    glossary = [
        ("Patient", "Persona identificada mediante `PatientID` en metadata DICOM; puede tener uno o más Studies."),
        ("Study / MRI Exam", "Examen completo de resonancia magnética, identificado por `StudyInstanceUID`; es la unidad central del dataset."),
        ("Series", "Conjunto de imágenes adquiridas bajo una configuración o secuencia común dentro de un Study."),
        ("Slice / DICOM Instance", "Imagen individual de una Series; múltiples slices representan posiciones dentro del volumen adquirido."),
        ("MRI / resonancia magnética", "Técnica de imagen médica basada en campos magnéticos y radiofrecuencia."),
        ("DICOM", "Estándar de archivo y metadata para imágenes médicas digitales."),
        ("Radiology report", "Texto producido durante la interpretación radiológica del examen."),
        ("Findings", "Sección del reporte que describe los hallazgos observados."),
        ("Impression / Conclusion", "Sección de síntesis o conclusión del reporte."),
        ("Sagittal", "Plano que divide anatómicamente el cuerpo en porciones izquierda y derecha."),
        ("Coronal", "Plano que divide anatómicamente el cuerpo en porciones anterior y posterior."),
        ("Axial", "Plano transversal que divide anatómicamente el cuerpo en porciones superior e inferior."),
        ("Fluid sensitive", "Característica de una secuencia en la que el líquido tiende a presentar señal destacada."),
        ("Fat suppression / fat-sat", "Técnica que reduce la señal de la grasa en una secuencia MRI."),
        ("T1 / T2 / proton density (PD)", "Tipos de ponderación MRI que enfatizan propiedades diferentes de los tejidos; no se infirieron aquí más allá de campos explícitos."),
        ("Slice thickness", "Espesor físico representado por un slice, usualmente expresado en milímetros."),
        ("Pixel spacing", "Separación física entre centros de píxeles contiguos dentro del plano de la imagen."),
        ("Field of view", "Extensión anatómica cubierta por una adquisición; no se calculó cuando no existía como campo directo."),
        ("Laterality", "Lado anatómico, típicamente izquierdo o derecho."),
        ("Magnetic field strength", "Intensidad del campo magnético del scanner, habitualmente expresada en teslas."),
        ("MRI protocol", "Conjunto planificado de adquisiciones utilizado para un examen."),
        ("MRI sequence", "Configuración de pulsos y parámetros que determina el contraste de una adquisición."),
        ("ACL / MCL", "Ligamento cruzado anterior / ligamento colateral medial; nombres de targets provistos por el dataset."),
        ("Meniscus", "Estructura fibrocartilaginosa de la rodilla; el dataset distingue medial y lateral."),
        ("OA", "Abreviatura de osteoartritis en los nombres de targets; `PF` refiere al compartimento patelofemoral."),
        ("Effusion", "Presencia de líquido articular aumentada, como denominación de un target."),
        ("Synovitis", "Inflamación de la membrana sinovial, como denominación de un target."),
        ("Baker's", "Referencia al quiste de Baker en el nombre de un target."),
        ("Contusion", "Contusión, como denominación de un target."),
        ("Fracture", "Fractura, como denominación de un target."),
    ]
    for term, definition in glossary:
        add(f"#### {term}")
        add("")
        add(definition)
        add("")
    add("### Reproducibilidad")
    add("")
    add("Desde la raíz del repositorio:")
    add("")
    add("```powershell")
    add("python scripts/dataset_characterization.py")
    add("```")
    add("")
    add(f"Dependencias usadas: Python {sys.version.split()[0]}, pandas {pd.__version__}, numpy {np.__version__}, matplotlib {matplotlib.__version__}, pydicom {pydicom.__version__}. No se usa aleatoriedad.")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reporte generado: {report_path}")
    print(f"Figuras generadas: {figures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
