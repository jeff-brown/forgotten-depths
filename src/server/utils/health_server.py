"""Lightweight HTTP health check server for Kubernetes probes."""

import asyncio
from aiohttp import web
from ..utils.logger import get_logger


class HealthServer:
    """Simple HTTP server for Kubernetes health checks."""

    def __init__(self, game_engine, port=8081):
        """Initialize the health server."""
        self.game_engine = game_engine
        self.port = port
        self.logger = get_logger()
        self.app = None
        self.runner = None

    async def health_check(self, request):
        """Health check endpoint."""
        # Check if game engine is running
        if self.game_engine.running:
            return web.Response(text="OK", status=200)
        else:
            return web.Response(text="Not Ready", status=503)

    async def readiness_check(self, request):
        """Readiness check endpoint."""
        # Check if game engine is running and world is loaded
        if self.game_engine.running and self.game_engine.world_manager.rooms:
            return web.Response(text="Ready", status=200)
        else:
            return web.Response(text="Not Ready", status=503)

    async def start(self):
        """Start the health server."""
        try:
            self.app = web.Application()
            self.app.router.add_get('/healthz', self.health_check)
            self.app.router.add_get('/readyz', self.readiness_check)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await site.start()
            
            self.logger.info(f"Health check server started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to start health server: {e}")

    async def stop(self):
        """Stop the health server."""
        if self.runner:
            await self.runner.cleanup()
            self.logger.info("Health check server stopped")
