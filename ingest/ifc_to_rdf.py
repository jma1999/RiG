# ingest/ifc_to_rdf.py
"""
IFC to RDF Conversion using IFCtoRDF (Java-based converter).

This module wraps the IFCtoRDF Java JAR to convert IFC-SPF files to RDF Turtle format.
The IFCtoRDF tool converts IFC files according to ifcOWL ontology.

Reference: https://github.com/pipauwel/IFCtoRDF
"""
import os
import sys
import pathlib
import argparse
import subprocess
import shutil
from typing import Optional, Dict, Any
from urllib.request import urlopen
from urllib.error import URLError

# IFCtoRDF JAR information
IFCTORDF_VERSION = "0.4"
IFCTORDF_JAR_NAME = f"IFCtoRDF-{IFCTORDF_VERSION}-SNAPSHOT-shaded.jar"
IFCTORDF_DOWNLOAD_URL = (
    f"https://github.com/pipauwel/IFCtoRDF/releases/download/"
    f"IFCtoRDF-{IFCTORDF_VERSION}/{IFCTORDF_JAR_NAME}"
)
IFCTORDF_MAVEN_URL = f"https://search.maven.org/remote_content?g=com.github.pipauwel&a=IFCtoRDF&v={IFCTORDF_VERSION}&c=shaded&e=jar"

# Default JAR location (will be downloaded if not present)
DEFAULT_JAR_DIR = pathlib.Path(__file__).parent.parent / "tools" / "ifctordf"
DEFAULT_JAR_PATH = DEFAULT_JAR_DIR / IFCTORDF_JAR_NAME


def ensure_jar_exists(jar_path: pathlib.Path) -> bool:
    """
    Ensure the IFCtoRDF JAR file exists. Download if necessary.
    
    Args:
        jar_path: Path where JAR should be located
    
    Returns:
        True if JAR exists or was downloaded successfully
    """
    if jar_path.exists():
        return True
    
    print(f"📦 IFCtoRDF JAR not found at {jar_path}")
    print(f"   Attempting to download from GitHub releases...")
    
    # Create directory if needed
    jar_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Try GitHub releases first
        print(f"   Downloading from: {IFCTORDF_DOWNLOAD_URL}")
        response = urlopen(IFCTORDF_DOWNLOAD_URL, timeout=30)
        
        with open(jar_path, 'wb') as f:
            f.write(response.read())
        
        print(f"✅ Successfully downloaded IFCtoRDF JAR to {jar_path}")
        return True
        
    except URLError as e:
        print(f"⚠️  Failed to download from GitHub: {e}")
        print(f"   Please manually download the JAR from:")
        print(f"   {IFCTORDF_DOWNLOAD_URL}")
        print(f"   Or from Maven Central:")
        print(f"   {IFCTORDF_MAVEN_URL}")
        print(f"   And place it at: {jar_path}")
        return False
    except Exception as e:
        print(f"❌ Error downloading JAR: {e}")
        return False


def check_java_available() -> bool:
    """Check if Java is available in the system."""
    java_cmd = shutil.which("java")
    if not java_cmd:
        print("❌ Java not found in PATH. Please install Java JDK 8 or later.")
        return False
    
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_info = result.stderr or result.stdout
            print(f"✅ Java found: {version_info.split(chr(10))[0]}")
            return True
    except Exception as e:
        print(f"⚠️  Error checking Java: {e}")
    
    return False


def convert_ifc_to_turtle(
    ifc_path: str,
    turtle_path: str,
    base_uri: Optional[str] = None,
    jar_path: Optional[str] = None,
    java_memory: str = "8g"
) -> Dict[str, Any]:
    """
    Convert IFC-SPF file to RDF Turtle format using IFCtoRDF.
    
    Args:
        ifc_path: Path to input IFC-SPF file
        turtle_path: Path to output Turtle (.ttl) file
        base_uri: Base URI for RDF resources (optional)
        jar_path: Path to IFCtoRDF JAR file (optional, will auto-download if not provided)
        java_memory: Java heap memory (e.g., "8g" for 8GB)
    
    Returns:
        Dictionary with conversion statistics
    """
    ifc_path = pathlib.Path(ifc_path)
    turtle_path = pathlib.Path(turtle_path)
    
    if not ifc_path.exists():
        raise FileNotFoundError(f"Input IFC file not found: {ifc_path}")
    
    # Check Java availability
    if not check_java_available():
        raise RuntimeError("Java is required but not found. Please install Java JDK 8+.")
    
    # Determine JAR path
    if jar_path:
        jar_path = pathlib.Path(jar_path)
    else:
        jar_path = DEFAULT_JAR_PATH
    
    # Ensure JAR exists
    if not ensure_jar_exists(jar_path):
        raise FileNotFoundError(
            f"IFCtoRDF JAR not found at {jar_path}. "
            f"Please download it manually or check your internet connection."
        )
    
    # Create output directory
    turtle_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build Java command
    java_cmd = [
        "java",
        f"-Xmx{java_memory}",
        f"-Xms{java_memory}",
        "-jar",
        str(jar_path),
    ]
    
    # Add base URI if provided
    if base_uri:
        java_cmd.extend(["--baseURI", base_uri])
    
    # Add input and output paths
    java_cmd.append(str(ifc_path))
    java_cmd.append(str(turtle_path))
    
    print(f"🔄 Converting IFC to RDF Turtle...")
    print(f"   Input:  {ifc_path}")
    print(f"   Output: {turtle_path}")
    if base_uri:
        print(f"   Base URI: {base_uri}")
    print(f"   Command: {' '.join(java_cmd)}")
    
    try:
        # Run IFCtoRDF conversion
        result = subprocess.run(
            java_cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            raise RuntimeError(
                f"IFCtoRDF conversion failed with return code {result.returncode}:\n{error_msg}"
            )
        
        # Check if output file was created
        if not turtle_path.exists():
            raise RuntimeError(
                f"Conversion completed but output file not found: {turtle_path}"
            )
        
        # Get file size for statistics
        ifc_size = ifc_path.stat().st_size
        turtle_size = turtle_path.stat().st_size
        
        stats = {
            "success": True,
            "input_file": str(ifc_path),
            "output_file": str(turtle_path),
            "input_size_mb": round(ifc_size / (1024 * 1024), 2),
            "output_size_mb": round(turtle_size / (1024 * 1024), 2),
            "base_uri": base_uri,
        }
        
        print(f"✅ Conversion successful!")
        print(f"   Input size:  {stats['input_size_mb']} MB")
        print(f"   Output size: {stats['output_size_mb']} MB")
        
        return stats
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("IFCtoRDF conversion timed out after 1 hour")
    except Exception as e:
        print(f"❌ Conversion error: {e}")
        raise


def convert_directory(
    input_dir: str,
    output_dir: str,
    base_uri: Optional[str] = None,
    jar_path: Optional[str] = None,
    java_memory: str = "8g"
) -> Dict[str, Any]:
    """
    Convert all IFC files in a directory to Turtle format.
    
    Args:
        input_dir: Directory containing IFC files
        output_dir: Directory for output Turtle files
        base_uri: Base URI for RDF resources
        jar_path: Path to IFCtoRDF JAR
        java_memory: Java heap memory
    
    Returns:
        Dictionary with conversion statistics
    """
    input_dir = pathlib.Path(input_dir)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ifc_files = list(input_dir.glob("*.ifc"))
    
    if not ifc_files:
        print(f"⚠️  No IFC files found in {input_dir}")
        return {"success": False, "files_processed": 0}
    
    print(f"📁 Found {len(ifc_files)} IFC file(s) to convert")
    
    results = []
    for ifc_file in ifc_files:
        turtle_file = output_dir / (ifc_file.stem + ".ttl")
        try:
            stats = convert_ifc_to_turtle(
                str(ifc_file),
                str(turtle_file),
                base_uri=base_uri,
                jar_path=jar_path,
                java_memory=java_memory
            )
            results.append(stats)
        except Exception as e:
            print(f"❌ Failed to convert {ifc_file.name}: {e}")
            results.append({"success": False, "file": str(ifc_file), "error": str(e)})
    
    successful = sum(1 for r in results if r.get("success", False))
    
    return {
        "success": successful > 0,
        "total_files": len(ifc_files),
        "successful": successful,
        "failed": len(ifc_files) - successful,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert IFC-SPF files to RDF Turtle format using IFCtoRDF"
    )
    parser.add_argument("input", help="Path to input IFC file or directory")
    parser.add_argument("output", nargs="?", help="Path to output Turtle file or directory")
    parser.add_argument("--base-uri", default=None,
                       help="Base URI for RDF resources (e.g., https://example.com/ifc/)")
    parser.add_argument("--jar", default=None,
                       help="Path to IFCtoRDF JAR file (auto-downloads if not provided)")
    parser.add_argument("--java-memory", default="8g",
                       help="Java heap memory (default: 8g)")
    parser.add_argument("--dir", action="store_true",
                       help="Process all IFC files in input directory")
    
    args = parser.parse_args()
    
    try:
        input_path = pathlib.Path(args.input)
        
        if args.dir or input_path.is_dir():
            # Directory mode
            if not args.output:
                output_dir = input_path.parent / (input_path.name + "_ttl")
            else:
                output_dir = pathlib.Path(args.output)
            
            stats = convert_directory(
                str(input_path),
                str(output_dir),
                base_uri=args.base_uri,
                jar_path=args.jar,
                java_memory=args.java_memory
            )
            
            print(f"\n📊 Conversion Summary:")
            print(f"   Total files: {stats['total_files']}")
            print(f"   Successful: {stats['successful']}")
            print(f"   Failed: {stats['failed']}")
            
        else:
            # Single file mode
            if not args.output:
                output_path = input_path.parent / (input_path.stem + ".ttl")
            else:
                output_path = pathlib.Path(args.output)
            
            stats = convert_ifc_to_turtle(
                str(input_path),
                str(output_path),
                base_uri=args.base_uri,
                jar_path=args.jar,
                java_memory=args.java_memory
            )
            
            print(f"\n✅ Conversion complete: {stats['output_file']}")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

