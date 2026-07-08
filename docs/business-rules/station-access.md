# Acesso por posto

## Regras

1. Usuário acessa somente postos em `user_stations`, exceto quando `has_all_stations_access=true` (ADMIN).
2. Posto inativo não aparece no seletor padrão.
3. Header `X-Station-Id` é validado pelo backend quando informado.
4. Seletor do frontend não concede permissão — apenas contexto de visualização.

## Seletor

- Persistência local: `active_station_id`
- Opção "Todos os postos" quando há mais de um posto autorizado
