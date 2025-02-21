import random
import string
import logging
import traceback

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View
from django.shortcuts import render
from django.db.models import Q
from django.db import connections
from django.db import transaction
import cx_Oracle
from django.contrib.auth.models import User

from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile, OrderItems

stripe.api_key = settings.STRIPE_SECRET_KEY

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='checkout.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, request, *args, **kwargs):
        form = CheckoutForm(request.POST or None)
        try:
            # Log the raw POST data
            logger.debug(f"Raw POST data: {request.POST}")
            
            # Check if the form is bound
            logger.debug(f"Form is bound: {form.is_bound}")
            logger.debug(f"Form data: {form.data}")
            
            if not form.is_valid():
                logger.error(f"Form errors: {form.errors}")
                for field, errors in form.errors.items():
                    messages.error(request, f"{field}: {', '.join(errors)}")
                return redirect("core:checkout")
            
            # Log cleaned data
            logger.debug(f"Form cleaned data: {form.cleaned_data}")
            
            order = Order.objects.using('other_db').get(
                user=request.user, 
                ordered=False
            )

            # Get shipping data
            shipping_data = {
                'address': form.cleaned_data.get('shipping_address'),
                'country': form.cleaned_data.get('shipping_country'),
                'zip': form.cleaned_data.get('shipping_zip')
            }
            logger.debug(f"Shipping data: {shipping_data}")

            # Validate shipping data
            if not all(shipping_data.values()):
                missing = [k for k, v in shipping_data.items() if not v]
                logger.error(f"Missing shipping fields: {missing}")
                messages.error(request, f"Please fill in all required shipping fields: {', '.join(missing)}")
                return redirect("core:checkout")

            try:
                shipping_address_obj = Address.objects.create(
                    user=request.user,
                    street_address=shipping_data['address'],
                    apartment_address=form.cleaned_data.get('shipping_address2', ''),
                    country=shipping_data['country'],
                    zip=shipping_data['zip'],
                    address_type='S'
                )
                logger.debug(f"Created shipping address: {shipping_address_obj.id}")
            except Exception as e:
                logger.error(f"Error creating shipping address: {str(e)}")
                messages.error(request, f"Error creating shipping address: {str(e)}")
                return redirect("core:checkout")

            if form.cleaned_data.get('set_default_shipping'):
                shipping_address_obj.default = True
                shipping_address_obj.save()

            # Handle billing address
            same_billing_address = form.cleaned_data.get('same_billing_address')
            logger.debug(f"Same billing address: {same_billing_address}")

            if same_billing_address:
                try:
                    billing_address_obj = Address.objects.create(
                        user=request.user,
                        street_address=shipping_address_obj.street_address,
                        apartment_address=shipping_address_obj.apartment_address,
                        country=shipping_address_obj.country,
                        zip=shipping_address_obj.zip,
                        address_type='B'
                    )
                    logger.debug(f"Created billing address (same as shipping): {billing_address_obj.id}")
                except Exception as e:
                    logger.error(f"Error creating billing address: {str(e)}")
                    messages.error(request, f"Error creating billing address: {str(e)}")
                    return redirect("core:checkout")
            else:
                billing_data = {
                    'address': form.cleaned_data.get('billing_address'),
                    'country': form.cleaned_data.get('billing_country'),
                    'zip': form.cleaned_data.get('billing_zip')
                }
                logger.debug(f"Billing data: {billing_data}")

                if not all(billing_data.values()):
                    missing = [k for k, v in billing_data.items() if not v]
                    logger.error(f"Missing billing fields: {missing}")
                    messages.error(request, f"Please fill in all required billing fields: {', '.join(missing)}")
                    return redirect("core:checkout")

                try:
                    billing_address_obj = Address.objects.create(
                        user=request.user,
                        street_address=billing_data['address'],
                        apartment_address=form.cleaned_data.get('billing_address2', ''),
                        country=billing_data['country'],
                        zip=billing_data['zip'],
                        address_type='B'
                    )
                    logger.debug(f"Created billing address: {billing_address_obj.id}")
                except Exception as e:
                    logger.error(f"Error creating billing address: {str(e)}")
                    messages.error(request, f"Error creating billing address: {str(e)}")
                    return redirect("core:checkout")

            if form.cleaned_data.get('set_default_billing'):
                billing_address_obj.default = True
                billing_address_obj.save()

            # Update order
            try:
                with transaction.atomic():
                    with connections['other_db'].cursor() as cursor:
                        # Convert IDs to integers and use a simpler SQL query
                        shipping_id = int(shipping_address_obj.id)
                        billing_id = int(billing_address_obj.id)
                        order_id = int(order.id)
                        
                        cursor.execute("""
                            UPDATE CORE_ORDER 
                            SET SHIPPING_ADDRESS_ID = %s,
                                BILLING_ADDRESS_ID = %s
                            WHERE ID = %s
                            """, [shipping_id, billing_id, order_id])
                logger.debug(f"Order updated successfully with shipping_id={shipping_id}, billing_id={billing_id}, order_id={order_id}")
            except Exception as e:
                logger.error(f"Error updating order: {str(e)}")
                logger.error(f"shipping_id={shipping_address_obj.id}, billing_id={billing_address_obj.id}, order_id={order.id}")
                messages.error(request, f"Error updating order: {str(e)}")
                return redirect("core:checkout")

            # Handle payment
            payment_option = form.cleaned_data.get('payment_option')
            logger.debug(f"Payment option: {payment_option}")
            
            if payment_option == 'S':
                return redirect('core:payment', payment_option='stripe')
            elif payment_option == 'P':
                return redirect('core:payment', payment_option='paypal')
            else:
                logger.warning(f"Invalid payment option: {payment_option}")
                messages.warning(request, "Invalid payment option")
                return redirect('core:checkout')

        except ObjectDoesNotExist:
            logger.error("No active order found")
            messages.error(request, "You do not have an active order")
            return redirect("core:order-summary")
        except Exception as e:
            logger.error(f"General error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error location: {e.__traceback__.tb_lineno}")
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect("core:checkout")

        return redirect('core:checkout')


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.using('other_db').get(user=self.request.user, ordered=False)
        if order.billing_address_id:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
            }
            return render(self.request, "payment.html", context)
        else:
            messages.warning(self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        try:
            order = Order.objects.using('other_db').get(user=self.request.user, ordered=False)
            form = PaymentForm(self.request.POST)
            userprofile = UserProfile.objects.using('default').get(user=self.request.user)

            if form.is_valid():
                token = form.cleaned_data.get('stripeToken')
                save = form.cleaned_data.get('save')
                use_default = form.cleaned_data.get('use_default')

                if save:
                    if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                        customer = stripe.Customer.retrieve(userprofile.stripe_customer_id)
                        customer.sources.create(source=token)
                    else:
                        customer = stripe.Customer.create(
                            email=self.request.user.email,
                            source=token
                        )
                        userprofile.stripe_customer_id = customer.id
                        userprofile.save(using='default')

                amount = int(order.get_total() * 100)  # cents

                try:
                    charge = stripe.Charge.create(
                        amount=amount,
                        currency="usd",
                        customer=userprofile.stripe_customer_id if use_default else None,
                        source=token if not use_default else None
                    )

                    # Create the payment
                    payment = Payment.objects.using('other_db').create(
                        stripe_charge_id=charge.id,
                        user=self.request.user,
                        amount=order.get_total()
                    )

                    # Update the order
                    order_items = order.items.all()
                    order_items.update(ordered=True)
                    for item in order_items:
                        item.save(using='other_db')

                    order.ordered = True
                    order.payment = payment
                    order.ref_code = create_ref_code()
                    order.save(using='other_db')

                    messages.success(self.request, "Your order was successful!")
                    return redirect("/")

                except stripe.error.CardError as e:
                    messages.warning(self.request, f"{e.error.message}")
                    return redirect("/")
                except stripe.error.RateLimitError as e:
                    messages.warning(self.request, "Rate limit error")
                    return redirect("/")
                except stripe.error.InvalidRequestError as e:
                    messages.warning(self.request, "Invalid parameters")
                    return redirect("/")
                except stripe.error.AuthenticationError as e:
                    messages.warning(self.request, "Not authenticated")
                    return redirect("/")
                except stripe.error.APIConnectionError as e:
                    messages.warning(self.request, "Network error")
                    return redirect("/")
                except stripe.error.StripeError as e:
                    messages.warning(self.request, "Something went wrong. You were not charged. Please try again.")
                    return redirect("/")
                except Exception as e:
                    messages.warning(self.request, "A serious error occurred. We have been notified.")
                    logger.error(f"Payment error: {str(e)}")
                    return redirect("/")

        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")


# class HomeView(ListView):
#     model = Item
#     paginate_by = 10
#     template_name = "home.html"

class HomeView(ListView):
    model = Item
    template_name = 'home.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        category = self.kwargs.get('category')
        if query:
            return Item.objects.filter(
                Q(title__icontains=query) | Q(category__icontains=query)
            ).distinct()
        if category:
            return Item.objects.filter(category=category).distinct()
        return Item.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.kwargs.get('category')
        return context


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"


@login_required
def add_to_cart(request, slug):
    try:
        # Get item from MySQL database
        item = get_object_or_404(Item.objects.using('item_db'), slug=slug)
        logger.debug(f"Found item: {item}")
        
        # Get user from default database (SQLite)
        user = get_object_or_404(User.objects.using('default'), id=request.user.id)
        logger.debug(f"Found user: {user}")
        
        # Get or create order item in Oracle database
        order_item, created = OrderItem.objects.using('other_db').get_or_create(
            item_id=item.id,  # Use item_id instead of item
            user_id=user.id,  # Use user_id instead of user
            ordered=False,
            defaults={'quantity': 1}
        )
        logger.debug(f"OrderItem created: {created}")
        
        # Get order queryset from Oracle database
        order_qs = Order.objects.using('other_db').filter(
            user_id=user.id,  # Use user_id instead of user
            ordered=False
        )
        logger.debug(f"Found order: {order_qs.exists()}")
        
        if order_qs.exists():
            order = order_qs[0]
            # Check if the order item is in the order using the through model
            if OrderItems.objects.using('other_db').filter(
                order=order,
                orderitem__item_id=item.id
            ).exists():
                order_item.quantity += 1
                order_item.save(using='other_db')
                messages.info(request, "This item quantity was updated.")
            else:
                OrderItems.objects.using('other_db').create(
                    order=order,
                    orderitem=order_item
                )
                messages.info(request, "This item was added to your cart.")
        else:
            ordered_date = timezone.now()
            order = Order.objects.using('other_db').create(
                user_id=user.id,  # Use user_id instead of user
                ordered_date=ordered_date
            )
            OrderItems.objects.using('other_db').create(
                order=order,
                orderitem=order_item
            )
            messages.info(request, "This item was added to your cart.")
        
        return redirect("core:order-summary")
    except Exception as e:
        logger.error(f"Error in add_to_cart: {str(e)}")
        # Print the SQL query that caused the error
        from django.db import connection
        logger.error(f"Last query: {connection.queries[-1] if connection.queries else 'No queries'}")
        raise


# @login_required
# def remove_from_cart(request, slug):
#     item = get_object_or_404(Item, slug=slug)
#     order_qs = Order.objects.using('other_db').filter(
#         user=request.user,
#         ordered=False
#     )
#     if order_qs.exists():
#         order = order_qs[0]
#         # check if the order item is in the order
#         with connections['other_db'].cursor() as cursor:
#             # Check if OrderItem exists
#             cursor.execute("""
#                 SELECT oi.ID 
#                 FROM CORE_ORDERITEM oi
#                 INNER JOIN CORE_ORDER_ITEMS coi ON oi.ID = coi.ORDERITEM_ID
#                 WHERE coi.ORDER_ID = :1 
#                 AND oi.ITEM_ID = :2
#                 AND oi.ORDERED = 0
#             """, [order.id, item.id])
            
#             order_item = cursor.fetchone()
            
#             if order_item:
#                 order_item_id = order_item[0]
#                 # First remove from CORE_ORDER_ITEMS
#                 cursor.execute("""
#                     DELETE FROM CORE_ORDER_ITEMS 
#                     WHERE ORDER_ID = :1 AND ORDERITEM_ID = :2
#                 """, [order.id, order_item_id])
                
#                 # Then delete the OrderItem
#                 cursor.execute("""
#                     DELETE FROM CORE_ORDERITEM 
#                     WHERE ID = :1
#                 """, [order_item_id])
                
#                 messages.info(request, "This item was removed from your cart.")
#                 return redirect("core:order-summary")
#             else:
#                 messages.info(request, "This item was not in your cart")
#                 return redirect("core:product", slug=slug)
#     else:
#         messages.info(request, "You do not have an active order")
#         return redirect("core:product", slug=slug)

@login_required
def remove_from_cart(request, slug):
    try:
        # Get item from MySQL database using slug instead of category
        item = get_object_or_404(Item.objects.using('item_db'), slug=slug)
        
        # Get Order from Oracle database
        order_qs = Order.objects.using('other_db').filter(
            user=request.user,
            ordered=False
        )
        
        if order_qs.exists():
            order = order_qs[0]
            
            # Check if the order item exists using raw SQL
            with connections['other_db'].cursor() as cursor:
                cursor.execute("""
                    SELECT oi.ID 
                    FROM CORE_ORDERITEM oi
                    INNER JOIN CORE_ORDER_ITEMS coi ON oi.ID = coi.ORDERITEM_ID
                    WHERE coi.ORDER_ID = %s 
                    AND oi.ITEM_ID = %s
                    AND oi.ORDERED = 0
                """, [order.id, item.id])
                
                order_item = cursor.fetchone()
                
                if order_item:
                    order_item_id = order_item[0]
                    
                    # First remove from CORE_ORDER_ITEMS
                    cursor.execute("""
                        DELETE FROM CORE_ORDER_ITEMS 
                        WHERE ORDER_ID = %s AND ORDERITEM_ID = %s
                    """, [order.id, order_item_id])
                    
                    # Then delete the OrderItem
                    cursor.execute("""
                        DELETE FROM CORE_ORDERITEM 
                        WHERE ID = %s
                    """, [order_item_id])
                    
                    messages.info(request, "Item removed from your cart.")
                    return redirect("core:order-summary")
                else:
                    messages.warning(request, "This item was not in your cart")
                    return redirect("core:home")
        else:
            messages.warning(request, "You do not have an active order")
            return redirect("core:home")
            
    except Exception as e:
        messages.error(request, f"Error removing item: {str(e)}")
        return redirect("core:home")


@login_required
def remove_single_item_from_cart(request, slug):
    # Get item from MySQL database
    item = get_object_or_404(Item.objects.using('item_db'), slug=slug)
    
    # Get Order from Oracle database
    order_qs = Order.objects.using('other_db').filter(
        user=request.user, 
        ordered=False
    )
    
    if order_qs.exists():
        order = order_qs[0]
        
        # Use raw SQL to check if item exists in order
        with connections['other_db'].cursor() as cursor:
            cursor.execute("""
                SELECT oitem.ID, oitem.QUANTITY 
                FROM CORE_ORDER_ITEMS oi
                JOIN CORE_ORDERITEM oitem ON oi.ORDERITEM_ID = oitem.ID
                WHERE oi.ORDER_ID = %s 
                AND oitem.ITEM_ID = %s
                AND oitem.ORDERED = 0
                """, [order.id, item.id])
            result = cursor.fetchone()
            
        if result:
            order_item_id, quantity = result
            if quantity > 1:
                # Update quantity
                with connections['other_db'].cursor() as cursor:
                    cursor.execute("""
                        UPDATE CORE_ORDERITEM 
                        SET QUANTITY = QUANTITY - 1 
                        WHERE ID = %s
                        """, [order_item_id])
                messages.info(request, "This item quantity was updated.")
            else:
                # Remove the order-item relationship and the order item
                with connections['other_db'].cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM CORE_ORDER_ITEMS 
                        WHERE ORDER_ID = %s AND ORDERITEM_ID = %s
                        """, [order.id, order_item_id])
                    cursor.execute("""
                        DELETE FROM CORE_ORDERITEM 
                        WHERE ID = %s
                        """, [order_item_id])
                messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart.")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.using('other_db').get(
                    user=self.request.user, 
                    ordered=False
                )
                try:
                    coupon = Coupon.objects.using('other_db').get(code=code)
                    order.coupon = coupon
                    order.save(using='other_db')
                    messages.success(self.request, "Successfully added coupon")
                    return redirect("core:checkout")
                except Coupon.DoesNotExist:
                    messages.warning(self.request, "This coupon does not exist")
                    return redirect("core:checkout")
            except Order.DoesNotExist:
                messages.warning(self.request, "You do not have an active order")
                return redirect("core:checkout")
        # if the form is not valid
        messages.warning(self.request, "Invalid coupon code")
        return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")
