# 🔐 IAM Lab com Keycloak + FastAPI (RBAC)

Projeto de laboratório para demonstrar **controle de acesso baseado em papéis (RBAC)** usando **Keycloak 24**, **FastAPI** e **Docker Compose**.  
Inclui autenticação via Keycloak, API protegida com JWT, e testes automatizados no Postman.

---

## 🚀 Stack
- Keycloak 24 (IAM)
- PostgreSQL (storage do Keycloak)
- FastAPI (API protegida)
- Docker Compose (infra)
- Postman (coleção de testes)

---

## ⚙️ Estrutura do Projeto
```bash
keycloak-lab/
├── docs/              # prints ou diagramas
├── keycloak/          # configs relacionadas ao Keycloak
├── postman/           # coleção de testes (JSON)
├── service-a/         # API FastAPI (service-a)
├── docker-compose.yml # sobe Keycloak + Postgres
├── .gitignore
└── README.md
```
---

## 🛠️ Setup

### 1. Subir Keycloak + Postgres
docker-compose up -d

### 2. Rodar a API
cd service-a
uvicorn main:app --reload

---

## 🔑 Configuração no Keycloak
- Realm: lab-iam
- Roles (realm):  
  - admin  
  - analyst  
  - viewer  
- Usuários:
  - alice / Senha!123 → admin
  - bruno / Senha!123 → analyst
  - carol / Senha!123 → viewer
- Client: lab-api (public, Direct Access Grants = ON)
- Issuer: http://localhost:8080/realms/lab-iam

---

## 📡 API (FastAPI)
Rota       | Método | Proteção
-----------|--------|----------------------
/health    | GET    | Pública
/reports   | GET    | admin ou analyst
/admin     | GET    | apenas admin

---

## 🧪 Testes (Postman)
- Requests de token para cada usuário (alice, bruno, carol).  
- Requests para /reports e /admin com validação de status code.  
- Scripts que salvam tokens em variáveis da Collection.  
- (Opcional) Pre-request Script que renova o token automaticamente.

---

## ✅ Demonstração RBAC
Usuário | Role    | /reports | /admin
--------|---------|----------|-------
alice   | admin   | 200 OK   | 200 OK
bruno   | analyst | 200 OK   | 403
carol   | viewer  | 403      | 403

---

## 📷 Demonstração

### Rotas no Swagger
![Swagger Docs](docs/swagger_routes.png)

### Teste de RBAC no Postman
- Alice (admin) acessando `/reports` → **200 OK**  
![Postman Alice](docs/postman_reports_alice.png)

- Carol (viewer) acessando `/reports` → **403 Forbidden**  
![Postman Carol](docs/postman_reports_carol.png)

### Roles e Usuários no Keycloak
- Roles configuradas no Realm `lab-iam`  
![Keycloak Roles](docs/keycloak_roles.png)

- Usuários e suas permissões  
![Keycloak Users](docs/keycloak_users.png)

### Containers rodando com Docker
![Docker ps](docs/docker_ps.png)

---

## 📌 Próximos Passos (Ideias de evolução)
- Adicionar refresh token.  
- Configurar Client Roles no lugar de Realm Roles.  
- Proteger múltiplos microservices.  
- Deploy em Kubernetes.

---

## ▶️ Como rodar este projeto localmente

### Pré-requisitos
- Docker Desktop (ou Docker + Compose)
- Python 3.11+ (para rodar a API)
- Postman (para testar os fluxos)

### 1) Clonar o repositório
git clone https://github.com/luciendelalves/keycloak-lab.git
cd keycloak-lab

### 2) Subir Keycloak + Postgres (Docker)
docker-compose up -d
- Console do Keycloak: http://localhost:8080  
  Login inicial: admin / admin

### 3) Criar Realm, Roles, Users e Client no Keycloak
- Realm: lab-iam
- Roles (realm): admin, analyst, viewer
- Users:
  - alice / Senha!123 → role admin
  - bruno / Senha!123 → role analyst
  - carol / Senha!123 → role viewer
- Client: lab-api (public)
  - Direct Access Grants: ON
- Issuer (conferir): http://localhost:8080/realms/lab-iam

### 4) Rodar a API (FastAPI)
cd service-a
python -m venv .venv
# Windows:
. .venv/Scripts/activate
# Linux/Mac:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
- Swagger: http://127.0.0.1:8000/docs

### 5) Testar com Postman
1. Importar postman/lab-iam.postman_collection.json.
2. Em Variables da Collection, confira:
   - base_url = http://127.0.0.1:8000
   - keycloak_base = http://localhost:8080
   - realm = lab-iam
   - client_id = lab-api
3. Executar:
   - POST token — alice/bruno/carol (salvam token_* na Collection).
   - GET /reports (alice) → 200 OK
   - GET /reports (carol) → 403 Forbidden
   - GET /admin (alice) → 200 OK
   - GET /admin (bruno/carol) → 403 Forbidden

### ✅ Resultado esperado (RBAC)
Usuário | Role    | /reports | /admin
--------|---------|----------|-------
alice   | admin   | 200      | 200
bruno   | analyst | 200      | 403
carol   | viewer  | 403      | 403

### 🔧 Troubleshooting rápido
- 401 invalid_token / expired: gere novamente o token no Postman (requests de token).
- 403 indevido: confira se a API lê realm_access.roles (não resource_access) e se as roles estão corretas no usuário.
- JWKS/issuer: em service-a/auth.py, o ISSUER deve ser http://localhost:8080/realms/lab-iam.
- Portas ocupadas: libere 8080 (Keycloak) e 5432 (Postgres) ou ajuste no docker-compose.yml.

---

## 👨‍💻 Autor
Luciendel Alves | Estudante de Cibersegurança
