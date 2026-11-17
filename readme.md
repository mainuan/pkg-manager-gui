# Pkg Manager GUI (Qt 6) da Mainuan
Este projeto é uma interface gráfica moderna e leve para a instalação e gerenciamento de pacotes Pkg, desenvolvida para a Mainuan. Ele substitui a implementação anterior baseada em Shell Script e YA.

## 🚀 Funcionalidades
Instalação Simplificada: Interface intuitiva com barras de progresso em tempo real para o pacote atual e o progresso geral.

Detecção de Estado: Verifica automaticamente se um aplicativo já está instalado.

Gestão de Remoção: Oferece a opção de desinstalação caso o usuário tente "instalar" um pacote já presente no sistema.

Parsing Inteligente: Monitora a saída do Pkg via QProcess para exibir porcentagens precisas.

Pacote Debian: usa o Python e o PySide6 do Ubuntu (`python3-pyside6.*`), com `.desktop`, política polkit e traduções.

## 🛠 Tecnologias Utilizadas
Linguagem: Python 3.10+

Interface Gráfica: PySide6 (Qt 6)

Empacotamento: debhelper (`debian/`)

Gerenciamento de Pacotes: Pkg CLI

## 🔗 Como Usar

1. Clone o projeto
```bash
git clone https://github.com/mainuan/pkg-manager-gui
cd pkg-manager-gui
```

2. Para rodar a partir do código-fonte (requer `gettext` e PySide6 — no Ubuntu,
   `python3-pyside6.qtwidgets`):
```bash
po/i18n.sh compile build/locale
python3 src/main.py /caminho/para/aplicativo.flatpakref
```

## 🏗️ Build e Empacotamento
O pacote `pkg-manager-gui` é gerado a partir de `debian/`:

```bash
dpkg-buildpackage -us -uc -b
```

Ele instala `/usr/bin/pkg-manager-gui`, o código em `/usr/share/pkg-manager-gui`,
o backend de AppImage em `/usr/libexec/pkg-manager-gui/appimage_manager_backend`
(executado como root via `pkexec`, ação polkit `br.com.aratie.appimagemanager.pkexec`),
o `.desktop`, a política polkit e as traduções. Os testes ficam em `tests/`.

O CI (`.github/workflows/ci.yml`) compila, testa, roda o lintian e instala o
pacote num Ubuntu 26.04 limpo; uma release só é publicada ao enviar uma tag
`v<versão>` igual à de `debian/changelog`.

## 📝 Como usar via linha de comando
A aplicação aceita o caminho de um arquivo .flatpakref ou .AppImage:

```bash
# O sistema detectará automaticamente se deve instalar ou remover.
pkg-manager-gui /caminho/para/aplicativo.flatpakref 
pkg-manager-gui /caminho/para/aplicativo.appimage 
```
### 🤝 Contribuição
Faça um Fork do projeto.

Crie uma Branch para sua Feature (git checkout -b feature/NovaFeature).

Faça o Commit de suas alterações (git commit -m 'Adicionando nova funcionalidade').

Faça o Push para a Branch (git push origin feature/NovaFeature).

Abra um Pull Request.