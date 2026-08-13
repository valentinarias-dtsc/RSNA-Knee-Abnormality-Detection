`prompt`:

planificá los cambios completos que requerirá la versión 3 para seguir aumentando el coverage sin cambiar el supuesto de no mención, tené en cuenta que los 58 gold labels son los únicos que van a estar presentes durante toda la competición. armá una nueva estructura conceptual con el algoritmo v3, explicando a detalle cómo funcionaría, qué lo diferencia de la implementación v2 y por qué se espera que mejoraría. para identificar patrones, comprobar eficacia de nuevas reglas o implementaciones target-específicas, basate de forma exclusiva en los Report actuales y en su corpus. poné especial atención en los targets e idiomas actualmente menos cubiertos. aún no apliques ningún cambio ni versión de la v3, simplemente hacé un reporte detallado de la versión conceptual que, según evidencias concretas encontradas en tu análisis, podrían mejorar sustancialmente el coverage del generador.

`respuesta (planificación)`:

# Propuesta conceptual para el generador v3

La recomendación central es reemplazar el extractor basado principalmente en coincidencias léxicas dentro de cláusulas por un sistema híbrido que combine detectores exactos, morfología por idioma, estructura del reporte y reglas específicas por target. La combinación debe ocurrir en el nivel de la evidencia, no mediante votación de labels.

Se mantiene estrictamente:

> Ausencia de evidencia textual específica → `unknown`.

No se implementó ni modificó ningún archivo durante este análisis.

## 1. Evidencia utilizada

El análisis se basó exclusivamente en:

- Los 4.407 `Report` actuales de `data/train.csv`.
- Los 52.884 pares estudio–target de `supervision_long_v2.csv`.
- La matriz de cobertura idioma–target de v2.
- Los errores y evidencias persistidos por v2.
- Inspección de cláusulas, patrones morfológicos, repeticiones y límites estructurales dentro del corpus.

No se usaron fuentes externas, traducciones web ni los 58 gold labels para descubrir términos o ajustar reglas.

Fuentes tabulares principales: :codex-file-citation{path="C:\Github\RSNA-Knee-Abnormality-Detection\artifacts\03_report_label_generation\supervision_long_v2.csv" purpose="source"} :codex-file-citation{path="C:\Github\RSNA-Knee-Abnormality-Detection\artifacts\03_report_label_generation\coverage_by_language_target_v2.csv" purpose="source"}

## 2. Estado de partida de v2

V2 produce:

| Estado | Pares |
|---|---:|
| Positive | 9.754 |
| Negative | 12.969 |
| Uncertain | 224 |
| Unknown | 29.937 |
| Total | 52.884 |

Esto implica dos definiciones diferentes de cobertura:

- Cobertura con label binario —positive o negative—: **42,97%**.
- Cobertura con alguna evidencia —incluyendo uncertain—: **43,39%**.

### Cobertura por idioma

| Grupo | Estudios | Cobertura binaria v2 | Candidatos v3 detectados en el análisis |
|---|---:|---:|---:|
| Greek script | 321 | 29,2% | 108 |
| Cyrillic script | 220 | 33,2% | 32 |
| Turkish | 547 | 33,9% | 230 |
| Dutch | 153 | 35,3% | 87 |
| German | 259 | 36,3% | 63 |
| South Slavic | 403 | 38,5% | 185 |
| Spanish | 678 | 39,9% | 26 |
| Latin other | 22 | 45,8% | 1 |
| French | 80 | 50,6% | 3 |
| English | 1.724 | 53,2% | 128 |

Los seis grupos menos cubiertos concentran **705 de los 863 candidatos encontrados, 81,7%**. Esto justifica priorizar detectores idioma–target antes de continuar ampliando reglas inglesas generales.

### Cobertura por target y evidencia candidata

Los “candidatos” son pares actualmente `unknown` que contienen patrones explícitos o asociaciones estructurales plausibles. Son un techo de revisión, no labels automáticamente válidos.

| Target | Cobertura binaria v2 | Candidatos |
|---|---:|---:|
| Synovitis | 11,3% | 12 |
| Contusion | 16,9% | 63 |
| Fracture | 18,6% | 15 |
| Lateral OA | 25,0% | 78 |
| Medial OA | 25,1% | 164 |
| PF OA | 36,5% | 200 |
| Baker’s | 38,2% | 78 |
| MCL | 60,5% | 27 |
| ACL | 65,8% | 21 |
| Lateral Meniscus | 69,3% | 26 |
| Medial Meniscus | 71,7% | 37 |
| Effusion | 76,8% | 142 |

Si los 863 candidatos fueran finalmente aceptables y binarios —hipótesis deliberadamente optimista—, la cobertura global tendría un techo aproximado de **44,60%**, +1,63 puntos porcentuales. El aumento no sería uniforme: el potencial observado es mayor en PF OA, Medial OA y Effusion.

## 3. Patrones concretos que v2 no captura

### 3.1 Variación morfológica

V2 usa principalmente expresiones completas. El corpus contiene flexiones, derivados y compuestos inequívocos no cubiertos:

- Griego:
  - `οστικου μωλωπα`
  - `παχυνσεις του αρθρικου υμενα`
- Cirílico:
  - `контузионен костно мозъчен едем`
- Turco:
  - `kontuzyonu`
  - `impaksiyon kiriklari`
  - `efuzyon`
- Eslavo meridional:
  - `kontuzijskih promjena`
  - `subhondralnom frakturom`
  - `baker cista`
- Neerlandés:
  - `bakerse cyste`
- Alemán:
  - `frakturlinie`
  - `synovialen proliferationen`
  - `ergussbildung`
- Francés:
  - `trait fracturaire`
- Inglés:
  - `osseous contusions`
  - `effusions`

Sólo esta familia produjo 90 candidatos para Synovitis/Contusion/Fracture y 220 para Effusion/Baker.

### 3.2 OA expresada mediante cartílago y compartimentos

Se encontraron 442 pares OA `unknown` en los que una referencia anatómica y una alteración condral aparecen en la misma cláusula, pero con formas o relaciones no contempladas por v2.

Ejemplos:

- Cirílico: `хрущял на пателата ... хондромалация`.
- Griego: `επιγονατιδομηριαια ... διαβρωσεις του χονδρου ... χονδροπαθειας`.
- Turco: `patellar kikirdakta ... fokal incelme ... grade ii kondromalazi`.
- Eslavo meridional: `stanjenje ... medijalnog i lateralnog ft kompartmenta`.
- Neerlandés: `denudatie van het kraakbeen mediaal femorotibiaal`.
- Alemán: `chondropathien ... lateralen femorotibialen gelenk`.
- Inglés: `medial and lateral femorotibial chondrosis`.

El problema no es sólo vocabulario: aparecen coordinaciones como “medial y lateral”, patologías antes de la anatomía y modificadores que abarcan varios compartimentos.

### 3.3 Asociaciones dentro de cláusulas complejas

Hay 111 pares de ACL, MCL o meniscos donde tanto la anatomía como la patología ya pertenecen a los léxicos v2, pero el resultado sigue siendo `unknown`.

Ejemplos claros:

- `signos de un esguince grado ii ... ligamento colateral medial`.
- `μερικη ρηξη ... προσθιου χιαστου συνδεσμου`.
- `medyal meniskus ... kompleks yirtik`.
- `complete rupture acl, pcl and mid fibers of the mcl`.

La causa habitual es una combinación de:

- Distancias máximas demasiado rígidas.
- Anatomías coordinadas.
- Patología compartida por una lista.
- Patología previa a la anatomía.
- Competencia entre varias estructuras dentro de la misma cláusula.

Pero la coocurrencia por sí sola no es suficiente. Por ejemplo, en una cláusula sobre una rotura meniscal puede aparecer el MCL sólo como referencia espacial. Un algoritmo de ventana ampliada etiquetaría erróneamente el MCL.

### 3.4 Información dividida por boundaries

En 1.100 pares estructurales `unknown`, la anatomía y algún término patológico aparecen en la misma cláusula o en cláusulas adyacentes:

- 156 en la misma cláusula.
- 967 en cláusulas adyacentes.
- 23 cumplen ambas condiciones.

La cifra de adyacencia no debe interpretarse como cobertura recuperable. Muchos casos son coincidencias no relacionadas, como un MCL normal seguido por tendinosis patelar. Demuestra que los boundaries rígidos pierden contexto, pero también que simplemente unir cláusulas produciría falsos positivos.

### 3.5 Repetición estructural del corpus

El corpus contiene:

- 4.259 reportes normalizados únicos sobre 4.407.
- 201 estudios pertenecientes a 53 grupos de reportes exactamente duplicados.
- 30.214 cláusulas diagnósticas únicas.
- 3.252 cláusulas diagnósticas repetidas al menos dos veces.
- 1.006 cláusulas repetidas cinco veces o más.

Esto habilita aprendizaje estructural corpus-only: reconocer plantillas, encabezados, listas y formas equivalentes sin convertir la similitud textual en un label automático.

## 4. Límites que v3 no debe cruzar

### Contusion no es sinónimo de edema óseo

Se encontraron **832** pares `Contusion=unknown` con alguna forma genérica de edema óseo o medular:

| Idioma | Pares |
|---|---:|
| South Slavic | 171 |
| English | 162 |
| Turkish | 123 |
| Cyrillic | 118 |
| Greek | 97 |
| Dutch | 84 |
| Spanish | 63 |
| German | 14 |

En cambio, sólo 63 contenían una forma explícita nueva de contusión o bone bruise.

El edema medular puede corresponder a OA, fractura por insuficiencia, osteonecrosis, sobrecarga o cirugía. V3 sólo debería asignar Contusion cuando exista:

1. Un término explícito de contusión/bruise; o
2. Edema óseo acompañado por una atribución traumática inequívoca —por ejemplo, mecanismo pivot-shift o “compatible con contusión”— dentro de la misma proposición.

### Synovitis no debe expandirse a cualquier expresión sinovial

En los 219 Synovitis `unknown` cirílicos, sólo cuatro cláusulas contenían una raíz `синов*`; correspondían a:

- Quistes perisinoviales.
- Condromatosis sinovial.

No eran sinovitis. La cobertura cirílica de 0,5% parece deberse, al menos en buena parte, a no mención real. Forzarla con “sinovial” produciría contaminación.

También deben excluirse explícitamente:

- Plica sinovial.
- Quiste sinovial.
- Tenosinovitis.
- Tumor/condromatosis sinovial.
- Bursitis.

### Baker’s

Una `popliteal cystic lesion` con diagnóstico diferencial de ganglión o quiste bursal no debe convertirse automáticamente en Baker positivo. Puede producir `uncertain` sólo cuando la anatomía sea compatible; de otro modo debe permanecer `unknown`.

## 5. Arquitectura conceptual propuesta

```text
Report original
    ↓
Normalización con offsets y preservación estructural
    ↓
Hipótesis de idioma por cláusula
    ↓
Lattice de segmentaciones
    ├─ cláusulas estrictas
    ├─ líneas reconstruidas
    ├─ pares padre–hijo
    ├─ listas y coordinaciones
    └─ secciones Findings/Impression/History
    ↓
Detectores de menciones
    ├─ exacto común
    ├─ morfológico por idioma
    ├─ estructural/plantillas
    ├─ colectivos
    └─ específico por target
    ↓
Grafo de menciones y modificadores
    ↓
Proposiciones clínicas normalizadas
    ↓
Reconciliación target-específica
    ↓
positive / negative / uncertain / unknown
```

### 5.1 Normalización dual

V3 debería conservar simultáneamente:

- Texto original.
- Texto normalizado.
- Offsets que permitan volver al fragmento original.
- Saltos de línea, delimitadores, encabezados y sangría.
- Forma canónica de apóstrofes, guiones y caracteres dañados.

V2 normaliza adecuadamente para matching, pero pierde parte de la estructura necesaria para resolver listas y scopes.

### 5.2 Idioma como hipótesis, no como puerta exclusiva

Cada cláusula debería recibir:

- Script dominante.
- Uno o más scores léxicos de idioma.
- Indicador de texto mixto.
- Detectores habilitados.

El detector exacto común se ejecutaría siempre. Los detectores morfológicos específicos se agregarían según las hipótesis de idioma. Una clasificación incorrecta no debería impedir reconocer un término inequívoco de otro idioma.

### 5.3 Lattice de segmentaciones

En lugar de una única lista de cláusulas, v3 generaría varias vistas:

1. Cláusula estricta, para negación y alta precisión.
2. Línea reconstruida, para wraps.
3. Par encabezado–valor:
   - `Fracture:` + `None`.
4. Lista coordinada:
   - `ACL, PCL and MCL: intact`.
5. Ventana estructural de cláusulas vecinas, sólo si existe una relación padre–hijo o continuidad sintáctica.
6. Sección completa, únicamente para resolver referencias compartidas, nunca para polaridad indiscriminada.

Una mención debe sobrevivir al menos una vista válida; no necesita aparecer en todas.

### 5.4 Morfología controlada por idioma

La v3 debería reemplazar enumeraciones exhaustivas de flexiones por familias auditables:

```text
raíz permitida
+ sufijos observados en el corpus
+ contexto anatómico obligatorio
+ lista de exclusiones
```

No conviene usar stemming libre. Cada raíz debe tener:

- Idioma/script.
- Target.
- Formas observadas y frecuencia.
- Contextos positivos, negativos y ambiguos.
- Regla de boundary.
- Evidencia de auditoría.

Ejemplos apropiados:

- `fraktur*` en alemán, con exclusión de contexto no diagnóstico.
- `kontuz*` en turco/eslavo.
- Familia observada de `Baker` + `cista/cyste/kist`.
- Flexiones griegas de `μωλωπ*`.
- `efuzyon*` en turco.

### 5.5 Grafo de menciones

Cada mención debería convertirse en un objeto estructurado:

```text
Mention:
    target/anatomy candidate
    finding
    phenotype
    polarity
    certainty
    grade
    laterality/compartment
    section
    text span
    detector
    language hypothesis
    collective scope
```

Luego se construyen relaciones:

- `finding → anatomy`
- `modifier → finding`
- `negation → proposition`
- `grade → lesion`
- `collective → members`
- `section → proposition`
- `list value → list targets`

La asociación se decide por compatibilidad y estructura, no sólo por distancia en caracteres.

## 6. Detectores target-específicos

| Target | Comportamiento recomendado para v3 |
|---|---|
| ACL | Resolver coordinaciones ACL/PCL; separar tear, sprain, mucoid degeneration y avulsion; colectivos de cruzados sólo negativos salvo asignación individual explícita. |
| MCL | Distinguir MCL de LCL y de referencias espaciales; manejar patología previa a la anatomía; colectivos colaterales conservadoramente. |
| Medial Meniscus | Parsear listas medial/lateral; adjuntar grade y tear al menisco correcto; conservar degeneration/extrusion como phenotype. |
| Lateral Meniscus | Misma estrategia; especial atención a frases donde una sola rotura pertenece sólo al medial. |
| Medial OA | Crear scopes compartimentales persistentes; aceptar cambios condrales localizados aunque “OA” no aparezca literalmente. |
| Lateral OA | Resolver coordinaciones “medial and lateral”; evitar trasladar una patología del compartimento medial al lateral. |
| PF OA | Incorporar patella, trochlea, facets y retropatellar mediante relaciones anatómicas; es el mayor candidato de ganancia. |
| Effusion | Incorporar `efuzyon`, flexiones y cantidad de líquido intraarticular; excluir líquido en bursas, vainas y tejidos blandos. |
| Synovitis | Exigir sinovitis explícita o hipertrofia/engrosamiento/proliferación del sinovio; aplicar exclusiones estrictas. |
| Baker’s | Expandir derivados Baker+cyst y la bursa gastrocnemio–semimembranosa; lesiones poplíteas ambiguas no deben ser positivas. |
| Contusion | Exigir contusion/bruise explícito o edema con atribución traumática inequívoca; nunca edema medular aislado. |
| Fracture | Usar familias morfológicas y compuestos como `frakturlinie`/`fracturaire`; mantener negaciones explícitas y excluir antecedentes no diagnósticos. |

## 7. Ensemble prudente

La estrategia recomendada es un ensemble de evidencia:

1. Detector exacto común.
2. Detector morfológico idioma–target.
3. Detector de plantillas y listas.
4. Detector semántico específico del target.
5. Detector de colectivos.
6. Recuperación por similitud corpus-only, pero sólo para proponer candidatos léxicos.

No debería utilizarse mayoría de votos. La reconciliación debe seguir precedencias:

- Evidencia anatómica individual > colectiva.
- Relación sintáctica/lista > cercanía textual.
- Término explícito > inferencia contextual.
- Sección diagnóstica > antecedentes.
- Conflicto real sobre la misma proposición → confidence menor o `uncertain`.
- Ausencia de proposiciones aceptables → `unknown`.

La recuperación por embeddings o similitud de plantillas puede descubrir expresiones, pero no emitir por sí sola un label.

## 8. Separar extracción clínica y política binaria

V2 convierte rápidamente una mención en un target binario. V3 debería separar:

1. Extracción de phenotype:
   - tear
   - sprain
   - degeneration
   - mucoid degeneration
   - grade I/II/III
   - normality
   - intact but abnormal signal
2. Mapeo phenotype → label de competición.

Esto es especialmente importante porque el gold actual presenta casos donde el reporte describe una anomalía y el label oficial es 0: degeneraciones mucoides, sprains leves o lesiones meniscales de bajo grado.

Con sólo 58 gold studies no es posible inferir confiablemente la ontología oficial. Por ello:

- La primera v3 debería conservar el mapeo binario v2.
- Debe agregar phenotype y provenance.
- No debería cambiar el mapeo para imitar discordancias individuales del gold.
- Cualquier cambio posterior de ontología tendría que ser una decisión explícita y versionada.

## 9. Validación sin consumir los 58 gold

Los 58 gold deben tratarse como un sentinel externo permanente, no como development set.

### Descubrimiento y validación corpus-only

1. Agrupar reportes por plantilla exacta o aproximada.
2. Separar familias completas entre discovery y validación; no hacer un split aleatorio de reportes casi duplicados.
3. Descubrir formas en una partición.
4. Auditar cada patrón en Reports held-out.
5. Evaluar por idioma, target, polaridad y detector.
6. Congelar reglas antes de consultar gold.
7. Ejecutar los 58 gold una sola vez por release candidate.

### Pruebas necesarias

- Consistencia entre Findings e Impression.
- Misma expresión, mismo phenotype.
- Cambio controlado de anatomía:
  - medial → lateral sólo debe cambiar el target correspondiente.
- Inserción de negación:
  - `fracture` → `no fracture`.
- Perturbación de punctuation y saltos de línea.
- Listas con una y varias patologías.
- Anatomías vecinas distractoras.
- Términos ambiguos:
  - plica, quiste sinovial, ganglión, bursitis, edema medular.
- Invariantes de persistencia:
  - `unknown` sin evidence.
  - evidence siempre contiene el span que justificó el resultado.
  - `uncertain` no genera binary label.
  - cardinalidad exacta de 4.407 × 12.
  - gold nunca participa en extraction.

Para reglas nuevas de alta precisión propondría auditar todos los matches cuando sean menos de 50 y una muestra estratificada cuando sean más numerosos. Un patrón que no alcance aproximadamente 95% de precisión manual debería restringirse o permanecer como candidate-only.

## 10. Diferencias fundamentales frente a v2

| Dimensión | V2 | V3 propuesta |
|---|---|---|
| Segmentación | Una secuencia de cláusulas | Varias vistas estructurales |
| Léxico | Frases enumeradas | Exactos + morfología controlada |
| Asociación | Distancia en caracteres | Grafo de menciones y scopes |
| Idioma | Grupo único para análisis | Hipótesis múltiples por cláusula |
| Targets | Directos o estructurales genéricos | Adaptadores semánticos por target |
| Listas | Colectivos predefinidos | Parsing de coordinaciones y valores |
| Output interno | Status y evidence | Phenotype + proposition + provenance |
| Combinación | Prioridad simple de menciones | Reconciliación a nivel de evidencia |
| Similitud corpus | No utilizada | Sólo discovery y validación |
| No mención | Unknown | Unknown, sin cambios |
| Gold | Evaluación y override final | Sentinel congelado y override final |

## 11. Estructura modular requerida al implementarla

Una organización posible sería:

```text
src/report_labels/v3/
    schema.py
    normalization.py
    language.py
    segmentation.py
    morphology.py
    mention_graph.py
    reconciliation.py
    extractor.py

    lexicons/
        common.py
        greek.py
        cyrillic.py
        turkish.py
        south_slavic.py
        dutch.py
        german.py
        spanish.py
        french.py
        english.py

    detectors/
        ligaments.py
        menisci.py
        osteoarthritis.py
        effusion.py
        synovitis.py
        baker.py
        contusion.py
        fracture.py
        collectives.py
```

Además serían necesarios:

- `policy_v3.json`.
- Un schema de `Mention` y `Proposition`.
- CLI seleccionable `--policy v2|v3`.
- Artefactos `_v3` separados.
- Coverage por detector, idioma y target.
- Registro de términos descubiertos, aceptados, ambiguos y rechazados.
- Tests de regresión que mantengan v2 reproducible.
- Auditoría de consistency equivalente a v2, ampliada con spans y phenotype.

## 12. Orden recomendado de implementación futura

1. Congelar v2 y sus resultados.
2. Implementar normalización con offsets y lattice de segmentación.
3. Incorporar objetos `Mention`/`Proposition` y reconciliación.
4. Implementar primero las expansiones más claras:
   - Turkish Effusion.
   - South Slavic/Dutch Baker.
   - Cyrillic/Greek/South Slavic Contusion explícita.
   - Compuestos alemanes de Fracture/Synovitis.
5. Implementar el adaptador OA:
   - PF OA.
   - Medial OA.
   - Lateral OA.
6. Resolver listas de meniscos y ligamentos.
7. Agregar exclusiones y casos ambiguos.
8. Ejecutar validación por familias de plantillas.
9. Congelar reglas.
10. Evaluar una vez contra los 58 gold y generar artefactos v3.

## Conclusión

La v3 no necesita abandonar las reglas interpretables. Necesita cambiar la unidad de razonamiento: de “término dentro de una cláusula” a “proposición clínica construida desde varias evidencias estructuradas”.

La evidencia del corpus respalda especialmente:

- Morfología controlada por idioma.
- Scopes compartimentales para OA.
- Parsing de listas y coordinaciones.
- Detectores específicos para los 12 targets.
- Ensemble a nivel de menciones.
- Separación de phenotype y label binario.
- Uso de plantillas sólo para descubrimiento y validación.

El mayor error conceptual sería intentar elevar cobertura asignando negativos por silencio o generalizando términos ambiguos. El diseño propuesto conserva `no mention → unknown`, concentra el esfuerzo en los idiomas y targets con oportunidades observables y mantiene cada label trazable hasta evidencia textual concreta.