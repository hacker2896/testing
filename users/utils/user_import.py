import re
import secrets
import string
from unidecode import unidecode


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = unidecode(s)  # To‘lqin -> Tolqin
    s = re.sub(r"[^a-zA-Z\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _first_letter(s: str) -> str:
    s = _norm(s)
    return s[0].lower() if s else "x"


def make_base_username(first_name: str, patronymic: str, last_name: str) -> str:
    f = _first_letter(first_name)
    p = _first_letter(patronymic)
    ln = _norm(last_name).replace(" ", "").replace("-", "").lower() or "user"
    return f"{f}.{p}.{ln}"


def pick_username(UserModel, base: str) -> str:
    if not UserModel.objects.filter(username=base).exists():
        return base
    for i in range(1, 100):
        cand = f"{base}{i:02d}"
        if not UserModel.objects.filter(username=cand).exists():
            return cand
    return f"{base}{secrets.randbelow(100):02d}"


def generate_password_8() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))
