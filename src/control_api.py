"""Control API for runtime management using FastAPI."""
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import threading
import time

logger = logging.getLogger(__name__)


class SpikeRequest(BaseModel):
    """Request to trigger a spike in metric values."""
    metric: str
    multiplier: float
    duration_s: int


class ErrorRateRequest(BaseModel):
    """Request to inject error rate."""
    metric: str
    rate: float
    duration_s: int


class ScenarioRequest(BaseModel):
    """Request to start/stop a named scenario."""
    scenario: str


class LogLevelRequest(BaseModel):
    """Request to change log level."""
    level: str


class ControlAPI:
    """FastAPI-based control API for runtime management."""
    
    def __init__(self, engine):
        """
        Initialize control API.
        
        Args:
            engine: Reference to the generator engine
        """
        self.engine = engine
        self.app = FastAPI(title="Synthetic Metrics Generator Control API")
        
        # Active modifiers
        self.active_spikes: Dict[str, Dict[str, Any]] = {}
        self.active_scenarios: Dict[str, bool] = {}
        
        # Thread safety for spike dictionary
        self._spike_lock = threading.Lock()
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/healthz")
        async def healthz():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": time.time()}
        
        @self.app.get("/status")
        async def status():
            """Get current generator status."""
            try:
                # Get spike details with thread safety
                spike_details = {}
                with self._spike_lock:
                    current_time = time.time()
                    for metric_name, spike_info in self.active_spikes.items():
                        remaining = max(0, spike_info["end_time"] - current_time)
                        spike_details[metric_name] = {
                            "multiplier": spike_info["multiplier"],
                            "remaining_seconds": round(remaining, 1),
                            "duration_s": spike_info["duration_s"]
                        }
                
                status_info = {
                    "uptime_seconds": time.time() - self.engine.start_time if hasattr(self.engine, 'start_time') else 0,
                    "tick_count": self.engine.tick_count if hasattr(self.engine, 'tick_count') else 0,
                    "active_metrics": len(self.engine.generators) if hasattr(self.engine, 'generators') else 0,
                    "available_metrics": list(self.engine.generators.keys()) if hasattr(self.engine, 'generators') else [],
                    "total_series": sum(
                        len(gen.label_combinations) 
                        for gen in self.engine.generators.values()
                    ) if hasattr(self.engine, 'generators') else 0,
                    "active_spikes": spike_details,
                    "active_scenarios": [k for k, v in self.active_scenarios.items() if v],
                    "config": {
                        "tick_interval_s": self.engine.config.global_.tick_interval_s if hasattr(self.engine, 'config') else None,
                        "seed": self.engine.config.global_.seed if hasattr(self.engine, 'config') else None,
                    }
                }
                return status_info
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/control/spike")
        async def trigger_spike(request: SpikeRequest):
            """Trigger a spike in metric values."""
            try:
                # Validate that the metric exists
                if not hasattr(self.engine, 'generators'):
                    raise HTTPException(
                        status_code=503,
                        detail="Engine not fully initialized"
                    )
                
                if request.metric not in self.engine.generators:
                    available_metrics = list(self.engine.generators.keys())
                    raise HTTPException(
                        status_code=404,
                        detail=f"Metric '{request.metric}' not found. Available metrics: {available_metrics}"
                    )
                
                logger.info(
                    f"Triggering spike: metric={request.metric}, "
                    f"multiplier={request.multiplier}, duration={request.duration_s}s"
                )
                
                # Store spike info with thread safety
                with self._spike_lock:
                    self.active_spikes[request.metric] = {
                        "multiplier": request.multiplier,
                        "start_time": time.time(),
                        "end_time": time.time() + request.duration_s,
                        "duration_s": request.duration_s
                    }
                
                # Schedule removal
                def remove_spike():
                    time.sleep(request.duration_s)
                    with self._spike_lock:
                        if request.metric in self.active_spikes:
                            del self.active_spikes[request.metric]
                            logger.info(f"Spike ended for metric: {request.metric}")
                
                threading.Thread(target=remove_spike, daemon=True).start()
                
                return {
                    "status": "spike_triggered",
                    "metric": request.metric,
                    "multiplier": request.multiplier,
                    "duration_s": request.duration_s
                }
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error triggering spike: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/control/error_rate")
        async def set_error_rate(request: ErrorRateRequest):
            """Set error injection rate."""
            try:
                logger.info(
                    f"Setting error rate: metric={request.metric}, "
                    f"rate={request.rate}, duration={request.duration_s}s"
                )
                
                # This would be implemented in the engine
                # For now, just log it
                return {
                    "status": "error_rate_set",
                    "metric": request.metric,
                    "rate": request.rate,
                    "duration_s": request.duration_s
                }
            
            except Exception as e:
                logger.error(f"Error setting error rate: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/control/reload")
        async def reload_config():
            """Reload configuration."""
            try:
                logger.info("Reloading configuration...")
                
                if hasattr(self.engine, 'reload_config'):
                    self.engine.reload_config()
                    return {"status": "config_reloaded", "timestamp": time.time()}
                else:
                    raise HTTPException(
                        status_code=501,
                        detail="Config reload not implemented in engine"
                    )
            
            except Exception as e:
                logger.error(f"Error reloading config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/control/scenario")
        async def start_scenario(request: ScenarioRequest):
            """Start a named scenario."""
            try:
                logger.info(f"Starting scenario: {request.scenario}")
                
                self.active_scenarios[request.scenario] = True
                
                return {
                    "status": "scenario_started",
                    "scenario": request.scenario,
                    "timestamp": time.time()
                }
            
            except Exception as e:
                logger.error(f"Error starting scenario: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/control/scenario/{scenario_name}")
        async def stop_scenario(scenario_name: str):
            """Stop a named scenario."""
            try:
                logger.info(f"Stopping scenario: {scenario_name}")
                
                if scenario_name in self.active_scenarios:
                    self.active_scenarios[scenario_name] = False
                
                return {
                    "status": "scenario_stopped",
                    "scenario": scenario_name,
                    "timestamp": time.time()
                }
            
            except Exception as e:
                logger.error(f"Error stopping scenario: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/control/loglevel")
        async def set_log_level(request: LogLevelRequest):
            """Change log level at runtime."""
            try:
                level = request.level.upper()
                
                if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid log level: {level}"
                    )
                
                logging.getLogger().setLevel(getattr(logging, level))
                logger.info(f"Log level changed to: {level}")
                
                return {
                    "status": "log_level_changed",
                    "level": level,
                    "timestamp": time.time()
                }
            
            except Exception as e:
                logger.error(f"Error changing log level: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def get_spike_multiplier(self, metric_name: str) -> float:
        """Get current spike multiplier for a metric."""
        with self._spike_lock:
            if metric_name in self.active_spikes:
                spike_info = self.active_spikes[metric_name]
                current_time = time.time()
                
                # Check if spike is still active
                if current_time < spike_info["end_time"]:
                    remaining = spike_info["end_time"] - current_time
                    logger.debug(
                        f"Active spike for '{metric_name}': multiplier={spike_info['multiplier']}, "
                        f"remaining={remaining:.1f}s"
                    )
                    return spike_info["multiplier"]
                else:
                    # Spike expired, remove it
                    logger.info(f"Spike expired for metric '{metric_name}', removing")
                    del self.active_spikes[metric_name]
            else:
                logger.debug(f"No active spike for metric '{metric_name}'")
        
        return 1.0  # No spike, return 1.0 (no change)
    
    def run(self, host: str = "0.0.0.0", port: int = 8081):
        """Run the API server."""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port, log_level="info")

