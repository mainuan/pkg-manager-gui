#!/usr/bin/env python3
"""Testes da lógica sem janelas e sem tocar no sistema: escolha da interface
pelo nome do arquivo, detecção de Flatpak instalado e código de saída do
backend de AppImage (subprocess simulado).

Executar: python3 tests/test_logic.py   (requer PySide6)
"""
import importlib.machinery
import importlib.util
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def load_backend():
    path = os.path.join(ROOT, "appimage_manager_backend")
    loader = importlib.machinery.SourceFileLoader("appimage_manager_backend", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class FactoryTest(unittest.TestCase):
    def setUp(self):
        try:
            from factory import ui_factory
        except ImportError as e:
            self.skipTest(f"PySide6 não disponível: {e}")
        self.ui_factory = ui_factory
        patches = {name: mock.patch.object(ui_factory, name, side_effect=lambda *a, n=name: n)
                   for name in ("FlatpakManager", "AppImageManager", "NotFoundManager")}
        for p in patches.values():
            p.start()
            self.addCleanup(p.stop)

    def infer(self, url):
        return self.ui_factory.BuildUi.AutoInferPkg(url)

    def test_appimage_extension_is_case_insensitive(self):
        # Arquivos AppImage costumam terminar em ".AppImage".
        self.assertEqual(self.infer("/home/u/Kdenlive-25.08-x86_64.AppImage"), "AppImageManager")
        self.assertEqual(self.infer("/home/u/app.appimage"), "AppImageManager")

    def test_flatpakref(self):
        self.assertEqual(self.infer("/home/u/org.gimp.GIMP.flatpakref"), "FlatpakManager")
        self.assertEqual(self.infer("/home/u/ORG.X.App.FlatpakRef"), "FlatpakManager")

    def test_other_files(self):
        self.assertEqual(self.infer("/home/u/foo.deb"), "NotFoundManager")


class FlatpakServiceTest(unittest.TestCase):
    def setUp(self):
        try:
            from service.flatpak_service import FlatpakService
        except ImportError as e:
            self.skipTest(f"PySide6 não disponível: {e}")
        with mock.patch("service.flatpak_service.GroupUtils.is_user_in_group", return_value=False):
            self.service = FlatpakService(process=None)

    def installed(self, listing, ref):
        done = subprocess.CompletedProcess([], 0, stdout=listing, stderr="")
        with mock.patch("service.flatpak_service.subprocess.run", return_value=done):
            return self.service.is_installed(ref)

    def test_exact_application_id(self):
        listing = "org.kde.Platform\norg.gimp.GIMP.Plugin.GMic\n"
        self.assertFalse(self.installed(listing, "org.gimp.GIMP.flatpakref"))
        self.assertTrue(self.installed(listing + "org.gimp.GIMP\n", "org.gimp.GIMP.flatpakref"))


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.backend = load_backend().AppImageBackend()

    def uninstall(self, dpkg_rc):
        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, dpkg_rc if cmd[0] == "dpkg" else 0)

        out = io.StringIO()
        code = 0
        with mock.patch("subprocess.run", side_effect=fake_run), redirect_stdout(out):
            try:
                self.backend.uninstall("Kdenlive-25.08-x86_64.AppImage")
            except SystemExit as e:
                code = e.code
        return code, calls, out.getvalue()

    def test_uninstall_success(self):
        code, calls, out = self.uninstall(0)
        self.assertEqual(code, 0)
        self.assertEqual(calls[0], ["dpkg", "-r", "kdenliveappimage"])
        self.assertIn("Sucesso", out)

    def test_uninstall_failure_is_reported(self):
        # dpkg falhou (por exemplo, base de dados bloqueada): a interface
        # precisa receber um código de saída diferente de zero.
        code, calls, out = self.uninstall(2)
        self.assertEqual(code, 1)
        self.assertNotIn("Sucesso", out)


class UnsupportedAppImageTest(unittest.TestCase):
    def test_backend_exit_code_shows_the_reason(self):
        # O backend sai com 3 para um arquivo que não é AppImage tipo 2; a
        # interface explica o motivo em vez do aviso genérico.
        try:
            from ui import appimage_manager
        except ImportError as e:
            self.skipTest(f"PySide6 não disponível: {e}")
        self.assertEqual(appimage_manager.EXIT_UNSUPPORTED, load_backend().EXIT_UNSUPPORTED)
        window = mock.Mock(spec=appimage_manager.AppImageManager)
        with mock.patch.object(appimage_manager.QMessageBox, "warning") as warning, \
                mock.patch.object(appimage_manager.PkgManager, "on_finished") as generic:
            appimage_manager.AppImageManager.on_finished(window, 3)
            self.assertIn("type 2", warning.call_args.args[2])
            window.close.assert_called_once()
            generic.assert_not_called()
            appimage_manager.AppImageManager.on_finished(window, 1)
            generic.assert_called_once_with(1)


class PolicyPathTest(unittest.TestCase):
    def test_service_and_policy_use_the_same_backend_path(self):
        try:
            from service.appimage_service import AppImageService
        except ImportError as e:
            self.skipTest(f"PySide6 não disponível: {e}")
        path = AppImageService(process=None).wrapper_path
        with open(os.path.join(ROOT, "br.com.aratie.appimagemanagerbackend.policy.in"),
                  encoding="utf-8") as fh:
            policy = fh.read()
        self.assertIn(f'"org.freedesktop.policykit.exec.path">{path}<', policy)
        self.assertFalse(path.startswith("/usr/local/"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
