"""Ukrainian -> Latin, official national transliteration (Cabinet of Ministers resolution No. 55, 2010), for showing
hromada names on the English site (D58). Example: "Липецька територіальна громада" -> "Lypetska hromada"."""
import re

_MAP = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh", "з": "z", "и": "y",
        "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s",
        "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "ю": "iu", "я": "ia",
        "'": "", "’": "", "ʼ": ""}
_FIRST = {"є": "ye", "ї": "yi", "й": "y", "ю": "yu", "я": "ya"}  # at the start of a word


def translit_word(w):
    out, low = [], w.lower().replace("зг", "\0")  # "зг" -> "zgh" (Згурівка -> Zghurivka)
    for k, ch in enumerate(low):
        if ch == "\0":
            out.append("zgh")
        elif k == 0 and ch in _FIRST:
            out.append(_FIRST[ch])
        else:
            out.append(_MAP.get(ch, ch))
    s = "".join(out)
    return s[:1].upper() + s[1:] if w[:1].isupper() else s


def translit(text):
    return re.sub(r"[А-Яа-яІіЇїЄєҐґ'’ʼ]+", lambda m: translit_word(m.group(0)), text)


def hromada_en(name):
    """English label of a hromada/city: 'Липецька територіальна громада' -> 'Lypetska hromada', 'м. Харків' -> 'Kharkiv city',
    'м. Харків та Харківська територіальна громада' -> 'Kharkiv city and Kharkivska hromada'."""
    parts = []
    for p in str(name).split(" та "):
        p = p.strip()
        if p.startswith("м. "):
            parts.append(f"{translit(p[3:])} city")
        else:
            parts.append(translit(re.sub(r"\s*(територіальна\s+)?громада$", "", p)) + " hromada")
    return " and ".join(parts)


def hromada_uk(name):
    """Short Ukrainian label: 'Липецька територіальна громада' -> 'Липецька громада'."""
    return re.sub(r"територіальна\s+громада", "громада", str(name))
