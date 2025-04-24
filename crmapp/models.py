from django.db import models
import random
from django.contrib.auth.models import User
from django.utils import timezone
from num2words import num2words
from django.contrib.auth.models import User


def generate_customerid():
    random_number = str(random.randint(1000, 9999))
    return f"DEFAULT{random_number}"


class customer_details(models.Model):
   
    firstname=models.CharField(max_length=100)
    lastname=models.CharField(max_length=100)
    primaryemail=models.EmailField()
    secondaryemail=models.EmailField(null=True , blank=True)
    primarycontact=models.BigIntegerField()
    secondarycontact=models.BigIntegerField(null=True , blank=True)
    contactperson=models.CharField(max_length=100)
    customersegment=models.CharField(max_length=100)
    shifttopartyaddress=models.CharField(max_length=100)
    shifttopartycity=models.CharField(max_length=100)
    shifttopartystate=models.CharField(max_length=100)
    shifttopartypostal=models.CharField(max_length=100)
    soldtopartyaddress=models.CharField(max_length=100)
    soldtopartycity=models.CharField(max_length=100)
    soldtopartystate=models.CharField(max_length=100)
    soldtopartypostal=models.CharField(max_length=100)
    customerid = models.CharField(max_length=255, unique=True, null=True, blank=True)


   
    def __str__(self):
        return self.firstname + " " + self.lastname
   
    def __str__(self):
        return self.customerid




from django.db import models
from django.utils import timezone


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=255)
    # price = models.DecimalField(max_digits=10, decimal_places=2)
    # quantity = models.PositiveIntegerField()
   
    CATEGORY_CHOICES = [
        ('Pest Control', 'Pest Control'),
        ('Fumigation', 'Fumigation'),
        ('Product Sell', 'Product Sell'),
    ]
   
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="NULL")


    def __str__(self):
        return self.product_name


    def delete_product(self):
        self.delete()





class quotation(models.Model):
    quantity=models.IntegerField()
    price=models.FloatField()
    termsandcondition=models.CharField(max_length=200)
    servicetype_q=models.CharField(max_length=5000)
    total_amount = models.FloatField(null=True, blank=True, editable=False)  # Make it readonly
    discount = models.FloatField(null=True, blank=True)  # percentage discount
    company_name = models.CharField(max_length=100 , null=True)
    company_email = models.EmailField(null=True)
    company_contact_no = models.CharField(max_length=15 , default=0)
    quotation_date = models.DateField(default=timezone.now)
    company_address = models.CharField(max_length=200 , null=True)
    subject = models.CharField(max_length=200 , null=True)
    total_amount_with_gst = models.FloatField(null=True, blank=True)
    termsandcondition = models.CharField(max_length=200 , null=True)
    gst_checkbox = models.BooleanField(default=False)
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE, null=True, blank=True)
    version = models.IntegerField(default=1)  # Added version field
    status = models.CharField(max_length=20, default='active')  # Added status field


    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.price  # Calculate total amount
        super().save(*args, **kwargs)


    def save(self, *args, **kwargs):
        if self.gst_checkbox:
            self.gst_status = "GST"
        else:
            self.gst_status = "NON-GST"
        super().save(*args, **kwargs)
   


    def save(self, *args, **kwargs):
        if self.discount:
            discounted_amount = self.total_amount - (self.total_amount * (self.discount / 100))
        else:
            discounted_amount = self.total_amount


        if self.gst_checkbox:
            self.total_amount_with_gst = discounted_amount * 1.18  # Adding 18% GST
        else:
            self.total_amount_with_gst = discounted_amount


        super().save(*args, **kwargs)


    class Meta:
        ordering = ['-version']  # Order quotations by the latest version




class invoice(models.Model):
    modeofpayment = models.CharField(max_length=100, default='Null')
    dispatchedthrough = models.CharField(max_length=100, default='Null')
    termofdelivery = models.CharField(max_length=100, default='Null')
    termsandcondition = models.CharField(max_length=255, default='Null')
    company_name = models.CharField(max_length=255, default='Null')
    company_email = models.EmailField(default='Null')
    company_contact_no = models.CharField(max_length=20, default='0')
    invoice_no = models.CharField(max_length=200, unique=True, editable=False, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    description_of_goods = models.TextField(max_length=5000, default='Null')
    hsn_sac_code = models.CharField(max_length=100, default='Null')
    quantity = models.IntegerField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    discount = models.FloatField(null=True, blank=True)
    gst_checkbox = models.BooleanField(default=False)
    total_amount = models.FloatField(null=True, blank=True, editable=False)
    total_amount_with_gst = models.DecimalField(max_digits=10, decimal_places=2, editable=False, null=True, blank=True)
    total_amount_in_words = models.CharField(max_length=255, editable=False, default='')
    pan_card_no = models.CharField(max_length=20, default='Null')
    account_no = models.CharField(max_length=20, default='Null')
    branch = models.CharField(max_length=255, default='Null')
    ifsc_code = models.CharField(max_length=20, default='Null')
    delivery_date = models.DateField(default=timezone.now)
    dispatched_date = models.DateField(default=timezone.now)
    designation = models.CharField(max_length=20, choices=[('Indoor', 'Indoor'), ('Outdoor', 'Outdoor')], default='Null')
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE, null=True, blank=True)


    def save(self, *args, **kwargs):
        if not self.invoice_no:
            self.invoice_no = self.generate_invoice_no()


        self.total_amount = self.quantity * self.price  # Calculate total amount


        discounted_amount = self.total_amount
        if self.discount:
            discounted_amount = self.total_amount - (self.total_amount * (self.discount / 100))


        if self.gst_checkbox:
            self.total_amount_with_gst = round(discounted_amount * 1.18, 2)  # Adding 18% GST and rounding to 2 decimal places
        else:
            self.total_amount_with_gst = round(discounted_amount, 2)  # Rounding to 2 decimal places


        self.total_amount_in_words = self.convert_amount_to_words(self.total_amount_with_gst)


        super().save(*args, **kwargs)


    def save(self, *args, **kwargs):
        if self.gst_checkbox:
            self.gst_status = "GST"
        else:
            self.gst_status = "NON-GST"
        super().save(*args, **kwargs)


    def generate_invoice_no(self):
        return ''.join(random.choices('0123456789', k=11))


    def convert_amount_to_words(self, amount):
        return num2words(amount, to='currency', lang='en').replace('euro', 'rupees').replace('cents', 'paise')


    def __str__(self):
        return f"Invoice No: {self.invoice_no}"


# class inventory(models.Model):
#     itemnumber=models.IntegerField()
#     itemname=models.CharField(max_length=100)
#     price=models.IntegerField()
#     quantity=models.IntegerField()


# class lead_management(models.Model):
#     sourceoflead = models.CharField(max_length=100)
#     salesperson = models.CharField(max_length=100)
#     havedonepestcontrolearlier = models.CharField(max_length=100)
#     leadstatus = models.CharField(max_length=100, choices=[('Call', 'Call'), ('Visit', 'Visit'), ('Quotation', 'Quotation')])
#     typeoflead = models.CharField(max_length=100,null=True, choices=[('Hot','Hot'),('Warm','Warm'),('Cold','Cold'),('Not Interested','Not Interested'),('Loss of Order','Loss of Order')])
#     typeofcontract = models.CharField(max_length=100, choices=[('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')])
#     dateoflead = models.DateField(default=timezone.now)
#     contactno = models.BigIntegerField(null=True)
#     customeremail = models.EmailField(null=True)
#     customeraddress = models.CharField(max_length=255 , null=True)
#     visitorsname=models.CharField(max_length=200 , default='Null')


#     def __str__(self):
#         return self.sourceoflead

class lead_management(models.Model):
    sourceoflead = models.CharField(max_length=200, choices=[('Google', 'Google'), ('Justdial', 'Justdial'), ('Indiamart', 'Indiamart'), ('Customer Reference', 'Customer Reference'), ('BNI', 'BNI'),('Lineclub', 'Lineclub'),('Employee Reference', 'Employee Reference'),('Others', 'Others')], default="NOT SELECTED")
    salesperson = models.CharField(max_length=100)
    customername = models.CharField(max_length=100, null=True, blank= True)
    customersegment = models.CharField(max_length=100, choices=[('Residential', 'Residential'), ('Industrial', 'Industrial'), ('Commercial', 'Commercial'), ('Institutional', 'Institutional'), ('Irrelevant Leads', 'Irrelevant Leads')], default="NOT SELECTED")
    enquirydate = models.DateField(default=timezone.now)
    contactedby = models.CharField(max_length=100, null=True, blank= True)
    maincategory = models.CharField(max_length=200, null=True, blank= True)
    subcategory = models.CharField(max_length=200, null=True, blank= True)
    primarycontact = models.BigIntegerField(null=True)
    secondarycontact = models.BigIntegerField(null=True)
    customeremail = models.EmailField(null=True)
    customeraddress = models.CharField(max_length=255 , null=True)
    location = models.URLField(null=True, blank=True)
    city = models.CharField(max_length=100, default="Unknown City")
    typeoflead = models.CharField(max_length=100,null=True, choices=[('Hot','Hot'),('Warm','Warm'),('Cold','Cold'),('Not Interested','Not Interested'),('Loss of Order','Loss of Order')])
    firstfollowupdate = models.DateField(default=timezone.now)
    stage = models.IntegerField(default=1)
    
    def __str__(self):
        return self.sourceoflead



# In crmapp/models.py

class firstfollowup(models.Model):
    lead = models.ForeignKey(lead_management, on_delete=models.CASCADE, null=True, blank=True)
    havedonepestcontrolearlier = models.CharField(max_length=100, choices=[('Yes', 'Yes'),('No','No')],default='NOT SELECTED')
    agency = models.CharField(max_length=100, default="NA")
    inspectiononsite = models.CharField(max_length=100, choices=[('Yes', 'Yes'),('No','No')],default='NOT SELECTED')
    levelofinspection = models.CharField(max_length=100, choices=[('Low', 'Low'),('Middle','Middle'),('High','High')],default='NOT SELECTED')
    quotationgiven = models.CharField(max_length=100, choices=[('Yes', 'Yes'),('No','No')],default='NOT SELECTED')
    quotationamount = models.FloatField(null=True, blank=True)
    mailsent = models.CharField(max_length=100, choices=[('Yes', 'Yes'),('No','No')],default='NOT SELECTED')
    customermeeting = models.CharField(max_length=100, choices=[('Yes', 'Yes'),('No','No')],default='NOT SELECTED')
    firstremark = models.CharField(max_length=100, default="NA")
    secondfollowupdate = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Follow-Up 1 for Lead {self.lead}"
    

class secondfollowup(models.Model):
    lead = models.ForeignKey(lead_management, on_delete=models.CASCADE, null=True, blank=True)
    negotiationstage = models.CharField(max_length=100, choices=[('Decision Pending', 'Decision Pending'),('Delay in Business Decision','Delay in Business Decision'),('Rates Finalized','Rates Finalized')],default='NOT SELECTED')
    mailsent2 = models.CharField(max_length=100, choices=[('Yes', 'Yes'),('No','No'),('NA','NA')],default='NOT SELECTED')
    secondremark = models.CharField(max_length=100, default="NA")
    thirdfollowupdate = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Follow-Up 2 for Lead {self.lead}"
    
    
class thirdfollowup(models.Model):
    lead = models.ForeignKey(lead_management, on_delete=models.CASCADE, null=True, blank=True)
    thirdremark = models.CharField(max_length=100, default="NA")
    fourthfollowupdate = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Follow-Up 3 for Lead {self.lead}"
    
class finalfollowup(models.Model):
    lead = models.ForeignKey(lead_management, on_delete=models.CASCADE, null=True, blank=True)
    fourthremark = models.CharField(max_length=100, default="NA")
    finalstatus = models.CharField(max_length=100, choices=[('Decision Pending', 'Decision Pending'),('Deal Done','Deal Done')],default='NOT SELECTED')
    contracttype = models.CharField(max_length=50, choices=[('AMC', 'AMC'), ('Single', 'Single')], default="NOT SELECTED")
    bookingamount = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Follow-Up 4 for Lead {self.lead}"



class Inventory_add(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()


    def __str__(self):
        return f'{self.product.product_name} - {self.quantity}'
   




class Inventory_summary(models.Model):
    customer_id = models.CharField(max_length=100, default='unknown')  # Add default value
    customer_name = models.CharField(max_length=255)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    date_added = models.DateTimeField(default=timezone.now)


    @property
    def product_name(self):
        return self.product.product_name


    @property
    def price_per_unit(self):
        return self.product.price




   
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.product.price
        super().save(*args, **kwargs)


    def __str__(self):
        return f'{self.customer_details.firstname} - {self.product.product_name} - {self.total_price}'
   
class TechnicianProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=15, unique=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    date_of_joining = models.DateField(default=timezone.now)
    password = models.CharField(max_length=128)  # This should not be needed if you are using Django's User model


    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class service_management(models.Model):
    customer = models.ForeignKey(customer_details, on_delete=models.CASCADE, null=True, blank=True)
    selected_services = models.ManyToManyField(Product, related_name="selected_services")
    gst_checkbox = models.BooleanField(default=False)
    gst_status = models.CharField(max_length=10, default='NON-GST')
    total_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price_with_gst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)    
    contract_type = models.CharField(max_length=50, choices=[('One Time', 'One Time'), ('AMC', 'AMC'), ('Warranty', 'Warranty')], default="NOT SELECTED")
    contract_status = models.CharField(max_length=100, choices=[('Yes', 'Yes'), ('No', 'No')], default="NOT SELECTED")
    property_type = models.TextField(null=True, blank=True)
    warranty_period = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=100, default="Null")
    city = models.CharField(max_length=100, default="Null")
    pincode = models.CharField(max_length=6, default="000000")
    address = models.TextField(default="Null")
    gps_location = models.URLField(null=True, blank=True)
    gst_number = models.CharField(max_length=15, null=True, blank=True)
    frequency_count = models.CharField(max_length=50, choices=[(str(i), str(i)) for i in range(1, 13)] + [('Fortnight', 'Fortnight'), ('Weekly', 'Weekly'), ('Daily', 'Daily')], default="NOT SELECTED")
    payment_terms = models.CharField(max_length=200, default="100% Advance payment OR Whatever mutually Decided", editable=False)
    sales_person_name = models.CharField(max_length=100, null=True, blank=True)
    sales_person_contact_no = models.CharField(max_length=15, null=True, blank=True)
    delivery_time = models.TimeField(default=timezone.now)
    lead_date = models.DateField(default=timezone.now)
    service_date = models.DateField(null=True, blank=True)
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, default=None, null=True, blank=True)


    def __str__(self):
        selected_services = ', '.join([str(service) for service in self.selected_services.all()])
        return f'Service Management - {self.customer} ({selected_services})'

class WorkAllocation(models.Model):
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE)
    customer_fname = models.CharField(max_length=100,null=True, blank=True)
    customer_lname = models.CharField(max_length=100,null=True, blank=True)
    customer_contact = models.CharField(max_length=15) 
    customer_address = models.CharField(max_length=255)
    gps_location = models.URLField(null=True, blank=True)
    work_description = models.TextField()
    customer_payment_status = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Cash', 'Cash'), ('Pending', 'Pending')])
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    allocated_datetime = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('workdesk','workdesk'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')


    def __str__(self):
        return f"Work Allocation for {self.customer_fname} ({self.status})"

from django.utils.timezone import now
class Reschedule(models.Model):
    service = models.ForeignKey(service_management, on_delete=models.CASCADE, default=None, null=True, blank=True)
    old_service_date = models.DateField(default=now)
    old_delivery_time = models.TimeField(default=now)
    reason = models.TextField()

    def __str__(self):
        return f"Reschedule for Service ID {self.service.id}"   

class UploadedFile(models.Model):
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class TechWorkList(models.Model):
    technician = models.ForeignKey(User, on_delete=models.CASCADE)
    work = models.ForeignKey(WorkAllocation, on_delete=models.CASCADE)
    service = models.ForeignKey(service_management, on_delete=models.CASCADE, default=None, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Completed', 'Completed')], default='Pending')
    photos_before_service = models.ManyToManyField(UploadedFile, related_name='photos_before_service', blank=True)
    photos_after_service = models.ManyToManyField(UploadedFile, related_name='photos_after_service', blank=True)
    customer_signature_photo = models.ImageField(upload_to='photos/signatures/', blank=True, null=True)
    payment_photos = models.ManyToManyField(UploadedFile, related_name='payment_photos', blank=True)
    completion_datetime = models.DateTimeField(default=timezone.now)

    def _str_(self):
        return f"Work {self.work.id} by {self.technician.username}"
    

