from app.schemas.health import ServiceHealth, ServicesHealthMap
from app.services.health import _aggregate_status


def test_aggregate_healthy() -> None:
    healthy = ServiceHealth(status="healthy", response_time_ms=1)
    services = ServicesHealthMap(
        api=healthy,
        database=healthy,
        redis=healthy,
        object_storage=healthy,
    )
    assert _aggregate_status(services) == "healthy"


def test_aggregate_degraded_when_redis_down() -> None:
    healthy = ServiceHealth(status="healthy", response_time_ms=1)
    unhealthy = ServiceHealth(status="unhealthy", message="Service unavailable")
    services = ServicesHealthMap(
        api=healthy,
        database=healthy,
        redis=unhealthy,
        object_storage=healthy,
    )
    assert _aggregate_status(services) == "degraded"


def test_aggregate_unhealthy_when_database_down() -> None:
    healthy = ServiceHealth(status="healthy", response_time_ms=1)
    unhealthy = ServiceHealth(status="unhealthy", message="Service unavailable")
    services = ServicesHealthMap(
        api=healthy,
        database=unhealthy,
        redis=healthy,
        object_storage=healthy,
    )
    assert _aggregate_status(services) == "unhealthy"
