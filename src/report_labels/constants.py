"""Policy constants and multilingual lexicons for report label extraction.

The lexicons intentionally favour precision and auditability over coverage. They are
language-level rules, never study-specific exceptions.
"""

from __future__ import annotations

POLICY_VERSION = "report-label-policy-v1.0.0"
STAGE_NUMBER = "03"

TARGETS = (
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
)

VALID_STATUSES = ("positive", "negative", "uncertain", "unknown")
VALID_FINAL_SOURCES = ("official", "report_derived", "unresolved")

# Clause-local modifiers. Text is normalized before matching.
NEGATION_TERMS = (
    # English / Spanish / French / Dutch / German
    "no", "not", "without", "negative for", "absence of", "free of", "none",
    "sin", "no hay", "ausencia de", "ningun", "ninguna",
    "pas de", "sans", "aucun", "aucune", "absence de",
    "geen", "zonder", "niet",
    "kein", "keine", "keinen", "ohne", "nicht",
    # Turkish / Croatian-Serbian-Bosnian
    "yok", "yoktur", "izlenmedi", "saptanmadi", "mevcut degil", "gozlenmedi",
    "nema", "bez", "nije", "nisu",
    # Greek / Cyrillic
    "δεν", "χωρις", "ουδεν",
    "без", "няма", "липсва", "не се установява", "не се открива",
)

UNCERTAINTY_TERMS = (
    "possible", "possibly", "probable", "suspicious", "suspected", "cannot exclude",
    "may represent", "questionable", "equivocal", "likely", "no definite", "not definite",
    "posible", "probable", "sospecha", "no se puede excluir", "dudoso",
    "possible", "probable", "suspect", "ne peut exclure",
    "mogelijk", "verdacht", "vermoeden",
    "moglich", "verdachtig", "fraglich", "vereinbar mit",
    "muhtemel", "olasi", "supheli", "dusundurmustur",
    "moguce", "vjerojatno", "sumnja", "suspektno",
    "πιθαν", "υποπτ",
    "възмож", "вероят", "суспект",
)

NORMALITY_TERMS = (
    "normal", "intact", "preserved", "unremarkable", "within normal limits",
    "conservado", "conservada", "integro", "integra", "normalidad",
    "normal", "intact", "conserve",
    "normaal", "intact", "gaaf",
    "regelrecht", "unauffallig", "intakt",
    "normaldir", "dogal", "korunmus",
    "uredan", "uredna", "uredni", "ocuvan", "ocuvana", "intaktan",
    "φυσιολογ", "ακεραι",
    "нормал", "запазен", "съхранен",
)

PATHOLOGY_TERMS = (
    "tear", "torn", "rupture", "disruption", "avulsion", "sprain", "injury",
    "degeneration", "degenerative", "mucoid", "fraying", "lesion", "abnormal signal",
    "rotura", "ruptura", "desgarro", "lesion", "degeneracion", "esguince",
    "dechirure", "rupture", "lesion", "degenerescence",
    "scheur", "ruptuur", "degeneratie", "letsel",
    "riss", "einriss", "ruptur", "lasion", "degeneration",
    "yirtik", "yirtigi", "ruptur", "dejenerasyon", "zorlanma", "hasar",
    "ruptura", "puknuce", "lezija", "degenerativ", "ozljeda",
    "ρηξη", "ρηγμα", "εκφυλ", "βλαβ",
    "руптура", "разкъс", "разрив", "скъс", "увред", "дегенерат",
)

OA_TERMS = (
    "osteoarthritis", "osteoarthrosis", "arthrosis", "degenerative joint disease",
    "chondrosis", "chondropathy", "chondromalacia", "cartilage loss", "cartilage defect",
    "joint space narrowing", "osteophyte", "full thickness cartilage",
    "artrosis", "osteoartrosis", "condrosis", "condropatia", "condromalacia",
    "perdida condral", "desgaste condral", "pinzamiento articular", "osteofito",
    "arthrose", "chondropathie", "chondromalacie", "perte cartilagineuse",
    "artrose", "chondropathie", "kraakbeenverlies", "kraakbeendefect",
    "arthrose", "chondropathie", "chondromalazie", "knorpeldefekt", "knorpelverlust",
    "artroz", "osteoartrit", "kondropati", "kondromalazi", "kikirdak kaybi",
    "artroza", "gonartroza", "hondropat", "hondromal", "defekt hrskavice",
    "οστεοαρθ", "χονδροπαθ", "χονδρομαλακ", "απωλεια χονδρου",
    "остеоарт", "артроз", "хондропат", "хондромалац", "хрущялен дефект",
)

ANATOMY_TERMS = {
    "ACL": (
        "acl", "anterior cruciate ligament", "ligamento cruzado anterior",
        "ligament croise anterieur", "voorste kruisband", "vorderes kreuzband",
        "on capraz bag", "prednji krizni ligament", "prednji ukrsteni ligament",
        "προσθιος χιαστος", "предна кръстна връзка", "передняя крестообразная",
    ),
    "MCL": (
        "mcl", "medial collateral ligament", "ligamento colateral medial",
        "ligament collateral medial", "mediale collaterale band", "innenband",
        "mediales kollateralband", "medial kollateral ligaman", "ic yan bag",
        "medijalni kolateralni ligament", "εσω πλαγιος συνδεσμος",
        "медиална колатерална връзка", "медиальная коллатеральная",
    ),
    "Medial Meniscus": (
        "medial meniscus", "medial meniscal", "menisco medial", "menisco interno",
        "menisque medial", "menisque interne", "mediale meniscus", "innenmeniskus",
        "medial meniskus", "medyal meniskus", "medijalni menisk",
        "εσω μηνισκος", "медиален менискус", "медиальный мениск",
    ),
    "Lateral Meniscus": (
        "lateral meniscus", "lateral meniscal", "menisco lateral", "menisco externo",
        "menisque lateral", "menisque externe", "laterale meniscus", "aussenmeniskus",
        "lateral meniskus", "lateralni menisk", "εξω μηνισκος",
        "латерален менискус", "латеральный мениск",
    ),
    "Medial OA": (
        "medial compartment", "medial femorotibial", "medial tibiofemoral",
        "compartimento medial", "femorotibial medial", "compartiment medial",
        "mediale compartiment", "mediaal compartiment", "mediales kompartiment",
        "medial kompartman", "medijalni kompartment", "medijalnog kompartmenta",
        "εσω διαμερισμα", "медиален компартмент", "медиалния отдел",
    ),
    "Lateral OA": (
        "lateral compartment", "lateral femorotibial", "lateral tibiofemoral",
        "compartimento lateral", "femorotibial lateral", "compartiment lateral",
        "laterale compartiment", "lateraal compartiment", "laterales kompartiment",
        "lateral kompartman", "lateralni kompartment", "lateralnog kompartmenta",
        "εξω διαμερισμα", "латерален компартмент", "латералния отдел",
    ),
    "PF OA": (
        "patellofemoral", "patello femoral", "retropatellar", "patellar cartilage",
        "femoropatelar", "patelofemoral", "retropatelar", "cartilago patelar",
        "femoropatellaire", "retropatellaire", "patellofemoraal", "retropatellair",
        "femoropatellar", "retropatellar", "patellofemoral eklem",
        "patelofemoralnog", "patelofemoralni", "επιγονατιδομηριαι",
        "пателофеморал", "ретропателар",
    ),
}

DIRECT_TERMS = {
    "Effusion": (
        "effusion", "joint fluid", "joint collection", "hydrops",
        "derrame", "liquido articular", "derrame articular",
        "epanchement", "hydarthrose", "vocht", "gewrichtsvocht",
        "gelenkerguss", "erguss", "eklem ici sivi", "eklem sivisi", "mayii artisi",
        "izljev", "izljeva", "zglobni izljev", "συλλογη υγρου", "υδραρθρο",
        "ставен излив", "излив в ставата", "суставной выпот",
    ),
    "Synovitis": (
        "synovitis", "synovial hypertrophy", "synovial thickening", "synovial proliferation",
        "sinovitis", "hipertrofia sinovial", "engrosamiento sinovial",
        "synovite", "hypertrophie synoviale", "synoviale hypertrofie",
        "synoviale verdikking", "synovitis", "synoviale hypertrophie",
        "sinovit", "sinovyal hipertrofi", "sinovijalna hipertrofija",
        "υμενιτιδα", "υμενικ", "синовит", "синовиална хипертрофия",
    ),
    "Baker's": (
        "baker cyst", "baker's cyst", "popliteal cyst", "quiste de baker",
        "quiste popliteo", "kyste de baker", "kyste poplite", "bakercyste",
        "popliteale cyste", "baker zyste", "poplitealzyste", "baker kisti",
        "popliteal kist", "bakerova cista", "poplitealna cista", "κυστη baker",
        "ιγνυακη κυστη", "киста на бейкър", "подколенная киста",
    ),
    "Contusion": (
        "bone contusion", "bone bruise", "osseous contusion", "traumatic marrow edema",
        "contusion osea", "edema oseo traumatico", "contusion osseuse",
        "bone bruise", "botcontusie", "knochenkontusion", "bone bruise",
        "kemik kontuzyonu", "kontuzija kosti", "kostana kontuzija",
        "οστικη θλαση", "οστικη κακωση", "костна контузия", "костный ушиб",
    ),
    "Fracture": (
        "fracture", "fractura", "fracture", "breuk", "fraktur", "kirik",
        "prijelom", "fraktura", "καταγμα", "фрактура", "счупване", "перелом",
    ),
}

# Clauses in these sections are not diagnostic assertions.
NON_DIAGNOSTIC_HEADERS = (
    "clinical history", "history", "indication", "clinical information", "reason for exam",
    "antecedentes", "indicacion", "informacion clinica", "motivo",
    "renseignements cliniques", "indication clinique", "klinische inlichtingen",
    "fragestellung", "anamnese", "klinik bilgi", "endikasyon",
    "klinicki podaci", "indikacija", "κλινικ", "анамнеза", "индикация",
    "technique", "tecnica", "techniek", "technik", "teknik", "протокол",
)

DIAGNOSTIC_HEADERS = (
    "findings", "impression", "conclusion", "results",
    "hallazgos", "resultados", "impresion", "conclusion",
    "constatations", "conclusion", "bevindingen", "conclusie",
    "befund", "beurteilung", "bulgular", "sonuc", "nalaz", "zakljucak",
    "ευρηματα", "συμπερασμα", "находка", "заключение",
)

LANGUAGE_MARKERS = {
    "english": (" findings", " impression", " without ", " no evidence", " knee "),
    "spanish": (" hallazgos", " rodilla", " ligamento cruzado", " derrame", " sin signos"),
    "french": (" constatations", " genou", " aucune", " sans ", " ligament croise"),
    "dutch": (" bevindingen", " kruisband", " geen ", " knie links", " knie rechts"),
    "german": (" kniegelenk", " kreuzband", " keine ", " gelenkerguss", " regelrecht"),
    "turkish": (" bulgular", " diz ", " capraz bag", " eklem", " yoktur"),
    "south_slavic": (" nalaz", " koljena", " koljenu", " uredan", " vidi se"),
}
