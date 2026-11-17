"""Gera os arquivos traduzidos instalados pelo pacote Debian (debian/rules):

  <destdir>/usr/share/locale/<lang>/LC_MESSAGES/pkg-manager-gui.mo
  <destdir>/usr/share/applications/pkg-manager-gui.desktop
  <destdir>/usr/share/polkit-1/actions/br.com.aratie.appimagemanagerbackend.policy

Uso: python3 build.py <destdir>   (requer gettext)
"""
import os
import re
import subprocess
import sys

POLICY_FILE = "br.com.aratie.appimagemanagerbackend.policy"
DESKTOP_FILE = "pkg-manager-gui.desktop"


def build_translations(working_dir: str):
    """Compila os catálogos (.mo) e gera .desktop/polkit traduzidos (requer gettext)."""
    env = dict(os.environ)
    env["GETTEXTDATADIRS"] = os.path.abspath("po") + (
        ":" + env["GETTEXTDATADIRS"] if env.get("GETTEXTDATADIRS") else "")
    for d in ("usr/share/applications", "usr/share/polkit-1/actions"):
        os.makedirs(os.path.join(working_dir, d), exist_ok=True)
    subprocess.run(["po/i18n.sh", "validate"], check=True)
    subprocess.run(["po/i18n.sh", "compile",
                   f"{working_dir}/usr/share/locale"], check=True)
    subprocess.run(["msgfmt", "--desktop", f"--template={DESKTOP_FILE}.in", "-d", "po",
                   "-o", f"{working_dir}/usr/share/applications/{DESKTOP_FILE}"],
                   check=True, env=env)
    policy = f"{working_dir}/usr/share/polkit-1/actions/{POLICY_FILE}"
    subprocess.run(["msgfmt", "--xml", f"--template={POLICY_FILE}.in", "-d", "po",
                   "-o", policy], check=True, env=env)
    posix_xml_lang(policy)


def posix_xml_lang(path: str):
    """msgfmt writes BCP 47 tags (xml:lang="pt-BR"), but polkit looks up
    g_get_locale_variants() of the session locale: pt_BR.UTF-8, pt_BR, pt.
    A hyphenated tag never matches, so convert language-region to POSIX."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # zh-Hans-CN / zh-Hant-TW (language-script-region) -> zh_CN / zh_TW
    text = re.sub(r'xml:lang="([a-z]{2,3})-(?:[A-Z][a-z]{3}-)?([A-Z]{2})"', r'xml:lang="\1_\2"', text)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build_translations(sys.argv[1])
