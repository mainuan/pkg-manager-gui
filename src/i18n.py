"""Internacionalização do pkg-manager-gui.

Domínio gettext = nome do pacote Debian (``pkg-manager-gui``). Os textos-fonte
são em inglês; a interface brasileira vem de ``po/pt_BR.po``. O idioma nunca é
forçado: segue ``LANGUAGE``/``LC_ALL``/``LC_MESSAGES``/``LANG``.

Catálogos procurados em, nesta ordem:
1. ``$PKG_MANAGER_GUI_LOCALEDIR``;
2. ``<repositório>/build/locale`` (execução a partir do código-fonte,
   ``po/i18n.sh compile build/locale``);
3. ``/usr/share/locale`` (pacote instalado; explícito porque o binário
   PyInstaller tem ``sys.base_prefix`` dentro do diretório temporário).
"""
import gettext
import os
import sys

TEXTDOMAIN = "pkg-manager-gui"
SYSTEM_LOCALEDIR = "/usr/share/locale"


def _find_localedir() -> str:
    env_dir = os.environ.get("PKG_MANAGER_GUI_LOCALEDIR")
    if env_dir:
        return env_dir
    if not getattr(sys, "frozen", False):
        source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "build", "locale")
        if os.path.isdir(source_dir):
            return source_dir
    return SYSTEM_LOCALEDIR


_translation = gettext.translation(TEXTDOMAIN, _find_localedir(), fallback=True)
_ = _translation.gettext
ngettext = _translation.ngettext
pgettext = _translation.pgettext


def install_qt_translator(app):
    """Botões padrão do Qt (QMessageBox etc.) no idioma do sistema."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

    translator = QTranslator(app)
    for path in (QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
                 "/usr/share/qt6/translations"):
        if translator.load(QLocale.system(), "qtbase", "_", path):
            app.installTranslator(translator)
            break
    return translator
