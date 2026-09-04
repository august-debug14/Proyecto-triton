import asyncio
import json
import logging
from typing import Any, Dict, List

import httpx

from .exceptions import (
    CorruptedPayloadError,
    NetworkPeeringError,
    ProviderTimeoutError,
)

logger = logging.getLogger("triton_monitor")

PROVIDER_ENDPOINTS: Dict[str, str] = {
    "AWS": "https://jsonplaceholder.typicode.com/posts/1",
    "Azure": "https://jsonplaceholder.typicode.com/posts/2",
    "GCP": "https://jsonplaceholder.typicode.com/posts/3",
}

CHAOS_ENDPOINTS: Dict[str, str] = {
    "TIMEOUT_TRIGGER": "https://httpbin.org/delay/3",      
    "BAD_GATEWAY_TRIGGER": "https://httpbin.org/status/504", 
    "CORRUPTED_TRIGGER": "https://httpbin.org/xml",        
}


async def query_provider_telemetry(
    provider: str,
    timeout: float,
    use_chaos: bool = False,
) -> Dict[str, Any]:
    """Consulta la telemetría de un proveedor en internet de forma asíncrona.
    """
    if use_chaos:
        if provider == "AWS":
            url = CHAOS_ENDPOINTS["TIMEOUT_TRIGGER"]
        elif provider == "Azure":
            url = CHAOS_ENDPOINTS["BAD_GATEWAY_TRIGGER"]
        else:
            url = CHAOS_ENDPOINTS["CORRUPTED_TRIGGER"]
    else:
        url = PROVIDER_ENDPOINTS.get(provider, "https://jsonplaceholder.typicode.com/posts/1")

    logger.debug(
        f"Iniciando petición asíncrona hacia {provider} en {url}",
        extra={"provider": provider, "target_url": url},
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=timeout)

            response.raise_for_status()

            try:
                data = response.json()
                logger.info(
                    f"Telemetría recibida exitosamente de {provider}",
                    extra={"provider": provider, "status_code": response.status_code},
                )

                return {
                    "provider": provider,
                    "status": "NOMINAL",
                    "latency_sec": response.elapsed.total_seconds(), 
                    "payload_id": data.get("id", -1),
                }

            except (json.JSONDecodeError, ValueError) as err:
                corrupt_err = CorruptedPayloadError(
                    f"El proveedor {provider} devolvió un payload no serializable o con datos corruptos."
                )
                corrupt_err.add_note(f"Provider_ID: {provider}")
                corrupt_err.add_note(f"Target_Endpoint: {url}")
                raise corrupt_err from err

        except httpx.TimeoutException as err:
            timeout_err = ProviderTimeoutError(
                f"Se agotó el tiempo de espera ({timeout}s) al conectar con {provider}."
            )
            timeout_err.add_note(f"Provider_ID: {provider}")
            timeout_err.add_note(f"Requested_Timeout_Limit: {timeout}s")
            timeout_err.add_note(f"Target_Endpoint: {url}")
            raise timeout_err from err

        except httpx.HTTPStatusError as err:
            status_err = NetworkPeeringError(
                f"Fallo de conexión o denegación de ruteo de {provider}. Estatus HTTP: {err.response.status_code}."
            )
            status_err.add_note(f"Provider_ID: {provider}")
            status_err.add_note(f"HTTP_Status_Code: {err.response.status_code}")
            status_err.add_note(f"Target_Endpoint: {url}")
            raise status_err from err

        except httpx.RequestError as err:
            net_err = NetworkPeeringError(
                f"Error crítico de transporte de red al intentar alcanzar {provider}."
            )
            net_err.add_note(f"Provider_ID: {provider}")
            net_err.add_note(f"Network_Error_Type: {type(err).__name__}")
            net_err.add_note(f"Target_Endpoint: {url}")
            raise net_err from err


async def scan_all_providers(
    providers: List[str],
    timeout: float,
    use_chaos: bool = False,
) -> List[Dict[str, Any]]:
    """Ejecuta en paralelo las colsultas de todos los proveedores.
    """
    tasks = []
    results = []

    async with asyncio.TaskGroup() as tg:
        for provider in providers:
            task = tg.create_task(
                query_provider_telemetry(provider, timeout, use_chaos),
                name=f"Task-{provider}",
            )
            tasks.append(task)

    for task in tasks:
        results.append(task.result())

    return results
