# Internacionalização (i18n) do pkg-manager-gui

* **Domínio gettext:** `pkg-manager-gui` (nome do pacote Debian em `debian/control`).
* **Idioma-fonte:** inglês; a interface brasileira está em `po/pt_BR.po`.
* **API:** `src/i18n.py` — `gettext.translation(..., fallback=True)`, exporta `_`,
  `ngettext`, `pgettext` e `install_qt_translator(app)` (carrega `qtbase_<lang>.qm`
  para `QLocale.system()`, para os botões padrão do Qt). Placeholders `{nome}`.
* **Idioma:** nunca forçado; segue `LANGUAGE`/`LC_ALL`/`LC_MESSAGES`/`LANG`.

## Layout

```
po/i18n.sh, po/i18n.conf     script padrão Mainuan e configuração
po/POTFILES.in               fontes Python + .desktop.in + .policy.in
po/LINGUAS                   idiomas instalados (hoje só pt_BR)
po/pkg-manager-gui.pot       modelo (versionado)
po/pt_BR.po
po/its/polkit.{its,loc}      regras ITS do polkit (para *.policy.in)
pkg-manager-gui.desktop.in   modelo do .desktop (Name/GenericName/Comment em inglês)
br.com.aratie.appimagemanagerbackend.policy.in   modelo da política polkit
tests/test_i18n.py           teste automático (pt_BR e en/C)
tests/test_logic.py          testes da lógica (formato do arquivo, Flatpak instalado, backend)
```

## Onde os catálogos são procurados

1. `$PKG_MANAGER_GUI_LOCALEDIR`;
2. `build/locale` na raiz do repositório (execução a partir do código-fonte);
3. `/usr/share/locale` (pacote instalado).

## Tarefas

```bash
po/i18n.sh extract && po/i18n.sh update   # após mudar textos
po/i18n.sh validate && po/i18n.sh check-pot
po/i18n.sh add es                          # novo idioma
po/i18n.sh compile build/locale            # rodar do código-fonte:
LANGUAGE=en python3 src/main.py arquivo.flatpakref
python3 tests/test_i18n.py                 # QT_QPA_PLATFORM=offscreen interno
```

## Empacotamento

`debian/rules` chama `python3 build.py <destino>` (requer `gettext`), que valida
os catálogos, compila `/usr/share/locale/<lang>/LC_MESSAGES/pkg-manager-gui.mo`
e gera, com `msgfmt --desktop`/`msgfmt --xml`, o `.desktop` e a política polkit
traduzidos. O CI (`.github/workflows/ci.yml`) roda `check-pot`, `validate`, os
testes e um teste de fumaça com o pacote instalado.

## Particularidades

* O backend `appimage_manager_backend` (executado como root via `pkexec`, saída
  lida só para extrair a porcentagem) **não** foi traduzido: não é interface e o
  `pkexec` descarta `LANGUAGE`/`LANG`.
* Mensagens de `NotImplementedError` são para desenvolvedores e não foram traduzidas.
* `PKG Manager`, `AppImage Manager` e `Flatpak Manager` já eram exibidos em inglês;
  o pt_BR os mantém idênticos.
* O ID polkit `br.com.aratie.appimagemanager.pkexec` e o arquivo
  `br.com.aratie.appimagemanagerbackend.policy` carregam a marca legada *Aratie*;
  não foram renomeados (mudança de comportamento/compatibilidade).
* O texto pt_BR da política polkit mantém a grafia original
  ("Gerênciar", "reliazar está operação") por exigência de interface idêntica;
  corrigir é uma decisão de revisão de tradução, só em `po/pt_BR.po`.
* `po/i18n.sh` local usa uma única tag `--add-comments` (`Translators:`): o
  xgettext só respeita a última tag passada.
