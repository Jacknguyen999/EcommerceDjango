from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_orderitems_alter_orderitem_options'),
    ]

    operations = [
        migrations.RunSQL("""
            CREATE TABLE IF NOT EXISTS "CORE_ORDERITEM" (
                "ID" SERIAL PRIMARY KEY,
                "USER_ID" INTEGER NOT NULL,
                "ORDERED" BOOLEAN NOT NULL DEFAULT FALSE,
                "ITEM_ID" INTEGER NOT NULL,
                "QUANTITY" INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS "CORE_ORDER" (
                "ID" SERIAL PRIMARY KEY,
                "USER_ID" INTEGER NOT NULL,
                "REF_CODE" VARCHAR(20),
                "START_DATE" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                "ORDERED_DATE" TIMESTAMP WITH TIME ZONE,
                "ORDERED" BOOLEAN NOT NULL DEFAULT FALSE,
                "SHIPPING_ADDRESS_ID" INTEGER,
                "BILLING_ADDRESS_ID" INTEGER,
                "PAYMENT_ID" INTEGER,
                "COUPON_ID" INTEGER,
                "BEING_DELIVERED" BOOLEAN NOT NULL DEFAULT FALSE,
                "RECEIVED" BOOLEAN NOT NULL DEFAULT FALSE,
                "REFUND_REQUESTED" BOOLEAN NOT NULL DEFAULT FALSE,
                "REFUND_GRANTED" BOOLEAN NOT NULL DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS "CORE_ORDER_ITEMS" (
                "ID" SERIAL PRIMARY KEY,
                "ORDER_ID" INTEGER NOT NULL,
                "ORDERITEM_ID" INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS "CORE_PAYMENT" (
                "ID" SERIAL PRIMARY KEY,
                "STRIPE_CHARGE_ID" VARCHAR(50) NOT NULL,
                "USER_ID" INTEGER,
                "AMOUNT" FLOAT NOT NULL,
                "TIMESTAMP" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS "CORE_COUPON" (
                "ID" SERIAL PRIMARY KEY,
                "CODE" VARCHAR(15) NOT NULL,
                "AMOUNT" FLOAT NOT NULL
            );
        """, "DROP TABLE IF EXISTS CORE_ORDERITEM, CORE_ORDER, CORE_ORDER_ITEMS, CORE_PAYMENT, CORE_COUPON CASCADE;")
    ] 