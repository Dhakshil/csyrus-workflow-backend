from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint.

    Used by:
    - Load balancers (to know if the app is alive)
    - Kubernetes readiness probes
    - Frontend (to verify backend connectivity during development)
    - Monitoring systems (PagerDuty, Datadog, etc.)
    """
    return {"status": "healthy"}