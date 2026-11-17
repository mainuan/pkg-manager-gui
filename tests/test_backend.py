#!/usr/bin/env python3
"""Testes do appimage_manager_backend sem root e sem tocar no sistema:

* cálculo do deslocamento do SquashFS a partir do cabeçalho ELF e recusa de
  AppImages tipo 1 e de outros arquivos;
* cópia privada (arquivo regular apenas; um FIFO não trava o backend);
* leitura de links simbólicos só dentro da árvore extraída;
* DEBIAN/control do pacote que registra o AppImage;
* com squashfs-tools: extração do .desktop e do ícone sem executar o AppImage;
* com dpkg-deb: o .deb gerado (campos e arquivos, ícones incluídos);
* com dpkg: instalação e remoção completas numa raiz temporária
  (dpkg --force-not-root --root=<dir>).

Executar: python3 tests/test_backend.py   (só a biblioteca padrão)
"""
import hashlib
import importlib.machinery
import importlib.util
import io
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAFE_PATH = "/usr/sbin:/usr/bin:/sbin:/bin"


def load_backend():
    path = os.path.join(ROOT, "appimage_manager_backend")
    loader = importlib.machinery.SourceFileLoader("appimage_manager_backend", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


B = load_backend()


def have(*tools):
    return all(shutil.which(t, path=SAFE_PATH) for t in tools)


def elf_header(elf_class=2, data=1, magic=b"AI\x02", machine=62, shoff=4096,
               shentsize=64, shnum=10):
    """Cabeçalho ELF mínimo de um runtime AppImage (e_ident[8:11] = AI\\x02)."""
    e = "<" if data == 1 else ">"
    ident = b"\x7fELF" + bytes([elf_class, data, 1]) + b"\0" + magic.ljust(8, b"\0")
    if elf_class == 2:
        rest = struct.pack(e + "HHIQQQIHHHHHH", 2, machine, 1, 0x400000, 64, shoff, 0,
                           64, 56, 1, shentsize, shnum, max(shnum - 1, 0))
    else:
        rest = struct.pack(e + "HHIIIIIHHHHHH", 2, machine, 1, 0x8048000, 52, shoff, 0,
                           52, 32, 1, shentsize, shnum, max(shnum - 1, 0))
    return ident + rest


def fake_superblock(bytes_used=4096, major=4):
    """Superbloco SquashFS 4.0 (96 bytes) escrito à mão."""
    sb = struct.pack("<4sIIIIHHHHHHQQQQQQQQ", b"hsqs", 1, 0, 131072, 0, 1, 17, 0, 1,
                     major, 0, 0, bytes_used, 96, ~0 & 0xFFFFFFFFFFFFFFFF, 96, 96, 96, 96)
    assert len(sb) == 96
    return sb


def build_appimage(path, squashfs, header=None, offset=None):
    header = header or elf_header()
    if offset is None:
        offset = B.appimage_info(header, 1 << 40)[0]
    with open(path, "wb") as fh:
        fh.write(header.ljust(offset, b"\0"))
        fh.write(squashfs)
    return offset


def make_squashfs(tree, out):
    subprocess.run(["mksquashfs", str(tree), str(out), "-noappend", "-all-root", "-no-progress",
                    "-quiet"], check=True, env={"PATH": SAFE_PATH}, stdout=subprocess.DEVNULL)
    return Path(out).read_bytes()


def app_tree(root, dir_icon="foo.png"):
    root.mkdir()
    (root / "foo.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Foo App\nExec=AppRun %U\n"
        "TryExec=AppRun\nIcon=foo\nCategories=Utility;\n", encoding="utf-8")
    (root / "foo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"icon" * 10)
    (root / "AppRun").write_text("#!/bin/sh\ntouch \"$HOME/executed\"\n")
    (root / "AppRun").chmod(0o755)
    (root / "big").write_bytes(os.urandom(64 * 1024))
    if dir_icon:
        os.symlink(dir_icon, root / ".DirIcon")
    return root


class OffsetTest(unittest.TestCase):
    def test_elf64_little_endian(self):
        h = elf_header(shoff=12345, shentsize=64, shnum=29)
        self.assertEqual(B.appimage_info(h, 1 << 30), (12345 + 64 * 29, "amd64"))

    def test_elf64_arm64(self):
        h = elf_header(machine=183, shoff=1000, shentsize=64, shnum=3)
        self.assertEqual(B.appimage_info(h, 1 << 30), (1192, "arm64"))

    def test_elf32(self):
        h = elf_header(elf_class=1, machine=3, shoff=7000, shentsize=40, shnum=25)
        self.assertEqual(B.appimage_info(h, 1 << 30), (8000, "i386"))

    def assertRefused(self, header, size=1 << 30, text=None):
        with self.assertRaises(B.UnsupportedAppImage) as cm:
            B.appimage_info(header, size)
        if text:
            self.assertIn(text, str(cm.exception))

    def test_type1_is_refused(self):
        self.assertRefused(elf_header(magic=b"AI\x01"), text="tipo 1")

    def test_without_appimage_signature(self):
        self.assertRefused(elf_header(magic=b""), text="AI")

    def test_not_elf(self):
        self.assertRefused(b"#!/bin/sh\necho hi\n".ljust(64, b" "), text="ELF")
        self.assertRefused(b"")

    def test_truncated_header(self):
        self.assertRefused(elf_header()[:40], text="truncado")

    def test_offset_outside_file(self):
        h = elf_header(shoff=4096, shnum=10)
        self.assertRefused(h, size=4096 + 640 + 95, text="fora do arquivo")
        self.assertEqual(B.appimage_info(h, 4096 + 640 + 96)[0], 4736)
        self.assertRefused(elf_header(shoff=0, shnum=0), text="fora do arquivo")

    def test_big_endian_and_unknown_machine(self):
        self.assertRefused(elf_header(data=2), text="arquitetura")
        self.assertRefused(elf_header(machine=243), text="arquitetura")


class InspectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_manual_squashfs(self):
        image = self.tmp / "a.AppImage"
        sq = fake_superblock(bytes_used=4096).ljust(4096, b"\0")
        offset = build_appimage(image, sq)
        self.assertEqual(B.inspect_appimage(image), (offset, "amd64"))

    def test_bad_squashfs(self):
        image = self.tmp / "a.AppImage"
        for sq, text in ((b"sqsh" + bytes(4092), "hsqs"),
                         (fake_superblock(major=3).ljust(4096, b"\0"), "versão"),
                         (fake_superblock(bytes_used=1 << 20).ljust(4096, b"\0"), "truncado")):
            build_appimage(image, sq)
            with self.assertRaises(B.UnsupportedAppImage) as cm:
                B.inspect_appimage(image)
            self.assertIn(text, str(cm.exception))

    @unittest.skipUnless(have("mksquashfs"), "mksquashfs (squashfs-tools) não instalado")
    def test_real_squashfs(self):
        sq = make_squashfs(app_tree(self.tmp / "tree"), self.tmp / "x.sqfs")
        image = self.tmp / "a.AppImage"
        offset = build_appimage(image, sq)
        self.assertEqual(B.inspect_appimage(image), (offset, "amd64"))
        with open(image, "rb") as fh:
            fh.seek(offset)
            self.assertEqual(fh.read(4), b"hsqs")


class CopyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.backend = B.AppImageBackend()

    def test_copy_is_private_and_hashed(self):
        src = self.tmp / "a.AppImage"
        src.write_bytes(b"conteudo" * 1000)
        digest = self.backend._copy_private(src, self.tmp / "copy")
        self.assertEqual(digest, hashlib.md5(src.read_bytes()).hexdigest())
        self.assertEqual(stat.S_IMODE(os.stat(self.tmp / "copy").st_mode), 0o600)
        self.assertEqual((self.tmp / "copy").read_bytes(), src.read_bytes())

    def test_destination_symlink_is_not_followed(self):
        src = self.tmp / "a.AppImage"
        src.write_bytes(b"x")
        victim = self.tmp / "victim"
        victim.write_bytes(b"intacto")
        os.symlink(victim, self.tmp / "copy")
        with self.assertRaises(OSError):
            self.backend._copy_private(src, self.tmp / "copy")
        self.assertEqual(victim.read_bytes(), b"intacto")

    def test_fifo_and_directory_are_refused(self):
        fifo = self.tmp / "f.AppImage"
        os.mkfifo(fifo)
        result = {}

        def run():
            try:
                self.backend._copy_private(fifo, self.tmp / "c1")
            except Exception as e:  # noqa: BLE001
                result["e"] = e
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(5)
        self.assertFalse(t.is_alive(), "o backend travou abrindo um FIFO")
        self.assertIsInstance(result.get("e"), B.UnsupportedAppImage)
        with self.assertRaises((B.UnsupportedAppImage, OSError)):
            self.backend._copy_private(self.tmp, self.tmp / "c2")


class ReadInsideTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = self.tmp / "squashfs-root"
        (self.root / "usr/share").mkdir(parents=True)
        (self.root / "usr/share/icon.png").write_bytes(b"PNG")

    def test_internal_symlinks(self):
        os.symlink("usr/share/icon.png", self.root / ".DirIcon")
        os.symlink("/usr/share/icon.png", self.root / "abs")  # fora da árvore
        self.assertEqual(B.read_inside(self.root, ".DirIcon", 10), b"PNG")
        self.assertIsNone(B.read_inside(self.root, "abs", 10))

    def test_escaping_symlinks(self):
        secret = self.tmp / "secret"
        secret.write_bytes(b"segredo")
        os.symlink(secret, self.root / ".DirIcon")
        os.symlink("../secret", self.root / "rel.desktop")
        os.symlink(self.tmp, self.root / "usr/up")
        self.assertIsNone(B.read_inside(self.root, ".DirIcon", 100))
        self.assertIsNone(B.read_inside(self.root, "rel.desktop", 100))
        self.assertIsNone(B.read_inside(self.root, "usr/up/secret", 100))

    def test_limits_and_types(self):
        (self.root / "big").write_bytes(b"x" * 11)
        self.assertIsNone(B.read_inside(self.root, "big", 10))
        self.assertIsNone(B.read_inside(self.root, "usr", 10))
        self.assertIsNone(B.read_inside(self.root, "missing", 10))
        os.mkfifo(self.root / "fifo")
        self.assertIsNone(B.read_inside(self.root, "fifo", 10))


class ControlTest(unittest.TestCase):
    def test_control(self):
        control = B.deb_control("kdenliveappimage", "1.0-0a1b2c", "amd64", "Kdenlive", 2048)
        self.assertEqual(control, (
            "Package: kdenliveappimage\n"
            "Version: 1.0-0a1b2c\n"
            "Architecture: amd64\n"
            "Maintainer: AppImageManager <root@localhost>\n"
            "Installed-Size: 2048\n"
            "Section: misc\n"
            "Priority: optional\n"
            "Description: Kdenlive via AppImage\n"
            " AppImage installed by pkg-manager-gui.\n"))

    def test_name_cannot_inject_fields(self):
        control = B.deb_control("fooappimage", "1.0-abcdef", "arm64",
                                "Foo\nStatus: hold\r\x00 \t Bar", 0)
        self.assertIn("Description: Foo Status: hold Bar via AppImage\n", control)
        self.assertEqual(sum(line.startswith("Status") for line in control.splitlines()), 0)
        self.assertIn("Installed-Size: 1\n", control)
        self.assertIn("Description: fooappimage via AppImage\n",
                      B.deb_control("fooappimage", "1.0-abcdef", "amd64", "\x01", 1))

    def test_invalid_values(self):
        for args in (("-appimage", "1.0-abcdef", "amd64"), ("Foo", "1.0-abcdef", "amd64"),
                     ("fooappimage", "1.0", "amd64"), ("fooappimage", "1.0-abc def", "amd64"),
                     ("fooappimage", "1.0-abcdef", "all")):
            with self.assertRaises(ValueError):
                B.deb_control(*args, "Foo", 1)

    def test_package_name_and_version_derivation(self):
        backend = B.AppImageBackend()
        self.assertEqual(backend._sanitize("/home/u/Kdenlive-25.08-x86_64.AppImage") + "appimage",
                         "kdenliveappimage")
        self.assertEqual(backend._sanitize("Ação-1.0.AppImage") + "appimage", "acaoappimage")


class InstallTest(unittest.TestCase):
    """install() com os programas reais, exceto o dpkg -i (gravado ou com --root)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.backend = B.AppImageBackend()
        self.backend.tmp_parent = str(self.tmp)
        self.calls = []
        real_run = subprocess.run

        def spy(cmd, *args, **kwargs):
            self.calls.append([str(c) for c in cmd])
            return real_run(cmd, *args, **kwargs)
        patcher = mock.patch.object(B.subprocess, "run", side_effect=spy)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_install(self, image):
        out = io.StringIO()
        code = 0
        with redirect_stdout(out):
            try:
                self.backend.install(str(image))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()

    def appimage(self, dir_icon="foo.png"):
        sq = make_squashfs(app_tree(self.tmp / "tree", dir_icon), self.tmp / "x.sqfs")
        image = self.tmp / "Foo-1.0-x86_64.AppImage"
        build_appimage(image, sq)
        image.chmod(0o755)
        return image

    def assertNotExecuted(self, image):
        for cmd in self.calls:
            self.assertNotIn("--appimage-extract", cmd)
            self.assertNotEqual(os.path.basename(cmd[0]), image.name)
            self.assertFalse(cmd[0].startswith(str(self.tmp)), cmd)
        self.assertFalse((Path.home() / "executed").exists())

    def test_unsupported_exits_3_without_running_anything(self):
        image = self.tmp / "Foo.AppImage"
        build_appimage(image, fake_superblock().ljust(4096, b"\0"),
                       header=elf_header(magic=b"AI\x01"), offset=4096 + 640)
        code, out = self.run_install(image)
        self.assertEqual(code, B.EXIT_UNSUPPORTED, out)
        self.assertIn("tipo 1", out)
        self.assertEqual(self.calls, [])
        image.write_bytes(b"#!/bin/sh\nexit 0\n")
        self.assertEqual(self.run_install(image)[0], 3)
        self.assertEqual(self.calls, [])
        self.assertEqual(os.listdir(self.tmp), [image.name])  # temporários removidos

    @unittest.skipUnless(have("mksquashfs", "unsquashfs", "dpkg-deb"),
                         "squashfs-tools/dpkg-deb não instalados")
    def test_builds_deb_with_all_files(self):
        image = self.appimage()
        md5 = hashlib.md5(image.read_bytes()).hexdigest()
        saved = self.tmp / "saved.deb"
        recorder = ("import os, shutil, stat, sys; deb = sys.argv[-1]; "
                    "shutil.copy(deb, sys.argv[1]); "
                    "print('MODE', oct(stat.S_IMODE(os.stat(os.path.dirname(deb)).st_mode)))")
        self.backend.dpkg = [sys.executable, "-c", recorder, str(saved)]
        code, out = self.run_install(image)
        self.assertEqual(code, 0, out)
        self.assertNotExecuted(image)
        self.assertEqual(self.calls[-1][-2], "-i")
        self.assertTrue(any(c[0] == "unsquashfs" and c[c.index("-o") + 1] != "0"
                            for c in self.calls))

        def deb(*args):
            return subprocess.run(["dpkg-deb", *args, str(saved)], check=True,
                                  capture_output=True, text=True).stdout
        self.assertEqual(deb("-f", "Package").strip(), "fooappimage")
        self.assertEqual(deb("-f", "Version").strip(), f"1.0-{md5[:6]}")
        self.assertEqual(deb("-f", "Architecture").strip(), "amd64")
        self.assertEqual(deb("-f", "Description").splitlines()[0], "Foo App via AppImage")
        listing = deb("-c")
        for path in (f"./opt/appimages-installed/{md5}",
                     "./usr/share/applications/fooappimage.desktop",
                     "./usr/share/icons/hicolor/128x128/apps/fooappimage.png",
                     "./usr/share/pixmaps/fooappimage.png"):
            self.assertIn(path, listing)
        self.assertIn("root/root", listing)
        extracted = self.tmp / "ex"
        subprocess.run(["dpkg-deb", "-x", str(saved), str(extracted)], check=True)
        self.assertEqual((extracted / f"opt/appimages-installed/{md5}").read_bytes(),
                         image.read_bytes())
        desktop = (extracted / "usr/share/applications/fooappimage.desktop").read_text()
        self.assertIn(f"Exec=/opt/appimages-installed/{md5}\n", desktop)
        self.assertIn("Icon=fooappimage\n", desktop)
        self.assertNotIn("TryExec", desktop)
        self.assertTrue((extracted / "usr/share/pixmaps/fooappimage.png").read_bytes()
                        .startswith(b"\x89PNG"))
        self.assertIn("MODE 0o700", out)  # diretório temporário privado
        self.assertEqual(sorted(os.listdir(self.tmp)),
                         sorted([image.name, "tree", "x.sqfs", "saved.deb", "ex"]))

    @unittest.skipUnless(have("mksquashfs", "unsquashfs", "dpkg-deb"),
                         "squashfs-tools/dpkg-deb não instalados")
    def test_icon_symlink_outside_the_image_is_ignored(self):
        image = self.appimage(dir_icon="/etc/passwd")
        saved = self.tmp / "saved.deb"
        self.backend.dpkg = [sys.executable, "-c",
                             "import shutil, sys; shutil.copy(sys.argv[-1], sys.argv[1])",
                             str(saved)]
        code, out = self.run_install(image)
        self.assertEqual(code, 0, out)
        listing = subprocess.run(["dpkg-deb", "-c", str(saved)], check=True,
                                 capture_output=True, text=True).stdout
        self.assertNotIn("fooappimage.png", listing)
        self.assertIn("fooappimage.desktop", listing)

    @unittest.skipUnless(have("mksquashfs", "unsquashfs", "dpkg-deb", "dpkg", "dpkg-query"),
                         "squashfs-tools/dpkg não instalados")
    def test_install_and_remove_with_dpkg_root(self):
        arch = subprocess.run(["dpkg", "--print-architecture"], capture_output=True,
                              text=True, check=False).stdout.strip()
        if arch != "amd64":
            self.skipTest(f"arquitetura do dpkg: {arch}")
        image = self.appimage()
        md5 = hashlib.md5(image.read_bytes()).hexdigest()
        sysroot = self.tmp / "sysroot"
        admin = sysroot / "var/lib/dpkg"
        for d in ("info", "updates", "triggers"):
            (admin / d).mkdir(parents=True)
        (admin / "status").touch()
        (admin / "available").touch()
        dpkg = ["dpkg", "--force-not-root", f"--root={sysroot}", "--log=/dev/null"]
        self.backend.dpkg = dpkg
        self.backend.update_desktop_database = ["true"]
        code, out = self.run_install(image)
        self.assertEqual(code, 0, out)
        self.assertIn("Sucesso", out)
        self.assertNotExecuted(image)

        def query(*args):
            return subprocess.run(["dpkg-query", f"--root={sysroot}", *args],
                                  capture_output=True, text=True, env={"PATH": SAFE_PATH},
                                  check=False)
        status = query("-W", "-f=${Status} ${Version}", "fooappimage").stdout
        self.assertEqual(status, f"install ok installed 1.0-{md5[:6]}")
        files = query("-L", "fooappimage").stdout.splitlines()
        installed = [f"/opt/appimages-installed/{md5}",
                     "/usr/share/applications/fooappimage.desktop",
                     "/usr/share/icons/hicolor/128x128/apps/fooappimage.png",
                     "/usr/share/pixmaps/fooappimage.png"]
        for path in installed:
            self.assertIn(path, files)
            self.assertTrue((sysroot / path.lstrip("/")).is_file(), path)

        out = io.StringIO()
        with redirect_stdout(out):
            self.backend.uninstall("Foo-1.0-x86_64.AppImage")
        self.assertIn("Sucesso", out.getvalue())
        for path in installed:
            self.assertFalse((sysroot / path.lstrip("/")).exists(), path)
        self.assertNotEqual(query("-W", "-f=${Status}", "fooappimage").stdout,
                            "install ok installed")

        # dpkg -i falha (pacote arm64 num dpkg amd64): código 1, nada instalado.
        with mock.patch.object(B, "ELF_ARCHITECTURES", {62: "arm64"}):
            code, out = self.run_install(image)
        self.assertEqual(code, 1, out)
        self.assertIn("dpkg não instalou", out)
        self.assertFalse((sysroot / installed[0].lstrip("/")).exists())

if __name__ == "__main__":
    unittest.main(verbosity=2)
