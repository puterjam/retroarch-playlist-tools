"""
Data Models Module
Common data structures used across the toolkit
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict


@dataclass
class ROMInfo:
    """ROM file information"""
    path: str
    filename: str
    system: str
    extension: str
    size: int
    size_formatted: str
    crc32: Optional[str] = None
    normalized_name: str = ""
    is_hack: bool = False
    base_game_name: Optional[str] = None
    region: Optional[str] = None
    matched: bool = False
    game_name: Optional[str] = None
    release_year: Optional[int] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
