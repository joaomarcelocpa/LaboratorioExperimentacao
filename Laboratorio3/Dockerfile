# Ambiente reprodutível da coleta. O grupo replicador roda isto sem instalar
# Python na máquina — só precisa do token no ambiente.
FROM python:3.12-slim

WORKDIR /app

# As dependências vêm antes do código para que um commit não invalide a
# camada de instalação.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# O cache fica aqui: sem o volume, ele morre junto com o container e a
# retomada deixa de existir.
VOLUME ["/app/data"]

ENTRYPOINT ["python", "-m", "pipeline"]
CMD ["--config", "config.yaml"]
