"""Style management utilities for the Monitor Prototype application"""

from pathlib import Path
from typing import Dict

class StyleManager:
    """Manages application styles and provides utilities for loading QSS files"""
    
    def __init__(self) -> None:
        self._styles_dir = Path(__file__).parent
        self._loaded_styles: Dict[str, str] = {}
    
    def load_style(self, style_name: str) -> str:
        """Load a QSS style file and return its contents"""
        if style_name in self._loaded_styles:
            return self._loaded_styles[style_name]
        
        style_path = self._styles_dir / f"{style_name}.qss"
        
        if not style_path.exists():
            raise FileNotFoundError(f"Style file not found: {style_path}")
        
        with open(style_path, 'r', encoding='utf-8') as file:
            style_content = file.read()
        
        # Cache the loaded style
        self._loaded_styles[style_name] = style_content
        return style_content
    
    def get_combined_styles(self, *style_names: str) -> str:
        """Combine multiple style files into a single stylesheet"""
        combined_styles = []
        
        for style_name in style_names:
            style_content = self.load_style(style_name)
            combined_styles.append(f"/* {style_name.upper()} STYLES */")
            combined_styles.append(style_content)
            combined_styles.append("")  # Empty line for separation
        
        return "\n".join(combined_styles)
    
    def reload_style(self, style_name: str) -> str:
        """Force reload a style file (useful for development)"""
        if style_name in self._loaded_styles:
            del self._loaded_styles[style_name]
        return self.load_style(style_name)
    
    def get_available_styles(self) -> list[str]:
        """Get a list of all available style files"""
        qss_files = list(self._styles_dir.glob("*.qss"))
        return [file.stem for file in qss_files]
    
    def clear_cache(self) -> None:
        """Clear the style cache (useful for development)"""
        self._loaded_styles.clear()

# Global style manager instance
style_manager = StyleManager()
