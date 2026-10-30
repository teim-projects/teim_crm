from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
from crmapp.models import SalesPerson, UserProfile, service_management, quotation_management, customer_details, lead_management

class Command(BaseCommand):
    help = "Fix data cross-contamination and user accounts when salesperson phone numbers are updated/reassigned"

    def handle(self, *args, **options):
        self.stdout.write("Starting fix for reassigned sales numbers and user accounts...")

        # -------------------------------------------------------------
        # STEP 1: Specific Fix for Trupti Desai & Swapnali Salunkhe
        # -------------------------------------------------------------
        trupti_sp = SalesPerson.objects.filter(full_name__icontains="Trupti").first()
        swapnali_sp = SalesPerson.objects.filter(full_name__icontains="Swapnali").first()

        trupti_new_mobile = "9975957361"
        trupti_email = "pc3.sevafacility@gmail.com"
        swapnali_mobile = "9503102302"
        swapnali_email = "swapnalinshinde@gmail.com"

        if trupti_sp:
            trupti_new_mobile = trupti_sp.mobile_no or trupti_new_mobile
            trupti_email = trupti_sp.email or trupti_email
            self.stdout.write(f"Found Trupti Desai in SalesPerson: ID={trupti_sp.id}, mobile={trupti_sp.mobile_no}")

        if swapnali_sp:
            swapnali_mobile = swapnali_sp.mobile_no or swapnali_mobile
            swapnali_email = swapnali_sp.email or swapnali_email
            self.stdout.write(f"Found Swapnali Salunkhe in SalesPerson: ID={swapnali_sp.id}, mobile={swapnali_sp.mobile_no}")

        # Update historical services belonging to Trupti Desai
        s_count = service_management.objects.filter(
            Q(sales_person_name__icontains="Trupti") |
            (Q(sales_person_contact_no__in=["9503102302", "09503102302"]) & ~Q(sales_person_name__icontains="Swapnali"))
        ).update(
            sales_person_name="Trupti Desai",
            sales_person_contact_no=trupti_new_mobile,
            sales_person_email=trupti_email
        )
        self.stdout.write(f"Updated {s_count} service_management records for Trupti Desai to contact {trupti_new_mobile}")

        # Update historical quotations belonging to Trupti Desai
        q_count = quotation_management.objects.filter(
            Q(contact_by__icontains="Trupti") |
            (Q(contact_by_no__in=["9503102302", "09503102302"]) & ~Q(contact_by__icontains="Swapnali"))
        ).update(
            contact_by="Trupti Desai",
            contact_by_no=trupti_new_mobile
        )
        self.stdout.write(f"Updated {q_count} quotation_management records for Trupti Desai to contact {trupti_new_mobile}")

        # Fix Django User accounts:
        # 1. Swapnali Salunkhe -> username 9503102302
        swapnali_user = User.objects.filter(username=swapnali_mobile).first()
        if swapnali_user:
            swapnali_user.first_name = "Swapnali Salunkhe"
            swapnali_user.email = swapnali_email
            swapnali_user.is_active = True
            swapnali_user.is_staff = True
            swapnali_user.save()
            up, _ = UserProfile.objects.get_or_create(user=swapnali_user)
            up.role = "sales"
            up.phone = swapnali_mobile
            up.save()
            self.stdout.write(f"Updated User ID={swapnali_user.id} ({swapnali_mobile}) to 'Swapnali Salunkhe'")
        else:
            # Check by email
            swapnali_user = User.objects.filter(email=swapnali_email).first()
            if swapnali_user:
                swapnali_user.username = swapnali_mobile
                swapnali_user.first_name = "Swapnali Salunkhe"
                swapnali_user.is_active = True
                swapnali_user.is_staff = True
                swapnali_user.save()
            else:
                swapnali_user = User.objects.create_user(
                    username=swapnali_mobile,
                    email=swapnali_email,
                    password="Password@123",
                    first_name="Swapnali Salunkhe"
                )
                swapnali_user.is_staff = True
                swapnali_user.save()
            up, _ = UserProfile.objects.get_or_create(user=swapnali_user)
            up.role = "sales"
            up.phone = swapnali_mobile
            up.save()
            self.stdout.write(f"Created/configured User for 'Swapnali Salunkhe' ({swapnali_mobile})")

        # 2. Trupti Desai -> username 9975957361
        trupti_user = User.objects.filter(Q(email=trupti_email) | Q(username=trupti_new_mobile)).first()
        if trupti_user:
            trupti_user.username = trupti_new_mobile
            trupti_user.first_name = "Trupti Desai"
            trupti_user.email = trupti_email
            trupti_user.is_active = True
            trupti_user.is_staff = True
            trupti_user.save()
            up, _ = UserProfile.objects.get_or_create(user=trupti_user)
            up.role = "sales"
            up.phone = trupti_new_mobile
            up.save()
            self.stdout.write(f"Updated User ID={trupti_user.id} ({trupti_new_mobile}) to 'Trupti Desai'")
        else:
            trupti_user = User.objects.create_user(
                username=trupti_new_mobile,
                email=trupti_email,
                password="Password@123",
                first_name="Trupti Desai"
            )
            trupti_user.is_staff = True
            trupti_user.save()
            up, _ = UserProfile.objects.get_or_create(user=trupti_user)
            up.role = "sales"
            up.phone = trupti_new_mobile
            up.save()
            self.stdout.write(f"Created/configured User for 'Trupti Desai' ({trupti_new_mobile})")

        # Archive any leftover duplicate user with 09503102302
        for old_u in User.objects.filter(username__in=["09503102302"]):
            if old_u.id not in [swapnali_user.id, trupti_user.id]:
                old_u.username = f"{old_u.username}_archived_{old_u.id}"
                old_u.save()
                self.stdout.write(f"Archived duplicate user ID={old_u.id}")

        # -------------------------------------------------------------
        # STEP 2: Generalized Sync for ALL Salespersons
        # -------------------------------------------------------------
        for sp in SalesPerson.objects.filter(is_active=True):
            if sp.mobile_no and sp.full_name:
                # Sync services
                service_management.objects.filter(
                    sales_person_name__iexact=sp.full_name
                ).update(
                    sales_person_contact_no=sp.mobile_no,
                    sales_person_email=sp.email
                )
                # Sync quotations
                quotation_management.objects.filter(
                    contact_by__iexact=sp.full_name
                ).update(
                    contact_by_no=sp.mobile_no
                )
                # Ensure User first_name matches SalesPerson full_name
                u = User.objects.filter(Q(username=sp.mobile_no) | Q(email=sp.email)).first()
                if u and u.first_name != sp.full_name:
                    u.first_name = sp.full_name
                    u.save()

        self.stdout.write(self.style.SUCCESS("Successfully fixed all salesperson data and login credentials!"))
