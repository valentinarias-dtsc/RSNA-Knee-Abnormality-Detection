# Tarea: implementar desde cero la etapa reproducible de generación de labels desde `Report`

Trabajá sobre el repositorio actual:

`valentinarias-dtsc/RSNA-Knee-Abnormality-Detection`

## Objetivo general

Implementá desde cero la etapa del proyecto destinada a **derivar/estimar los 12 targets de la competición exclusivamente a partir del texto del campo `Report`**, utilizando los 58 estudios con labels oficiales completos como referencia gold para diseñar, evaluar y auditar el procedimiento.

Esta etapa pertenece exclusivamente a la **construcción de supervisión**.

No implementar todavía ningún modelo de MRI.

No utilizar píxeles, DICOM, metadata de Series, scanner, plano anatómico ni ninguna otra característica del estudio para predecir o derivar los labels.

El flujo conceptual es:

```text
train.csv
│
├── StudyInstanceUID
├── Report
└── 12 targets parcialmente observados
          │
          ├── 58 studies con labels oficiales completos
          │           ↓
          │      referencia gold
          │
          └── resto de studies
                      ↓
Report
  ↓
procesamiento textual reproducible
  ↓
12 weak/derived labels
  +
confidence / estado de extracción
  ↓
evaluación contra los 58 gold labels
  ↓
dataset de supervisión preparado
para una futura etapa de modelado MRI
```

La implementación debe quedar integrada a la estructura general del proyecto y producir, de manera reproducible:

```text
código
↓
artefactos estructurados
↓
figuras
↓
reporte de etapa
+
reporte de implementación
```

---

# 1. Fuentes y contexto que deben inspeccionarse primero

Antes de modificar o crear código, inspeccioná el repositorio completo.

Como mínimo, revisá las fuentes internas existentes relacionadas con:

- caracterización inicial del dataset;
- estrategia de supervisión identificada a partir de notebooks de Kaggle;
- estructura actual del repositorio;
- convenciones de artefactos, figuras, reportes y código;
- scripts y módulos existentes;
- `requirements.txt`;
- cualquier implementación previa que pueda entrar en conflicto con esta tarea.

Los nombres concretos de archivos pueden haber cambiado debido a la nueva convención documental. Localizalos por contenido y propósito, no únicamente por el path histórico.

Como referencias históricas relevantes existen o existieron documentos equivalentes a:

```text
dataset_initial_characterization
kaggle_notebooks_supervision_strategy_review
```

También podés inspeccionar los notebooks almacenados en:

```text
private/kaggle_notebooks/
```

únicamente cuando ayuden a comprender posibles estrategias de extracción de labels.

No copies indiscriminadamente código de notebooks de terceros.

No bases la estrategia principal en la calidad, score, eficiencia o popularidad de modelos ajenos.

Las referencias externas prioritarias del proyecto son:

**Kaggle Competition**  
https://www.kaggle.com/competitions/rsna-knee-abnormality-detection

**Kaggle Data**  
https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/data

**Kaggle Rules**  
https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/rules

**RSNA Challenge**  
https://www.rsna.org/artificial-intelligence/ai-image-challenge/knee-mri-ai-challenge

**DICOM Standard**  
https://www.dicomstandard.org/

La implementación final debe pertenecer al proyecto y ser comprensible, modular, reproducible y auditable.

---

# 2. Hechos del proyecto que deben tratarse como restricciones

La caracterización previa estableció que:

- `train.csv` tiene una fila por `StudyInstanceUID`;
- cada Study de train tiene un `Report`;
- existen 12 targets:
  - `ACL`
  - `MCL`
  - `Medial Meniscus`
  - `Lateral Meniscus`
  - `Medial OA`
  - `Lateral OA`
  - `PF OA`
  - `Effusion`
  - `Synovitis`
  - `Baker's`
  - `Contusion`
  - `Fracture`
- sólo 58 Studies tienen los 12 labels oficiales observados;
- esos 58 constituyen la referencia gold disponible;
- los restantes Studies necesitan supervisión derivada;
- el `Report` está disponible en train;
- el `Report` no debe asumirse como input del modelo durante inferencia;
- la siguiente etapa del proyecto utilizará la supervisión construida aquí para desarrollar un modelo basado exclusivamente en MRI.

La revisión de cinco notebooks públicos de Kaggle respaldó de forma consistente el flujo:

```text
Report
→ extracción/estimación de 12 labels
→ combinación con los 58 labels explícitos
→ entrenamiento de modelo MRI
→ inferencia sin Report
```

Por lo tanto, esta implementación debe concentrarse exclusivamente en:

```text
Report → training supervision
```

No avances al procesamiento visual.

---

# 3. Filosofía arquitectónica obligatoria

La fuente de verdad ejecutable del proyecto no debe ser un notebook.

Separá:

```text
EXPLORACIÓN
notebooks opcionales
        ↓
ideas / inspección / diagnóstico

IMPLEMENTACIÓN OFICIAL
módulos Python
+
configuración
+
orquestadores
        ↓
artefactos reproducibles
        ↓
figuras
        ↓
reportes
```

## Código reusable

La lógica real debe vivir en módulos `.py`.

Debe cubrir, cuando corresponda:

- carga y validación de datos;
- normalización textual;
- detección o caracterización lingüística;
- segmentación de secciones;
- normalización terminológica;
- extracción de evidencia;
- negación;
- incertidumbre;
- contexto;
- extracción específica por target;
- confidence;
- provenance;
- evaluación contra gold labels;
- error analysis;
- construcción del dataset final;
- persistencia de artefactos;
- generación reproducible de figuras;
- generación o soporte para generación de reportes.

## Orquestación

Debe existir un entry point reproducible que permita ejecutar esta etapa sin abrir un notebook.

Por ejemplo, conceptualmente:

```bash
python ...
```

o:

```bash
python -m ...
```

Adaptá el comando a la arquitectura real del repositorio.

## Notebook

El notebook deja de ser un entregable obligatorio de la etapa.

Puede crearse o mantenerse únicamente si aporta valor para:

- exploración rápida;
- inspección de reports;
- error analysis interactivo;
- debugging;
- investigación de hipótesis.

Si existe, no debe contener lógica indispensable para reproducir los outputs oficiales.

La etapa debe poder regenerarse completamente sin ejecutarlo.

---

# 4. Convención de etapas y nombres

Esta tarea pertenece a una secuencia lógica del proyecto.

Antes de elegir nombres, inspeccioná las etapas existentes y asigná a esta etapa el número correspondiente.

Cuando varios archivos dentro de un mismo directorio formen parte de la secuencia narrativa del proyecto, utilizá el formato:

```text
00 - ...
01 - ...
02 - ...
03 - ...
```

El número representa la **etapa conceptual**, no simplemente el orden temporal de creación del archivo.

Por ejemplo, si generación de labels corresponde a la etapa `02`, podrían existir conceptos como:

```text
reports/stages/
└── 02 - report label generation.md

reports/implementation/
└── 02 - report label generation implementation.md
```

No uses necesariamente `02`; determiná el número correcto inspeccionando el proyecto.

Aplicá la misma lógica de reconocimiento rápido donde tenga sentido para:

- artefactos;
- figuras;
- configuraciones;
- subdirectorios de etapa.

Los nombres deben ser:

- descriptivos;
- inequívocos;
- consistentes;
- fáciles de encontrar.

---

# 5. Organización de outputs

Cada output debe pertenecer a un directorio semánticamente apropiado.

No deben quedar:

```text
figuras sueltas
CSV sin contexto
outputs en la raíz
artefactos sin documentar
archivos ambiguamente nombrados
```

Una estructura conceptual posible sería:

```text
artifacts/
└── <etapa-report-labels>/
    ├── labels...
    ├── metrics...
    ├── error_analysis...
    ├── metadata...
    └── ...

reports/
├── stages/
│   └── <NN - reporte de etapa>.md
│
└── implementation/
    └── <NN - reporte de implementación>.md

figures/
└── <etapa-report-labels>/
    └── ...
```

Pero adaptá esta propuesta a las convenciones reales existentes.

No reorganices innecesariamente todo el repositorio.

Si necesitás introducir una nueva convención, hacelo de manera mínima, coherente y sin romper referencias existentes.

---

# 6. Diseño de la extracción

Implementá una **primera política explícita, interpretable y reproducible** de extracción.

No asumas que la ausencia de una palabra equivale automáticamente a un label negativo.

Debés contemplar como mínimo cuatro estados conceptuales:

```text
positive
negative
uncertain
unknown / unresolved
```

Podés representarlos internamente de otra manera si la semántica queda inequívocamente documentada.

---

## A. Sinonimia y variantes terminológicas

Los reportes pueden utilizar términos diferentes para el mismo hallazgo.

Ejemplo conceptual:

```text
ACL
anterior cruciate ligament
ligamento cruzado anterior
...
```

No limites la búsqueda al nombre literal de las columnas.

Las reglas deben ser target-específicas cuando la semántica lo requiera.

---

## B. Negación

Debe distinguirse correctamente:

```text
ACL tear
```

de:

```text
no ACL tear
ACL intact
without evidence of ACL tear
```

La estrategia de negation handling debe ser:

- explícita;
- reusable;
- testeable;
- suficientemente local para evitar negar hallazgos independientes.

---

## C. Incertidumbre

Distinguí, cuando sea posible:

```text
tear
```

de:

```text
possible tear
cannot exclude tear
suspicious for tear
```

Los casos inciertos no tienen que convertirse forzosamente en 0/1.

Pueden producir:

- estado `uncertain`;
- soft score;
- confidence menor;
- label binario missing.

La política debe quedar documentada y evaluada.

---

## D. Contexto

Evitá que una palabra aislada active un target cuando aparezca en contexto irrelevante.

Revisá particularmente:

- antecedentes;
- indicación clínica;
- comparación con estudios previos;
- técnica;
- diagnóstico diferencial;
- hallazgos explícitamente descartados.

---

## E. Multilingüismo

El dataset contiene reports en varios idiomas.

No implementes una solución English-only sin medir previamente su cobertura.

Inspeccioná empíricamente los idiomas o grupos lingüísticos.

La solución puede utilizar:

- reglas multilingües;
- normalización terminológica;
- diccionarios;
- NLP local;
- otra estrategia reproducible.

No utilices servicios externos como requisito estructural.

No utilices APIs de LLM remotos como única forma de reproducir los labels.

---

# 7. Los 58 gold labels: uso obligatorio y separado

Los 58 Studies con labels oficiales deben cumplir dos funciones diferentes.

## A. Evaluación del extractor

Ejecutá primero la extracción textual sin modificarla con los gold labels.

Compará:

```text
derived
vs
official
```

por target.

La predicción textual debe existir **antes** de aplicar cualquier gold override.

## B. Construcción de supervisión final

Para el dataset que será consumido posteriormente por el modelo visual:

```text
official > report-derived
```

El gold label tiene prioridad absoluta.

Sin embargo, preservá siempre:

```text
derived
official
final
```

y su provenance.

Nunca reemplaces silenciosamente la extracción textual.

---

# 8. Prevención de overfitting a los 58 gold cases

El gold set es demasiado pequeño para justificar reglas específicas por observación.

No implementes:

- excepciones por `StudyInstanceUID`;
- reglas destinadas exclusivamente a corregir un report puntual;
- lookup tables que memoricen el gold set;
- búsqueda indiscriminada de reglas para maximizar F1.

Toda modificación surgida del error analysis debe generalizar como procedimiento lingüístico razonable.

La política debe poder aplicarse sin cambios a los 4.407 reports.

---

# 9. Confidence y provenance

Cada weak label debe permitir reconstruir:

```text
qué se decidió
por qué
con qué evidencia
con qué confianza
desde qué fuente
```

Como mínimo debe distinguirse:

```text
official
report_derived
unresolved
```

Cuando sea apropiado, conservá también:

```text
status
score
confidence
evidence
rationale
```

La confidence no necesita interpretarse como probabilidad calibrada.

Puede ser inicialmente una escala determinista basada en la fortaleza de la evidencia.

Pero debe tener:

- definición explícita;
- dominio conocido;
- interpretación documentada.

---

# 10. Evaluación requerida

Evaluá por target.

Como mínimo, cuando matemáticamente corresponda:

- gold positives;
- gold negatives;
- coverage;
- precision;
- recall;
- F1;
- confusion matrix;
- unknown;
- uncertain;
- FP;
- FN.

Si existen scores continuos, evaluá su comportamiento cuando resulte justificable.

No fuerces una binarización sólo para aumentar la cantidad de métricas.

Con:

```text
N = 58
```

no presentes pequeñas diferencias numéricas como evidencia concluyente.

El reporte debe distinguir:

```text
métrica observada
≠
conclusión definitiva sobre generalización
```

---

# 11. Error analysis obligatorio

Generá un artefacto reproducible que permita inspeccionar:

```text
StudyInstanceUID
target
Report
gold
derived
status
confidence
evidence
error_type
```

con categorías relevantes como:

```text
FP
FN
unknown
uncertain
```

Analizá patrones generales de error:

- vocabulario faltante;
- sinonimia;
- negación;
- incertidumbre;
- idioma;
- contexto;
- secciones;
- conflictos report/gold;
- otras causas observables.

No atribuyas automáticamente una discordancia al extractor: el reporte y el gold pueden no representar exactamente la misma semántica clínica.

Documentá esa limitación cuando aparezca.

---

# 12. Iteración del extractor

Podés implementar versiones sucesivas sólo cuando respondan preguntas concretas.

Por ejemplo:

```text
v0
→ baseline léxico

v1
→ añade negación

v2
→ añade incertidumbre / contexto / multilingüismo
```

No es necesario implementar todas.

Para cada iteración relevante registrá:

```text
problema identificado
→ decisión
→ cambio
→ resultado observado
→ interpretación
```

La versión final de esta etapa debe quedar explícitamente identificada.

---

# 13. Artefacto principal de labels

Generá un artefacto persistente, versionado y reproducible.

No sobrescribas `train.csv`.

El dataset principal debe contener, por `StudyInstanceUID` y para cada target, información equivalente a:

```text
derived label
derived score
confidence
status
provenance/source
gold label
final label
final source
```

y, cuando resulte útil:

```text
evidence
rationale
```

Los unresolved deben permanecer explícitamente unresolved/missing.

No los conviertas silenciosamente en cero.

El formato principal puede ser:

- Parquet, preferentemente para estructura rica;
- CSV si la interoperabilidad actual del repositorio lo justifica.

Podés ofrecer una representación secundaria para inspección humana, pero evitá duplicación innecesaria.

---

# 14. Otros artefactos requeridos

Persistí por separado, como mínimo:

### Métricas

Tabla por target.

### Error analysis

Casos auditables.

### Resumen lingüístico

Si la estrategia utiliza idioma o grupos lingüísticos.

### Metadata de ejecución

Debe permitir identificar:

- versión de la política;
- input;
- output;
- schema;
- fecha/run cuando corresponda;
- hashes si la infraestructura actual lo permite;
- configuración relevante.

Estos archivos deben estar claramente asociados con la etapa.

---

# 15. Figuras

Generá únicamente figuras que ayuden a entender o decidir.

Posibles ejemplos:

- coverage por target;
- precision/recall/F1;
- unresolved rate;
- FP/FN;
- gold vs derived prevalence;
- confidence distribution;
- positive labels por Study.

Cada figura debe:

1. tener un nombre descriptivo;
2. estar en el directorio correspondiente a la etapa;
3. aparecer o ser referenciada explícitamente en el reporte de etapa;
4. tener interpretación textual.

No deben quedar figuras huérfanas.

Si una figura no aporta al reporte, no la generes.

---

# 16. Regla obligatoria de trazabilidad documental

**Todo artefacto o figura creado durante esta etapa debe ser mencionado en alguno de sus reportes correspondientes.**

Para cada output debe quedar explicado:

```text
qué contiene
por qué fue generado
dónde está
cómo debe interpretarse o utilizarse
```

No es necesario incrustar tablas enormes dentro de Markdown.

El reporte puede:

- mostrar una síntesis;
- incluir algunas filas;
- enlazar o referenciar el artefacto completo.

Pero ningún output debe quedar sin documentar.

---

# 17. Reporte principal de la etapa

Generá un reporte Markdown específico de esta etapa en el directorio de reportes de etapas.

Debe seguir la numeración lógica:

```text
NN - ...
```

Este documento es el registro principal del **conocimiento y las decisiones** obtenidas.

No es un changelog de código.

Debe ser:

- autoconcluyente;
- autoexplicativo;
- profesional;
- técnico;
- preciso;
- orientado a compañeros de data science;
- comprensible sin abrir notebooks ni leer el código;
- explícito respecto de incertidumbre y limitaciones.

## Tono

Usá lenguaje profesional, técnico y descriptivo.

Evitá:

- lenguaje promocional;
- afirmaciones más fuertes que la evidencia;
- conclusiones clínicas no respaldadas;
- informalidad innecesaria.

Cuando aparezca terminología radiológica o clínica imprescindible, explicala brevemente si puede dificultar la interpretación para un data scientist no especializado en salud.

---

# 18. Estructura obligatoria del reporte de etapa

## 1. Resumen ejecutivo

Sintetizar:

- propósito;
- enfoque;
- principales resultados;
- decisión;
- implicación para el siguiente paso.

## 2. Conexión con la etapa anterior

Explicar:

- qué problema previo motivó esta etapa;
- qué inputs heredó;
- qué decisiones ya estaban fijadas.

Debe poder entenderse por qué:

```text
dataset characterization
+
supervision strategy
→
report label generation
```

## 3. Objetivo y preguntas

Definir qué debía resolver la etapa.

## 4. Datos utilizados

Documentar:

```text
train.csv
StudyInstanceUID
Report
12 gold targets
58 gold Studies
```

y cantidades relevantes.

## 5. Formulación del problema

Explicar:

```text
Report → 12 weak labels
```

y distinguir:

- gold;
- derived;
- soft score;
- confidence;
- unknown;
- uncertain;
- final label.

## 6. Exploración textual relevante

Sólo lo necesario para diseñar y comprender la extracción.

No repetir el EDA general.

## 7. Metodología

Explicar qué procedimiento se implementó.

## 8. Decisiones

Separar explícitamente las decisiones metodológicas.

## 9. Findings / resultados

Presentar:

- métricas;
- coverage;
- distribuciones;
- tablas;
- figuras;
- error patterns.

## 10. Interpretación

Interpretar los findings sin mezclarlos con los resultados brutos.

Debe quedar claro qué es:

```text
observado
```

y qué es:

```text
interpretado
```

## 11. Error analysis

Resumir patrones relevantes y referenciar el artefacto completo.

## 12. Supervisión final obtenida

Documentar:

- cantidad de Studies;
- resolved;
- unresolved;
- uncertain;
- gold overrides;
- coverage por target;
- confidence;
- provenance.

## 13. Artefactos y figuras

Enumerar **todos** los outputs producidos en esta etapa.

No omitir ninguno.

## 14. Limitaciones

Incluir explícitamente:

- tamaño del gold set;
- representatividad;
- multilingüismo;
- ambigüedad;
- coverage;
- targets difíciles;
- limitaciones de confidence;
- posibles discordancias report/gold.

## 15. Conclusiones

Sintetizar qué puede considerarse establecido al terminar la etapa.

## 16. Conexión con la siguiente etapa

Cerrar con una transición explícita:

```text
report-derived + gold supervision
        ↓
MRI preprocessing / representation
        ↓
first visual baseline
```

No implementar esa etapa aquí.

---

# 19. Reporte de implementación de código

Generá además un segundo Markdown en:

```text
reports/implementation/
```

con el mismo número lógico de etapa:

```text
NN - ... implementation.md
```

Este reporte es distinto del reporte principal.

Su objetivo es permitir un catch-up técnico rápido sobre **cómo quedó implementado el código**.

## Debe contener

### Resumen técnico

Qué fue implementado.

### Contexto

A qué etapa del proyecto pertenece.

### Arquitectura

Por ejemplo:

```text
train.csv
   ↓
text preprocessing
   ↓
target extraction
   ↓
evaluation
   ↓
gold override
   ↓
artifacts
   ↓
reporting
```

### Archivos creados o modificados

Lista exacta con responsabilidad breve.

### Módulos

Responsabilidades e interfaces principales.

### Orquestador / entry point

Cómo ejecutar la etapa.

### Configuración

Qué parámetros relevantes existen.

### Tests

Qué comportamiento protegen.

### Dependencias

Qué se agregó o reutilizó.

### Artefactos generados

Enumerarlos todos.

### Figuras generadas

Enumerarlas todas.

### Reproducibilidad

Comandos exactos.

### Limitaciones técnicas

Sólo las relacionadas con implementación.

### Conexión con el siguiente componente

Explicar qué contrato de salida queda disponible para el pipeline MRI.

No dupliques innecesariamente todo el análisis estadístico del reporte principal.

---

# 20. Reports generados desde artefactos

Siempre que resulte razonable:

```text
artefactos estructurados
        ↓
tablas / figuras
        ↓
Markdown
```

y no:

```text
valores copiados manualmente
        ↓
Markdown
```

Las tablas de métricas o resúmenes que aparezcan en los reportes deberían derivarse de los outputs reales.

Los reports deben mantenerse sincronizados con la ejecución de la etapa.

No hardcodees manualmente resultados si pueden recuperarse de los artefactos.

---

# 21. Tests y validaciones de software

Incluí tests significativos para componentes críticos.

Como mínimo:

## Negación

```text
"ACL tear"
→ positive
```

```text
"No ACL tear"
→ negative
```

## Incertidumbre

```text
"Possible ACL tear"
```

no debe interpretarse exactamente igual que una afirmación inequívoca.

## Ausencia

Un report sin referencia fiable a ACL no debe producir evidencia positiva.

## Reproducibilidad

Misma entrada → misma salida.

## Schema

Verificá:

- 4.407 Study IDs;
- ningún Study duplicado;
- 12 targets;
- gold labels preservados;
- dominios válidos;
- provenance válido;
- confidence válida;
- ningún merge que elimine Studies.

## Gold override

Verificá explícitamente que:

```text
final == official
```

para los 58 casos gold.

No agregues tests ornamentales.

---

# 22. Reproducibilidad

Toda la etapa debe poder regenerarse desde datos originales mediante uno o pocos comandos documentados.

No debe depender de:

- estado previo de notebook;
- archivos creados manualmente;
- modificaciones interactivas;
- APIs externas;
- servicios remotos imprescindibles.

Si existe aleatoriedad:

- fijá seed;
- documentala.

Si no es necesaria, evitala.

---

# 23. Dependencias

Antes de agregar una dependencia:

1. comprobá si las dependencias existentes son suficientes;
2. evitá paquetes innecesariamente pesados;
3. priorizá ejecución offline;
4. actualizá `requirements.txt` o la configuración equivalente;
5. documentá la razón en el reporte de implementación.

No introduzcas infraestructura innecesaria para esta primera política de weak labeling.

---

# 24. Fuera de alcance

No implementes:

- lectura de PixelData;
- preprocessing MRI;
- ordenamiento de slices para modelado visual;
- DICOM como feature;
- CNN;
- ViT;
- DINO;
- 2.5D;
- 3D;
- MIL;
- embeddings visuales;
- multimodal fusion;
- image/text joint training;
- entrenamiento del baseline;
- checkpoints visuales;
- Kaggle inference;
- submission;
- ensembles;
- optimización de modelos;
- análisis de leaderboard;
- benchmarking de modelos de terceros.

Tampoco utilices metadata del MRI para derivar labels.

El output de esta tarea es:

```text
supervisión reusable
```

no:

```text
modelo predictivo final
```

---

# 25. Criterios de aceptación

Considerá completada la etapa únicamente si:

1. existe una pipeline textual modular en Python;
2. existe un orquestador ejecutable sin notebook;
3. procesa los 4.407 reports;
4. genera estados para los 12 targets;
5. conserva derived labels;
6. conserva gold labels;
7. conserva confidence;
8. conserva provenance;
9. evalúa contra los 58 gold Studies antes del override;
10. official labels tienen prioridad en el dataset final;
11. unresolved/uncertain no se convierten silenciosamente en negativos;
12. existe error analysis reproducible;
13. existe un artifact principal de supervisión versionado;
14. existen artefactos de métricas y auditoría;
15. existen tests relevantes;
16. las figuras son reproducibles;
17. no existen figuras huérfanas;
18. no existen artefactos huérfanos;
19. existe un reporte principal de etapa autoconcluyente;
20. existe un reporte separado de implementación;
21. ambos reportes utilizan la numeración lógica `NN -`;
22. todos los artefactos y figuras aparecen documentados en los reportes;
23. existe una forma explícita de reproducir todo desde cero;
24. el proyecto no depende de un notebook para generar los resultados;
25. cualquier notebook creado es únicamente exploratorio/diagnóstico;
26. no se utilizaron MRI/DICOM como features de labeling;
27. no se implementó todavía el baseline visual.

---

# 26. Comportamiento esperado durante la tarea

Inspeccioná primero.

Diseñá después.

Implementá después de entender las convenciones reales del repositorio.

No reemplaces decisiones importantes por supuestos silenciosos.

Cuando existan varias interpretaciones razonables:

- elegí la alternativa más conservadora;
- documentá por qué;
- preservá información en lugar de descartarla.

No conviertas missing/no mention automáticamente en negativo.

No optimices ciegamente contra los 58 gold labels.

No confundas:

```text
finding
interpretation
decision
```

en los reportes.

Priorizá:

```text
accuracy conceptual
+
interpretabilidad
+
reproducibilidad
+
auditabilidad
+
provenance
+
claridad documental
```

sobre complejidad.

---

# 27. Estado final esperado

Al terminar, el proyecto debe disponer conceptualmente de:

```text
RAW TRAIN REPORTS
       ↓
REPRODUCIBLE TEXT PIPELINE
       ↓
WEAK / DERIVED LABELS
       +
GOLD OVERRIDE
       +
CONFIDENCE
       +
MASKS / UNRESOLVED
       +
PROVENANCE
       ↓
VERSIONED ARTIFACTS
       ↓
STAGE REPORT
       +
IMPLEMENTATION REPORT
```

y quedar preparado para la siguiente etapa:

```text
supervision artifact
        +
MRI preprocessing
        ↓
first visual baseline
```

No avances a esa etapa.