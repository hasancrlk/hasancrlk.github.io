"""Medium'a aktarılacak kopyaları üretir: medium/<ad>/index.html

Medium'un "Import a story" aracı:
  - <pre><code> içindeki satır sonlarını birleştiriyor, <code>'suz <pre> + <br> ise
    satırları koruyor;
  - satır başı boşluklarını eritiyor (&nbsp; korunuyor);
  - yalnızca <article> içini alıyor;
  - bir adresi bir kez okuyup önbelleğe alıyor.

Ana sitedeki kod blokları kopyalanınca doğru girinti versin diye dönüşüm yalnızca
bu kopyalarda yapılıyor. Kopyalar canlı siteden üretilir; önce siteyi yayınla.

Kullanım:  python _araclar/medium_kopyasi.py
"""

from __future__ import annotations

import html
import pathlib
import re
import urllib.request

KOK = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://hasancrlk.github.io"

PRE = re.compile(r"<pre><code(?: class=\"[^\"]*\")?>(.*?)</code></pre>", re.S)


def pre_donustur(m: re.Match[str]) -> str:
    satirlar = m.group(1).rstrip("\n").split("\n")
    cikti = []
    for s in satirlar:
        bosluk = len(s) - len(s.lstrip(" "))
        cikti.append("&nbsp;" * bosluk + s[bosluk:])
    return "<pre>" + "<br>".join(cikti) + "</pre>"


def kopya_uret(yol: str, hedef: pathlib.Path) -> None:
    with urllib.request.urlopen(SITE + yol) as r:
        sayfa = r.read().decode("utf-8")
    bas = re.search(r"<head>.*?</head>", sayfa, re.S).group(0)
    makale = re.search(r"<article class=\"yazi\">.*?</article>", sayfa, re.S).group(0)
    makale = PRE.sub(pre_donustur, makale)
    if "<table" in makale:
        print(f"  ! {yol}: tablo var, Medium düşürecek")
    lang = re.search(r'<html lang="([a-z]+)"', sayfa).group(1)
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / "index.html").write_text(
        f"<!doctype html>\n<html lang=\"{lang}\">\n{bas}\n<body>\n<main>\n{makale}\n"
        f"<p>Bu yazının asıl adresi: <a href=\"{SITE}{yol}\">{SITE}{yol}</a></p>\n"
        "</main>\n</body>\n</html>\n",
        encoding="utf-8",
    )
    print(f"  {yol} -> {hedef.relative_to(KOK)}")


def main() -> None:
    for klasor, onek, url_on in (("_projeler", "", "/projeler/"), ("_projects", "en-", "/en/projects/")):
        for md in sorted((KOK / klasor).glob("*.md")):
            kopya_uret(f"{url_on}{md.stem}/", KOK / "medium" / f"{onek}{md.stem}")


if __name__ == "__main__":
    main()
