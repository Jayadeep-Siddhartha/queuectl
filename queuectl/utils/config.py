"""
Configuration management with persistent storage
"""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """
    Manages application configuration with persistent storage
    Configuration is stored in JSON format
    """
    
    DEFAULT_CONFIG = {
        'max_retries': 3,
        'backoff_base': 2.0,
        'job_timeout': 300,  # 5 minutes default timeout
        'poll_interval': 1,  # Worker poll interval in seconds
        'worker_shutdown_timeout': 10,  # Timeout for graceful worker shutdown
    }
    
    def __init__(self, config_file: str = "queuectl_config.json"):
        """
        Initialize configuration
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or create with defaults
        
        Returns:
            Configuration dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)
                    return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load configuration: {e}")
                print("Using default configuration")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create new config file with defaults
            config = self.DEFAULT_CONFIG.copy()
            self._save_config(config)
            return config
    
    def _save_config(self, config: Dict[str, Any] = None):
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save (uses self.config if None)
        """
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set configuration value and persist to file
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value
        self._save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values
        
        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()
    
    def reset(self):
        """Reset configuration to defaults"""
        self.config = self.DEFAULT_CONFIG.copy()
        self._save_config()
    
    def validate(self) -> bool:
        """
        Validate configuration values
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate max_retries
            if not isinstance(self.config.get('max_retries'), int) or self.config['max_retries'] < 0:
                print("Error: max_retries must be a non-negative integer")
                return False
            
            # Validate backoff_base
            if not isinstance(self.config.get('backoff_base'), (int, float)) or self.config['backoff_base'] <= 0:
                print("Error: backoff_base must be a positive number")
                return False
            
            # Validate job_timeout
            if not isinstance(self.config.get('job_timeout'), int) or self.config['job_timeout'] <= 0:
                print("Error: job_timeout must be a positive integer")
                return False
            
            return True
            
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False
    
    def __str__(self) -> str:
        """String representation of configuration"""
        return json.dumps(self.config, indent=2)
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"Config(file='{self.config_file}', values={self.config})"