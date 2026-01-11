"""
Base Bank API Interface for Depot Tracker.

This module defines the abstract base class for all bank API implementations.
It provides a common interface and shared functionality for different banking
APIs (like Comdirect, ING, etc.) while allowing each implementation to handle
their specific authentication and data retrieval procedures.

The base class handles:
- Common file I/O operations for storing API responses
- Data sanitization and type conversion
- Consistent folder structure for different depot data
- Abstract methods that must be implemented by concrete bank APIs
"""
import os
import json
from typing import Union, Dict, List, Any, Optional
from abc import ABC, abstractmethod
import yaml


class BaseBankAPI(ABC):
    """
    Abstract base class for bank API implementations.
    
    This class provides a common interface for all banking APIs used in the
    depot tracker application. It defines the contract that all bank-specific
    implementations must follow while providing shared functionality for
    data storage and manipulation.
    
    Each bank API implementation must provide:
    - Authentication procedures specific to their API
    - Position retrieval methods
    - Statement/transaction history access
    
    The base class handles common tasks like file operations, data sanitization,
    and consistent folder structure management.
    """
    
    def __init__(self, depot_name: str) -> None:
        """
        Initialize the base bank API instance.
        
        Sets up the basic properties common to all bank API implementations,
        including the depot name and data folder structure. Each depot gets
        its own folder under the data directory for organized storage.
        
        Args:
            depot_name: Human-readable name for the depot (e.g., "Growth Portfolio")
        """
        self.name: str = depot_name
        self.account_id: Optional[str] = None
        
        # Inform user about data source for transparency
        print(f"📊 Using REAL DATA for {self.name} (from last synchronized depot data)")
        
        # Set up data folder structure for this depot
        self.data_folder: str = os.path.join("data", self.name)
        
        # Ensure data folder exists for storing API responses
        os.makedirs(self.data_folder, exist_ok=True)

    def get_name(self) -> str:
        """
        Get the depot name.
        
        Returns the human-readable name of this depot, used for display
        purposes and folder organization.
        
        Returns:
            The depot name as configured during initialization
        """
        return self.name

    # ---------------------------
    # Abstract methods - must be implemented by concrete bank APIs
    # ---------------------------
    
    @abstractmethod
    def authenticate(self) -> None:
        """
        Perform bank-specific authentication procedure.
        
        This method must be implemented by each bank API to handle their
        specific authentication requirements. This might include:
        - OAuth2 flows
        - Username/password authentication
        - Two-factor authentication
        - API key validation
        
        Raises:
            NotImplementedError: If not implemented by concrete class
        """
        pass

    @abstractmethod
    def _get_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieve current depot positions from the bank API.
        
        This method must be implemented to fetch the current holdings
        in the depot, including quantities, prices, and other position data.
        
        Returns:
            List of position dictionaries containing stock/fund holdings
            
        Raises:
            NotImplementedError: If not implemented by concrete class
        """
        pass

    @abstractmethod
    def _get_statements(self) -> List[Dict[str, Any]]:
        """
        Retrieve bank statements and transaction history.
        
        This method must be implemented to fetch historical transaction
        data, typically covering several years of depot activity including
        purchases, sales, dividends, and fees.
        
        Returns:
            List of statement/transaction dictionaries
            
        Raises:
            NotImplementedError: If not implemented by concrete class
        """
        pass
    
    # ---------------------------
    # Protected helper methods - shared functionality for concrete implementations
    # ---------------------------
    
    def _sanitize_numbers(self, obj: Any) -> Any:
        """
        Recursively sanitize and convert string numbers to appropriate numeric types.
        
        Bank APIs often return numeric values as strings, which can cause issues
        with calculations. This method recursively traverses data structures and
        converts string representations of numbers to proper int or float types.
        
        Args:
            obj: The object to sanitize (dict, list, str, or other type)
            
        Returns:
            The sanitized object with string numbers converted to numeric types
        """
        if isinstance(obj, dict):
            # Recursively process dictionary values
            return {k: self._sanitize_numbers(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            # Recursively process list items
            return [self._sanitize_numbers(i) for i in obj]
        elif isinstance(obj, str):
            # Try to convert string to number if it looks like a number
            try:
                # Use float if decimal point exists, otherwise int
                return float(obj) if "." in obj else int(obj)
            except ValueError:
                # Return original string if conversion fails
                return obj
        else:
            # Return non-string types unchanged
            return obj

    def _write_data(self, filename: str, data: Union[Dict[str, Any], List[Any]]) -> None:
        """
        Write data to a JSON file in the depot's data folder.
        
        This method handles the file I/O for storing API responses and processed
        data. It creates properly formatted JSON files with indentation for
        readability and debugging purposes.
        
        Args:
            filename: Name of the file to create (e.g., "positions.json")
            data: The data structure to save (dict or list)
        """
        file_path: str = os.path.join(self.data_folder, filename)
        
        # Write data with pretty formatting for easier debugging
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"💾 New data stored: {file_path}")

    def _save_positions(self, normalize: bool = True, init_value: int = 50000) -> None:
        """
        Save current depot positions to file.
        
        Retrieves current positions from the bank API and saves them to the
        depot's positions.json file. This creates a local cache of position
        data that can be used even when the API is unavailable.
        
        Args:
            normalize: Whether to normalize/sanitize the data before saving
            init_value: Initial value parameter (for compatibility with legacy code)
        """
        positions_data = self._get_positions()
        
        # Sanitize numeric data if requested
        if normalize:
            positions_data = self._sanitize_numbers(positions_data)
            
        self._write_data("positions.json", positions_data)

    def _save_statements(self) -> None:
        """
        Save bank statements and transaction history to file.
        
        Retrieves statement data from the bank API and saves it to the depot's
        statements.json file. This includes transaction history, dividends,
        and other account activities.
        """
        statements_data = self._get_statements()
        self._write_data("statements.json", statements_data)

    def _save_depot_id(self) -> None:
        """
        Save the depot ID to file for reference.
        
        Stores the depot/account ID in a separate file for tracking purposes
        and API reference. This ID is typically used in subsequent API calls.
        """
        depot_data = {"depot_id": self.depot_id}
        self._write_data("depot_id.json", depot_data)
