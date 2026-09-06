"""
Management command: seed_data

Creates demo users, departments, contract categories, and sample contracts.

Usage:
    python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = "Seed the database with demo data for development"

    def handle(self, *args, **options):
        from accounts.models import User, Department
        from contracts.models import Contract, ContractCategory, ContractVersion

        self.stdout.write("Seeding departments…")
        dept_names = ["Training", "Finance", "HR", "Administration", "Operations", "IT"]
        departments = {}
        for name in dept_names:
            dept, _ = Department.objects.get_or_create(name=name)
            departments[name] = dept

        self.stdout.write("Seeding contract categories…")
        categories = {}
        cat_names = [
            "Service Agreement", "Vendor Agreement", "Training Agreement",
            "Employment Agreement", "Maintenance Agreement",
            "Consultancy Agreement", "Other",
        ]
        for name in cat_names:
            cat, _ = ContractCategory.objects.get_or_create(name=name)
            categories[name] = cat

        self.stdout.write("Seeding users…")

        # Admin
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@iaa.gov.in",
                "first_name": "System",
                "last_name": "Administrator",
                "role": User.Role.ADMIN,
                "status": User.Status.ACTIVE,
                "is_staff": True,
                "is_superuser": True,
                "department": departments["Administration"],
            }
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write(f"  Created admin: admin / admin123")

        # Manager
        manager, created = User.objects.get_or_create(
            username="manager1",
            defaults={
                "email": "manager@iaa.gov.in",
                "first_name": "Rajesh",
                "last_name": "Kumar",
                "role": User.Role.MANAGER,
                "status": User.Status.ACTIVE,
                "department": departments["Training"],
            }
        )
        if created:
            manager.set_password("manager123")
            manager.save()
            self.stdout.write(f"  Created manager: manager1 / manager123")

        # Employee
        employee, created = User.objects.get_or_create(
            username="employee1",
            defaults={
                "email": "employee@iaa.gov.in",
                "first_name": "Priya",
                "last_name": "Sharma",
                "role": User.Role.EMPLOYEE,
                "status": User.Status.ACTIVE,
                "department": departments["Training"],
            }
        )
        if created:
            employee.set_password("employee123")
            employee.save()
            self.stdout.write(f"  Created employee: employee1 / employee123")

        self.stdout.write("Seeding sample contracts…")

        today = timezone.now().date()
        sample_contracts = [
            {
                "title": "Annual Aviation Training Agreement",
                "contract_type": categories["Training Agreement"],
                "party_name": "SkyTech Training Services Pvt Ltd",
                "department": departments["Training"],
                "owner": manager,
                "start_date": today - datetime.timedelta(days=90),
                "end_date": today + datetime.timedelta(days=270),
                "contract_value": 1500000,
                "status": Contract.Status.ACTIVE,
                "priority": Contract.Priority.HIGH,
                "description": "Annual training agreement for aviation personnel.",
            },
            {
                "title": "IT Infrastructure Maintenance",
                "contract_type": categories["Maintenance Agreement"],
                "party_name": "TechCore Solutions",
                "department": departments["IT"],
                "owner": manager,
                "start_date": today - datetime.timedelta(days=30),
                "end_date": today + datetime.timedelta(days=20),
                "contract_value": 450000,
                "status": Contract.Status.EXPIRING_SOON,
                "priority": Contract.Priority.CRITICAL,
                "description": "IT infrastructure support and maintenance.",
            },
            {
                "title": "Security Services Agreement",
                "contract_type": categories["Service Agreement"],
                "party_name": "SecureGuard Services",
                "department": departments["Administration"],
                "owner": admin,
                "start_date": today - datetime.timedelta(days=180),
                "end_date": today - datetime.timedelta(days=10),
                "contract_value": 800000,
                "status": Contract.Status.EXPIRED,
                "priority": Contract.Priority.HIGH,
                "description": "Campus security services.",
            },
            {
                "title": "Consultancy for Digital Transformation",
                "contract_type": categories["Consultancy Agreement"],
                "party_name": "Digital Future Consultants",
                "department": departments["IT"],
                "owner": manager,
                "start_date": today,
                "end_date": today + datetime.timedelta(days=365),
                "contract_value": 2200000,
                "status": Contract.Status.DRAFT,
                "priority": Contract.Priority.MEDIUM,
                "description": "Digital transformation consultancy services.",
            },
            {
                "title": "Housekeeping & Facilities Management",
                "contract_type": categories["Service Agreement"],
                "party_name": "CleanPro Facilities",
                "department": departments["Administration"],
                "owner": admin,
                "start_date": today - datetime.timedelta(days=60),
                "end_date": today + datetime.timedelta(days=305),
                "contract_value": 360000,
                "status": Contract.Status.ACTIVE,
                "priority": Contract.Priority.LOW,
                "description": "Housekeeping and facility management services.",
            },
        ]

        for data in sample_contracts:
            if not Contract.objects.filter(title=data["title"]).exists():
                contract = Contract.objects.create(
                    title=data["title"],
                    contract_type=data["contract_type"],
                    party_name=data["party_name"],
                    department=data["department"],
                    owner=data["owner"],
                    start_date=data["start_date"],
                    end_date=data["end_date"],
                    contract_value=data.get("contract_value"),
                    status=data["status"],
                    priority=data["priority"],
                    description=data.get("description", ""),
                    created_by=admin,
                )
                # Create version 1
                ContractVersion.objects.create(
                    contract=contract,
                    version_number=1,
                    created_by=admin,
                    change_summary="Initial version",
                    is_current=True,
                )
                self.stdout.write(f"  Created: {contract.contract_number} — {contract.title}")

        self.stdout.write(self.style.SUCCESS("\nSeed complete! Login credentials:"))
        self.stdout.write("  Admin:    admin / admin123")
        self.stdout.write("  Manager:  manager1 / manager123")
        self.stdout.write("  Employee: employee1 / employee123")
