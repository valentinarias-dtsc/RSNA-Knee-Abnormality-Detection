`prompt`: 

apoyate primero en los idiomas menos cubiertos para tratar de identificar expresiones linguisticas no reconocidas actualmente, avanzando hacia las lenguas actualmente más cubiertas. realizá el mismo procedimiento riguroso con los labels, de menos a más cubiertos, tratando de identificar terminología actualmente no considerada. tratá de mantener la política de no mention -> unknown y el espíritu de la implementación. cuando termines, quiero que hagas un análisis exhaustivo del supervision_long_v2.csv para tratar de identificar inconsistencias entre el evidence y rationale, de identificar un patrón recurrente, o inconsistencias solucionables, implementalo junto al resto de cambios.  los cambios que surjan de este análisis deben ser implementados en la misma v2, sin crear un nuevo v3. pensá si es actualmente requerido, para alcanzar a cubrir más pares report-label, cambiar de estrategia de implementación, ya sea haciendo un merge entre varias alternativas según idioma/target/etc. o alguna alternativa prudente. (en este paso sólo debés proponer cambios conceptuales de una v3 en vez de aplicarlos ahora mismo)

`respuesta`:

La v2 fue ampliada, auditada y regenerada manteniendo `no mention → unknown`. Sigue identificada como `report-label-policy-v2.0.0`; no se creó una v3.

## Resultado global

- Pares resueltos: 20.430 → **22.723**.
- Cobertura: 38,6% → **42,97%**.
- Incremento neto: **2.293 pares report-target**.
- `unknown`: 29.937.
- `uncertain`: 224.
- Las 31 pruebas pasan.
- La auditoría integral terminó con **0 inconsistencias**.

## Revisión por idioma

Comparación sobre los grupos originales, ordenados por cobertura previa:

| Grupo | Cobertura anterior | Nueva | Pares adicionales |
|---|---:|---:|---:|
| Griego | 16,5% | **29,2%** | +492 |
| Turco | 22,9% | **33,9%** | +723 |
| Latin other | 24,7% | **26,9%** | +98 |
| Cirílico/Búlgaro | 26,0% | **33,2%** | +189 |
| Sudeslavo | 26,6% | **38,3%** | +452 |
| Neerlandés | 31,3% | **35,3%** | +74 |
| Alemán | 33,0% | **36,6%** | +110 |
| Español | 35,3% | **39,9%** | +378 |
| Francés | 49,6% | **50,6%** | +10 |
| Inglés | 60,1% | **58,8%** | −233 |

La reducción inglesa es deliberada: se eliminaron resoluciones incorrectas como inferir `OA=0` porque el menisco de ese compartimento era normal, o inferir lesión del MCL por una rotura meniscal cercana.

Se incorporaron flexiones, abreviaturas y expresiones corpus-específicas griegas, turcas, búlgaras, sudeslavas, neerlandesas, alemanas, españolas, francesas e inglesas. También se mejoró la clasificación de reportes previamente agrupados como `latin_other`.

## Revisión por target

| Target | Cobertura anterior | Nueva | Delta |
|---|---:|---:|---:|
| Synovitis | 10,9% | **11,3%** | +15 |
| Contusion | 16,4% | **16,9%** | +21 |
| Fracture | 17,8% | **18,6%** | +35 |
| Medial OA | 22,1% | **25,1%** | +132 |
| Lateral OA | 22,6% | **25,0%** | +106 |
| PF OA | 33,4% | **36,5%** | +134 |
| Baker’s | 37,8% | **38,2%** | +18 |
| MCL | 55,1% | **60,5%** | +238 |
| Medial Meniscus | 55,6% | **71,7%** | +709 |
| Lateral Meniscus | 60,2% | **69,3%** | +400 |
| ACL | 62,6% | **65,8%** | +143 |
| Effusion | 69,0% | **76,8%** | +342 |

Synovitis, Contusion y Fracture siguen bajos principalmente por baja mención explícita. No se usaron proxies semánticamente débiles: derrame no implica sinovitis, edema medular inespecífico no implica contusión y normalidad ósea global no niega fractura.

## Inconsistencias encontradas y corregidas

- La evidencia decisiva podía quedar fuera del límite de tres cláusulas. Ahora se persiste primero la evidencia que determina el estado y después una cláusula conflictiva.
- Una misma cláusula con “degeneración, pero ligamento intacto” producía un conflicto artificial. La normalidad estructural y la patología explícita dentro de la misma cláusula ya no se consideran menciones contradictorias.
- Patologías de estructuras vecinas podían contaminar targets: una rotura meniscal próxima al MCL podía etiquetar MCL; un menisco normal dentro de un compartimento podía negar OA.
- Se separó el vocabulario patológico de meniscos, ligamentos y OA.
- Cada hallazgo se asocia ahora con la anatomía compatible más cercana dentro de la cláusula.
- Se mejoró la reconstrucción de líneas usando indentación y capitalización originales.
- Se preservan líneas en blanco como boundaries.
- Se reconocen ordinales como `I. stupnja` sin dividir la lesión del MCL.
- Se manejan estructuras tipo `deep MCL; high grade partial tear`.

El UID sudeslavo analizado ahora produce correctamente:

- ACL = 1
- MCL = 1
- Medial Meniscus = 1
- Lateral Meniscus = 0
- Los restantes targets = `unknown`

## Auditoría exhaustiva

Se verificaron las 52.884 filas y diez invariantes:

- Unicidad Study-target.
- Versión de política.
- JSON y cardinalidad de evidence.
- Evidence perteneciente a una cláusula diagnóstica.
- Coherencia status/label/score.
- Coherencia rationale/confidence.
- Provenance y override oficial.
- Evidencia decisiva visible.
- Evidencia conflictiva visible.
- Correspondencia entre rationale directo/colectivo y evidence.

Resultado: **0 errores y 0 warnings**. La ejecución falla automáticamente si aparece una inconsistencia de severidad `error`.

Artefactos principales:

- [supervision_long_v2.csv](C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/supervision_long_v2.csv)
- [coverage_by_language_target_v2.csv](C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/coverage_by_language_target_v2.csv)
- [consistency_audit_summary_v2.csv](C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/consistency_audit_summary_v2.csv)
- [consistency_audit_issues_v2.csv](C:/Github/RSNA-Knee-Abnormality-Detection/artifacts/03_report_label_generation/consistency_audit_issues_v2.csv)
- [reporte actualizado](C:/Github/RSNA-Knee-Abnormality-Detection/reports/stages/03_report_label_generation.md)

## Evaluación del gold

El gold de 58 estudios presenta algunas discrepancias semánticas: existen reportes que describen explícitamente esguince grado I, degeneración meniscal, degeneración mucoide o fractura por insuficiencia, pero cuyo target oficial vale 0. No eliminé esos términos para optimizar artificialmente el gold.

Mejoraron F1 en Medial OA, Effusion, Synovitis y Contusion. Descendieron moderadamente MCL, ambos meniscos y Fracture por las discrepancias anteriores. Esto refuerza la necesidad de revisar la definición exacta y granularidad del gold antes de interpretar toda discordancia como error del extractor.

## Propuesta conceptual para v3 — no implementada

No considero imprescindible cambiar de arquitectura todavía: la v2 ganó cobertura y eliminó errores de alcance manteniendo un único motor auditable.

Para superar sustancialmente el 43%, una v3 sí podría usar un ensemble a nivel de **mención**, no de label final:

1. Reglas universales de alta precisión.
2. Extractores morfosintácticos por idioma.
3. Reglas target-específicas.
4. Reconciliación por span con prioridad `target-specific > collective > generic`.
5. Desacuerdos como `uncertain` o revisión manual.
6. Ninguna rama podría convertir no mención en negativo.

Esa arquitectura sólo debería implementarse después de disponer de un gold multilingüe mayor y aclarar si degeneración grado I–II, esguince y fractura por insuficiencia pertenecen a la definición positiva de cada target.