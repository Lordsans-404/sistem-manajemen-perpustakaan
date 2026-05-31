import os
import sys
import django

# Add root project to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.catalog.services.storage_service import delete_cover_image, upload_cover_image

IMAGE_PATH = "test_assets/test_cover.jpg"

class FakeFile:
    content_type = "image/jpeg"
    def read(self):
        with open(IMAGE_PATH, "rb") as f:
            return f.read()

print("Testing Supabase Storage...")

url = upload_cover_image(file=FakeFile(), filename="test_cover.jpg")
print(f"✅ Upload sukses: {url}")
