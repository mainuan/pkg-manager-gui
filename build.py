import os
import subprocess
from dotenv import load_dotenv
import sys

load_dotenv()

APP_NAME = os.getenv("APP_NAME")
VERSION = os.getenv("VERSION")
MAINTAINER = os.getenv("MAINTAINER")
POLICY_FILE = "br.com.aratie.appimagemanagerbackend.policy"
DESKTOP_FILE = "pkg-manager-gui.desktop"


def build_translations(working_dir: str):
    """Compila os catálogos (.mo) e gera .desktop/polkit traduzidos (requer gettext)."""
    env = dict(os.environ)
    env["GETTEXTDATADIRS"] = os.path.abspath("po") + (
        ":" + env["GETTEXTDATADIRS"] if env.get("GETTEXTDATADIRS") else "")
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
    import re
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # zh-Hans-CN / zh-Hant-TW (language-script-region) -> zh_CN / zh_TW
    text = re.sub(r'xml:lang="([a-z]{2,3})-(?:[A-Z][a-z]{3}-)?([A-Z]{2})"', r'xml:lang="\1_\2"', text)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def build():
    print("--- Iniciando Build do ELF ---")
    subprocess.run([
        "pyinstaller", "--onefile", "--windowed",
        f"--name={APP_NAME}", "./src/main.py"
    ], check=True)

    print("--- Criando estrutura do pacote DEB ---")
    working_dir = f"/tmp/{APP_NAME}-build"

    if os.path.exists(working_dir):
        subprocess.run(["rm", "-rf", working_dir])

    os.makedirs(f"{working_dir}/DEBIAN", exist_ok=True)
    os.makedirs(f"{working_dir}/usr/bin", exist_ok=True)
    os.makedirs(f"{working_dir}/usr/local/bin", exist_ok=True)
    os.makedirs(f"{working_dir}/usr/share/polkit-1/actions", exist_ok=True)
    os.makedirs(f"{working_dir}/usr/share/applications", exist_ok=True)

    print("--- Copiando arquivos ---")
    subprocess.run(["cp", f"dist/{APP_NAME}",
                   f"{working_dir}/usr/bin/"], check=True)
    subprocess.run(
        ["chmod", "755", f"{working_dir}/usr/bin/{APP_NAME}"], check=True)

    subprocess.run(["cp", "appimage_manager_backend",
                   f"{working_dir}/usr/local/bin/"], check=True)
    subprocess.run(
        ["chmod", "755", f"{working_dir}/usr/local/bin/appimage_manager_backend"], check=True)

    print("--- Gerando traduções, .desktop e polkit ---")
    build_translations(working_dir)

    print("--- Gerando arquivo de controle ---")
    control_content = f"""Package: {APP_NAME}
Version: {VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: {MAINTAINER}
Depends: flatpak, pkexec
Description: {os.getenv("DESCRIPTION")}
"""

    with open(f"{working_dir}/DEBIAN/control", "w") as f:
        f.write(control_content)

    print("--- Gerando script postinst ---")
    postinst_content = """#!/bin/sh
set -e

if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database /usr/share/applications
fi

if [ -x /usr/bin/update-mime-database ]; then
    update-mime-database /usr/share/mime
fi
"""

    postinst_path = f"{working_dir}/DEBIAN/postinst"
    with open(postinst_path, "w") as f:
        f.write(postinst_content)

    subprocess.run(["chmod", "755", postinst_path], check=True)

    os.makedirs("./dist", exist_ok=True)
    print("--- Empacotando .deb ---")
    subprocess.run(["dpkg-deb", "--build", working_dir,
                   f"./dist/{APP_NAME}.deb"], check=True)
    print(f"--- Sucesso: {APP_NAME}.deb gerado! ---")


if __name__ == "__main__":
    build()
