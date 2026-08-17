`prompt`: 

hacé una búsqueda de términos en distintos idiomas que sirva para ampliación de los ya definidos en src/report_labels/constants.py, declará cuando se trate de términos ambiguos, separá como creas conveniente los términos que agrupan varios targets. tratá de basar la elección de nuevos términos en palabras realmente existentes en el corpus normalizado de Report.

`respuesta (planificación)`: 

Sí. La búsqueda corpus-first muestra un conjunto relevante de ampliaciones de bajo costo. No modifiqué [constants.py](C:/Github/RSNA-Knee-Abnormality-Detection/src/report_labels/constants.py) ni el generador.

## Metodología

Busqué los candidatos sobre las cláusulas diagnósticas producidas por `segment_report(normalize_text(Report))`.

Las frecuencias siguientes representan:

- estudios únicos con al menos una aparición;
- sólo secciones consideradas diagnósticas;
- `unknown` actual para el target asociado.

Son un techo de cobertura potencial, no una estimación de cuántos casos quedarían correctamente resueltos tras agregar el término. El mismo estudio puede contener otra mención o una polaridad conflictiva.

## 1. Términos target-específicos prioritarios

### Alta precisión

| Idioma | Término normalizado observado | Target | Estudios | `unknown` actual | Recomendación |
|---|---|---:|---:|---:|---|
| ES | `lca` | ACL | 90 | 88 | Agregar como abreviatura exacta |
| ES | `lcm` | MCL | 31 | 29 | Agregar como abreviatura exacta |
| ES | `quistes popliteos` | Baker’s | 282 | 203 | Agregar plural |
| ES | `fracturas` | Fracture | 21 | 18 | Agregar plural |
| EN | `popliteal cysts` | Baker’s | 10 | 4 | Agregar plural |
| EN | `fractures` | Fracture | 35 | 29 | Agregar plural |
| EN | `bone contusions` | Contusion | 27 | 23 | Agregar plural |
| ES | `contusiones oseas` | Contusion | 4 | 4 | Agregar plural |
| FR | `contusions osseuses` | Contusion | 2 | 2 | Agregar plural |
| DE | `synoviale proliferation`, `synoviale proliferationen` | Synovitis | 4 | 4 | Agregar ambas formas |
| SS | `poplitealne ciste` | Baker’s | 148 | 147 | Agregar flexión |
| SS | `bakerove ciste` | Baker’s | 9 | 9 | Agregar flexión |
| SS | `frakture`, `frakturi` | Fracture | 15 | 14 | Agregar flexiones |
| SS | `medijalni kolateralni ligamenti` | MCL | 82 | 79 | Agregar plural |
| BG | `бекерова киста` | Baker’s | ≥31 | ≥31 | Agregar forma búlgara |
| BG | `латералния менискус` | Lateral Meniscus | 63 en una plantilla frecuente | 63 | Agregar forma definida |
| BG | `медиалния менискус` | Medial Meniscus | Presente en corpus | Alta | Agregar forma definida |

`LCA` y `LCM` son abreviaturas de alta precisión dentro de reportes de rodilla, pero deberían conservar límites exactos de palabra para evitar coincidencias internas.

### Patología de cartílago/OA

Estas extensiones son consistentes con la semántica vigente de `OA_TERMS`, que ya trata defectos y pérdida de cartílago como evidencia de OA compartimental.

| Idioma | Términos observados | Estudios | Comentario |
|---|---|---:|---|
| EN | `cartilage defects`, `cartilage fissures`, `cartilage fissuring`, `cartilage thinning` | Hasta 354 | Plurales actualmente no cubiertos |
| EN | `chondral defects`, `chondral thinning`, `chondral fissures`, `chondral fissuring` | 113 | Requieren anatomía compartimental |
| ES | `defectos condrales`, `lesiones condrales` | 15 | Alta precisión con compartimento |
| NL | `kraakbeenlijden` | 66 | Patología cartilaginosa; 62/66 PF OA siguen `unknown` |
| NL | `kraakbeendefecten` | 38 | Plural de un concepto ya aceptado |
| NL | `kraakbeenfissuren` | 9 | Compatible con lesión condral |
| NL | `kraakbeenletsels` | 4 | Compatible, algo más amplio |
| DE | `knorpeldefekte` | 4 | Plural |
| DE | `knorpelirregularitaten` | 19 | Evidencia leve pero patológica |
| DE | `knorpelschaden` | 4 | Daño cartilaginoso |
| DE | `knorpelglatze` | 3 | Pérdida completa de cartílago |

No agregaría `cartilage`, `cartilago`, `knorpel` o `kraakbeen` de manera aislada: nombran la anatomía, no necesariamente una anomalía.

### Meniscopatía turca

`meniskopati` aparece en 87 estudios, por ejemplo:

> `lateral meniskuste grade ii meniskopati`

Actualmente permanecen `unknown` 33 pares de menisco medial y 7 laterales dentro de esos estudios.

Es un candidato razonable porque la política actual ya considera `degeneration` y `degeneracion` como patología meniscal. No obstante, lo clasificaría como **ambigüedad moderada**: puede representar degeneración intrameniscal sin rotura. Sólo debería agregarse si el target representa cualquier anomalía meniscal y no exclusivamente tear.

## 2. Modificadores faltantes

Estos términos no deben asignar un target por sí solos. Sólo deberían modificar una anatomía o hallazgo reconocido en la misma cláusula.

| Idioma | Nuevas formas observadas | Estudios |
|---|---|---:|
| ES | `normales` | 325 |
| ES | `conservados`, `conservadas` | 37 y 6 |
| ES | `sin alteraciones` | 275 |
| ES | `dentro de limites normales` | 285 |
| FR | `intacts`, `intactes` | 22 |
| FR | `normaux`, `normales` | ≈29 franceses |
| FR | `sans particularite` | 36 |
| NL | `intacte` | 45 |
| DE | `intakte`, `intakter`, `intaktes` | 115 |
| DE | `unauffallige`, potencialmente otras flexiones | 94 |
| DE | `regelrechte`, potencialmente otras flexiones | 128 |
| TR | `dogaldir` | 208 |
| SS | `urednog`, `uredne`, `uredno`, `urednih` | ≥240 |
| SS | `odrzanog`, `odrzani`, `odrzan`, `odrzane` | ≥164 |
| EL | `εντος του φυσιολογικου` | Muy frecuente |
| EL | `φυσιολογικα απεικονιζονται` | Recurrente |
| BG | `запазена цялост` | ≥50 en plantillas frecuentes |
| BG | `интактни` | ≥19 |
| BG | `нормално изобразяване` | Muy frecuente |
| BG | `без особености` | ≥48 |

Hay una inconsistencia técnica importante: algunas entradas griegas y cirílicas existentes parecen raíces, como equivalentes de `φυσιολογ...`, `нормал...` o `запазен...`, pero `contains_any()` exige un límite de palabra después del término. En consecuencia, esas raíces no funcionan como prefijos.

Las alternativas conservadoras son:

1. añadir las formas completas observadas;
2. introducir separadamente `PREFIX_NORMALITY_TERMS`;
3. no relajar globalmente el límite derecho de todos los términos.

La primera opción implica menos riesgo.

### Negadores pospuestos

En turco aparece `saptanmamistir` en 133 estudios:

> `eklemde sivi artisi saptanmamistir`

Significa que no se detectó el hallazgo, pero agregarlo únicamente a `NEGATION_TERMS` no basta. `_polarity()` sólo admite unos pocos negadores pospuestos: [extraction.py](C:/Github/RSNA-Knee-Abnormality-Detection/src/report_labels/extraction.py:38).

Requiere agregarlo también al conjunto de negadores pospuestos. Debe evitarse generalizar `izlenmemistir`: en frases como “el cuerpo del menisco no se visualiza” puede representar una anomalía positiva, no una negación del target.

## 3. Expresiones colectivas

Conviene mantenerlas fuera de `ANATOMY_TERMS`, porque su propagación depende de la polaridad y del alcance.

### Meniscos: propagación bilateral permitida

| Idioma | Expresión observada | Estudios |
|---|---|---:|
| ES | `ambos meniscos` | 8 |
| ES | `menisco/meniscos medial y lateral` | 17 |
| ES | `meniscos interno y externo` | Incluida en las coordinaciones observadas |
| EN | `medial and lateral menisci` | 199 |
| EN | `both menisci` | 12 |
| FR | `menisques interne et externe` | 4 |
| NL | `normaal voorkomen menisci`, `normaal voorkomende menisci` | 36 |
| DE | `menisken intakt`, `menisci intakt` | 12 |
| TR | `medyal ve lateral meniskus` | 58 |
| SS | `oba meniska`, `oba meniskusa` | 17 |
| EL | `μηνισκοι` dentro de una afirmación colectiva normal | 8 en una plantilla exacta |

Regla recomendada:

- normalidad/negación con alcance completo → ambos negativos;
- patología que explícitamente afecta a ambos → ambos positivos;
- `uno de ambos meniscos`, `alguno de los meniscos` → no propagar.

La coordinación turca es especialmente relevante: en `medyal ve lateral meniskus`, el sustantivo aparece una sola vez y el matcher no puede construir `medyal meniskus`.

### Ligamentos: propagación asimétrica

| Idioma | Expresión observada | Estudios |
|---|---|---:|
| ES | `ligamentos cruzados y colaterales` | 260 |
| EN | `cruciate and collateral ligaments` | 57 |
| FR | `ligaments croises anterieur et posterieur` | 22 |
| NL | `kruisbanden` | 66 |
| DE | `kreuzbander` | 133 |
| DE | `kollateralbander` | 69 |
| EL | `χιαστοι και πλαγιοι συνδεσμοι` y orden inverso | ≥17 en plantillas repetidas |
| BG | `кръстните връзки` | ≥58 |
| BG | `колатерални лигаменти` | ≥64 |

Reglas seguras:

- “ligamentos cruzados normales” → `ACL = negative`;
- “ligamentos colaterales normales” → `MCL = negative`;
- “cruzados y colaterales normales” → ACL y MCL negativos;
- “ACL y PCL rotos” → ACL positivo porque ACL es explícito;
- “lesión/rotura de los ligamentos cruzados” → no asignar ACL: podría referirse sólo al PCL;
- “lesión de ligamentos colaterales” → no asignar MCL: podría referirse sólo al LCL.

La expresión mencionada `ligamentos cruzados y laterales` es **ambigua**. En el corpus aparecen construcciones como:

> `ligamentos cruzados y colateral lateral sin alteraciones`

Eso comprende cruzados y LCL, no MCL. No debería activar MCL.

### Compartimentos OA

| Idioma | Expresión | Estudios |
|---|---|---:|
| ES | `compartimentos femorotibiales` | 197 |
| EN | `tibiofemoral compartments` | 9 |
| BG | `хрущял на фемура и тибията` en afirmaciones globales | ≥11 |
| EL | `αρθρικος χονδρος` globalmente normal | ≥52 |

Para `compartimentos femorotibiales`:

- “ambos/los compartimentos femorotibiales normales” → Medial OA y Lateral OA negativos;
- “cambios degenerativos en ambos compartimentos” → ambos positivos;
- “cambios femorotibiales” sin especificación bilateral → ambiguo;
- “cartílago articular normal” sin localización → potencialmente todos los OA negativos, pero es una expansión más severa y debería auditarse por separado.

No mezclaría la regla tibiofemoral con PF OA salvo que también aparezca `patelofemoral`, `patellar`, `trochlear` o equivalente.

## 4. Términos ambiguos que no agregaría directamente

| Término o familia | Posible target | Razón de ambigüedad |
|---|---|---|
| `bone marrow edema`, `edema oseo`, `knochenmarkodem`, `kemik iligi odemi`, `kostani edem`, `костномозъчен едем` | Contusion | El edema medular puede ser traumático, degenerativo, inflamatorio o por fractura |
| `synovium`, `sinovial`, `synoviale` aislado | Synovitis | Puede nombrar anatomía sin inflamación |
| `popliteal fossa normal/no mass` | Baker’s | No siempre equivale a exclusión dirigida de quiste de Baker |
| `cartilage abnormality` global | OA compartimental | No identifica medial, lateral o PF |
| `ligament injury` | ACL/MCL | No identifica cuál ligamento |
| `cruciate ligament tear` colectivo | ACL | Puede ser PCL |
| `collateral ligament tear` colectivo | MCL | Puede ser LCL |
| `meniscal signal` | Meniscos | Puede ser señal intrameniscal no equivalente a tear |
| `meniskopati` | Meniscos | Patología amplia; depende de la definición oficial del target |
| `б.` en plantillas búlgaras | Varios | Probablemente abrevia “sin particularidades”, pero es una abreviatura de una letra y demasiado riesgosa globalmente |
| `no significant abnormality identified` | Todos | Declaración global; no garantiza que los 12 targets hayan sido evaluados explícitamente |

Para contusión sólo ampliaría términos inequívocamente traumáticos:

- `bone contusions`;
- `contusiones oseas`;
- `contusions osseuses`;
- `pivot shift contusion`;
- equivalentes que incluyan explícitamente `contusion`, `bruise` o un modificador traumático.

## 5. Organización recomendada

Mantendría cuatro familias separadas:

```python
NORMALITY_TERMS = (...)
NEGATION_TERMS = (...)
PATHOLOGY_TERMS = (...)
OA_TERMS = (...)

COLLECTIVE_TERMS = {
    "both_menisci": {
        "targets": ("Medial Meniscus", "Lateral Meniscus"),
        "terms": (...),
        "positive_scope": "explicit_all",
        "negative_scope": "whole_group",
    },
    "cruciate_ligaments": {
        "targets": ("ACL",),
        "terms": (...),
        "positive_scope": "not_allowed_without_acl",
        "negative_scope": "whole_group",
    },
    "collateral_ligaments": {
        "targets": ("MCL",),
        "terms": (...),
        "positive_scope": "not_allowed_without_mcl",
        "negative_scope": "whole_group",
    },
    "tibiofemoral_compartments": {
        "targets": ("Medial OA", "Lateral OA"),
        "terms": (...),
        "positive_scope": "explicit_all",
        "negative_scope": "whole_group",
    },
}
```

## Prioridad sugerida

1. Agregar plurales y flexiones inequívocas: `lca`, `lcm`, `quistes popliteos`, `fracturas`, contusiones plurales, formas de Baker y fractura eslavas.
2. Completar modificadores frecuentes: `normales`, `sin alteraciones`, `sans particularite`, flexiones alemanas, `dogaldir`, formas eslavas y búlgaras.
3. Incorporar expresiones colectivas negativas de meniscos y ligamentos.
4. Incorporar coordinación elíptica turca, alemana y neerlandesa.
5. Ampliar términos de cartílago por plural/compuesto.
6. Evaluar aparte términos ambiguos como edema medular, meniscopatía y normalidad global.

Los mayores retornos esperables están en español, alemán, turco, neerlandés y lenguas eslavas. Griego y búlgaro requieren además corregir la incompatibilidad entre raíces léxicas y matching por palabras completas.