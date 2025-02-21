# Generated by Django 5.1.5 on 2025-02-21 12:40

import django.db.models.deletion
import django_countries.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "ref_code",
                    models.CharField(
                        blank=True, db_column="REF_CODE", max_length=20, null=True
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(auto_now_add=True, db_column="START_DATE"),
                ),
                ("ordered_date", models.DateTimeField(db_column="ORDERED_DATE")),
                ("ordered", models.BooleanField(db_column="ORDERED", default=False)),
                (
                    "shipping_address_id",
                    models.IntegerField(db_column="SHIPPING_ADDRESS_ID", null=True),
                ),
                (
                    "billing_address_id",
                    models.IntegerField(db_column="BILLING_ADDRESS_ID", null=True),
                ),
                (
                    "being_delivered",
                    models.BooleanField(db_column="BEING_DELIVERED", default=False),
                ),
                ("received", models.BooleanField(db_column="RECEIVED", default=False)),
                (
                    "refund_requested",
                    models.BooleanField(db_column="REFUND_REQUESTED", default=False),
                ),
                (
                    "refund_granted",
                    models.BooleanField(db_column="REFUND_GRANTED", default=False),
                ),
            ],
            options={
                "db_table": "CORE_ORDER",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.AutoField(db_column="ID", primary_key=True, serialize=False),
                ),
                (
                    "stripe_charge_id",
                    models.CharField(db_column="STRIPE_CHARGE_ID", max_length=50),
                ),
                ("amount", models.FloatField(db_column="AMOUNT")),
                (
                    "timestamp",
                    models.DateTimeField(auto_now_add=True, db_column="TIMESTAMP"),
                ),
            ],
            options={
                "db_table": "CORE_PAYMENT",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Coupon",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.CharField(max_length=15)),
                ("amount", models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=100)),
                ("price", models.FloatField()),
                ("discount_price", models.FloatField(blank=True, null=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("S", "Shirt"),
                            ("SW", "Sport wear"),
                            ("OW", "Outwear"),
                        ],
                        max_length=2,
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        choices=[("P", "primary"), ("S", "secondary"), ("D", "danger")],
                        max_length=1,
                    ),
                ),
                ("slug", models.SlugField()),
                ("description", models.TextField()),
                ("image", models.ImageField(upload_to="")),
            ],
        ),
        migrations.CreateModel(
            name="Address",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("street_address", models.CharField(max_length=100)),
                (
                    "apartment_address",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("country", django_countries.fields.CountryField(max_length=2)),
                ("zip", models.CharField(max_length=100)),
                (
                    "address_type",
                    models.CharField(
                        choices=[("B", "Billing"), ("S", "Shipping")], max_length=1
                    ),
                ),
                ("default", models.BooleanField(default=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Addresses",
                "managed": True,
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ordered", models.BooleanField(default=False)),
                ("quantity", models.IntegerField(default=1)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.item"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "CORE_ORDERITEM",
            },
        ),
        migrations.CreateModel(
            name="Refund",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("reason", models.TextField()),
                ("accepted", models.BooleanField(default=False)),
                ("email", models.EmailField(max_length=254)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.order"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "stripe_customer_id",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("one_click_purchasing", models.BooleanField(default=False)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
