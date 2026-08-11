#!/bin/sh
# Migrations sempre antes de servir; seed opcional para demonstracao.
# O worker compartilha esta imagem, mas nao deve migrar (evita corrida com a API).
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Aplicando migrations..."
  alembic upgrade head
fi

if [ "${RUN_SEED}" = "true" ]; then
  echo "Executando seed..."
  python seed.py || echo "Seed ignorado (dados ja existentes)."
fi

exec "$@"
