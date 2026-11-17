# Pkg Manager GUI (Qt 6) da Mainuan
Este projeto é uma interface gráfica moderna e leve para a instalação e gerenciamento de pacotes Pkg, desenvolvida para a Mainuan. Ele substitui a implementação anterior baseada em Shell Script e YA.

## 🚀 Funcionalidades
Instalação Simplificada: Interface intuitiva com barras de progresso em tempo real para o pacote atual e o progresso geral.

Detecção de Estado: Verifica automaticamente se um aplicativo já está instalado.

Gestão de Remoção: Oferece a opção de desinstalação caso o usuário tente "instalar" um pacote já presente no sistema.

Parsing Inteligente: Monitora a saída do Pkg via QProcess para exibir porcentagens precisas.

Portable ELF: Gera um binário executável único que não depende da instalação manual de bibliotecas Python no sistema alvo.

Empacotamento DEB: Script automatizado para gerar pacotes .deb prontos para distribuição.

## 🛠 Tecnologias Utilizadas
Linguagem: Python 3.10+

Interface Gráfica: PySide6 (Qt 6)

Configuração: Python-dotenv

Build: PyInstaller

Gerenciamento de Pacotes: Pkg CLI

## 🔗 Como Usar

1. Clone o projeto
```bash
git clone https://github.com/mainuan/pkg-manager-gui
cd pkg-manager-gui
```

2. Instale as depenências
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Configurar o .env
Crie um arquivo .env na raiz do projeto:

```env
APP_NAME=pkg-manager-gui
VERSION=26.01.03
MAINTAINER=Seu Nome <email@provedor.com>
DESCRIPTION=Gerenciador gráfico de aplicativos Flatpak e AppImage (Qt 6) da Mainuan
```

## 🏗️ Build e Empacotamento
Para gerar o executável binário (ELF) e o pacote .deb automaticamente, execute o script de build:

```bash
python3 build.py
```
O binário será gerado na pasta dist/ junto com pacote .deb instalável na raiz do projeto como 

## 📝 Como usar via linha de comando
A aplicação aceita o caminho de um arquivo flatpak, ou, de um appimage:

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