"""Stage 04 orchestration over reusable dataset, training and evaluation modules."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from src.report_labels.constants import TARGETS

from .aggregation import aggregate_clause_predictions, study_level_weak_agreement
from .constants import STAGE_VERSION, UPSTREAM_POLICY_VERSION
from .dataset import (
    annotate_test_novelty,
    build_stage04_datasets,
    deduplicate_training_examples,
    unique_evaluation_slice,
)
from .evaluation import evaluate_frame, evaluate_test_slices
from .metadata import (
    base_run_metadata,
    checkpoint_manifest,
    file_manifest,
    sha256_file,
    write_json,
)
from .modeling import count_truncated_examples, predict_frame
from .reporting import (
    plot_confusion,
    plot_dataset_dedup,
    plot_target_test_comparison,
    plot_training_curves,
)
from .splitting import (
    apply_split_manifest,
    assign_grouped_splits,
    audit_split_assignments,
    split_summary,
)
from .training import train_model


def load_config(config_path: Path) -> dict[str, object]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("version") != STAGE_VERSION:
        raise ValueError("Stage 04 config version differs from executable")
    if config.get("upstream_policy_version") != UPSTREAM_POLICY_VERSION:
        raise ValueError("upstream policy version differs from executable")
    if set(config["targets"]) != set(TARGETS):
        raise ValueError("config target descriptions differ from report-label targets")
    labels = config["labels"]["label2id"]
    if set(labels) != {"positive", "negative", "uncertain", "no_evidence"}:
        raise ValueError("config must define exactly four local labels")
    return config


def _resolve(root: Path, value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _prepare_metadata(
    root: Path,
    config_path: Path,
    config: Mapping[str, object],
    paths: Mapping[str, Path],
    frames: Mapping[str, object],
    output_paths: list[Path],
) -> dict[str, object]:
    metadata = base_run_metadata(
        root=root,
        config_path=config_path,
        input_paths={
            "train_csv": paths["train_csv"],
            "supervision_v3": paths["supervision_v3"],
            "evidence_inventory": paths["evidence_inventory"],
            "upstream_policy_config": paths["upstream_policy_config"],
            "upstream_inspection_metadata": paths["upstream_inspection_metadata"],
        },
        seed=int(config["seed"]),
        stage_version=STAGE_VERSION,
        upstream_policy_version=UPSTREAM_POLICY_VERSION,
    )
    candidates = frames["candidate_examples"]
    split_candidates = frames["split_candidates"]
    train_dedup = frames["train_examples_dedup"]
    metadata.update({
        "run_status": "prepared_without_model_training",
        "model_identifier": config["model"]["name_or_path"],
        "model_revision": config["model"].get("revision"),
        "tokenizer_identifier": config["model"].get("tokenizer_name_or_path"),
        "counts": {
            "source_studies": int(config["expected_source_studies"]),
            "official_studies_excluded": len(frames["excluded_official_studies"]),
            "eligible_studies": frames["reports"]["StudyInstanceUID"].nunique(),
            "strict_clauses": len(frames["strict_clauses"]),
            "alignment_failures": len(frames["alignment_failures"]),
            "raw_candidate_examples": len(candidates),
            "trusted_teacher_examples": int((~candidates["label"].eq("no_evidence")).sum()),
            "contrastive_no_evidence_examples": int(candidates["label"].eq("no_evidence").sum()),
            "train_source_examples": int(split_candidates["split"].eq("train").sum()),
            "train_examples_after_dedup": len(train_dedup),
            "validation_examples": int(split_candidates["split"].eq("validation").sum()),
            "test_examples": int(split_candidates["split"].eq("test").sum()),
        },
        "counts_by_split_target_label": split_candidates.groupby(
            ["split", "target", "label"], sort=True,
        ).size().rename("count").reset_index().to_dict("records"),
        "split_manifest_sha256": sha256_file(paths["artifact_dir"] / "split_assignments.csv"),
        "outputs": file_manifest(output_paths, root),
        "determinism": {
            "semantic_preparation_outputs": "deterministic for identical inputs/config/software/seed",
            "pytorch_deterministic_algorithms": "enabled with warn_only during model training",
        },
    })
    return metadata


def prepare_stage04(root: Path, config_path: Path) -> dict[str, object]:
    """Build candidates, grouped splits, leakage audits and train-only dedup artifacts."""
    config = load_config(config_path)
    paths = {name: _resolve(root, value) for name, value in config["paths"].items()}
    artifact_dir = paths["artifact_dir"]
    figure_dir = paths["figure_dir"]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    frames = build_stage04_datasets(
        train_path=paths["train_csv"],
        supervision_path=paths["supervision_v3"],
        evidence_inventory_path=paths["evidence_inventory"],
        target_descriptions=config["targets"],
        seed=int(config["seed"]),
    )
    expected_excluded = int(config["expected_official_studies_excluded"])
    if len(frames["excluded_official_studies"]) != expected_excluded:
        raise ValueError(
            f"expected {expected_excluded} official Studies, found {len(frames['excluded_official_studies'])}"
        )
    if len(frames["reports"]) + len(frames["excluded_official_studies"]) != int(config["expected_source_studies"]):
        raise ValueError("eligible plus excluded Study counts do not reconcile")
    assignments = assign_grouped_splits(
        frames["reports"], frames["templates"], frames["candidate_examples"],
        config["split"]["ratios"], int(config["seed"]),
    )
    repeated = assign_grouped_splits(
        frames["reports"], frames["templates"], frames["candidate_examples"],
        config["split"]["ratios"], int(config["seed"]),
    )
    audit = audit_split_assignments(
        assignments,
        frames["candidate_examples"],
        repeated_assignments=repeated,
        minimum_groups_for_full_support=int(config["split"]["minimum_groups_for_full_support_audit"]),
    )
    split_candidates = apply_split_manifest(frames["candidate_examples"], assignments)
    train_source = split_candidates[split_candidates["split"].eq("train")].copy()
    train_dedup, collisions, dedup_summary = deduplicate_training_examples(train_source)
    validation = split_candidates[split_candidates["split"].eq("validation")].copy()
    test = annotate_test_novelty(
        split_candidates[split_candidates["split"].eq("test")].copy(), train_source,
    )
    test_unique = unique_evaluation_slice(test)
    test_novel = test[test["novel_exact_target_clause"]].copy()
    frames.update({
        "config": config,
        "paths": paths,
        "split_assignments": assignments,
        "split_leakage_audit": audit,
        "split_candidates": split_candidates,
        "train_source_examples": train_source,
        "train_examples_dedup": train_dedup,
        "validation_examples": validation,
        "test_examples": test,
        "test_unique": test_unique,
        "test_novel": test_novel,
        "label_collision_cases": collisions,
        "dedup_summary": dedup_summary,
    })
    output_paths = [
        _write_csv(frames["candidate_examples"], artifact_dir / "candidate_examples.csv"),
        _write_csv(frames["alignment_failures"], artifact_dir / "alignment_failures.csv"),
        _write_csv(frames["no_evidence_generation_summary"], artifact_dir / "no_evidence_generation_summary.csv"),
        _write_csv(collisions, artifact_dir / "label_collision_cases.csv"),
        _write_csv(assignments, artifact_dir / "split_assignments.csv"),
        _write_csv(split_summary(assignments, frames["candidate_examples"]), artifact_dir / "split_summary.csv"),
        _write_csv(audit, artifact_dir / "split_leakage_audit.csv"),
        _write_csv(train_dedup, artifact_dir / "train_examples_dedup.csv"),
        _write_csv(validation, artifact_dir / "validation_examples.csv"),
        _write_csv(test, artifact_dir / "test_examples.csv"),
        _write_csv(dedup_summary, artifact_dir / "dedup_summary.csv"),
        _write_csv(pd.DataFrame([
            {"slice": "TEST-ALL", "examples": len(test)},
            {"slice": "TEST-UNIQUE", "examples": len(test_unique)},
            {"slice": "TEST-NOVEL", "examples": len(test_novel)},
        ]), artifact_dir / "test_slice_summary.csv"),
    ]
    audit_json = artifact_dir / "split_leakage_audit.json"
    write_json(audit_json, audit.to_dict("records"))
    excluded_json = artifact_dir / "excluded_official_studies.json"
    write_json(excluded_json, {
        "count": len(frames["excluded_official_studies"]),
        "StudyInstanceUIDs": frames["excluded_official_studies"],
        "source_indicator_only": "final_source == official; official_label/final_label were not loaded",
    })
    output_paths.extend([audit_json, excluded_json])
    dedup_figure = figure_dir / "dataset_size_before_after_dedup.png"
    plot_dataset_dedup(dedup_summary, dedup_figure)
    output_paths.append(dedup_figure)
    metadata = _prepare_metadata(root, config_path, config, paths, frames, output_paths)
    metadata_path = artifact_dir / "run_metadata.json"
    write_json(metadata_path, metadata)
    output_paths.append(metadata_path)
    frames["output_paths"] = output_paths
    frames["run_metadata"] = metadata
    return frames


def _all_clause_inference_frame(frames: Mapping[str, object], config: Mapping[str, object]) -> pd.DataFrame:
    clauses = frames["strict_clauses"]
    assignments = frames["split_assignments"]
    base = clauses[
        clauses["diagnostic"].astype(bool) & clauses["alignment_verified"].astype(bool)
    ].merge(
        assignments[["StudyInstanceUID", "split", "language_group"]],
        on="StudyInstanceUID",
        validate="many_to_one",
        suffixes=("", "_manifest"),
    )
    base = base[base["split"].isin(["validation", "test"])].copy()
    target_frame = pd.DataFrame({
        "target": list(config["targets"]),
        "target_description": list(config["targets"].values()),
    })
    output = base.merge(target_frame, how="cross")
    output["example_id"] = [
        hashlib.sha256(f"inference|{uid}|{index}|{target}".encode("utf-8")).hexdigest()
        for uid, index, target in zip(output["StudyInstanceUID"], output["source_index"], output["target"])
    ]
    output["model_version"] = config["version"]
    return output


def _complete_study_grid(
    aggregated: pd.DataFrame,
    assignments: pd.DataFrame,
    split: str,
) -> pd.DataFrame:
    studies = assignments.loc[assignments["split"].eq(split), ["StudyInstanceUID"]]
    grid = studies.merge(pd.DataFrame({"target": list(TARGETS)}), how="cross")
    output = grid.merge(aggregated, on=["StudyInstanceUID", "target"], how="left", validate="one_to_one")
    output["predicted_status"] = output["predicted_status"].fillna("unknown")
    count_columns = [column for column in output if column.endswith("_count")]
    output[count_columns] = output[count_columns].fillna(0).astype(int)
    return output


def run_full_stage04(root: Path, config_path: Path) -> dict[str, object]:
    """Prepare, train, evaluate local weak labels, infer clauses and aggregate Studies."""
    frames = prepare_stage04(root, config_path)
    config = frames["config"]
    paths = frames["paths"]
    artifact_dir = paths["artifact_dir"]
    figure_dir = paths["figure_dir"]
    checkpoint_dir = artifact_dir / "checkpoint"
    trained = train_model(
        frames["train_examples_dedup"], frames["validation_examples"], config, checkpoint_dir,
    )
    output_paths: list[Path] = list(frames["output_paths"])
    output_paths.extend([
        _write_csv(trained["history"], artifact_dir / "training_history.csv"),
        _write_csv(trained["sampled_distribution"], artifact_dir / "effective_sampled_distribution.csv"),
    ])
    checkpoint_details = checkpoint_manifest(checkpoint_dir, root)
    checkpoint_path = artifact_dir / "checkpoint_manifest.json"
    write_json(checkpoint_path, checkpoint_details)
    output_paths.append(checkpoint_path)
    max_length = int(config["tokenization"]["max_length"])
    label2id = config["labels"]["label2id"]
    eval_batch_size = int(config["training"]["eval_batch_size"])
    validation_predictions = predict_frame(
        trained["model"], trained["tokenizer"], frames["validation_examples"], label2id,
        max_length, eval_batch_size, trained["device"],
    )
    test_predictions = predict_frame(
        trained["model"], trained["tokenizer"], frames["test_examples"], label2id,
        max_length, eval_batch_size, trained["device"],
    )
    output_paths.append(_write_csv(test_predictions, artifact_dir / "predictions_local_test.csv"))
    validation_metrics = evaluate_frame(
        validation_predictions, list(label2id), "VALIDATION",
    )
    test_metrics = evaluate_test_slices(test_predictions, list(label2id))
    table_map = {
        "metrics_overall.csv": pd.concat([validation_metrics["overall"], test_metrics["overall"]], ignore_index=True),
        "metrics_by_target.csv": pd.concat([validation_metrics["by_target"], test_metrics["by_target"]], ignore_index=True),
        "metrics_by_label.csv": pd.concat([validation_metrics["by_label"], test_metrics["by_label"]], ignore_index=True),
        "metrics_by_language.csv": pd.concat([validation_metrics["by_language"], test_metrics["by_language"]], ignore_index=True),
        "metrics_by_detector.csv": pd.concat([validation_metrics["by_detector"], test_metrics["by_detector"]], ignore_index=True),
        "metrics_by_phenotype.csv": pd.concat([validation_metrics["by_phenotype"], test_metrics["by_phenotype"]], ignore_index=True),
        "test_slice_summary.csv": test_metrics["summary"],
    }
    for filename, frame in table_map.items():
        output_paths.append(_write_csv(frame, artifact_dir / filename))
    validation_confusion = validation_metrics["confusion"].drop(columns="evaluation")
    test_all_confusion = test_metrics["confusion"].query("evaluation == 'TEST-ALL'").drop(columns="evaluation")
    test_novel_confusion = test_metrics["confusion"].query("evaluation == 'TEST-NOVEL'").drop(columns="evaluation")
    output_paths.extend([
        _write_csv(validation_confusion, artifact_dir / "confusion_matrix_validation.csv"),
        _write_csv(test_all_confusion, artifact_dir / "confusion_matrix_test_all.csv"),
        _write_csv(test_novel_confusion, artifact_dir / "confusion_matrix_test_novel.csv"),
    ])
    inference_frame = _all_clause_inference_frame(frames, config)
    inference_predictions = predict_frame(
        trained["model"], trained["tokenizer"], inference_frame, label2id,
        max_length, eval_batch_size, trained["device"],
    )
    output_paths.append(_write_csv(
        inference_predictions, artifact_dir / "predictions_all_strict_clauses_validation_test.csv",
    ))
    test_clause_predictions = inference_predictions[inference_predictions["split"].eq("test")]
    aggregated = _complete_study_grid(
        aggregate_clause_predictions(test_clause_predictions), frames["split_assignments"], "test",
    )
    output_paths.append(_write_csv(aggregated, artifact_dir / "predictions_study_test.csv"))
    derived = pd.read_csv(
        paths["supervision_v3"],
        usecols=["StudyInstanceUID", "target", "status"],
        dtype={"StudyInstanceUID": str, "target": str, "status": str},
    )
    test_uids = set(frames["split_assignments"].loc[
        frames["split_assignments"]["split"].eq("test"), "StudyInstanceUID",
    ])
    derived = derived[derived["StudyInstanceUID"].isin(test_uids)]
    study_rows, transitions, study_summary = study_level_weak_agreement(aggregated, derived)
    output_paths.extend([
        _write_csv(study_rows, artifact_dir / "study_level_weak_agreement.csv"),
        _write_csv(transitions, artifact_dir / "study_status_transitions.csv"),
        _write_csv(study_summary, artifact_dir / "study_level_weak_agreement_summary.csv"),
    ])
    labels = list(label2id)
    output_paths.extend(plot_training_curves(trained["history"], figure_dir))
    for confusion, title, filename in (
        (validation_confusion, "Validation weak-label confusion", "confusion_matrix_validation.png"),
        (test_all_confusion, "TEST-ALL weak-label confusion", "confusion_matrix_test_all.png"),
        (test_novel_confusion, "TEST-NOVEL weak-label confusion", "confusion_matrix_test_novel.png"),
    ):
        path = figure_dir / filename
        plot_confusion(confusion, labels, title, path)
        output_paths.append(path)
    target_figure = figure_dir / "per_target_macro_f1_test_all_vs_novel.png"
    plot_target_test_comparison(table_map["metrics_by_target.csv"], target_figure)
    output_paths.append(target_figure)
    truncation_count, maximum_tokens = count_truncated_examples(
        trained["tokenizer"],
        pd.concat([
            frames["train_examples_dedup"], frames["validation_examples"], frames["test_examples"],
        ], ignore_index=True),
        max_length,
    )
    metadata = frames["run_metadata"]
    metadata.update({
        "run_status": "full_training_and_evaluation_complete",
        "hardware": trained["hardware"],
        "resolved_model_revision": trained["resolved_revision"],
        "best_epoch": trained["best_epoch"],
        "best_validation_primary_metric": trained["best_validation_primary_metric"],
        "tokenization": {
            "max_length": max_length,
            "truncated_examples": truncation_count,
            "maximum_untruncated_tokens": maximum_tokens,
        },
        "checkpoint": checkpoint_details,
        "outputs": file_manifest(output_paths, root),
    })
    write_json(artifact_dir / "run_metadata.json", metadata)
    frames.update({
        "training": trained,
        "validation_predictions": validation_predictions,
        "test_predictions": test_predictions,
        "inference_predictions": inference_predictions,
        "study_predictions": aggregated,
        "output_paths": output_paths,
    })
    return frames


def run_smoke_stage04(root: Path, config_path: Path) -> dict[str, object]:
    """Exercise model I/O on tiny split subsets without producing official metrics."""
    frames = prepare_stage04(root, config_path)
    config = copy.deepcopy(frames["config"])
    config["training"].update({
        "max_epochs": 1,
        "train_batch_size": 2,
        "eval_batch_size": 2,
        "early_stopping_patience": 1,
        "mixed_precision": False,
    })
    config["model"]["local_files_only"] = True

    def subset(frame: pd.DataFrame, limit: int) -> pd.DataFrame:
        ordered = frame.sort_values(["target", "label", "example_id"])
        heads = ordered.groupby(["target", "label"], group_keys=False).head(1)
        remainder = ordered[~ordered["example_id"].isin(heads["example_id"])]
        return pd.concat([heads, remainder], ignore_index=True).head(limit).copy()

    train = subset(frames["train_examples_dedup"], 8)
    validation = subset(frames["validation_examples"], 4)
    smoke_dir = frames["paths"]["artifact_dir"] / "smoke"
    trained = train_model(train, validation, config, smoke_dir / "checkpoint")
    predictions = predict_frame(
        trained["model"], trained["tokenizer"], validation.head(8),
        config["labels"]["label2id"], int(config["tokenization"]["max_length"]),
        2, trained["device"],
    )
    result = {
        "status": "smoke_test_complete_not_official_stage04_metrics",
        "train_examples": len(train),
        "validation_examples": len(validation),
        "predictions": len(predictions),
        "forward_pass": True,
        "backward_pass": True,
        "checkpoint_save_load": True,
        "inference": True,
        "metrics_computed_for_smoke_validation_only": True,
        "hardware": trained["hardware"],
        "resolved_model_revision": trained["resolved_revision"],
        "epoch_duration_seconds": float(trained["history"]["epoch_duration_seconds"].sum()),
    }
    write_json(smoke_dir / "smoke_result.json", result)
    return {**frames, "smoke_result": result}
