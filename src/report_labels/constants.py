"""Policy constants and multilingual lexicons for report label extraction.

The lexicons intentionally favour precision and auditability over coverage. They are
language-level rules, never study-specific exceptions.
"""

from __future__ import annotations

POLICY_VERSION = "report-label-policy-v2.0.0"
OUTPUT_VERSION = "v2"
POLICY_CONFIG_NAME = "policy_v2.json"
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
    "sin", "no hay", "ausencia de", "ningun", "ninguna", "ni",
    "pas de", "sans", "aucun", "aucune", "absence de",
    "geen", "zonder", "niet",
    "kein", "keine", "keinen", "ohne", "nicht",
    # Turkish / Croatian-Serbian-Bosnian
    "yok", "yoktur", "izlenmedi", "saptanmadi", "saptanmamistir", "mevcut degil", "gozlenmedi",
    "nema", "bez", "nije", "nisu", "ne nalazi se",
    # Greek / Cyrillic
    "δεν", "χωρις", "ουδεν",
    "без", "няма", "липсва", "не се установява", "не се открива",
)

# Only these negators are safe after a target mention. Broad forms such as
# ``izlenmemistir`` are excluded because "the meniscal body is not visualized"
# may itself describe an abnormality.
POSTPOSED_NEGATION_TERMS = (
    "no", "not", "none", "ningun", "ninguna", "aucun", "aucune",
    "niet", "nicht", "yok", "yoktur", "degil", "nema", "nije",
    "saptanmamistir", "δεν", "не", "няма",
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
    "normal", "intact", "preserve", "preserved", "unremarkable", "within normal limits",
    "conservado", "conservada", "conservados", "conservadas",
    "integro", "integra", "integros", "integras", "normalidad", "normales",
    "sin alteraciones", "dentro de limites normales",
    "normal", "intact", "conserve", "intacts", "intactes", "normaux", "normales",
    "sans particularite",
    "normaal", "normale", "intact", "intacte", "gaaf",
    "regelrecht", "regelrechte", "regelrechter", "regelrechtes",
    "unauffallig", "unauffallige", "unauffalliger", "unauffalliges",
    "intakt", "intakte", "intakter", "intaktes",
    "normaldir", "dogal", "dogaldir", "korunmus", "korunmustur", "normal olup",
    "uredan", "uredna", "uredni", "uredne", "uredno", "urednog", "urednih",
    "ocuvan", "ocuvana", "odrzan", "odrzana", "odrzani", "odrzane", "odrzanog",
    "intaktan", "primjeren", "primjerene", "primjereni", "primjerenog", "primjereno",
    "φυσιολογ", "φυσιολογικα", "φυσιολογικος", "φυσιολογικου",
    "εντος του φυσιολογικου", "φυσιολογικα απεικονιζονται", "φυσιολογικοι ελεγχονται",
    "χωρις παθολογικα ευρηματα", "δεν παρατηρουνται παθολογικα ευρηματα", "ακεραι", "ακεραια",
    "нормал", "нормална", "нормален", "нормални", "нормално изобразяване",
    "запазен", "запазена", "запазени", "запазена цялост", "съхранен", "съхранена",
    "интактни", "без особености",
)

PATHOLOGY_TERMS = (
    "tear", "tears", "tearing", "torn", "rupture", "ruptures", "disruption", "avulsion", "sprain", "injury",
    "degeneration", "degenerative", "mucoid", "fraying", "lesion", "abnormal signal",
    "rotura", "roturas", "ruptura", "rupturas", "desgarro", "desgarros", "lesion", "lesiones",
    "degeneracion", "esguince",
    "dechirure", "dechirures", "rupture", "ruptures", "lesion", "lesions", "degenerescence",
    "scheur", "meniscusscheur", "ruptuur", "degeneratie", "letsel",
    "riss", "einriss", "ruptur", "lasion", "degeneration",
    "yirtik", "yirtigi", "ruptur", "dejenerasyon", "meniskopati", "zorlanma", "hasar",
    "ruptura", "puknuce", "lezija", "degeneracija", "mukoidna degeneracija", "degenerativ", "ozljeda",
    "ρηξη", "ρηγμα", "εκφυλιση", "εκφυλιστικη", "μυξοειδη εκφυλιση", "βλαβη",
    "руптура", "разкъсване", "скъсване", "скъсването", "разрив", "лезия", "увреда",
    "дегенеративни изменения", "мукоидна дегенерация",
)

MENISCUS_PATHOLOGY_TERMS = PATHOLOGY_TERMS + (
    "maceration", "blunting", "extrusion", "extruded", "meniscal extrusion",
    "amputacion", "fibrilacion", "meniskal ekstruzyon", "ekstrude", "υπεξαρθρημα",
    "експулсиран",
)

LIGAMENT_PATHOLOGY_TERMS = PATHOLOGY_TERMS + (
    "periligamentous edema", "ligamentous edema", "ligament thickening", "fiber discontinuity",
    "κακωση", "sprain grade", "periligamentoz odem",
)

OA_TERMS = (
    "osteoarthritis", "osteoarthrosis", "arthrosis", "degenerative joint disease",
    "chondrosis", "chondropathy", "chondromalacia", "cartilage loss", "cartilage defect",
    "cartilage defects", "cartilage fissure", "cartilage fissures", "cartilage fissuring",
    "cartilage thinning", "articular cartilage thinning", "thinning articular cartilage",
    "thinning of the cartilage", "chondral defect", "chondral defects", "chondral loss",
    "chondral thinning", "chondral fissure", "chondral fissures", "chondral fissuring",
    "joint space narrowing", "osteophyte", "osteophytes", "full thickness cartilage",
    "artrosis", "osteoartrosis", "condrosis", "condropatia", "condromalacia",
    "perdida condral", "desgaste condral", "defecto condral", "defectos condrales",
    "lesion condral", "lesiones condrales", "adelgazamiento condral", "fisura condral",
    "fisuras condrales", "ulcera condral", "ulceras condrales", "pinzamiento articular",
    "osteofito", "osteofitos",
    "arthrose", "chondropathie", "chondromalacie", "perte cartilagineuse",
    "amincissement du cartilage", "fissuration du cartilage", "perte complete du cartilage",
    "artrose", "chondropathie", "kraakbeenverlies", "kraakbeendefect", "kraakbeendefecten",
    "kraakbeenlijden", "kraakbeenfissuur", "kraakbeenfissuren", "kraakbeenletsel", "kraakbeenletsels",
    "arthrose", "chondropathie", "chondromalazie", "knorpeldefekt", "knorpeldefekte",
    "knorpelverlust", "knorpelschaden", "knorpelirregularitat", "knorpelirregularitaten",
    "knorpelglatze", "knorpelausdunnung", "gelenkspaltverschmalerung",
    "artroz", "gonartroz", "osteoartrit", "osteoartriti", "kondropati", "kondromalazi",
    "kikirdak kaybi", "kikirdakta incelme", "eklem araliginda daralma",
    "eklem mesafesinde daralma", "dejeneratif eklem hastaligi", "dejeneratif artrit",
    "osteokondral defekt",
    "artroza", "gonartroza", "osteoartriticke promjene", "hondropatija", "hondromalacija",
    "defekt hrskavice", "fisure hrskavice", "stanjenje hrskavice", "denudacija hrskavice",
    "οστεοαρθριτιδα", "χονδροπαθεια", "χονδρομαλακια", "απωλεια αρθρικου χονδρου",
    "διαβρωση του αρθρικου χονδρου", "λεπτυνση του αρθρικου χονδρου", "οστεοφυτα",
    "остеоартрит", "артроза", "хондропатия", "хондромалация", "хрущялен дефект",
    "остеохондрална лезия", "изтънен хрущял", "дегенеративни изменения на хрущяла",
)

ANATOMY_TERMS = {
    "ACL": (
        "acl", "lca", "anterior cruciate ligament", "ligamento cruzado anterior",
        "ligament croise anterieur", "voorste kruisband", "vorderes kreuzband",
        "vordere kreuzband", "vorderen kreuzband", "on capraz bag", "on capraz bagda",
        "anterior capraz bag", "anterior capraz bagda", "prednji krizni ligament",
        "prednjeg kriznog ligamenta", "prednji ukrsteni ligament",
        "προσθιος χιαστος", "προσθιος χιαστος συνδεσμος", "προσθιου χιαστου συνδεσμου",
        "προσθιο χιαστο συνδεσμο", "предна кръстна връзка", "предната кръстна връзка",
        "передняя крестообразная",
    ),
    "MCL": (
        "mcl", "lcm", "medial collateral ligament", "ligamento colateral medial",
        "ligament collateral medial", "ligament collateral interne", "ligament medial collateral",
        "mediale collaterale band", "mediale collateral ligament", "medial collateral ligamentous complex",
        "innenband", "mediales kollateralband", "medialen kollateralband", "medial kollateral ligaman",
        "medial kollateral ligamanda", "medial kollateral ligamende", "ic yan bag", "ic yan bagin",
        "medijalni kolateralni ligament", "medijalnog kolateralnog ligamenta",
        "medijalni kolateralni ligamenti", "εσω πλαγιος συνδεσμος", "εσω πλαγιου συνδεσμου",
        "εσω πλαγιο συνδεσμο", "медиална колатерална връзка", "медиалната колатерална връзка",
        "медиальная коллатеральная",
    ),
    "Medial Meniscus": (
        "medial meniscus", "medial meniscal", "menisco medial", "menisco interno",
        "menisque medial", "menisque interne", "mediale meniscus", "innenmeniskus",
        "medial meniskus", "medial meniskuste", "medyal meniskus", "medyal meniskuste",
        "medyal meniskusun", "medijalni menisk", "medijalnog meniska",
        "εσω μηνισκος", "εσω μηνισκου", "εσω μηνισκο", "медиален менискус",
        "медиалния менискус", "медиальный мениск",
    ),
    "Lateral Meniscus": (
        "lateral meniscus", "lateral meniscal", "menisco lateral", "menisco externo",
        "menisque lateral", "menisque externe", "laterale meniscus", "aussenmeniskus",
        "lateral meniskus", "lateral meniskuste", "lateral meniskusun", "lateralni menisk",
        "lateralnog meniska", "εξω μηνισκος", "εξω μηνισκου", "εξω μηνισκο",
        "латерален менискус", "латералния менискус", "латеральный мениск",
    ),
    "Medial OA": (
        "medial compartment", "medial femorotibial", "medial tibiofemoral",
        "compartimento medial", "femorotibial medial", "compartiment medial", "compartiment interne",
        "mediale compartiment", "mediaal compartiment", "mediaal femorotibiaal compartiment",
        "mediales kompartiment", "medialen kompartiment", "medialen femorotibialen",
        "medial kompartman", "medyal femorotibyal kompartman", "tibiofemoral eklem medialde",
        "medijalni kompartment", "medijalnog kompartmenta", "medijalnom kompartmentu",
        "εσω διαμερισμα", "εσω διαμερισματος", "εσω κνημομηριαιο διαμερισμα",
        "εσω μεσαρθριο διαστημα", "медиален компартмент", "медиалния компартмент",
        "медиалния отдел", "медиалната страна на ставата",
    ),
    "Lateral OA": (
        "lateral compartment", "lateral femorotibial", "lateral tibiofemoral",
        "compartimento lateral", "femorotibial lateral", "compartiment lateral", "compartiment externe",
        "laterale compartiment", "lateraal compartiment", "lateraal femorotibiaal compartiment",
        "laterales kompartiment", "lateralen kompartiment", "lateralen femorotibialen",
        "lateral kompartman", "lateral femoral tibyal eklem", "tibiofemoral eklem lateralde",
        "lateralni kompartment", "lateralnog kompartmenta", "lateralnom kompartmentu",
        "εξω διαμερισμα", "εξω διαμερισματος", "εξω κνημομηριαιο διαμερισμα",
        "εξω μεσαρθριο διαστημα", "латерален компартмент", "латералния компартмент",
        "латералния отдел", "латералната страна на ставата",
    ),
    "PF OA": (
        "patellofemoral", "patello femoral", "retropatellar", "patellar cartilage",
        "femoropatelar", "patelofemoral", "retropatelar", "cartilago patelar",
        "femoropatellaire", "retropatellaire", "patellofemoraal", "retropatellair",
        "femoropatellar", "retropatellar", "patellofemoral eklem", "patellafemoral eklem",
        "patelofemoralnog", "patelofemoralni", "femoropatelarnog", "femoropatelarni",
        "επιγονατιδομηριαιο διαμερισμα", "προσθιο διαμερισμα", "χονδρος της επιγονατιδας",
        "пателофеморал", "ретропателар",
    ),
}

DIRECT_TERMS = {
    "Effusion": (
        "effusion", "joint fluid", "joint collection", "hydrops",
        "derrame", "liquido articular", "derrame articular",
        "epanchement", "hydarthrose", "vocht", "gewrichtsvocht",
        "gelenkerguss", "erguss", "eklem ici sivi", "diz eklemi ici sivi", "eklem sivisi",
        "eklemde sivi artisi", "diz eklem mesafesinde sivi artisi", "eklem araliginda efuzyon",
        "eklem mesafesinde efuzyon", "mayii artisi",
        "izljev", "izljeva", "zglobni izljev", "συλλογη υγρου", "ενδαρθρικη συλλογη υγρου",
        "ενδοαρθρικη συλλογη υγρου", "ενδαρθρικη συλλογη", "ενδαρθρικου υγρου",
        "υγρου ενδαρθρικα", "υδραρθρο", "υδραρθρου", "υδραρθρου",
        "ставен излив", "излив в ставата", "суставной выпот",
    ),
    "Synovitis": (
        "synovitis", "synovial hypertrophy", "synovial thickening", "synovial proliferation",
        "sinovitis", "hipertrofia sinovial", "engrosamiento sinovial",
        "synovite", "hypertrophie synoviale", "synoviale hypertrofie",
        "synoviale verdikking", "synovitis", "synoviale hypertrophie",
        "sinovit", "snovit", "sinovyal hipertrofi", "sinovyal kalinlasma", "sinoviumda kalinlasma",
        "sinovijalna hipertrofija",
        "synoviale proliferation", "synoviale proliferationen",
        "υμενιτιδα", "υμενιτιδας", "παχυνση του αρθρικου υμενα", "παχυνση αρθρικου υμενα",
        "синовит", "синовиална хипертрофия", "синовиално задебеляване",
    ),
    "Baker's": (
        "baker cyst", "baker's cyst", "popliteal cyst", "quiste de baker",
        "quiste popliteo", "quistes popliteos", "kyste de baker", "kyste poplite", "kystes poplites", "bakercyste",
        "popliteale cyste", "baker zyste", "bakerzyste", "poplitealzyste", "baker kisti",
        "popliteal cysts", "popliteal kist", "bakerova cista", "bakerove ciste",
        "poplitealna cista", "poplitealne ciste", "κυστη baker",
        "ιγνυακη κυστη", "κυστης baker", "киста на бейкър", "бекерова киста",
        "поплитеална киста", "подколенная киста",
    ),
    "Contusion": (
        "bone contusion", "bone contusions", "bone bruise", "osseous contusion", "traumatic marrow edema",
        "contusion osea", "contusiones oseas", "edema oseo traumatico",
        "contusion osseuse", "contusions osseuses",
        "bone bruise", "botcontusie", "knochenkontusion", "bone bruise",
        "kemik kontuzyonu", "kemik kontuzyonlari", "kontuzyonel", "kontuzija kosti",
        "kostana kontuzija", "kontuzijski biljeg", "kontuzione promjene",
        "οστικη θλαση", "οστικες θλασεις", "οστικος μωλωπας", "οστικο μωλωπα",
        "костна контузия", "костни контузии", "костный ушиб",
    ),
    "Fracture": (
        "fracture", "fractures", "fracturing", "fractura", "fracturas", "breuk", "fractuur",
        "fracturen", "fraktur", "frakturen", "kirik", "kiriklar", "mikro frakturler",
        "prijelom", "prijeloma", "prijelomi", "fraktura", "frakture", "frakturi",
        "καταγμα", "καταγματος", "καταγματα", "καταγματων", "фрактура", "фрактури",
        "счупване", "счупвания", "перелом",
    ),
}

# Group-level anatomy is evaluated separately because positive propagation is
# not always safe. A normal whole group can exclude a member target; a group-level
# injury may still be ambiguous about which member is abnormal.
COLLECTIVE_TERMS = {
    "both_menisci": {
        "targets": ("Medial Meniscus", "Lateral Meniscus"),
        "terms": (
            "ambos meniscos", "menisco medial y lateral", "meniscos medial y lateral",
            "menisco interno y lateral", "meniscos interno y externo",
            "both menisci", "medial and lateral menisci", "medial and lateral meniscus",
            "medial meniscus, the lateral meniscus", "medial meniscus and lateral meniscus",
            "menisques interne et externe", "menisque interne, le menisque externe",
            "normaal voorkomen menisci",
            "normaal voorkomende menisci", "menisci intakt", "menisken intakt",
            "innenmeniskus und aussenmeniskus", "medyal ve lateral meniskus",
            "medial ve lateral meniskus", "medial meniskus ve lateral meniskus",
            "lateral meniskus ve medial meniskus",
            "medial ve lateral meniskuste", "oba meniska", "oba meniskusa", "μηνισκοι",
        ),
        "pathology_terms": MENISCUS_PATHOLOGY_TERMS,
        "allow_positive": True,
        "allow_uncertain": True,
    },
    "both_menisci_negative_only": {
        "targets": ("Medial Meniscus", "Lateral Meniscus"),
        "terms": (
            "meniscos", "les menisques", "menisci", "menisken", "meniskusler",
            "meniskusi", "менискусите",
        ),
        "pathology_terms": MENISCUS_PATHOLOGY_TERMS,
        "allow_positive": False,
        "allow_uncertain": False,
    },
    "cruciate_ligaments": {
        "targets": ("ACL",),
        "terms": (
            "ligamentos cruzados", "cruciate ligaments", "ligaments croises anterieur et posterieur",
            "kruisbanden", "kreuzbander", "vorderes und hinteres kreuzband",
            "capraz baglar", "prednjeg i straznjeg kriznog ligamenta", "kriznih ligamenata",
            "χιαστοι συνδεσμοι", "χιαστων συνδεσμων", "χιαστοι και πλαγιοι συνδεσμοι",
            "πλαγιοι και χιαστοι συνδεσμοι", "кръстните връзки", "кръстни връзки",
            "предната и задната кръстна връзка", "кръстните връзки",
        ),
        "pathology_terms": LIGAMENT_PATHOLOGY_TERMS,
        "allow_positive": False,
        "allow_uncertain": False,
    },
    "collateral_ligaments": {
        "targets": ("MCL",),
        "terms": (
            "ligamentos colaterales", "collateral ligaments", "collaterale banden", "laterale banden",
            "kollateralbander", "yan baglar", "kolateralnih ligamenata", "kolateralni ligamenti",
            "χιαστοι και πλαγιοι συνδεσμοι", "πλαγιων συνδεσμων", "πλαγιοι συνδεσμοι",
            "πλαγιοι και χιαστοι συνδεσμοι", "колатерални лигаменти",
            "колатералните лигаменти", "двата колатерални лигамента",
        ),
        "pathology_terms": LIGAMENT_PATHOLOGY_TERMS,
        "allow_positive": False,
        "allow_uncertain": False,
    },
    "cruciate_and_collateral_ligaments": {
        "targets": ("ACL", "MCL"),
        "terms": (
            "ligamentos cruzados y colaterales", "cruciate and collateral ligaments",
            "acl, pcl, mcl and lcl", "acl, pcl, mcl, lcl",
            "anterior cruciate ligament, posterior cruciate ligament, medial collateral ligament and lateral collateral ligament",
            "anterior cruciate ligament, the posterior cruciate ligament, the medial collateral ligament",
            "ligament croise anterieur, le ligament croise posterieur",
            "on capraz bag ve arka capraz bag, lateral ve medial kollateral ligaman",
            "kriznih i kolateralnih ligamenata",
            "prednjeg i straznjeg kriznog ligamenta i kolateralnih ligamenata",
            "χιαστοι και πλαγιοι συνδεσμοι", "χιαστων και πλαγιων συνδεσμων",
        ),
        "pathology_terms": LIGAMENT_PATHOLOGY_TERMS,
        "allow_positive": False,
        "allow_uncertain": False,
    },
    "tibiofemoral_compartments": {
        "targets": ("Medial OA", "Lateral OA"),
        "terms": (
            "compartimentos femorotibiales", "ambos compartimentos femorotibiales",
            "both tibiofemoral compartments", "tibiofemoral compartments",
            "medial and lateral tibiofemoral", "medial ve lateral tibiofemoral",
            "medijalnog i lateralnog kompartmenta", "medijalni i lateralni kompartment",
            "εσω και εξω διαμερισμα", "εσω και εξω διαμερισματος",
            "медиалния и латералния компартмент",
        ),
        "pathology_terms": OA_TERMS,
        "allow_positive": True,
        "allow_uncertain": True,
    },
    "lateral_and_patellofemoral_compartments": {
        "targets": ("Lateral OA", "PF OA"),
        "terms": (
            "lateral tibiofemoral and patellofemoral", "lateral compartment and patellofemoral",
            "lateral and patellofemoral compartments",
        ),
        "pathology_terms": OA_TERMS,
        "allow_positive": True,
        "allow_uncertain": True,
    },
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
    "english": (
        " findings", " impression", " without ", " no evidence", " knee ",
        " technique: mri", " medial meniscus", " lateral meniscus",
    ),
    "spanish": (" hallazgos", " rodilla", " ligamento cruzado", " derrame", " sin signos"),
    "french": (" constatations", " genou", " aucune", " sans ", " ligament croise"),
    "dutch": (" bevindingen", " kruisband", " geen ", " knie links", " knie rechts"),
    "german": (
        " kniegelenk", " kreuzband", " keine ", " gelenkerguss", " regelrecht",
        " knorpel", " innenmeniskus", " kompartiment",
    ),
    "turkish": (
        " bulgular", " diz ", " capraz bag", " eklem", " yoktur", " meniskus", " izlenmistir",
    ),
    "south_slavic": (
        " nalaz", " koljena", " koljenu", " uredan", " vidi se", " hrskavice",
        " medijalnog", " kriznog ligamenta", " kostani", " kompartmenta",
    ),
}
