from django.db.models.signals import post_save
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.shortcuts import reverse
from django_countries.fields import CountryField
from decimal import Decimal


CATEGORY_CHOICES = (
    ('S', 'Shirt'),
    ('SW', 'Sport wear'),
    ('OW', 'Outwear')
)

LABEL_CHOICES = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger')
)

ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    one_click_purchasing = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Item(models.Model):
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
    label = models.CharField(choices=LABEL_CHOICES, max_length=1)
    slug = models.SlugField()
    description = models.TextField()
    image = models.ImageField()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("core:add-to-cart", kwargs={
            'slug': self.slug
        })
    

    def get_remove_from_cart_url(self):
        return reverse("core:remove-from-cart", kwargs={
            'slug': self.slug
        })
    class Meta:
        app_label = 'core'
   
        


# class OrderItem(models.Model):
    # id = models.AutoField(primary_key=True, db_column='ID')
    # user = models.ForeignKey(
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.CASCADE,
    #     db_constraint=False,
    #     db_column='USER_ID'
    # )
    # ordered = models.BooleanField(
    #     default=False,
    #     db_column='ORDERED'
    # )
    # item = models.ForeignKey(
    #     Item,
    #     on_delete=models.CASCADE,
    #     db_constraint=False,
    #     db_column='ITEM_ID'
    # )
    # quantity = models.IntegerField(
    #     default=1,
    #     db_column='QUANTITY'
    # )

    # class Meta:
    #     db_table = 'CORE_ORDERITEM'
    #     managed = False

    # def __str__(self):
    #     return f"{self.quantity} of {self.item.title}"

    # def get_total_item_price(self):
    #     return self.quantity * self.item.price

    # def get_total_discount_item_price(self):
    #     return self.quantity * self.item.discount_price

    # def get_amount_saved(self):
    #     return self.get_total_item_price() - self.get_total_discount_item_price()

    # def get_final_price(self):
    #     if self.item.discount_price:
    #         return self.get_total_discount_item_price()
    #     return self.get_total_item_price()
  

class OrderItem(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_constraint=False,
        db_column='USER_ID'
    )
    ordered = models.BooleanField(default=False, db_column='ORDERED')
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        db_constraint=False,
        db_column='ITEM_ID'
    )
    quantity = models.IntegerField(default=1, db_column='QUANTITY')

    class Meta:
        managed = False
        db_table = 'CORE_ORDERITEM'

    def __str__(self):
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self):
        return Decimal(str(self.quantity)) * Decimal(str(self.item.price))

    def get_total_discount_item_price(self):
        return Decimal(str(self.quantity)) * Decimal(str(self.item.discount_price))

    def get_amount_saved(self):
        return self.get_total_item_price() - self.get_total_discount_item_price()

    def get_final_price(self):
        if self.item.discount_price:
            return float(self.get_total_discount_item_price())
        return float(self.get_total_item_price())


class OrderItems(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    order = models.ForeignKey(
        'Order', 
        on_delete=models.CASCADE,
        db_constraint=False,
        db_column='ORDER_ID'
    )
    orderitem = models.ForeignKey(
        'OrderItem',
        on_delete=models.CASCADE,
        db_constraint=False,
        db_column='ORDERITEM_ID'
    )

    class Meta:
        managed = False
        db_table = 'CORE_ORDER_ITEMS'


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_constraint=False,
        db_column='USER_ID'
    )
    ref_code = models.CharField(max_length=20, blank=True, null=True, db_column='REF_CODE')
    items = models.ManyToManyField(
        OrderItem,
        through=OrderItems,
        through_fields=('order', 'orderitem')
    )
    start_date = models.DateTimeField(auto_now_add=True, db_column='START_DATE')
    ordered_date = models.DateTimeField(db_column='ORDERED_DATE')
    ordered = models.BooleanField(default=False, db_column='ORDERED')
    shipping_address_id = models.IntegerField(null=True, db_column='SHIPPING_ADDRESS_ID')
    billing_address_id = models.IntegerField(null=True, db_column='BILLING_ADDRESS_ID')
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_constraint=False,
        db_column='PAYMENT_ID'
    )
    coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_constraint=False,
        db_column='COUPON_ID'
    )
    being_delivered = models.BooleanField(default=False, db_column='BEING_DELIVERED')
    received = models.BooleanField(default=False, db_column='RECEIVED')
    refund_requested = models.BooleanField(default=False, db_column='REFUND_REQUESTED')
    refund_granted = models.BooleanField(default=False, db_column='REFUND_GRANTED')

    class Meta:
        managed = False
        db_table = 'CORE_ORDER'

    def __str__(self):
        return self.user.username

    def get_total(self):
        total = Decimal('0.0')
        for order_item in self.items.all():
            total += Decimal(str(order_item.get_final_price()))
        if self.coupon:
            total -= Decimal(str(self.coupon.amount))
        return float(total)

    def shipping_address(self):
        if self.shipping_address_id:
            return Address.objects.get(id=self.shipping_address_id)
        return None

    def billing_address(self):
        if self.billing_address_id:
            return Address.objects.get(id=self.billing_address_id)
        return None


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100, blank=True, null=True)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Addresses'
        managed = True

    def __str__(self):
        return self.user.username


class Payment(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    stripe_charge_id = models.CharField(max_length=50, db_column='STRIPE_CHARGE_ID')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        db_column='USER_ID',
        db_constraint=False
    )
    amount = models.FloatField(db_column='AMOUNT')
    timestamp = models.DateTimeField(auto_now_add=True, db_column='TIMESTAMP')

    class Meta:
        managed = False
        db_table = 'CORE_PAYMENT'

    def __str__(self):
        return self.stripe_charge_id


class Coupon(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    code = models.CharField(max_length=15, db_column='CODE')
    amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='AMOUNT')

    class Meta:
        managed = False
        db_table = 'CORE_COUPON'

    def __str__(self):
        return self.code


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"


def userprofile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        userprofile = UserProfile.objects.create(user=instance)


post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)
