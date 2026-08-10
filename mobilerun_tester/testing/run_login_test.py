#!/usr/bin/env python3
"""
Standalone Login Test Runner for Mobilerun Tester

This script demonstrates how to execute a login test using the MobileAgent framework.
It loads a scenario, initializes MobileAgent with proper configuration, and runs the test.
"""

import asyncio
import yaml
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import required modules
from mobilerun.agent.droid.droid_agent import MobileAgent
from mobilerun.agent.droid.state import MobileAgentState
from mobilerun.config_manager.config_manager import DEFAULT_DISABLED_TOOLS
from mobilerun.telemetry import capture, flush
from mobilerun.config_manager.config import MobileConfig, AgentConfig
from mobilerun.credential_manager import CredentialManager, FileCredentialManager
from mobilerun.tools.ui.provider import AndroidStateProvider
from mobilerun.tools.ui.screenshot_provider import ScreenshotOnlyStateProvider
from mobilerun.macro.recorder import MacroRecorder
from mobilerun.tools.filters import ConciseFilter
from mobilerun.tools.formatters import IndexedFormatter

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestResult:
    """Represents the result of a test execution"""
    def __init__(self):
        self.success = True
        self.error = None
        self.steps_executed = 0
        self.screenshot_path = None
        self.final_ui_state = None

async def create_test_driver_and_provider(package_name: str = None, 
                                          app_path: str = None, 
                                          device_serial: str = None):
    """Create a driver and state provider for testing"""
    try:
        from mobilerun_core_local.driver.android import AndroidDriver
        from mobilerun_core_local.driver.iextended_adb import IExtendedAdb
        from mobilerun_core_local.driver.base import DeviceMode
        
        # Auto-setup portal if needed
        driver = AndroidDriver(
            serial=device_serial or "emulator-5554",  # Default emulator
            use_tcp=False,
            portal_mode="disabled",  # Will be enabled if auto_setup is True
        )
        
        # Connect to device
        await driver.connect()
        
        # Enable auto-setup if needed (this would be configurable)
        # await ensure_portal_ready(driver)  # Would be called based on config
        
        # Create state provider
        vision_enabled = False  # Will be determined by agent config
        state_provider = AndroidStateProvider(
            driver,
            tree_filter=ConciseFilter() if vision_enabled else DetailedFilter(),
            tree_formatter=IndexedFormatter(),
            use_normalized=False,
            stealth=False,
            vision_enabled=vision_enabled,
        )
        
        return driver, state_provider
    except Exception as e:
        logger.error(f"Failed to create driver/provider: {e}")
        raise

async def setup_mobile_agent_from_scenario(scenario_path: str, 
                                          agent_reasoning: bool = True,
                                          device_serial: str = None,
                                          package_name: str = None,
                                          app_path: str = None):
    """Create and configure MobileAgent from a scenario file"""
    try:
        # Load scenario
        with open(scenario_path, 'r') as f:
            scenario_data = yaml.safe_load(f)
        
        scenario_name = scenario_data.get('name', 'Unknown Test')
        description = scenario_data.get('description', '')
        steps = scenario_data.get('steps', [])
        post_conditions = scenario_data.get('postconditions', [])
        
        logger.info(f"🧪 Loading scenario: {scenario_name}")
        logger.info(f"   Description: {description}")
        logger.info(f"   Steps: {len(steps)}")
        
        # Setup driver and provider
        driver, state_provider = await create_test_driver_and_provider(
            package_name=package_name, 
            app_path=app_path, 
            device_serial=device_serial
        )
        
        # Configure MobileAgent
        agent_config = AgentConfig(
            name="droidrun",
            reasoning=agent_reasoning,
            max_steps=10,
            vision_only=False,
            manager={
                "stateless": False,
                "vision": True,
                "max_thoughts": 5,
            },
            executor={
                "vision": True,
                "max_steps": 5,
            },
            fast_agent={
                "vision": True,
            },
            # Disable coordinate-dependent tools for non-visual modes
            disabled_tools=DEFAULT_DISABLED_TOOLS,
        )
        
        config = MobileConfig(
            agent=agent_config,
            device=None,  # Will be populated from driver
            tools=None,   # Would come from config
            logging={
                "debug": True,
                "save_trajectory": "disk",
                "trajectory_path": "./trajectories",
                "save_logs": True,
                "log_level": "INFO",
            },
            telemetry={
                "enabled": False,  # Disable telemetry for test
            },
            traces_sample_rate=None,
        )
        
        # Initialize MobileAgent
        shared_state = MobileAgentState(
            instruction=f"Run login test: {scenario_name}",
            err_to_manager_thresh=2,
            user_id="test_user",
            runtype="developer",
        )
        
        agent = MobileAgent(
            goal=shared_state.instruction,
            config=config,
            llms=None,  # Will use default LLMs
            driver=driver,
            state_provider=state_provider,
            variables={},
        )
        
        # Override some configs for testing
        agent.shared_state.custom_variables = {
            "goal": scenario_name,
            "description": description,
            "steps": steps,
            "postconditions": post_conditions,
        }
        
        # Save scenario data to shared state for reference
        agent.shared_state.scenario_data = scenario_data
        
        logger.info("✅ MobileAgent configured and ready")
        return agent, driver, state_provider
        
    except Exception as e:
        logger.error(f"Failed to setup MobileAgent: {e}")
        raise

async def run_login_test():
    """Execute the login test"""
    parser = argparse.ArgumentParser(description="Run login test with MobileAgent")
    parser.add_argument("--scenario", type=str, required=True, 
                       help="Path to scenario YAML file")
    parser.add_argument("--device", type=str, default=None,
                       help="Device serial to use")
    parser.add_argument("--reasoning", type=str, default="yes",
                       choices=["yes", "no"],
                       help="Use reasoning mode (Manager+Executor)")
    
    args = parser.parse_args()
    
    # Setup agent
    agent, driver, state_provider = await setup_mobile_agent_from_scenario(
        scenario_path=args.scenario,
        agent_reasoning=(args.reasoning == "yes"),
        device_serial=args.device,
    )
    
    try:
        # Run the agent
        logger.info("🚀 Starting MobileAgent execution...")
        result_event = await agent.run()
        
        # Process the result
        logger.info(f"🏁 Test completed with status: {result_event.success}")
        if result_event.reason:
            logger.info(f"   Reason: {result_event.reason}")
        
        return result_event.success
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            await agent.finalize()
        except:
            pass
            
        try:
            await driver.disconnect()
        except:
            pass

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run login test")
    parser.add_argument("--scenario", type=str, required=True,
                       help="Path to scenario YAML file")
    parser.add_argument("--device", type=str, default=None,
                       help="Device serial (default: first connected)")
    parser.add_argument("--reasoning", type=str, default="yes",
                       choices=["yes", "no"],
                       help="Use reasoning mode")
    
    args = parser.parse_args()
    
    try:
        success = await run_login_test()
        if success:
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
        return 0 if success else 1
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)