"""
Management command: seed_data
Seeds 5 realistic sample HCPs into the database for development/testing.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear    # wipe existing HCPs first
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from interactions.models import HCP, Specialty


SAMPLE_HCPS = [
    {
        "name":      "Dr. Priya Sharma",
        "specialty": Specialty.CARDIOLOGY,
        "email":     "priya.sharma@apollohospital.in",
        "phone":     "+919876543210",
        "hospital":  "Apollo Hospital",
        "city":      "Mumbai",
        "state":     "Maharashtra",
        "country":   "India",
        "notes":     "High prescriber for ACE inhibitors and statins. Prefers evidence-based detailing.",
    },
    {
        "name":      "Dr. Rajesh Kapoor",
        "specialty": Specialty.ONCOLOGY,
        "email":     "rajesh.kapoor@tata.memorial.in",
        "phone":     "+919823456781",
        "hospital":  "Tata Memorial Centre",
        "city":      "Mumbai",
        "state":     "Maharashtra",
        "country":   "India",
        "notes":     "Leads NSCLC clinical trials. Very interested in immunotherapy updates.",
    },
    {
        "name":      "Dr. Meena Iyer",
        "specialty": Specialty.ENDOCRINOLOGY,
        "email":     "meena.iyer@fortishealthcare.in",
        "phone":     "+918800123456",
        "hospital":  "Fortis Healthcare",
        "city":      "Bangalore",
        "state":     "Karnataka",
        "country":   "India",
        "notes":     "Key opinion leader in diabetes management. Runs a busy OPD with 30+ patients/day.",
    },
    {
        "name":      "Dr. Arun Mehta",
        "specialty": Specialty.NEUROLOGY,
        "email":     "arun.mehta@aiims.delhi.in",
        "phone":     "+911123456789",
        "hospital":  "AIIMS New Delhi",
        "city":      "New Delhi",
        "state":     "Delhi",
        "country":   "India",
        "notes":     "Academic physician with research focus on Parkinson's and epilepsy.",
    },
    {
        "name":      "Dr. Sunita Rao",
        "specialty": Specialty.PULMONOLOGY,
        "email":     "sunita.rao@yashoda.in",
        "phone":     "+914023456789",
        "hospital":  "Yashoda Hospitals",
        "city":      "Hyderabad",
        "state":     "Telangana",
        "country":   "India",
        "notes":     "Specialises in COPD and asthma management. Open to digital CME programs.",
    },
]


class Command(BaseCommand):
    help = "Seed 5 sample HCP records for development and testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing HCP records before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            count = HCP.objects.count()
            HCP.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"[DELETED] {count} existing HCP record(s).")
            )

        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for data in SAMPLE_HCPS:
                hcp, created = HCP.objects.get_or_create(
                    email=data["email"],
                    defaults=data,
                )
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  [OK] Created: {hcp.name} ({hcp.get_specialty_display()})")
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.HTTP_INFO(f"  [SKIPPED] (already exists): {hcp.name}")
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"[DONE] Seeding complete — {created_count} created, {skipped_count} skipped."
            )
        )
        self.stdout.write(
            self.style.HTTP_INFO(
                f"  Total HCPs in DB: {HCP.objects.count()}"
            )
        )
