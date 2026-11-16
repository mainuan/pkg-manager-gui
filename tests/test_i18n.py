#!/usr/bin/env python3
"""Teste de i18n: executa o código real (PySide6, QT_QPA_PLATFORM=offscreen) com
LANGUAGE=pt_BR e LANGUAGE=en/C e compara os textos exibidos.

Nada é instalado/removido: o serviço é falso e os QMessageBox são interceptados.
Executar: python3 tests/test_i18n.py   (requer PySide6 e GNU gettext/msgfmt)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROBE = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication, QMessageBox
from i18n import install_qt_translator
from ui.pkg_manager import PkgManager, PKGAction
from ui.notfound_manager import NotFoundManager

boxes = []
QMessageBox.information = lambda parent, title, text: boxes.append([title, text])
QMessageBox.warning = lambda parent, title, text: boxes.append([title, text])
QMessageBox.critical = lambda parent, title, text: boxes.append([title, text])
def fake_exec(self):
    boxes.append([self.windowTitle(), self.text(), self.informativeText(),
                  [b.text() for b in self.buttons()]])
    return 0
QMessageBox.exec = fake_exec

class FakeService:
    def install(self, ref): raise Exception("boom")
    def uninstall(self, ref): pass

app = QApplication([])
install_qt_translator(app)
out = {}
m = PkgManager(title="T", service=FakeService(), action=PKGAction.INSTALL)
out["checking"] = m.label.text()
out["format"] = m.current_progress.format()
out["cancel"] = m.btn_cancel.text()
try:
    m.start_installation("Foo", "foo.flatpakref")
except SystemExit:
    pass
out["installing"] = m.label.text()
m.start_removal("Foo", "foo")
out["removing"] = m.label.text()
m.on_finished(0); m.on_finished(1)
m.target_name = "Foo"
m.msg_box_install("Foo"); m.msg_box_remove("Foo")
out["boxes"] = boxes
n = NotFoundManager()
out["notfound_title"] = n.windowTitle()
from PySide6.QtWidgets import QLabel, QPushButton
out["notfound_labels"] = [l.text() for l in n.findChildren(QLabel)][1:]
out["notfound_button"] = n.findChild(QPushButton).text()
from PySide6.QtWidgets import QDialogButtonBox
bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
out["qt_close"] = bb.buttons()[0].text()
print(json.dumps(out, ensure_ascii=False))
'''

# install_qt_translator() as main.py calls it, with every Qt translations
# directory replaced by an empty one (no qtbase_<lang>.qm).
DIRECTION_PROBE = r'''
import sys, tempfile
from unittest import mock
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QTranslator
from PySide6.QtWidgets import QApplication
from i18n import install_qt_translator
from ui.notfound_manager import NotFoundManager

app = QApplication([])
with tempfile.TemporaryDirectory() as empty:
    load = QTranslator.load
    with mock.patch.object(QTranslator, "load",
                           lambda self, locale, name, prefix, path: load(self, locale, name, prefix, empty)):
        install_qt_translator(app)
window = NotFoundManager()
print(app.layoutDirection().name, window.isRightToLeft(), window.windowTitle())
'''


class I18nTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import PySide6.QtWidgets  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("PySide6 não disponível")
        cls.tmp = tempfile.mkdtemp()
        subprocess.run([os.path.join(ROOT, "po", "i18n.sh"), "compile", cls.tmp], check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def env(self, language):
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PKG_MANAGER_GUI_LOCALEDIR=self.tmp,
                   PYTHONDONTWRITEBYTECODE="1")
        for var in ("LC_ALL", "LC_MESSAGES"):
            env.pop(var, None)
        env["LANG"] = "C.UTF-8" if language in ("C", "en") else "pt_BR.UTF-8"
        env["LANGUAGE"] = language
        return env

    def probe(self, language):
        r = subprocess.run([sys.executable, "-c", PROBE, os.path.join(ROOT, "src")],
                           env=self.env(language), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def usage(self, language):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "src", "main.py")],
                           env=self.env(language), capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stderr)
        return r.stdout

    def test_pt_BR(self):
        o = self.probe("pt_BR")
        self.assertEqual(o["checking"], "<b>Verificando status...</b>")
        self.assertEqual(o["format"], "Ação atual: %p%")
        self.assertEqual(o["cancel"], "Cancelar")
        self.assertEqual(o["installing"], "<b>Instalando:</b> Foo 😎")
        self.assertEqual(o["removing"], "<b>Removendo:</b> Foo 😥")
        self.assertEqual(o["boxes"], [
            ["Erro", "Falha na instalação: boom"],
            ["Sucesso", "Operação concluída com êxito!"],
            ["Aviso", "A operação foi encerrada ou apresentou erros."],
            ["Confirmação de instalação", "O pacote 'Foo' não está instalado no sistema.",
             "Deseja instala-lo?", ["Instalar", "Cancelar"]],
            ["Aplicativo já instalado", "O pacote 'Foo' já está instalado no sistema.",
             "Deseja removê-lo?", ["Desinstalar", "Cancelar"]],
        ])
        self.assertEqual(o["notfound_title"], "Aviso do Sistema")
        self.assertEqual(o["notfound_labels"], [
            "Formato não Suportado",
            "O tipo de formato de pacote detectado não é compatível com esta versão."])
        self.assertEqual(o["notfound_button"], "Entendi, fechar")
        self.assertEqual(o["qt_close"].replace("&", ""), "Fechar")
        self.assertEqual(self.usage("pt_BR"), "Uso: flatpak-manager-gui <url/arquivo>\n")

    def test_english(self):
        for language in ("en", "C"):
            o = self.probe(language)
            self.assertEqual(o["checking"], "<b>Checking status...</b>")
            self.assertEqual(o["format"], "Current action: %p%")
            self.assertEqual(o["installing"], "<b>Installing:</b> Foo 😎")
            self.assertEqual(o["boxes"][3], [
                "Confirm Installation", "The package 'Foo' is not installed on the system.",
                "Do you want to install it?", ["Install", "Cancel"]])
            self.assertEqual(o["notfound_title"], "System Notice")
            self.assertEqual(o["qt_close"].replace("&", ""), "Close")
            self.assertEqual(self.usage(language), "Usage: flatpak-manager-gui <url/file>\n")

    def direction(self, language):
        r = subprocess.run([sys.executable, "-c", DIRECTION_PROBE, os.path.join(ROOT, "src")],
                           env=self.env(language), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip().splitlines()[-1]

    def test_right_to_left_catalog_mirrors_without_qtbase(self):
        # The application's Arabic catalog is used: mirrored even without qtbase_ar.
        self.assertTrue(self.direction("ar").startswith("RightToLeft True "))
        # Urdu is right-to-left but has no application catalog: English, left to right.
        self.assertTrue(self.direction("ur").startswith("LeftToRight False "))


if __name__ == "__main__":
    unittest.main(verbosity=2)
