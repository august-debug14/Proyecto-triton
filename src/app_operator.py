import sys
import argparse
import asyncio
import logging
from triton_telemetry import (
    setup_triton_logging,
    scan_all_providers,
    parse_timeout,
    parse_cluster_id,
    ProviderTimeoutError,
    NetworkPeeringError,
    CorruptedPayloadError,
    TritonError
)

logger = setup_triton_logging()


def build_cli_parser() -> argparse.ArgumentParser:
    """Configura el analizador CLI oficial."""
    parser = argparse.ArgumentParser(
        prog="TritonMonitor",
        description="Consola de Telemetria Multicloud y Observabilidad Asincrona (PROYECTO TRITON)."
    )

    parser.add_argument(
        "proveedores",
        nargs="+",
        choices=["AWS", "Azure", "GCP"],
        help="Lista de identificadores de los proveedores cloud a monitorear."
    )

    parser.add_argument(
        "-c", "--cluster-id",
        type=parse_cluster_id,
        required=True,
        help="Identificador unico del cluster."
    )

    parser.add_argument(
        "-t", "--timeout",
        type=parse_timeout,
        default=2.5,
        help="Tiempo de espera limite (0.1s - 5.0s)."
    )

    parser.add_argument(
        "--chaos",
        action="store_true",
        help="Forzar inyeccion de caos."
    )

    parser.add_argument(
        "-m", "--mode",
        choices=["nominal", "debug", "emergency"],
        default="nominal",
        help="Modo de operacion."
    )

    return parser


async def async_main():
    parser = build_cli_parser()
    args = parser.parse_args()

    logger.info("=" * 64)
    logger.info("INICIANDO MONITOREO MULTICLOUD: PROYECTO TRITON")
    logger.info("=" * 64)
    logger.info(f"Cluster Objetivo: {args.cluster_id}")
    logger.info(f"Modo Operativo: {args.mode.upper()}")
    logger.info(f"Proveedores seleccionados: {', '.join(args.proveedores)}")
    logger.info(f"Timeout limite configurado: {args.timeout}s")
    if args.chaos:
        logger.warning("ADVERTENCIA: MODO CAOS ACTIVADO.")
    logger.info("=" * 64)

    try:
        results = await scan_all_providers(args.proveedores, args.timeout, use_chaos=args.chaos)
        logger.info("ESCANEO COMPLETADO CON EXITO:")
        for r in results:
            logger.info(f"  {r['provider']} -> Latencia: {r['latency_sec']:.3f}s | ID: {r['payload_id']}")

    except* ProviderTimeoutError as group:
        logger.error(f"TIMEOUTS DETECTADOS ({len(group.exceptions)} incidentes):")
        for exc in group.exceptions:
            logger.error(f"  Fallo: {exc}")
            for note in getattr(exc, "__notes__", []):
                logger.error(f"      [FORENSE] {note}")

    except* NetworkPeeringError as group:
        logger.error(f"FALLOS DE RED DETECTADOS ({len(group.exceptions)} incidentes):")
        for exc in group.exceptions:
            logger.error(f"  Fallo: {exc}")
            for note in getattr(exc, "__notes__", []):
                logger.error(f"      [FORENSE] {note}")

    except* CorruptedPayloadError as group:
        logger.error(f"PAYLOADS CORRUPTOS ({len(group.exceptions)} incidentes):")
        for exc in group.exceptions:
            logger.error(f"  Fallo: {exc}")

    except* TritonError as group:
        logger.error("ERROR OPERACIONAL IMPREVISTO:")
        for exc in group.exceptions:
            logger.error(f"  Fallo: {exc}")

    finally:
        logger.info("[FIN DE CICLO]")
        if hasattr(logger, "listener") and logger.listener:
            logger.listener.stop()


if __name__ == "__main__":
    asyncio.run(async_main())