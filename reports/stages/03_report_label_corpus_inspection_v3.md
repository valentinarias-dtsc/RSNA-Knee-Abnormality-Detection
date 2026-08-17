# Report-label corpus inspection for NLP modeling evidence

## 1. Scope

Esta inspección caracteriza de forma descriptiva los `4,407` Reports y los `52,884` pares Study × target procesados por `report-label-policy-v3.0.0`. Se reconstruyeron las unidades internas vigentes y se analizaron exclusivamente `status`, `derived_label`, evidence y provenance derivados del texto.

No se diseñó ningún modelo, no se compararon arquitecturas, no se seleccionaron pretrained models, no se definieron unidades de entrenamiento, teachers, thresholds ni subconjuntos de entrenamiento. No se modificaron policies ni labels. Los valores de `official_label` y `final_label` no se cargaron en la inspección analítica. Tampoco se utilizaron PixelData, DICOM/Series metadata, scanner ni anatomical plane.

## 2. Sources

- Dataset textual: `C:/Github/RSNA-Knee-Abnormality-Detection/data/train.csv`.
- Supervisión derivada v3: `C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/supervision_long_v3.csv`.
- Configuración: `C:/Github/RSNA-Knee-Abnormality-Detection/config/03_report_label_generation/policy_v3.json`.
- Código ejecutable: `src/report_labels/`, `src/report_labels/v3/` y `scripts/generate_report_labels.py`.
- Reportes revisados: stage 03 v3 y reporte de implementación v3.

Los hashes SHA-256 de inputs, fuentes revisadas y outputs se encuentran en `inspection_run_metadata.json`.

## 3. Reproducibility

Comando:

```powershell
python scripts/inspect_report_label_corpus.py
```

Parámetros semánticos: seed `20260817`, máximo `600` filas de auditoría, máximo `20,000` pares de similitud por target/status y top `100` n-grams. Los CSV son deterministas para inputs, código y parámetros fijos; el timestamp UTC se registra únicamente en metadata.

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

| unit | count | denominator |
| --- | --- | --- |
| Report | 4407 | Reports |
| clause | 79781 | strict TextViews produced by segment_report |
| strict TextView | 79781 | TextViews |
| linked TextView | 2578 | TextViews |
| Mention | 52604 | Mentions before deduplication |
| Proposition | 41811 | deduplicated Propositions |
| selected evidence | 38706 | selected provenance entries, including retained conflicts |
| selected winning evidence | 38184 | selected provenance entries matching the final status |
| Study-target pair | 52884 | Study × target pairs |
| binary resolved Study-target pair | 24294 | Study × target pairs |

Distribución de cláusulas strict por Report:

| count | mean | std | median | min | max | p05 | p25 | p75 | p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4407 | 18.1032 | 11.5048 | 15.0000 | 1.0000 | 70.0000 | 6.0000 | 10.0000 | 23.0000 | 44.0000 |

## 6. Target/status distribution

| target | pairs | positive | negative | uncertain | unknown | binary_resolved | binary_resolved_rate | positive_over_binary_resolved | negative_over_binary_resolved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ACL | 4407 | 963 | 2077 | 50 | 1317 | 3040 | 0.6898 | 0.3168 | 0.6832 |
| MCL | 4407 | 447 | 2620 | 18 | 1322 | 3067 | 0.6959 | 0.1457 | 0.8543 |
| Medial Meniscus | 4407 | 2008 | 1283 | 74 | 1042 | 3291 | 0.7468 | 0.6101 | 0.3899 |
| Lateral Meniscus | 4407 | 952 | 2191 | 64 | 1200 | 3143 | 0.7132 | 0.3029 | 0.6971 |
| Medial OA | 4407 | 662 | 589 | 1 | 3155 | 1251 | 0.2839 | 0.5292 | 0.4708 |
| Lateral OA | 4407 | 438 | 680 | 0 | 3289 | 1118 | 0.2537 | 0.3918 | 0.6082 |
| PF OA | 4407 | 1015 | 864 | 10 | 2518 | 1879 | 0.4264 | 0.5402 | 0.4598 |
| Effusion | 4407 | 2550 | 977 | 6 | 874 | 3527 | 0.8003 | 0.7230 | 0.2770 |
| Synovitis | 4407 | 486 | 21 | 8 | 3892 | 507 | 0.1150 | 0.9586 | 0.0414 |
| Baker's | 4407 | 989 | 841 | 9 | 2568 | 1830 | 0.4152 | 0.5404 | 0.4596 |
| Contusion | 4407 | 359 | 448 | 14 | 3586 | 807 | 0.1831 | 0.4449 | 0.5551 |
| Fracture | 4407 | 249 | 585 | 40 | 3533 | 834 | 0.1892 | 0.2986 | 0.7014 |

Los porcentajes utilizan los `4,407` pares disponibles para cada target.

## 7. Language distribution

| language_group | reports | study_target_pairs | positive | negative | uncertain | unknown | resolved_rate | strict_views | linked_views | mentions | propositions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cyrillic_script | 220 | 2640 | 438 | 522 | 0 | 1680 | 0.3636 | 4249 | 12 | 1905 | 1529 |
| dutch | 153 | 1836 | 378 | 414 | 8 | 1036 | 0.4314 | 1850 | 2 | 1481 | 1189 |
| english | 1724 | 20688 | 4797 | 6694 | 177 | 9020 | 0.5554 | 42588 | 1447 | 27883 | 22795 |
| french | 80 | 960 | 260 | 254 | 2 | 444 | 0.5354 | 1701 | 114 | 1186 | 923 |
| german | 259 | 3108 | 437 | 722 | 10 | 1939 | 0.3729 | 3895 | 13 | 1973 | 1837 |
| greek_script | 321 | 3852 | 828 | 401 | 0 | 2623 | 0.3191 | 3145 | 96 | 2395 | 1964 |
| latin_other | 22 | 264 | 43 | 83 | 0 | 138 | 0.4773 | 305 | 15 | 214 | 166 |
| south_slavic | 403 | 4836 | 1183 | 1073 | 69 | 2511 | 0.4665 | 6540 | 188 | 3708 | 3015 |
| spanish | 678 | 8136 | 1261 | 2021 | 17 | 4837 | 0.4034 | 8925 | 691 | 6889 | 4411 |
| turkish | 547 | 6564 | 1493 | 992 | 11 | 4068 | 0.3786 | 6583 | 0 | 4970 | 3982 |

`language_group` y las hypotheses son heurísticas de routing. Las hypotheses no son exclusivas y sus conteos no deben sumarse como Reports independientes.

## 8. Text lengths

Token simple significa `normalize_text` seguido por la expresión Unicode `\b\w+\b`; no se utilizó tokenizer de un modelo.

| unit | measure | count | mean | std | median | min | p05 | p25 | p75 | p95 | p99 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Report | characters | 4407 | 1097.9056 | 693.9489 | 977.0000 | 52.0000 | 205.0000 | 587.5000 | 1459.5000 | 2452.7000 | 3101.9400 | 4743.0000 |
| Report | simple_tokens | 4407 | 148.9235 | 97.1855 | 129.0000 | 7.0000 | 28.0000 | 76.0000 | 202.0000 | 336.0000 | 430.0000 | 685.0000 |
| strict TextView | characters | 79781 | 59.1660 | 45.9757 | 48.0000 | 1.0000 | 8.0000 | 29.0000 | 78.0000 | 147.0000 | 221.0000 | 536.0000 |
| strict TextView | simple_tokens | 79781 | 8.2263 | 6.4923 | 6.0000 | 0.0000 | 1.0000 | 4.0000 | 11.0000 | 21.0000 | 31.0000 | 71.0000 |
| linked TextView | characters | 2578 | 71.7289 | 54.3990 | 63.0000 | 12.0000 | 14.0000 | 29.5000 | 97.0000 | 176.0000 | 249.2300 | 381.0000 |
| linked TextView | simple_tokens | 2578 | 9.7413 | 7.8048 | 8.0000 | 2.0000 | 2.0000 | 3.0000 | 13.0000 | 25.0000 | 36.2300 | 57.0000 |
| selected evidence | characters | 38706 | 71.5734 | 51.0165 | 61.0000 | 8.0000 | 21.0000 | 35.0000 | 87.0000 | 172.0000 | 262.0000 | 536.0000 |
| selected evidence | simple_tokens | 38706 | 9.8257 | 6.9039 | 8.0000 | 1.0000 | 3.0000 | 5.0000 | 12.0000 | 24.0000 | 35.0000 | 68.0000 |

## 9. Detector provenance

| unit | detector | count | unique_studies | unique_study_target_pairs |
| --- | --- | --- | --- | --- |
| mention | v2_exact | 23695 | 4190 | 18753 |
| mention | v3_target | 17230 | 3928 | 13366 |
| mention | v3_morphology | 6481 | 2840 | 4948 |
| mention | v2_collective | 5198 | 1844 | 3874 |
| proposition_participation | v2_exact | 23005 | 4190 | 18753 |
| proposition_participation | v3_target | 16995 | 3928 | 13366 |
| proposition_participation | v3_morphology | 6177 | 2840 | 4948 |
| proposition_participation | v2_collective | 3955 | 1844 | 3874 |
| selected_pair_participation | v2_exact | 17712 | 4175 | 17712 |
| selected_pair_participation | v3_target | 13314 | 3927 | 13314 |
| selected_pair_participation | v3_morphology | 4931 | 2834 | 4931 |
| selected_pair_participation | v2_collective | 3826 | 1819 | 3826 |
| selected_winning_pair_participation | v2_exact | 17704 | 4175 | 17704 |
| selected_winning_pair_participation | v3_target | 13285 | 3925 | 13285 |
| selected_winning_pair_participation | v3_morphology | 4924 | 2833 | 4924 |
| selected_winning_pair_participation | v2_collective | 3768 | 1783 | 3768 |

Una Proposition puede estar soportada por más de un detector. `detector_combination_summary.csv` conserva las combinaciones y separa 1, 2 y 3+ detectors.

## 10. Confidence distribution

| unit | value | count |
| --- | --- | --- |
| Study-target pair | 0.0 | 28296 |
| Study-target pair | 0.4 | 14 |
| Study-target pair | 0.45 | 1 |
| Study-target pair | 0.5 | 279 |
| Study-target pair | 0.6200000000000001 | 5 |
| Study-target pair | 0.69 | 64 |
| Study-target pair | 0.7 | 4 |
| Study-target pair | 0.72 | 435 |
| Study-target pair | 0.75 | 3319 |
| Study-target pair | 0.8 | 128 |
| Study-target pair | 0.82 | 1006 |
| Study-target pair | 0.83 | 88 |
| Study-target pair | 0.85 | 8763 |
| Study-target pair | 0.87 | 1036 |
| Study-target pair | 0.88 | 286 |
| Study-target pair | 0.9 | 9160 |
| selected Proposition | 0.45 | 2 |
| selected Proposition | 0.5 | 506 |
| selected Proposition | 0.75 | 3645 |
| selected Proposition | 0.8 | 224 |
| selected Proposition | 0.82 | 6313 |
| selected Proposition | 0.83 | 2109 |
| selected Proposition | 0.85 | 8796 |
| selected Proposition | 0.87 | 2203 |
| selected Proposition | 0.88 | 3361 |
| selected Proposition | 0.9 | 11547 |

La confidence es un ranking determinista de fuerza de evidencia definido por la policy; no es una probabilidad calibrada. `confidence_summary.csv` contiene además las distribuciones por target, status, detector, rule, phenotype, idioma, conflicto y modo colectivo/target-specific.

## 11. Phenotypes

| phenotype | propositions | unique_studies | selected_pair_participations | selected_winning_pair_participations | targets | statuses |
| --- | --- | --- | --- | --- | --- | --- |
| abnormality_absent | 13031 | 3515 | 12396 | 12213 | ["ACL", "Baker's", "Contusion", "Effusion", "Fracture", "Lateral Meniscus", "Lateral OA", "MCL", "Medial Meniscus", "Medial OA", "PF OA", "Synovitis"] | ["negative"] |
| abnormality | 6302 | 2896 | 4018 | 4011 | ["ACL", "Baker's", "Contusion", "Effusion", "Fracture", "Lateral Meniscus", "Lateral OA", "MCL", "Medial Meniscus", "Medial OA", "PF OA", "Synovitis"] | ["positive", "uncertain"] |
| tear | 4757 | 2080 | 2951 | 2939 | ["ACL", "Baker's", "Contusion", "Effusion", "Lateral Meniscus", "Lateral OA", "MCL", "Medial Meniscus", "Medial OA", "PF OA", "Synovitis"] | ["positive", "uncertain"] |
| normal_structure | 4496 | 2274 | 4444 | 4357 | ["ACL", "Lateral Meniscus", "MCL", "Medial Meniscus"] | ["negative"] |
| chondral_abnormality | 2894 | 1375 | 2064 | 2064 | ["Baker's", "Contusion", "Effusion", "Fracture", "Lateral Meniscus", "Lateral OA", "MCL", "Medial Meniscus", "Medial OA", "PF OA", "Synovitis"] | ["positive", "uncertain"] |
| joint_effusion | 1998 | 1553 | 1549 | 1549 | ["Effusion"] | ["positive", "uncertain"] |
| degeneration | 1715 | 1030 | 1344 | 1343 | ["ACL", "Baker's", "Contusion", "Effusion", "Lateral Meniscus", "Lateral OA", "MCL", "Medial Meniscus", "Medial OA", "PF OA", "Synovitis"] | ["positive", "uncertain"] |
| baker_cyst | 939 | 737 | 734 | 734 | ["Baker's"] | ["positive", "uncertain"] |
| chondral_abnormality_absent | 935 | 485 | 930 | 897 | ["Lateral OA", "Medial OA", "PF OA"] | ["negative"] |
| normal_cartilage | 868 | 729 | 858 | 802 | ["Lateral OA", "Medial OA", "PF OA"] | ["negative"] |
| joint_effusion_absent | 676 | 631 | 629 | 617 | ["Effusion"] | ["negative"] |
| fracture | 651 | 294 | 318 | 318 | ["ACL", "Contusion", "Effusion", "Fracture", "Lateral OA", "MCL", "Medial Meniscus", "Medial OA", "PF OA", "Synovitis"] | ["positive", "uncertain"] |
| fracture_absent | 647 | 589 | 589 | 577 | ["Fracture"] | ["negative"] |
| bone_contusion | 486 | 327 | 325 | 323 | ["Contusion"] | ["positive", "uncertain"] |
| bone_contusion_absent | 456 | 454 | 454 | 447 | ["Contusion"] | ["negative"] |
| sprain | 368 | 253 | 267 | 266 | ["ACL", "Baker's", "Contusion", "Lateral Meniscus", "MCL", "Medial Meniscus", "Synovitis"] | ["positive", "uncertain"] |
| baker_cyst_absent | 344 | 342 | 342 | 339 | ["Baker's"] | ["negative"] |
| extrusion | 93 | 80 | 65 | 65 | ["Effusion", "Lateral Meniscus", "MCL", "Medial Meniscus"] | ["positive", "uncertain"] |
| synovitis | 80 | 64 | 64 | 64 | ["Synovitis"] | ["positive", "uncertain"] |
| avulsion | 74 | 33 | 21 | 20 | ["ACL", "Fracture", "Lateral Meniscus", "MCL", "Medial Meniscus"] | ["positive", "uncertain"] |
| synovitis_absent | 1 | 1 | 1 | 1 | ["Synovitis"] | ["negative"] |

`target_phenotype_status.csv` expresa el porcentaje usando como denominador todas las Propositions del mismo target/status. La inspección no asigna un rol futuro a phenotype.

## 12. Rules

| rule | mentions | propositions | unique_studies | selected_pair_participations | selected_winning_pair_participations | cumulative_selected_participation_share |
| --- | --- | --- | --- | --- | --- | --- |
| <no_explicit_rule> | 23695 | 14711 | 3966 | 11770 | 11764 | 0.3385 |
| target_local_association | 8255 | 8090 | 3004 | 5378 | 5356 | 0.4926 |
| target_local_normality | 4510 | 4496 | 2274 | 4444 | 4357 | 0.6180 |
| compartment_scope | 3595 | 3541 | 1613 | 2785 | 2783 | 0.6981 |
| effusion_en_plural | 1867 | 1853 | 1403 | 1398 | 1398 | 0.7383 |
| both_menisci_negative_only | 952 | 948 | 474 | 932 | 923 | 0.7649 |
| baker_variants | 1125 | 1078 | 889 | 887 | 887 | 0.7904 |
| collateral_ligaments | 928 | 925 | 921 | 911 | 887 | 0.8159 |
| cruciate_ligaments | 895 | 891 | 889 | 874 | 858 | 0.8406 |
| compartment_normality | 870 | 868 | 729 | 858 | 802 | 0.8637 |
| cruciate_and_collateral_ligaments | 706 | 706 | 353 | 705 | 703 | 0.8839 |
| fracture_en | 1007 | 986 | 705 | 701 | 697 | 0.9040 |
| contusion_en | 854 | 843 | 698 | 697 | 695 | 0.9240 |
| both_menisci | 714 | 702 | 399 | 676 | 673 | 0.9433 |
| tibiofemoral_compartments | 996 | 621 | 225 | 563 | 557 | 0.9594 |
| effusion_tr_root | 471 | 471 | 457 | 457 | 457 | 0.9725 |
| baker_sl | 175 | 175 | 170 | 170 | 170 | 0.9774 |
| effusion_el_root | 206 | 202 | 164 | 163 | 163 | 0.9821 |
| effusion_de_root | 150 | 149 | 148 | 148 | 148 | 0.9864 |
| baker_el | 120 | 119 | 105 | 104 | 104 | 0.9894 |
| fracture_de | 51 | 51 | 50 | 50 | 50 | 0.9908 |
| fracture_el | 60 | 60 | 45 | 45 | 45 | 0.9921 |
| contusion_el | 48 | 48 | 42 | 42 | 42 | 0.9933 |
| fracture_fr | 75 | 75 | 35 | 35 | 35 | 0.9943 |
| contusion_tr | 36 | 36 | 30 | 29 | 29 | 0.9951 |
| synovitis_el | 40 | 40 | 26 | 26 | 26 | 0.9959 |
| synovitis_tr | 22 | 22 | 22 | 22 | 22 | 0.9965 |
| fracture_cyr | 45 | 45 | 21 | 21 | 21 | 0.9971 |
| fracture_tr | 28 | 28 | 20 | 20 | 20 | 0.9977 |
| contusion_cyr | 30 | 30 | 19 | 19 | 19 | 0.9982 |

La columna acumulada usa participaciones de reglas; un mismo par puede participar en más de una rule.

## 13. Duplicates and template families

| level | total_instances | unique_texts | duplicated_instances_excess | duplicate_rate_excess | instances_in_duplicate_groups | duplicate_groups | mean_duplicate_group_size | median_duplicate_group_size | max_duplicate_group_size | duplicate_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Report | 4407 | 4259 | 148 | 0.0336 | 201 | 53 | 3.7925 | 2.0000 | 37 | excess instances = total instances - unique normalized texts |
| strict TextView | 79781 | 33756 | 46025 | 0.5769 | 50994 | 4969 | 10.2624 | 3.0000 | 657 | excess instances = total instances - unique normalized texts |
| linked TextView | 2578 | 1036 | 1542 | 0.5981 | 1641 | 99 | 16.5758 | 3.0000 | 491 | excess instances = total instances - unique normalized texts |
| selected evidence | 38706 | 13324 | 25382 | 0.6558 | 29416 | 4034 | 7.2920 | 2.0000 | 980 | excess instances = total instances - unique normalized texts |

La duplicate rate se define como `(instances - unique normalized texts) / instances`. Los grupos completos y sus IDs se encuentran en `duplicate_groups.csv`.

| template_mode | families | duplicated_families | reports_covered | max_family_size | homogeneous_families | heterogeneous_families | reports_in_duplicated_families |
| --- | --- | --- | --- | --- | --- | --- | --- |
| exact | 4259 | 53 | 4407 | 37 | 4259 | 0 | 201 |
| numeric_normalized | 4259 | 53 | 4407 | 37 | 4259 | 0 | 201 |

Las familias exact y numeric-normalized usan la misma normalización vigente en `exact_template_consistency`. Se incluyen familias singleton y duplicadas, distinguidas por `is_duplicated_family`.

## 14. Lexical/textual diversity

| target | status | evidence_instances | unique_normalized_texts | duplicate_rate_excess | total_simple_tokens | unique_tokens | type_token_ratio | unigram_top_10_coverage | bigram_top_10_coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ACL | negative | 3084 | 469 | 0.8479 | 27796 | 756 | 0.0272 | 0.3806 | 0.2626 |
| ACL | positive | 1415 | 1044 | 0.2622 | 16270 | 1736 | 0.1067 | 0.2535 | 0.1453 |
| ACL | uncertain | 62 | 62 | 0.0000 | 1001 | 300 | 0.2997 | 0.2328 | 0.1523 |
| Baker's | negative | 1133 | 118 | 0.8959 | 6087 | 202 | 0.0332 | 0.6006 | 0.5077 |
| Baker's | positive | 1754 | 897 | 0.4886 | 15778 | 1507 | 0.0955 | 0.2762 | 0.1717 |
| Baker's | uncertain | 16 | 12 | 0.2500 | 140 | 49 | 0.3500 | 0.5429 | 0.5000 |
| Contusion | negative | 894 | 36 | 0.9597 | 5922 | 117 | 0.0198 | 0.8544 | 0.7770 |
| Contusion | positive | 648 | 473 | 0.2701 | 9812 | 1251 | 0.1275 | 0.2586 | 0.1340 |
| Contusion | uncertain | 25 | 17 | 0.3200 | 355 | 116 | 0.3268 | 0.3577 | 0.2212 |
| Effusion | negative | 1594 | 183 | 0.8852 | 8845 | 323 | 0.0365 | 0.5053 | 0.3908 |
| Effusion | positive | 4252 | 1530 | 0.6402 | 31080 | 1953 | 0.0628 | 0.2754 | 0.1709 |
| Effusion | uncertain | 8 | 6 | 0.2500 | 204 | 99 | 0.4853 | 0.2353 | 0.1327 |
| Fracture | negative | 1153 | 117 | 0.8985 | 7323 | 475 | 0.0649 | 0.7138 | 0.6496 |
| Fracture | positive | 393 | 388 | 0.0127 | 6928 | 1409 | 0.2034 | 0.1895 | 0.0739 |
| Fracture | uncertain | 48 | 40 | 0.1667 | 653 | 252 | 0.3859 | 0.2864 | 0.2231 |
| Lateral Meniscus | negative | 3583 | 480 | 0.8660 | 24454 | 752 | 0.0308 | 0.4341 | 0.3003 |
| Lateral Meniscus | positive | 1401 | 1189 | 0.1513 | 18918 | 1892 | 0.1000 | 0.2864 | 0.1489 |
| Lateral Meniscus | uncertain | 84 | 66 | 0.2143 | 1171 | 271 | 0.2314 | 0.4330 | 0.2732 |
| Lateral OA | negative | 1144 | 120 | 0.8951 | 10211 | 304 | 0.0298 | 0.5439 | 0.4263 |
| Lateral OA | positive | 594 | 496 | 0.1650 | 9131 | 1047 | 0.1147 | 0.2244 | 0.0889 |
| MCL | negative | 3728 | 577 | 0.8452 | 34315 | 743 | 0.0217 | 0.3516 | 0.2370 |
| MCL | positive | 645 | 493 | 0.2357 | 8196 | 1031 | 0.1258 | 0.3314 | 0.1677 |
| MCL | uncertain | 23 | 20 | 0.1304 | 406 | 140 | 0.3448 | 0.3498 | 0.2298 |
| Medial Meniscus | negative | 1776 | 374 | 0.7894 | 14293 | 668 | 0.0467 | 0.4366 | 0.3233 |
| Medial Meniscus | positive | 3123 | 2476 | 0.2072 | 45820 | 2873 | 0.0627 | 0.2755 | 0.1491 |
| Medial Meniscus | uncertain | 91 | 82 | 0.0989 | 1433 | 432 | 0.3015 | 0.2889 | 0.1803 |
| Medial OA | negative | 945 | 96 | 0.8984 | 8955 | 298 | 0.0333 | 0.5415 | 0.4257 |
| Medial OA | positive | 915 | 775 | 0.1530 | 15122 | 1595 | 0.1055 | 0.2113 | 0.0874 |
| Medial OA | uncertain | 1 | 1 | 0.0000 | 29 | 23 | 0.7931 | 0.5517 | 0.4286 |
| PF OA | negative | 1414 | 229 | 0.8380 | 11785 | 467 | 0.0396 | 0.4717 | 0.3343 |
| PF OA | positive | 1412 | 1267 | 0.1027 | 22921 | 2084 | 0.0909 | 0.2215 | 0.0949 |
| PF OA | uncertain | 12 | 12 | 0.0000 | 275 | 109 | 0.3964 | 0.3200 | 0.1787 |
| Synovitis | negative | 22 | 19 | 0.1364 | 188 | 69 | 0.3670 | 0.3936 | 0.2169 |
| Synovitis | positive | 783 | 448 | 0.4278 | 7618 | 990 | 0.1300 | 0.3196 | 0.1789 |
| Synovitis | uncertain | 9 | 7 | 0.2222 | 124 | 56 | 0.4516 | 0.4435 | 0.2870 |

Type-token ratio depende de la longitud observada. `ngram_summary.csv` conserva unigramas/bigramas y `text_similarity_summary.csv` documenta exact match, normalized exact match y Jaccard sobre sets de tokens. Estas métricas describen similitud superficial, no similitud semántica.

## 15. Strict vs linked evidence

| record_type | view_kind | support_scope | views | mentions | propositions | selected_pair_participations |
| --- | --- | --- | --- | --- | --- | --- |
| overall | strict | __all__ | 79781.0000 | 51937.0000 | 41175 | 24571.0000 |
| overall | linked | __all__ | 2578.0000 | 667.0000 | 636 | 362.0000 |
| proposition_support_scope | __all__ | linked_only |  |  | 636 | 362.0000 |
| proposition_support_scope | __all__ | strict_only |  |  | 41175 | 24571.0000 |

`linked_view_dependency_cases.csv` contiene los pares con selected winning evidence que incluye linked views y distingue linked-only de soporte combinado.

## 16. Collective evidence

| mentions | propositions | selected_propositions | selected_study_target_pairs_participations |
| --- | --- | --- | --- |
| 5198 | 3927 | 3871 | 3803 |

`collective_evidence_summary.csv` desagrega target, status, rule, language, phenotype y confidence sin decidir un uso posterior.

## 17. Conflicts

Se observaron `522` pares con rationale conflictivo (0.9871% de los pares).

| target | winning_status | language_group | pairs |
| --- | --- | --- | --- |
| ACL | positive | cyrillic_script | 4 |
| ACL | positive | dutch | 2 |
| ACL | positive | english | 57 |
| ACL | positive | greek_script | 1 |
| ACL | positive | south_slavic | 5 |
| ACL | positive | spanish | 1 |
| ACL | positive | turkish | 1 |
| ACL | uncertain | french | 1 |
| Baker's | positive | dutch | 1 |
| Baker's | positive | english | 7 |
| Baker's | positive | french | 1 |
| Baker's | positive | spanish | 18 |
| Contusion | positive | english | 10 |
| Contusion | positive | german | 4 |
| Contusion | positive | greek_script | 1 |
| Effusion | positive | cyrillic_script | 2 |
| Effusion | positive | dutch | 6 |
| Effusion | positive | english | 14 |
| Effusion | positive | french | 2 |
| Effusion | positive | german | 1 |
| Effusion | positive | greek_script | 2 |
| Effusion | positive | latin_other | 1 |
| Effusion | positive | south_slavic | 14 |
| Effusion | positive | turkish | 3 |
| Effusion | uncertain | south_slavic | 1 |
| Fracture | positive | cyrillic_script | 1 |
| Fracture | positive | dutch | 1 |
| Fracture | positive | english | 16 |
| Fracture | positive | french | 2 |
| Fracture | positive | greek_script | 1 |

`conflict_cases.csv` conserva winning/conflicting statuses y provenance completa; la inspección no los resuelve ni reinterpreta.

## 18. Uncertain cases

El artefacto v3 contiene `294` pares uncertain.

| target | evidence_instances | unique_evidence_texts |
| --- | --- | --- |
| ACL | 62 | 62 |
| Baker's | 16 | 12 |
| Contusion | 25 | 17 |
| Effusion | 8 | 6 |
| Fracture | 48 | 40 |
| Lateral Meniscus | 84 | 66 |
| MCL | 23 | 20 |
| Medial Meniscus | 91 | 82 |
| Medial OA | 1 | 1 |
| PF OA | 12 | 12 |
| Synovitis | 9 | 7 |

Los patrones se atribuyen únicamente a `UNCERTAINTY_TERMS` y `_V3_UNCERTAINTY` vigentes.

## 19. Unknown population

| target | pairs | unknown | unknown_rate |
| --- | --- | --- | --- |
| ACL | 4407 | 1317 | 0.2988 |
| Baker's | 4407 | 2568 | 0.5827 |
| Contusion | 4407 | 3586 | 0.8137 |
| Effusion | 4407 | 874 | 0.1983 |
| Fracture | 4407 | 3533 | 0.8017 |
| Lateral Meniscus | 4407 | 1200 | 0.2723 |
| Lateral OA | 4407 | 3289 | 0.7463 |
| MCL | 4407 | 1322 | 0.3000 |
| Medial Meniscus | 4407 | 1042 | 0.2364 |
| Medial OA | 4407 | 3155 | 0.7159 |
| PF OA | 4407 | 2518 | 0.5714 |
| Synovitis | 4407 | 3892 | 0.8831 |

Las tablas de unknown describen longitud, cláusulas, idioma, views y presencia de otros targets resueltos en el mismo Report. No se afirma que unknown carezca de hallazgos ni que sea irrelevante.

`clause_usage_summary.csv` separa cláusulas diagnósticas seleccionadas, cláusulas con mentions no seleccionadas y cláusulas sin mentions, sin convertirlas en labels.

## 20. Study-level structure and target co-occurrence

| measure | mean | std | median | min | p05 | p25 | p75 | p95 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| binary_resolved_targets | 5.5126 | 2.7214 | 6.0000 | 0 | 1.0000 | 4.0000 | 7.0000 | 11.0000 | 12 |
| positive_targets | 2.5228 | 1.9598 | 2.0000 | 0 | 0.0000 | 1.0000 | 4.0000 | 6.0000 | 10 |
| negative_targets | 2.9898 | 2.5578 | 3.0000 | 0 | 0.0000 | 1.0000 | 4.0000 | 8.0000 | 11 |
| uncertain_targets | 0.0667 | 0.2938 | 0.0000 | 0 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 4 |
| unknown_targets | 6.4207 | 2.7323 | 6.0000 | 0 | 1.0000 | 5.0000 | 8.0000 | 11.0000 | 12 |
| propositions | 9.4874 | 5.8848 | 8.0000 | 0 | 1.0000 | 6.0000 | 12.0000 | 22.0000 | 36 |
| unique_evidence_fragments | 5.9052 | 3.2905 | 5.0000 | 0 | 1.0000 | 4.0000 | 8.0000 | 12.0000 | 17 |

Principales celdas off-diagonal de co-ocurrencia positive-positive, presentadas sólo como conteos:

| row_target | column_target | study_count | denominator_studies |
| --- | --- | --- | --- |
| Effusion | Medial Meniscus | 1359 | 4407 |
| Medial Meniscus | Effusion | 1359 | 4407 |
| Baker's | Effusion | 739 | 4407 |
| Effusion | Baker's | 739 | 4407 |
| Effusion | PF OA | 728 | 4407 |
| PF OA | Effusion | 728 | 4407 |
| Effusion | ACL | 717 | 4407 |
| ACL | Effusion | 717 | 4407 |
| Lateral Meniscus | Effusion | 693 | 4407 |
| Effusion | Lateral Meniscus | 693 | 4407 |
| Lateral Meniscus | Medial Meniscus | 608 | 4407 |
| Medial Meniscus | Lateral Meniscus | 608 | 4407 |
| Baker's | Medial Meniscus | 578 | 4407 |
| Medial Meniscus | Baker's | 578 | 4407 |
| Medial Meniscus | ACL | 571 | 4407 |

`target_cooccurrence.csv` contiene matrices positive-positive, binary-resolved y shared normalized selected evidence. No se atribuye causalidad.

## 21. Effective example structure

| target | status | raw_evidence_count | unique_normalized_evidence_count | unique_report_count | unique_exact_template_family_count | unique_numeric_normalized_template_family_count | detector_rule_combination_count | language_group_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ACL | negative | 3084 | 469 | 2077 | 2054 | 2054 | 6 | 10 |
| ACL | positive | 1415 | 1044 | 963 | 962 | 962 | 3 | 10 |
| ACL | uncertain | 62 | 62 | 50 | 50 | 50 | 2 | 6 |
| Baker's | negative | 1133 | 118 | 841 | 835 | 835 | 4 | 7 |
| Baker's | positive | 1754 | 897 | 989 | 987 | 987 | 5 | 10 |
| Baker's | uncertain | 16 | 12 | 9 | 9 | 9 | 3 | 3 |
| Contusion | negative | 894 | 36 | 448 | 443 | 443 | 2 | 3 |
| Contusion | positive | 648 | 473 | 359 | 359 | 359 | 6 | 9 |
| Contusion | uncertain | 25 | 17 | 14 | 14 | 14 | 4 | 3 |
| Effusion | negative | 1594 | 183 | 977 | 956 | 956 | 5 | 9 |
| Effusion | positive | 4252 | 1530 | 2550 | 2504 | 2504 | 5 | 10 |
| Effusion | uncertain | 8 | 6 | 6 | 6 | 6 | 2 | 3 |
| Fracture | negative | 1153 | 117 | 585 | 579 | 579 | 7 | 9 |
| Fracture | positive | 393 | 388 | 249 | 249 | 249 | 15 | 10 |
| Fracture | uncertain | 48 | 40 | 40 | 40 | 40 | 7 | 5 |
| Lateral Meniscus | negative | 3583 | 480 | 2191 | 2135 | 2135 | 9 | 10 |
| Lateral Meniscus | positive | 1401 | 1189 | 952 | 952 | 952 | 6 | 10 |
| Lateral Meniscus | uncertain | 84 | 66 | 64 | 64 | 64 | 2 | 6 |
| Lateral OA | negative | 1144 | 120 | 680 | 670 | 670 | 4 | 9 |
| Lateral OA | positive | 594 | 496 | 438 | 438 | 438 | 9 | 10 |
| MCL | negative | 3728 | 577 | 2620 | 2558 | 2558 | 6 | 10 |
| MCL | positive | 645 | 493 | 447 | 441 | 441 | 3 | 9 |
| MCL | uncertain | 23 | 20 | 18 | 18 | 18 | 2 | 4 |
| Medial Meniscus | negative | 1776 | 374 | 1283 | 1220 | 1220 | 6 | 10 |
| Medial Meniscus | positive | 3123 | 2476 | 2008 | 1993 | 1993 | 4 | 10 |
| Medial Meniscus | uncertain | 91 | 82 | 74 | 74 | 74 | 4 | 7 |
| Medial OA | negative | 945 | 96 | 589 | 579 | 579 | 4 | 9 |
| Medial OA | positive | 915 | 775 | 662 | 662 | 662 | 6 | 10 |
| Medial OA | uncertain | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| PF OA | negative | 1414 | 229 | 864 | 848 | 848 | 4 | 10 |
| PF OA | positive | 1412 | 1267 | 1015 | 1015 | 1015 | 7 | 10 |
| PF OA | uncertain | 12 | 12 | 10 | 10 | 10 | 2 | 2 |
| Synovitis | negative | 22 | 19 | 21 | 21 | 21 | 2 | 4 |
| Synovitis | positive | 783 | 448 | 486 | 485 | 485 | 5 | 10 |
| Synovitis | uncertain | 9 | 7 | 8 | 8 | 8 | 1 | 1 |

No se estima un effective sample size estadístico. Las columnas son conteos estructurales observables.

## 22. Audit sample

`audit_sample.csv` contiene `600` filas seleccionadas determinísticamente con seed `20260817`. Las strata combinan target, status, detector, rule, phenotype, idioma, conflicto, soporte strict/linked y collective; unknown se muestrea por target/idioma. Los campos `judgment` y `review_note` están vacíos y no se realizó anotación clínica.

## 23. Limitations of this inspection

- Todas las unidades Mention/Proposition dependen de las reglas vigentes de v3.
- `language_group` y language hypotheses son heurísticas de routing.
- Las familias de templates se limitan a exact y numeric-normalized según el mecanismo existente.
- Exact match, n-grams y Jaccard describen forma textual y no equivalencia semántica.
- La classification de negation se reconstruye desde términos/spans persistidos y conserva una categoría residual cuando el marcador no puede reconstruirse.
- Las participaciones de detectors, rules y phenotypes se superponen.
- La inspección no evalúa corrección clínica ni utiliza official labels para comparar fuentes.

## 24. Artifact index

| artifact | path | description |
| --- | --- | --- |
| corpus_unit_counts | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/corpus_unit_counts.csv | corpus unit counts |
| text_length_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/text_length_summary.csv | text length summary |
| target_status_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/target_status_summary.csv | target status summary |
| language_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/language_summary.csv | language summary |
| language_hypothesis_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/language_hypothesis_summary.csv | language hypothesis summary |
| language_target_status_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/language_target_status_summary.csv | language target status summary |
| detector_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/detector_summary.csv | detector summary |
| detector_combination_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/detector_combination_summary.csv | detector combination summary |
| confidence_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/confidence_summary.csv | confidence summary |
| phenotype_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/phenotype_summary.csv | phenotype summary |
| target_phenotype_status | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/target_phenotype_status.csv | target phenotype status |
| rule_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/rule_summary.csv | rule summary |
| duplicate_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/duplicate_summary.csv | duplicate summary |
| duplicate_group_size_distribution | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/duplicate_group_size_distribution.csv | duplicate group size distribution |
| duplicate_groups | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/duplicate_groups.csv | duplicate groups |
| template_family_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/template_family_summary.csv | template family summary |
| lexical_diversity_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/lexical_diversity_summary.csv | lexical diversity summary |
| ngram_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/ngram_summary.csv | ngram summary |
| text_similarity_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/text_similarity_summary.csv | text similarity summary |
| evidence_target_status_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/evidence_target_status_summary.csv | evidence target status summary |
| evidence_inventory | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/evidence_inventory.csv | evidence inventory |
| conflict_cases | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/conflict_cases.csv | conflict cases |
| collective_evidence_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/collective_evidence_summary.csv | collective evidence summary |
| view_kind_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/view_kind_summary.csv | view kind summary |
| linked_view_dependency_cases | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/linked_view_dependency_cases.csv | linked view dependency cases |
| context_structure_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/context_structure_summary.csv | context structure summary |
| negation_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/negation_summary.csv | negation summary |
| uncertain_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/uncertain_summary.csv | uncertain summary |
| unknown_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/unknown_summary.csv | unknown summary |
| clause_usage_summary | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/clause_usage_summary.csv | clause usage summary |
| study_level_distribution | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/study_level_distribution.csv | study level distribution |
| target_cooccurrence | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/target_cooccurrence.csv | target cooccurrence |
| effective_example_structure | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/effective_example_structure.csv | effective example structure |
| audit_sample | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/audit_sample.csv | audit sample |
| metadata | C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/corpus_inspection_v3/inspection_run_metadata.json | metadata |
