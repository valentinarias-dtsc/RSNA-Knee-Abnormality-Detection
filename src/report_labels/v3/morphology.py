"""Corpus-observed, bounded morphology rules for v3.

Rules use target-specific contexts and explicit exclusions.  They are not a
general stemmer and do not infer findings from broad proxies such as marrow
edema or the word ``synovial`` alone.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MorphRule:
    name: str
    target: str
    language: str
    phenotype: str
    pattern: str
    exclusions: tuple[str, ...] = ()

    def compiled(self) -> re.Pattern[str]:
        return re.compile(self.pattern)


def _rule(name: str, target: str, language: str, phenotype: str, pattern: str, *exclusions: str) -> MorphRule:
    return MorphRule(name, target, language, phenotype, pattern, tuple(exclusions))


DIRECT_RULES: tuple[MorphRule, ...] = (
    # Effusion: only intra-articular fluid/effusion formulations observed in the corpus.
    _rule("effusion_en_plural", "Effusion", "english", "joint_effusion", r"\b(?:joint\s+)?effusions?\b"),
    _rule("effusion_tr_root", "Effusion", "turkish", "joint_effusion", r"\b(?:efuzyon\w*|eklem.{0,35}sivi\w*(?:\s+(?:miktar\w*|artis\w*|fazlalig\w*))?)"),
    _rule("effusion_de_root", "Effusion", "german", "joint_effusion", r"\b(?:gelenkerguss\w*|ergussbildung\w*)"),
    _rule("effusion_el_root", "Effusion", "greek_script", "joint_effusion", "\\b(?:\u03c5\u03b4\u03c1\u03b1\u03c1\u03b8\u03c1\\w*|\u03b5\u03bd\u03b4\\w*.{0,30}\u03c5\u03b3\u03c1\\w*)"),
    # Baker: anatomical name/derivative required. Generic popliteal masses stay unknown.
    _rule("baker_variants", "Baker's", "english", "baker_cyst", r"\bbaker\w*.{0,20}(?:cyst\w*|kist\w*|zyst\w*|quiste\w*|cista\w*)"),
    _rule("baker_sl", "Baker's", "south_slavic", "baker_cyst", r"\bbaker\w*.{0,15}cist\w*"),
    _rule("baker_nl", "Baker's", "dutch", "baker_cyst", r"\bbaker(?:se|s)?\s+cyst\w*"),
    _rule("baker_el", "Baker's", "greek_script", "baker_cyst", "(?:\u03ba\u03c5\u03c3\u03c4\\w*.{0,20}baker|baker.{0,20}\u03ba\u03c5\u03c3\u03c4\\w*)"),
    # Synovitis: explicit inflammation or synovial thickening/proliferation only.
    _rule("synovitis_de", "Synovitis", "german", "synovitis", r"\b(?:synovit\w*|synovial\w*.{0,45}(?:hypertroph\w*|verdick\w*|prolifer\w*))", "tenosynov", "zyst", "plica"),
    _rule("synovitis_el", "Synovitis", "greek_script", "synovitis", "\\b(?:\u03c5\u03bc\u03b5\u03bd\u03b9\u03c4\\w*|\u03c0\u03b1\u03c7\u03c5\u03bd\\w*.{0,60}\u03c5\u03bc\u03b5\u03bd\\w*)", "\u03ba\u03c5\u03c3\u03c4", "\u03c0\u03c4\u03c5\u03c7"),
    _rule("synovitis_sl", "Synovitis", "south_slavic", "synovitis", r"\b(?:sinovit\w*|sinovij\w*.{0,45}(?:hipertrof\w*|zadeblj\w*))", "cista", "plika"),
    _rule("synovitis_tr", "Synovitis", "turkish", "synovitis", r"\b(?:sinovit\w*|snovit\w*|sinov\w*.{0,45}(?:kalinla\w*|hipertrof\w*))", "kist", "plika"),
    # Explicit contusion/bruise. Generic marrow edema is intentionally absent.
    _rule("contusion_en", "Contusion", "english", "bone_contusion", r"\b(?:bone\s+bruis\w*|osseous\s+contusion\w*|bone\s+contusion\w*)"),
    _rule("contusion_tr", "Contusion", "turkish", "bone_contusion", r"\bkontuz\w*"),
    _rule("contusion_sl", "Contusion", "south_slavic", "bone_contusion", r"\b(?:kontuz\w*|nagnjec\w*)"),
    _rule("contusion_el", "Contusion", "greek_script", "bone_contusion", "\\b(?:\u03bf\u03c3\u03c4\u03b9\u03ba\\w+.{0,30})?(?:\u03b8\u03bb\u03b1\u03c3\\w*|\u03bc\u03c9\u03bb\u03c9\u03c0\\w*)"),
    _rule("contusion_cyr", "Contusion", "cyrillic_script", "bone_contusion", "\\b(?:\u043a\u043e\u0441\u0442\u043d\\w+.{0,30})?(?:\u043a\u043e\u043d\u0442\u0443\u0437\\w*|\u0443\u0448\u0438\u0431\\w*)"),
    # Explicit fracture morphology and compounds.
    _rule("fracture_en", "Fracture", "english", "fracture", r"\bfractur\w*"),
    _rule("fracture_de", "Fracture", "german", "fracture", r"\bfraktur\w*"),
    _rule("fracture_fr", "Fracture", "french", "fracture", r"\bfractur\w*"),
    _rule("fracture_tr", "Fracture", "turkish", "fracture", r"\b(?:kirik\w*|fraktur\w*)"),
    _rule("fracture_sl", "Fracture", "south_slavic", "fracture", r"\b(?:fraktur\w*|prijelom\w*|prelom\w*)"),
    _rule("fracture_el", "Fracture", "greek_script", "fracture", "\\b\u03ba\u03b1\u03c4\u03b1\u03b3\\w*"),
    _rule("fracture_cyr", "Fracture", "cyrillic_script", "fracture", "\\b(?:\u0444\u0440\u0430\u043a\u0442\u0443\u0440\\w*|\u0441\u0447\u0443\u043f\\w*|\u043f\u0435\u0440\u0435\u043b\u043e\u043c\\w*)"),
)


# Target-aware OA roots. Anatomy and pathology are matched separately and must
# participate in the same proposition.
OA_ANATOMY_PATTERNS: dict[str, str] = {
    "Medial OA": (
        r"(?:\bmedial\w*.{0,35}(?:compart\w*|femorotib\w*|tibiofem\w*)|"
        r"\bmediaal\w*.{0,35}(?:compartiment\w*|femorotibiaal\w*)|"
        r"\bmedijaln\w*.{0,35}(?:kompartment\w*|femorotibijal\w*)|"
        r"\bmed(?:ial|yal)\w*.{0,35}(?:kompartman\w*|femorotibyal\w*)|"
        "\u03b5\u03c3\u03c9.{0,35}(?:\u03b4\u03b9\u03b1\u03bc\u03b5\u03c1\u03b9\u03c3\u03bc|\u03ba\u03bd\u03b7\u03bc\u03bf\u03bc\u03b7\u03c1\u03b9\u03b1\u03b9)|"
        "\u043c\u0435\u0434\u0438\u0430\u043b\\w*.{0,35}(?:\u043a\u043e\u043c\u043f\u0430\u0440\u0442\\w*|\u043e\u0442\u0434\u0435\u043b\\w*))"
    ),
    "Lateral OA": (
        r"(?:\blateral\w*.{0,35}(?:compart\w*|femorotib\w*|tibiofem\w*)|"
        r"\blateraal\w*.{0,35}(?:compartiment\w*|femorotibiaal\w*)|"
        r"\blateraln\w*.{0,35}(?:kompartment\w*|femorotibijal\w*)|"
        r"\blateral\w*.{0,35}(?:kompartman\w*|femorotibyal\w*)|"
        "\u03b5\u03be\u03c9.{0,35}(?:\u03b4\u03b9\u03b1\u03bc\u03b5\u03c1\u03b9\u03c3\u03bc|\u03ba\u03bd\u03b7\u03bc\u03bf\u03bc\u03b7\u03c1\u03b9\u03b1\u03b9)|"
        "\u043b\u0430\u0442\u0435\u0440\u0430\u043b\\w*.{0,35}(?:\u043a\u043e\u043c\u043f\u0430\u0440\u0442\\w*|\u043e\u0442\u0434\u0435\u043b\\w*))"
    ),
    "PF OA": (
        r"(?:\bpatell?o?femoral\w*|\bfemoropatel\w*|\bretropatel\w*|\btrochle\w*|"
        r"\bpatell?ar?\w*.{0,30}(?:cartilage\w*|kikirdak\w*|knorpel\w*|kraakbeen\w*)|"
        r"\b(?:cartilag|hrskavic)\w*.{0,30}patel\w*|"
        "\u03b5\u03c0\u03b9\u03b3\u03bf\u03bd\u03b1\u03c4\u03b9\u03b4\u03bf\u03bc\u03b7\u03c1\u03b9\u03b1\u03b9|"
        "\u03c7\u03bf\u03bd\u03b4\u03c1\\w*.{0,30}\u03b5\u03c0\u03b9\u03b3\u03bf\u03bd\u03b1\u03c4\\w*|"
        "\u043f\u0430\u0442\u0435\u043b\u043e\u0444\u0435\u043c\u043e\u0440\\w*|\u0440\u0435\u0442\u0440\u043e\u043f\u0430\u0442\u0435\u043b\\w*|"
        "\u0445\u0440\u0443\u0449\u044f\u043b\\w*.{0,30}\u043f\u0430\u0442\u0435\u043b\\w*)"
    ),
}

OA_PATHOLOGY_PATTERN = (
    r"(?:\bosteoarthr\w*|\barthros\w*|\bartroz\w*|\bgonartroz\w*|"
    r"\bchondr(?:osis|opath\w*|omal\w*)|\bcondr(?:osis|opat\w*|omal\w*)|"
    r"\bhondr(?:opat\w*|omal\w*)|\bkondr(?:opat\w*|omal\w*)|"
    r"(?:cartilage|chondral|cartilag|condral|kraakbeen|knorpel|hrskavic|kikirdak)\w*.{0,35}"
    r"(?:loss|defect|fissur|thinn|denud|perd|desgast|lesion|adelgaz|ulcer|verlies|schaden|ausdunn|stanjen|reduc|ostec|kayb|incel)|"
    r"\bosteophyt\w*|\bosteofit\w*|\bosteofyt\w*|"
    "\u03bf\u03c3\u03c4\u03b5\u03bf\u03b1\u03c1\u03b8\u03c1\\w*|\u03c7\u03bf\u03bd\u03b4\u03c1\u03bf(?:\u03c0\u03b1\u03b8|\u03bc\u03b1\u03bb\u03b1\u03ba)\\w*|"
    "(?:\u03bb\u03b5\u03c0\u03c4\u03c5\u03bd|\u03b1\u03c0\u03c9\u03bb\u03b5|\u03b4\u03b9\u03b1\u03b2\u03c1)\\w*.{0,30}\u03c7\u03bf\u03bd\u03b4\u03c1\\w*|"
    "\u043e\u0441\u0442\u0435\u043e\u0430\u0440\u0442\u0440\\w*|\u0430\u0440\u0442\u0440\u043e\u0437\\w*|\u0445\u043e\u043d\u0434\u0440\u043e(?:\u043f\u0430\u0442|\u043c\u0430\u043b\u0430\u0446)\\w*|"
    "\u0445\u0440\u0443\u0449\u044f\u043b\\w*.{0,35}(?:\u0434\u0435\u0444\u0435\u043a\u0442|\u0438\u0437\u0442\u044a\u043d|\u0438\u0437\u043d\u043e\u0441|\u0440\u0435\u0434\u0443\u0446)\\w*)"
)


STRUCTURAL_ANATOMY_ROOTS: dict[str, str] = {
    "ACL": r"(?:\bacl\b|\blca\b|anterior cruciate ligament|ligamento cruzado anterior|on capraz bag\w*|prednj\w*.{0,20}(?:krizn|ukrsten)\w*.{0,20}ligament\w*)",
    "MCL": r"(?:\bmcl\b|\blcm\b|medial collateral ligament|ligamento colateral medial|medial kollateral ligam\w*|ic yan bag\w*|medijaln\w*.{0,20}kolateraln\w*.{0,20}ligament\w*)",
    "Medial Meniscus": r"(?:medial menisc\w*|menisco (?:medial|interno)|menisque (?:medial|interne)|innenmenisk\w*|medyal menisk\w*|medijaln\w+ men(?:isk|sik)\w*)",
    "Lateral Meniscus": r"(?:lateral menisc\w*|menisco (?:lateral|externo)|menisque (?:lateral|externe)|aussenmenisk\w*|lateral menisk\w*|lateraln\w+ menisk\w*)",
}

LIGAMENT_PATHOLOGY_PATTERN = r"\b(?:tear\w*|torn|ruptur\w*|sprain\w*|injur\w*|avulsion\w*|degener\w*|mucoid\w*|lesion\w*|rotur\w*|desgarr\w*|esguince\w*|yirtik\w*|dejener\w*|lezij\w*|puknuc\w*|ozljed\w*)"
MENISCUS_PATHOLOGY_PATTERN = LIGAMENT_PATHOLOGY_PATTERN + r"|\b(?:macerat\w*|extrus\w*|extrud\w*|blunt\w*|fray\w*|meniskopat\w*)"

NORMAL_PATTERN = r"\b(?:normal\w*|intact\w*|preserv\w*|unremarkable|conservad\w*|integr\w*|sin alteraciones|normaal\w*|regelrecht\w*|unauffallig\w*|intakt\w*|dogal\w*|korunmus\w*|ured\w*|ocuvan\w*|odrzan\w*|primjeren\w*)"

CARTILAGE_PATTERN = (
    r"(?:cartilage|chondral|cartilag|condral|kraakbeen|knorpel|hrskavic|kikirdak|"
    "\u03c7\u03bf\u03bd\u03b4\u03c1|\u0445\u0440\u0443\u0449)"
)

LOCATIVE_MCL_EXCLUSION = re.compile(
    r"\b(?:(?:adjacent to|deep to|beneath|under|along|next to|por debajo de|subyacente a)\s+(?:the\s+)?mcl|"
    r"(?:pod|ispod|uz)\s+mcl)\b"
)

# A finding separated from the target by these relations usually belongs to a
# neighbouring structure (cyst anterior to a meniscus, fluid along the MCL,
# lesion in front of the ACL) rather than to the target itself.
LOCATIVE_BRIDGE = re.compile(
    r"\b(?:adjacent to|abutting|along|around|next to|near|in front of|anterior to|"
    r"posterior to|deep to|beneath|under|extending to|extension to|por delante de|"
    r"junto a|adyacente a|uz|pod|ispod|auf die|vor dem|neben)\b"
)
