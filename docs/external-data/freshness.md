# Freshness

Estados: `FRESH`, `DUE_SOON`, `STALE`, `UNKNOWN`, `SOURCE_UNAVAILABLE`.

Intervalo esperado depende da frequência da série + `freshness_grace_minutes`.

Série semanal **não** fica STALE por ausência de observação diária.
