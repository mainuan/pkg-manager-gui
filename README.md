<div align="center">

<img src="https://raw.githubusercontent.com/mainuan/.github/main/profile/assets/mainuan-logo.svg" width="96" alt="Logotipo do Mainuan">

# PKG Manager

Instala ou remove, com confirmação e barra de progresso, o aplicativo de um arquivo `.flatpakref` ou `.AppImage`.

[![CI](https://github.com/mainuan/pkg-manager-gui/actions/workflows/ci.yml/badge.svg)](https://github.com/mainuan/pkg-manager-gui/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mainuan/pkg-manager-gui)](https://github.com/mainuan/pkg-manager-gui/releases/latest)
[![Licença](https://img.shields.io/github/license/mainuan/pkg-manager-gui)](license)
![Plataforma](https://img.shields.io/badge/Kubuntu%2026.04%20%7C%20Plasma%206.6-0079c1)

**Português** · [English](README.en.md)

</div>

---

## O que é

O PKG Manager (`pkg-manager-gui`) é um instalador gráfico leve, em Python com
PySide6 (Qt 6), que decide o que fazer pela extensão do arquivo recebido. Ele
substitui a implementação anterior em shell script com YAD.

A partir da versão 1.1.0 é um pacote Debian de 36 KB, `Architecture: all`, que
usa o Python e o PySide6 do Ubuntu. O antigo `flatpak-manager-gui`, um binário
PyInstaller de 81 MB com Python e PySide6 embutidos, foi substituído
(`Conflicts`/`Replaces: flatpak-manager-gui`).

## Funcionalidades

- **`.flatpakref`**: instala com `flatpak install`, ou oferece a remoção quando um aplicativo com o mesmo ID (o nome do arquivo sem a extensão) já está instalado. Se o usuário não é root nem membro do grupo `flatpak`, o comando passa pelo `pkexec`.
- **`.AppImage`** (tipo 2): copia o arquivo para `/opt/appimages-installed`, cria entrada no menu e ícone a partir do `.desktop` do AppImage e registra o aplicativo na base do `dpkg` como o pacote `<nome>appimage`, para poder removê-lo depois; ou remove esse pacote (`dpkg -r`) se ele já existir. O trabalho é feito pelo backend `/usr/libexec/pkg-manager-gui/appimage_manager_backend`, via `pkexec` (ação polkit `br.com.aratie.appimagemanager.pkexec`, com senha de administrador).
  - O AppImage **nunca é executado**: o backend copia o arquivo para um diretório temporário privado do root (lido com as permissões de quem pediu a instalação), calcula o deslocamento do SquashFS pelo cabeçalho ELF (`e_shoff + e_shentsize × e_shnum`, como `appimagetool --appimage-offset`), confere a assinatura `hsqs` e extrai só o `.desktop` e o `.DirIcon` com `unsquashfs -o <deslocamento>`. Links simbólicos que saem da imagem são ignorados.
  - O registro é um pacote `.deb` de verdade, gerado com `dpkg-deb --build` e instalado com `dpkg -i`: o `dpkg` respeita a trava da sua base e registra todos os arquivos (binário, `.desktop` e ícones), que o `dpkg -r` remove por completo.
  - AppImages do tipo 1 e outros arquivos são recusados com uma mensagem que explica o motivo.
- Pergunta antes de instalar ou remover; acompanha a saída do processo (`QProcess`) e mostra a porcentagem numa barra de progresso; informa o resultado numa caixa de mensagem.
- Outros arquivos recebem um aviso de formato não suportado.
- Interface, `.desktop` e política polkit traduzidos em 33 idiomas.

## Instalação

O PKG Manager já vem na ISO do Mainuan Linux.

Em outro sistema Kubuntu/Ubuntu 26.04, baixe o `.deb` e o `SHA256SUMS` da
[última release](https://github.com/mainuan/pkg-manager-gui/releases/latest),
confira e instale:

```bash
sha256sum --check --ignore-missing SHA256SUMS
sudo apt install ./pkg-manager-gui_1.1.1_all.deb
```

## Uso

```bash
pkg-manager-gui ~/Downloads/org.gimp.GIMP.flatpakref
pkg-manager-gui ~/Downloads/Aplicativo-1.0-x86_64.AppImage
```

O comando recebe um arquivo; sem argumento, mostra
`Uso: pkg-manager-gui <url/arquivo>` e sai com código 1
(`man pkg-manager-gui`). A entrada de menu **PKG Manager** abre arquivos
`application/vnd.flatpak.ref`, `application/vnd.appimage` e
`application/x-iso9660-appimage`. A interface segue `LANGUAGE`, `LC_ALL`,
`LC_MESSAGES` e `LANG`.

## Informações técnicas

| Item | Valor |
|---|---|
| Linguagem | Python 3 |
| Toolkit | Qt 6 (PySide6 do Ubuntu: `python3-pyside6.qtcore`, `.qtgui`, `.qtwidgets`) |
| Base | Kubuntu 26.04 LTS, KDE Plasma 6.6 |
| Pacote | `pkg-manager-gui`, `Architecture: all`, cerca de 36 KB |
| Dependências | `flatpak`, `pkexec`, `python3`, `desktop-file-utils`, `squashfs-tools`; recomenda `qt6-translations-l10n` |
| Privilégios | `pkexec` para o backend de AppImage e para o Flatpak de sistema |
| Arquitetura do sistema | amd64 |
| Arquivos instalados | `/usr/bin/pkg-manager-gui`, `/usr/share/pkg-manager-gui/`, `/usr/libexec/pkg-manager-gui/appimage_manager_backend`, `.desktop`, política polkit, catálogos e página de manual |

## Compilação e testes

```bash
git clone https://github.com/mainuan/pkg-manager-gui.git
cd pkg-manager-gui
sudo apt build-dep ./
dpkg-buildpackage -us -uc -b      # gera ../pkg-manager-gui_<versão>_all.deb
```

A versão vem de `debian/changelog`. Durante o build, o `debian/rules` executa
`tests/test_logic.py`, `tests/test_backend.py`, `tests/test_i18n.py`, `desktop-file-validate` no
`.desktop` gerado e `xmllint` na política polkit. Antes dele, o CI executa:

```bash
po/i18n.sh check-pot && po/i18n.sh validate && python3 tests/test_logic.py && python3 tests/test_backend.py
```

`tests/test_backend.py` não precisa de root: monta um AppImage sintético
(cabeçalho ELF + SquashFS feito com `mksquashfs`), testa o cálculo do
deslocamento e as recusas, gera o `.deb` e instala e remove o pacote com
`dpkg --force-not-root --root=<diretório temporário>`. Sem `squashfs-tools` ou
`dpkg`, só essas etapas são puladas.

O workflow [`CI`](.github/workflows/ci.yml) usa o pipeline Debian comum da
organização: build num contêiner Ubuntu 26.04 fixado por digest, `lintian`,
`SHA256SUMS`, instalação num Ubuntu 26.04 limpo e teste de fumaça (política
polkit apontando para o backend instalado, backend que recusa rodar sem root,
mensagem de uso em português e inglês, janela aberta offscreen para cada tipo
de arquivo), reinstalação e remoção. A release só é publicada por uma tag
`v*` igual à versão de `debian/changelog`.

Para rodar a partir do código-fonte (requer `gettext` e `python3-pyside6.qtwidgets`):

```bash
po/i18n.sh compile build/locale
python3 src/main.py /caminho/para/aplicativo.flatpakref
```

## Traduções

Catálogos gettext em `po/` (domínio `pkg-manager-gui`, textos-fonte em
inglês), em 33 idiomas listados em `po/LINGUAS`; o `.desktop` e a política
polkit são gerados traduzidos pelo `build.py`. Como contribuir:
[docs/i18n/README.md](docs/i18n/README.md).

## Contribuição

Relate problemas em [Issues](https://github.com/mainuan/pkg-manager-gui/issues)
e envie mudanças por pull request para `main`, a partir de um branch próprio.
O [CI](https://github.com/mainuan/pkg-manager-gui/actions/workflows/ci.yml)
precisa estar verde.

## Créditos

- Guilherme Rialli Oliveira ([@guirialli](https://github.com/guirialli)): migração de YAD para Qt 6 e suporte a AppImage.
- Rafael Ruscher ([@ruscher](https://github.com/ruscher)): internacionalização, empacotamento Debian e CI.

## Licença

[MIT](license), Copyright (c) 2025 Charles Santana.
