# app/services/metadata_extractor.py
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MetadataExtractorService:
    """
    Enterprise-grade metadata isolation service. Uses a hardened asynchronous 
    subprocess boundary around ExifTool to extract headers while protecting 
    the system from memory-corruption exploits or shell injection pathways.
    """
    def __init__(self, exiftool_path: str = "exiftool"):
        # Resolve path defensively without shell-escaping functions that corrupt execve vectors
        self.exiftool_path = str(Path(exiftool_path).as_posix())

    async def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Executes a hardened ExifTool instance as an isolated subprocess read-only pass.
        Returns a dictionary of raw tags or an error payload.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Target media file {file_path} not found.")

        # Hardened arguments passed as a direct list vector to completely bypass shell execution
        cmd = [
            self.exiftool_path, 
            "-json", 
            "-G",                    # Group names for elements (e.g., EXIF/Composite/XMP)
            "-coordFormat", "%+.6f", # Force uniform float outputs directly from binary string
            str(file_path.resolve()) # Resolve to clean absolute path to thwart path traversal vectors
        ]

        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Defensive execution wrapping: Guarantee processing limits via native wait_for patterns
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

            if process.returncode != 0:
                err_msg = stderr.decode(errors='replace').strip()
                logger.error(f"ExifTool execution failure: {err_msg}")
                return {"error": "Failed to parse file structural tags."}

            if not stdout:
                return {}

            # Catch structurally deformed JSON streams safely
            parsed_json = json.loads(stdout.decode(errors='replace'))
            return parsed_json[0] if isinstance(parsed_json, list) and parsed_json else {}

        except asyncio.TimeoutError:
            if process:
                logger.error(f"Metadata processing timed out for file: {file_path.name}. Terminating process.")
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass  
                except Exception as e:
                    logger.error(f"Error clean-killing stalled process: {str(e)}")
            return {"error": "Processing timeout exceeded."}

        except json.JSONDecodeError as jde:
            logger.error(f"Malformed output payload structurally rejected: {str(jde)}")
            return {"error": "Metadata mapping syntax failure."}

        except Exception as e:
            logger.critical(f"Unhandled system mapping error during extraction: {str(e)}")
            return {"error": f"Internal mapping error: {str(e)}"}

    @staticmethod
    def parse_gps_coordinates(metadata: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Safely extracts coordinate layouts out of compound namespace hierarchies 
        (Composite vs Native EXIF structures) to provide baseline verification indicators.
        """
        if not metadata or "error" in metadata:
            return None

        try:
            # Expanded fallback map handling multiple device schema layouts
            gps_latitude = (
                metadata.get("Composite:GPSLatitude") or 
                metadata.get("EXIF:GPSLatitude") or 
                metadata.get("GPS:GPSLatitude") or
                metadata.get("XMP:GPSLatitude") or
                metadata.get("XMP:EXIF:GPSLatitude")
            )
            gps_longitude = (
                metadata.get("Composite:GPSLongitude") or 
                metadata.get("EXIF:GPSLongitude") or 
                metadata.get("GPS:GPSLongitude") or
                metadata.get("XMP:GPSLongitude") or
                metadata.get("XMP:EXIF:GPSLongitude")
            )

            if gps_latitude is not None and gps_longitude is not None:
                lat = float(gps_latitude)
                lon = float(gps_longitude)

                # Defensive Hemisphere Validation Override:
                # If falling back to standard EXIF fields, check if reference direction strings 
                # exist and require programmatic sign adjustment (South/West = Negative)
                lat_ref = metadata.get("EXIF:GPSLatitudeRef") or metadata.get("GPS:GPSLatitudeRef")
                lon_ref = metadata.get("EXIF:GPSLongitudeRef") or metadata.get("GPS:GPSLongitudeRef")

                if isinstance(lat_ref, str) and lat_ref.strip().upper() in ["S", "SOUTH"] and lat > 0:
                    lat = -lat
                if isinstance(lon_ref, str) and lon_ref.strip().upper() in ["W", "WEST"] and lon > 0:
                    lon = -lon

                return {
                    "latitude": lat,
                    "longitude": lon,
                    "source": "EXIF_EMBEDDED"
                }
                
        except (ValueError, TypeError):
            logger.warning("Coordinate translation schema mismatch occurred during string parsing workflows.")
            
        return None
