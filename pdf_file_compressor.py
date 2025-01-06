import fitz  # PyMuPDF
from PIL import Image
import io
import os
import logging
from pathlib import Path

class PDFCompressor:
    def __init__(self, input_path, output_path, image_quality=30):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.image_quality = image_quality
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def compress_image(self, image_bytes, image_ext):
        """Compress a single image using PIL."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            compressed_bytes = io.BytesIO()
            
            # Convert RGBA to RGB if necessary
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background

            # Optimize based on image format
            if image_ext.lower() in ('jpg', 'jpeg'):
                image.save(compressed_bytes, 
                          format='JPEG', 
                          quality=self.image_quality, 
                          optimize=True)
            elif image_ext.lower() == 'png':
                image.save(compressed_bytes, 
                          format='PNG', 
                          optimize=True, 
                          quality=self.image_quality)
            else:
                image.save(compressed_bytes, 
                          format=image_ext.upper(), 
                          quality=self.image_quality)

            compressed_bytes.seek(0)
            return compressed_bytes

        except Exception as e:
            self.logger.error(f"Error compressing image: {str(e)}")
            return None

    def compress_pdf(self):
        """Compress PDF by reducing the quality of embedded images."""
        try:
            if not self.input_path.exists():
                raise FileNotFoundError(f"Input file not found: {self.input_path}")

            self.logger.info(f"Starting compression of {self.input_path}")
            pdf_document = fitz.open(str(self.input_path))
            output_pdf = fitz.open()

            total_pages = len(pdf_document)
            for page_num in range(total_pages):
                self.logger.info(f"Processing page {page_num + 1}/{total_pages}")
                page = pdf_document[page_num]
                images = page.get_images(full=True)
                
                # Create a new page in output PDF
                output_page = output_pdf.new_page(width=page.rect.width,
                                                height=page.rect.height)
                
                # Copy original content to new page
                output_page.show_pdf_page(page.rect, pdf_document, page_num)
                
                # Process images if any
                if images:
                    for img_index, img in enumerate(images):
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        
                        if base_image:
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            compressed_bytes = self.compress_image(image_bytes, image_ext)
                            if compressed_bytes:
                                # Get the image rectangle and rotation
                                image_rect = page.get_image_bbox(img)
                                if image_rect:
                                    output_page.insert_image(
                                        image_rect,
                                        stream=compressed_bytes.getvalue()
                                    )

            # Save the compressed PDF
            output_pdf.save(str(self.output_path), 
                          garbage=4,  # Maximum garbage collection
                          deflate=True,  # Compress streams
                          clean=True  # Clean unused elements
            )
            
            # Calculate compression ratio
            original_size = os.path.getsize(self.input_path)
            compressed_size = os.path.getsize(self.output_path)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            self.logger.info(f"Compression complete. Saved to: {self.output_path}")
            self.logger.info(f"Original size: {original_size/1024:.2f}KB")
            self.logger.info(f"Compressed size: {compressed_size/1024:.2f}KB")
            self.logger.info(f"Compression ratio: {compression_ratio:.1f}%")
            
            output_pdf.close()
            pdf_document.close()
            
            return True

        except Exception as e:
            self.logger.error(f"Error compressing PDF: {str(e)}")
            return False

def main():
    # Example usage
    input_pdf = r"C:\Users\Vadym\Desktop\pdfCompressor\test_1.pdf"
    output_pdf = r"C:\Users\Vadym\Desktop\pdfCompressor\compressed.pdf"
    
    compressor = PDFCompressor(input_pdf, output_pdf, image_quality=50)
    compressor.compress_pdf()

if __name__ == "__main__":
    main()