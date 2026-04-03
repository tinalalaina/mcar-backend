
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import User
from vehicule.models import Vehicule, VehiclePhoto, StatusVehicule
import uuid

def verify_vehicule_deletion():
    print("--- Verification: Vehicule Deletion & Cascade File Cleanup ---")
    
    # Setup
    with open('test_vehicule_image.jpg', 'wb') as f:
        f.write(b'\xFF\xD8\xFF\xE0\x00\x10\x4A\x46\x49\x46\x00\x01')

    def get_image():
        with open('test_vehicule_image.jpg', 'rb') as f:
            return SimpleUploadedFile('test_vehicule_image.jpg', f.read(), content_type="image/jpeg")

    try:
        owner = User.objects.create_user(email=f"owner_{uuid.uuid4().hex[:6]}@test.com", password="password")
        status = StatusVehicule.objects.create(nom="Dispo TEST")
        
        vehicule = Vehicule.objects.create(
            proprietaire=owner,
            titre="Vehicule de Test Cascade",
            annee=2024,
            adresse_localisation="Test 123",
            montant_caution=1000
        )
        
        photo = VehiclePhoto.objects.create(vehicle=vehicule, image=get_image())
        photo_path = photo.image.path
        
        print(f"Step 1: Vehicule and Photo created. Path: {photo_path}")
        if os.path.exists(photo_path):
            print("✅ File exists on disk.")
        else:
            print("❌ Error: File not found.")
            return

        print("Step 2: Deleting Vehicule (should trigger CASCADE and signals)...")
        vehicule.delete()
        
        if not os.path.exists(photo_path):
            print("✅ SUCCESS: Photo file has been deleted from the filesystem!")
        else:
            print("❌ FAILURE: Photo file is still on disk.")

        owner.delete()
        status.delete()

    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if os.path.exists('test_vehicule_image.jpg'):
            os.remove('test_vehicule_image.jpg')

verify_vehicule_deletion()
