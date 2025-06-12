# 📖 Marriplan Backend

## 🚀 Como executar

### `Passo 01:` Preparação de ambiente para GPU

1. Download e instale/atualize seu [driver NVIDIA](https://www.nvidia.com.br/Download/index.aspx?lang=br) para última versão
2. Download e instale o [CUDA 12.4](https://developer.nvidia.com/cuda-12-4-0-download-archive)
3. Download e instale [cuDNN v8.9.7 for CUDA 12.x](https://developer.nvidia.com/rdp/cudnn-archive)
4. É recomendado que reinicie sua máquina.

### `Passo 02:` Crie seu ambiente Anaconda

1. Download e instale o [anaconda](https://repo.anaconda.com/archive/Anaconda3-2024.10-1-Windows-x86_64.exe).
   - Para verificar se o anaconda é reconhecido, abra o CMD e execute `conda`. Se não for reconhecido, adicione o path de instalação do Anaconda às variáveis de ambiente. Exemplos de paths:
     - `C:\path\to\conda\anaconda3`
     - `C:\path\to\conda\anaconda3\Library\usr\bin`
     - `C:\path\to\conda\anaconda3\Library\bin`
     - `C:\path\to\conda\anaconda3\Scripts`


2. Abra um CMD no mesmo nível deste arquivo e execute o comando abaixo para criar o ambiente:
```bash
  conda env create -f environment.yml
```
3. Após criar o conda env, abra um novo cmd e ative a env:
```bash
  conda activate marriplan
```
ou
```bash
  activate marriplan
```

### `Passo 03:` Ollama

1. Download e instale [Ollama](https://github.com/ollama/ollama) com o arquivo executável.
2. Tenha certeza que o ollama está em execução.

### `Passo 04`: MongoDB

1. Download e instale o [MongoDB](https://www.mongodb.com/try/download/community)
2. Verifique que tudo está funcionando corretamente com o comando `mongosh` em um cmd

### `Passo 05`: Docker

1. Download e instale o [Docker](https://docs.docker.com/desktop/setup/install/windows-install/)
2. Verifique que ele está funcionando corretamente.

### `Passo 06`: qdrant

1. Com o docker, faça a instalação do [qdrant](https://qdrant.tech/documentation/quickstart/)
2. No raiz do projeto, execute: `mkdir -p app/data/qdrant_storage`
3. Depois execute `docker run -p 6333:6333 -v ./app/data/qdrant_storage:/qdrant/storage qdrant/qdrant`
4. Execute o qdrant e verifique que está funcionando corretamente através `localhost:6333/dashboard`


### `Passo 07`: Django

Para rodar este backend aplicação você deverá seguir os passos abaixo.

1. Com o CMD aberto e a env conda ativada, execute os comandos abaixo para criar o banco de dados e as tabelas:
```bash
  python manage.py makemigrations
  python manage.py migrate
```

2. Crie um super usuário para acessar o admin
```bash
  python manage.py createsuperuser
```

3. Rode o servidor
```bash
  python manage.py runserver
```

## 🔮 Outras informações

### Swagger

Tomei a liberdade de incrementar ainda mais a qualidade de projeto backend adicionando mais uma camada para futuros
desenvolvedores terem acesso a documentação da API, o Swagger.

A ideia é simplificar o desenvolvimento desta API pois esta ferramenta pode nos ajudar a projetar e documentar as APIs
em escala.

Para acessar a documentação da API, acesse o link abaixo:

```bash
  http://localhost:8000/swagger/
```

Neste link será possível visualizar todos os endpoints disponíveis, bem como os métodos permitidos e os parâmetros
necessários para cada endpoint.

### Testes

Todos os testes criados são testes de integração, pois não haveria necessidade de implementação de testes unitários
visto que o sistema ainda é pequeno, e todas as funções e métodos implementados são utilizados dentro dos testes de
integração, portanto, os comportamentos esperados de cada função são testados nestes testes de integração.

Para rodar os testes de integração implementados, basta executar o comando abaixo:

```bash
  python manage.py test
```

### Endpoints para Autenticação

- [x] POST /api/auth/register/

Cria um novo usuário. É necessário enviar o username, email e password.

  ``` json
    {
      "username": "caio",
      "email": "caio@gmail.com",
      "password": "Admin123!"
    }
  ```

- [x] POST /api/auth/login/

Faz o login do usuário. Após o login você receberá um Token de autorização para você poder realizar as consultas neste
backend.
O Token deve ser enviado no cabeçalho no padrão:

```
Token <token_hash>
```

Os dados a serem enviados são:

``` json
  {
      "username": "caio",
      "password": "Admin123!"
    }
```

- [x] POST /api/auth/logout/ - Faz o logout do usuário. Requer o Token de autorização.
- [x] GET /api/auth/user/ - Retorna os dados do usuário logado. Requer o Token de autorização.

### Docker

Além da instalação manual, o projeto também pode ser executado em um container Docker. Para isso, temos dois caminhos
bem fáceis. Assim, basta seguir os passos abaixo:

#### Primeiro caminho

Com o docker e docker-compose instalados, basta rodar o comando abaixo na raiz do projeto backend:

```bash
  docker-compose up --build
```

A aplicação já estará rodando em http://localhost:8000

#### Segundo caminho

1 - Crie a imagem do projeto

```bash
  docker build -t backend .
```

2 - Rode o container

```bash
  docker run -p 8000:8000 backend
```

3 - Acesse o endereço do backend:

```bash
  http://localhost:8000/
```


Credenciais:

```bash
username: admin
password: Admin123!
```

## Autor

<a href="#">
 <img style="border-radius: 50%;" src="https://avatars.githubusercontent.com/u/7137962?v=4" width="100px;" alt=""/>
</a>
 <br />
 <sub><b>Caio Marinho</b></sub>
 <a href="#" title="Caio Marinho">🚀</a>

[![Linkedin Badge](https://img.shields.io/badge/-Caio%20Marinho-blue?style=flat-square&logo=Linkedin&logoColor=white&link=https://www.linkedin.com/in/caiomarinho/)](https://www.linkedin.com/in/caiomarinho/)
[![Gmail Badge](https://img.shields.io/badge/-caiomarinho8@gmail.com-c14438?style=flat-square&logo=Gmail&logoColor=white&link=mailto:caiomarinho8@gmail.com)](mailto:caiomarinho8@gmail.com)

Made with ❤️ by [Caio Marinho!](https://www.linkedin.com/in/caiomarinho/)
👋🏽 [Get in Touch!](https://www.linkedin.com/in/caiomarinho/)
