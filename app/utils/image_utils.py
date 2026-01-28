"""
Image processing utilities
"""
from PIL import Image
import io
from typing import Optional, Tuple


def validate_image(image_bytes: bytes, max_size_mb: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Validate image file
    
    Args:
        image_bytes: Image file bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"Image size ({size_mb:.2f}MB) exceeds maximum ({max_size_mb}MB)"
    
    # Check if it's a valid image
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        return True, None
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def resize_image(image: Image.Image, max_dimension: int = 2048) -> Image.Image:
    """
    Resize image if it's too large, maintaining aspect ratio
    
    Args:
        image: PIL Image
        max_dimension: Maximum width or height
        
    Returns:
        Resized PIL Image
    """
    width, height = image.size
    
    if width <= max_dimension and height <= max_dimension:
        return image
    
    # Calculate new dimensions maintaining aspect ratio
    if width > height:
        new_width = max_dimension
        new_height = int(height * (max_dimension / width))
    else:
        new_height = max_dimension
        new_width = int(width * (max_dimension / height))
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def convert_to_rgb(image: Image.Image) -> Image.Image:
    """
    Convert image to RGB mode (required for some AI models)
    
    Args:
        image: PIL Image
        
    Returns:
        RGB PIL Image
    """
    if image.mode != 'RGB':
        return image.convert('RGB')
    return image


def process_screenshot(image_bytes: bytes) -> Tuple[Optional[Image.Image], Optional[str]]:
    """
    Process screenshot for AI analysis
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Tuple of (processed_image, error_message)
    """
    try:
        # Validate
        is_valid, error = validate_image(image_bytes)
        if not is_valid:
            return None, error
        
        # Load image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB
        img = convert_to_rgb(img)
        
        # Resize if needed
        img = resize_image(img)
        
        return img, None
        
    except Exception as e:
        return None, f"Error processing image: {str(e)}"
