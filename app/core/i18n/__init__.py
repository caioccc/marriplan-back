"""
Internationalization module for Marriplan.

This module provides internationalization support for the Marriplan system,
allowing for multilingual operation without hardcoded strings.
"""

from .localization import LocalizationManager
from .patterns import PatternManager
from .constants import SupportedLanguages, MessageTypes

__all__ = ['LocalizationManager', 'PatternManager', 'SupportedLanguages', 'MessageTypes']